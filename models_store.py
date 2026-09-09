"""Каталог моделей: наличие, размер на диске, скачивание и удаление.

Веса лежат в общем кэше Hugging Face, а не в бандле: они большие и переживают
обновление приложения.
"""
import os
from pathlib import Path
from i18n import t

CACHE = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"

# role — ключ перевода, а не готовый текст: язык переключается на лету.
CATALOG = [
    {"kind": "llm", "repo": "mlx-community/Qwen3.5-9B-4bit",
     "role": "Языковая модель", "gb": 5.6},
    {"kind": "llm", "repo": "mlx-community/Qwen3.6-35B-A3B-4bit",
     "role": "Языковая модель", "gb": 19.0},
    {"kind": "asr", "repo": "mlx-community/whisper-large-v3-mlx",
     "role": "Распознавание речи", "gb": 2.9},
]


def short_name(repo):
    return repo.split("/")[-1]

DEFAULT_LLM = "mlx-community/Qwen3.5-9B-4bit"


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


def human(n):
    if n <= 0:
        return "—"
    for unit in (t("Б"), t("КБ"), t("МБ"), t("ГБ")):
        if n < 1024 or unit == t("ГБ"):
            return f"{n:.1f} {unit}".replace(".0 ", " ")
        n /= 1024


GRAB = ("import sys\n"
        "from huggingface_hub import snapshot_download\n"
        "snapshot_download(repo_id=sys.argv[1])\n")


# Общее хранилище моделей всех приложений (models_home): папка на выбор,
# одна очередь загрузок на все приложения, загрузчик докачивает с места и при
# закрытом окне. Определения ниже заменяют прежние с теми же именами.
import time as _time  # noqa: E402

import models_home as home  # noqa: E402


def size_on_disk(repo):
    p = home.resolve(repo)
    if p is None:
        return home.on_disk(repo)
    if home.shared(repo):
        return home._size(home.cache_dir(repo) / "blobs")
    return home._size(p)


def size_ready(repo):
    return size_on_disk(repo) if home.resolve(repo) is not None else 0


def is_ready(repo, gb=None):
    return home.resolve(repo) is not None


def delete(repo):
    home.remove(repo)


def download(repo, on_progress=lambda done, total: None, should_stop=lambda: False, where=None):
    """В общую очередь; where — своя папка для этой модели, иначе папка по
    умолчанию. Ход — из файла хода загрузчика."""
    expected = next((m["gb"] for m in CATALOG if m["repo"] == repo), 1.0) * 1024 ** 3
    home.enqueue(repo, where)
    while True:
        st = home.state(repo)
        if st == "ready":
            on_progress(expected, expected)
            return True
        if should_stop():
            home.cancel(repo)
            return False
        if st not in ("queued", "downloading"):
            err = home.status().get("errors", {}).get(repo)
            raise RuntimeError(err or "скачивание не удалось")
        p = home.progress(repo)
        if p:
            on_progress(int(p[0] * expected), expected)
        _time.sleep(0.5)
