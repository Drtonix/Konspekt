"""Каталог моделей: наличие, размер на диске, скачивание и удаление.

Веса лежат в общем кэше Hugging Face, а не в бандле: они большие и переживают
обновление приложения.
"""
import os
import shutil
from pathlib import Path
from i18n import t

CACHE = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"

# role — ключ перевода, а не готовый текст: язык переключается на лету.
CATALOG = [
    {"kind": "llm", "repo": "mlx-community/Qwen3-8B-4bit",
     "role": "Языковая модель", "gb": 4.5},
    {"kind": "llm", "repo": "mlx-community/Qwen3-30B-A3B-4bit",
     "role": "Языковая модель", "gb": 16.0},
    {"kind": "asr", "repo": "mlx-community/whisper-large-v3-turbo",
     "role": "Распознавание речи", "gb": 1.5},
]


def short_name(repo):
    return repo.split("/")[-1]

DEFAULT_LLM = "mlx-community/Qwen3-8B-4bit"


def active_llm(preferred=None):
    """Выбранная модель, если она на месте, иначе любая скачанная."""
    llms = [m for m in CATALOG if m["kind"] == "llm"]
    if preferred and any(m["repo"] == preferred and is_ready(preferred, m["gb"])
                         for m in llms):
        return preferred
    for m in llms:
        if is_ready(m["repo"], m["gb"]):
            return m["repo"]
    return preferred or DEFAULT_LLM


def _dir_for(repo):
    return CACHE / ("models--" + repo.replace("/", "--"))


def size_on_disk(repo):
    """Байты в blobs: snapshot — это ссылки на них."""
    d = _dir_for(repo) / "blobs"
    if not d.exists():
        return 0
    total = 0
    for f in d.iterdir():
        try:
            total += f.stat().st_size
        except OSError:
            pass
    return total


def is_ready(repo, gb):
    """Точного размера заранее нет: считаем готовой от 75% ожидаемого."""
    return size_on_disk(repo) >= gb * 1024 ** 3 * 0.75


def human(n):
    if n <= 0:
        return "—"
    for unit in (t("Б"), t("КБ"), t("МБ"), t("ГБ")):
        if n < 1024 or unit == t("ГБ"):
            return f"{n:.1f} {unit}".replace(".0 ", " ")
        n /= 1024


def delete(repo):
    shutil.rmtree(_dir_for(repo), ignore_errors=True)


GRAB = ("import sys\n"
        "from huggingface_hub import snapshot_download\n"
        "snapshot_download(repo_id=sys.argv[1])\n")


def download(repo, on_progress=lambda done, total: None, should_stop=lambda: False):
    """Скачивание отдельным процессом; ход считается по размеру на диске.

    Процессом, а не потоком: остановку huggingface_hub не умеет, поток
    продолжал качать и после отмены. Процесс снимается целиком.
    """
    import subprocess, sys, tempfile

    env = {**os.environ, "HF_HUB_DISABLE_PROGRESS_BARS": "1"}
    log = tempfile.TemporaryFile()      # не канал: он забьётся и всё встанет
    proc = subprocess.Popen([sys.executable, "-c", GRAB, repo],
                            stdout=log, stderr=log, env=env)
    expected = next((m["gb"] for m in CATALOG if m["repo"] == repo), 1.0) * 1024 ** 3
    while proc.poll() is None:
        if should_stop():
            proc.terminate()
            return False        # недокачанное докачается при следующем запуске
        on_progress(size_on_disk(repo), expected)
        try:
            proc.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
    if proc.returncode:
        log.seek(0)
        lines = [x.strip() for x in
                 log.read().decode("utf-8", "replace").splitlines() if x.strip()]
        # Последняя строка трассировки бывает подсказкой про пароль; берём саму ошибку.
        why = next((x for x in reversed(lines) if "Error" in x), lines[-1] if lines else "")
        raise RuntimeError(why[:300] or "скачивание не удалось")
    on_progress(size_on_disk(repo), expected)
    return True
