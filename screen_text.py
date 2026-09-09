"""Распознавание текста на кадрах видео через Vision (macOS)."""
import re
import subprocess
from difflib import SequenceMatcher
from pathlib import Path

from i18n import tf

SCENE = 0.25             # порог смены сцены
EVERY = 3.0              # плюс кадр раз в N секунд: на статичном фоне смен нет
HEIGHT, MAX_FRAMES = 720, 60
MIN_CONFIDENCE = 0.4
SAME_RATIO = 0.86        # выше — одна надпись, прочитанная по-разному


def _grab_frames(video, outdir, ffmpeg, log=lambda m: None):
    outdir.mkdir(parents=True, exist_ok=True)
    vf = (f"select='gt(scene,{SCENE})+isnan(prev_selected_t)"
          f"+gte(t-prev_selected_t,{EVERY})',scale=-2:{HEIGHT}")
    # fps_mode, а не vsync: в ffmpeg 8 старое имя убрали, и отбор молча давал ноль.
    r = subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(video),
                        "-vf", vf, "-fps_mode", "vfr", "-frames:v", str(MAX_FRAMES),
                        "-q:v", "3", str(outdir / "f_%04d.jpg")],
                       capture_output=True, text=True)
    frames = sorted(outdir.glob("f_*.jpg"))
    if not frames and r.returncode:
        log(tf("  кадры извлечь не удалось: {e}", e=(r.stderr or "").strip()[-200:]))
        return frames
    log(tf("  кадров отобрано: {n}", n=len(frames)))
    return frames


def _image(path):
    import Quartz
    from Foundation import NSURL
    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(str(path)), None)
    return Quartz.CGImageSourceCreateImageAtIndex(src, 0, None) if src else None


def _read(path):
    """Строки текста с кадра как (текст, уверенность)."""
    import Vision
    img = _image(path)
    if img is None:
        return []
    req = Vision.VNRecognizeTextRequest.alloc().init()
    # Fast калечит кириллицу: «KaK A noxyAen» вместо «Как я похудел».
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setRecognitionLanguages_(["ru-RU", "en-US"])
    req.setUsesLanguageCorrection_(True)
    Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
        img, None).performRequests_error_([req], None)
    out = []
    for obs in (req.results() or []):
        cand = obs.topCandidates_(1)
        if cand and cand[0].confidence() >= MIN_CONFIDENCE:
            out.append((" ".join(cand[0].string().split()),
                        float(cand[0].confidence())))
    return _join_hyphens(out)


def _labels(path, limit=6, floor=0.25):
    """Метки классификатора: outdoor, people, videogame."""
    import Vision
    img = _image(path)
    if img is None:
        return []
    req = Vision.VNClassifyImageRequest.alloc().init()
    Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
        img, None).performRequests_error_([req], None)
    got = sorted(((o.identifier(), float(o.confidence()))
                  for o in (req.results() or [])), key=lambda x: -x[1])
    return [n for n, c in got[:limit] if c >= floor]


def _join_hyphens(items):
    """Склеить слово, разорванное переносом: «ста-» + «новится»."""
    out = []
    for text, conf in items:
        if out and re.search(r"[А-Яа-яЁёA-Za-z]-$", out[-1][0]):
            prev, pconf = out[-1]
            out[-1] = (prev[:-1] + text.lstrip(), min(pconf, conf))
        else:
            out.append((text, conf))
    return out


def _norm(s):
    return re.sub(r"[^\w]+", "", s.lower())


def _same(a, b):
    """Совпадение с поправкой на путаницу букв: «залястья» ~ «запястья»."""
    if abs(len(a) - len(b)) > max(4, len(a) * 0.25):
        return False
    return SequenceMatcher(None, a, b).ratio() >= SAME_RATIO


def read_video(video, workdir, ffmpeg, log=lambda m: None):
    """Надписи с кадров; из повторов берётся самое уверенное прочтение."""
    frames = _grab_frames(Path(video), Path(workdir) / "frames", ffmpeg, log=log)
    groups = []                                   # (ключ, текст, уверенность)
    for f in frames:
        for text, conf in _read(f):
            key = _norm(text)
            if len(key) < 3:
                continue
            for i, (k, _, c) in enumerate(groups):
                if _same(key, k):
                    if conf > c:
                        groups[i] = (key, text, conf)
                    break
            else:
                groups.append((key, text, conf))
    lines = [text for _, text, _ in groups]
    log(tf("  надписей на экране: {n}", n=len(lines)))
    return lines


def describe_video(video, workdir, ffmpeg, log=lambda m: None):
    """Метки происходящего по нескольким кадрам."""
    frames = _grab_frames(Path(video), Path(workdir) / "frames", ffmpeg, log=log)
    seen = []
    for f in frames[:12]:
        for name in _labels(f):
            if name not in seen:
                seen.append(name)
    log(tf("  что видно на кадрах: {n} признаков", n=len(seen)))
    return seen[:20]
