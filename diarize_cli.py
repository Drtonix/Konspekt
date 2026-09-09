"""Разделение голосов. Отдельный процесс: библиотека держит GIL и морозит окно.

Кластеризация своя, не sherpa-onnx: её штатный порог склеивал разных людей
в один голос, а одного диктора дробил надвое.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAD_MODEL = HERE / "models/silero_vad.onnx"
EMB_MODEL = HERE / "models/nemo_en_titanet_large.onnx"

WIN, HOP, MIN_WIN = 4.0, 3.0, 1.2   # окно, шаг, минимальный кусок речи, секунды
SILENCE = 0.004
MAX_VOICES = 10
MAX_WINDOWS = 3000                  # матрица похожести квадратична по числу окон
VAD_THRESHOLD = 0.65                # при 0.5 в речь просачивается фоновый шум


def _speech_regions(audio, sr):
    """Границы речи. Silero вместо сегментации pyannote: та же точность, в 7 раз быстрее."""
    import sherpa_onnx
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = str(VAD_MODEL)
    cfg.silero_vad.threshold = VAD_THRESHOLD
    cfg.silero_vad.min_silence_duration = 0.4
    cfg.silero_vad.min_speech_duration = 0.3
    cfg.sample_rate = sr
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)
    out, step = [], 512

    def drain():
        while not vad.empty():
            s = vad.front
            out.append((s.start / sr, (s.start + len(s.samples)) / sr))
            vad.pop()

    for i in range(0, len(audio) - step, step):
        vad.accept_waveform(audio[i:i + step])
        drain()
    vad.flush()
    drain()
    return out


def _windows(audio, sr, regions, extractor):
    """Отпечаток голоса на каждое окно. Отрезок целиком брать нельзя: в него влезают двое."""
    import numpy as np
    out = []
    for start, end in regions:
        t = start
        while t + MIN_WIN <= end:
            b = min(t + WIN, end)
            piece = audio[int(t * sr):int(b * sr)]
            if float(np.abs(piece).mean()) > SILENCE:
                s = extractor.create_stream()
                s.accept_waveform(sample_rate=sr, waveform=piece)
                s.input_finished()
                v = np.asarray(extractor.compute(s), dtype="float32")
                out.append((t, b, v / (float(np.linalg.norm(v)) + 1e-9)))
            t += HOP
    return out


def _silhouette(dist, lab, k):
    """Чёткость разделения: +1 — идеально, 0 — никак. Матрично: цикл слишком медленный."""
    import numpy as np
    n = len(lab)
    onehot = np.zeros((n, k), dtype="float32")
    onehot[np.arange(n), lab] = 1.0
    cnt = onehot.sum(0)
    if (cnt < 2).any():
        return -1.0
    tot = dist @ onehot
    own = np.arange(n), lab
    a = tot[own] / (cnt[lab] - 1)
    other = tot / cnt
    other[own] = np.inf
    b = other.min(1)
    return float(np.mean((b - a) / np.maximum(a, b)))


def _cluster(vecs, num_speakers=0):
    """Спектральная кластеризация окон.

    Агломеративная на живой записи слипается в один ком: 2949 секунд из 3541
    в одном кластере. Число голосов — по силуэту; разрыв в спектре занижал его.
    """
    import numpy as np
    from scipy.cluster.vq import kmeans2
    from scipy.linalg import eigh

    X = np.stack([v for _, _, v in vecs])
    idx = np.arange(len(X))
    if len(X) > MAX_WINDOWS:
        idx = np.linspace(0, len(X) - 1, MAX_WINDOWS).astype(int)
    Xs = X[idx]

    A = np.clip(Xs @ Xs.T, 0, None)
    np.fill_diagonal(A, 0.0)
    deg = A.sum(1) + 1e-9
    L = np.eye(len(A)) - A / np.sqrt(np.outer(deg, deg))
    top = min(MAX_VOICES, len(A) - 1)
    _, v = eigh(L, subset_by_index=[0, top])

    def partition(k):
        E = v[:, :k]
        E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
        return kmeans2(E, k, minit="++", seed=0, missing="warn")[1]

    if num_speakers:
        part = partition(max(2, min(num_speakers, top)))
    else:
        dist = 1.0 - Xs @ Xs.T
        scored = []
        for k in range(2, top + 1):
            lab = partition(k)
            scored.append((_silhouette(dist, lab, k), lab))
        if not scored:
            return np.zeros(len(X), dtype=int)
        # При почти равном силуэте берём меньшее k: лишний кластер — это
        # разрезанный надвое человек, заметнее чем недобор.
        best = max(s for s, _ in scored)
        part = next(lab for s, lab in scored if s >= best * 0.95)
    k = int(part.max()) + 1

    cents = []                                   # центры по подвыборке
    for l in range(k):
        m = Xs[part == l]
        if len(m):
            c = m.mean(0)
            cents.append(c / (np.linalg.norm(c) + 1e-9))
    if not cents:
        return np.zeros(len(X), dtype=int)
    return np.argmax(X @ np.stack(cents).T, axis=1)


def _to_segments(vecs, labels):
    """Соседние окна одного голоса — в отрезок; на стыке граница по середине нахлёста."""
    segs = []
    for (start, end, _), lab in zip(vecs, labels):
        lab = int(lab)
        if segs and segs[-1]["speaker"] == lab and start <= segs[-1]["end"] + 0.4:
            segs[-1]["end"] = max(segs[-1]["end"], end)
            continue
        if segs and start < segs[-1]["end"]:
            mid = (start + segs[-1]["end"]) / 2
            segs[-1]["end"] = mid
            start = mid
        segs.append({"start": start, "end": end, "speaker": lab})
    return segs


def main(wav, num_speakers=0):
    import sherpa_onnx, soundfile as sf

    audio, sr = sf.read(wav, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    empty = {"segments": [], "voices": 0, "windows": 0}
    regions = _speech_regions(audio, sr)
    if not regions:
        return json.dump(empty, sys.stdout)

    ex = sherpa_onnx.SpeakerEmbeddingExtractor(
        sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(EMB_MODEL),
                                                    num_threads=8))
    vecs = _windows(audio, sr, regions, ex)
    if not vecs:
        return json.dump(empty, sys.stdout)
    labels = _cluster(vecs, num_speakers)
    json.dump({"segments": _to_segments(vecs, labels),
               "voices": len(set(int(x) for x in labels)),
               "windows": len(vecs)}, sys.stdout)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0)
