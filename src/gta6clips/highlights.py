"""Uzun yayınlarda (VOD) öne çıkan anları ses yüksekliği sıçramalarından bulur:
bağırma, gülme ve patlamalar genelde ses seviyesinde ani bir zirve yapar."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

RATE = 8000


def loudness_per_second(audio: Path) -> np.ndarray:
    proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", str(audio), "-ac", "1", "-ar", str(RATE),
                             "-f", "s16le", "-"], stdout=subprocess.PIPE)
    out = []
    assert proc.stdout
    while chunk := proc.stdout.read(RATE * 2 * 60):  # 60 saniyelik parçalar
        s = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
        n = len(s) // RATE
        if n:
            sec = s[: n * RATE].reshape(n, RATE)
            out.append(20 * np.log10(np.sqrt((sec ** 2).mean(axis=1)) + 1.0))
    proc.wait()
    return np.concatenate(out) if out else np.zeros(0)


def pick_windows(loud: np.ndarray, *, length: int = 30, top_k: int = 5, pre_roll: int = 18,
                 baseline: int = 120) -> list[tuple[int, int, float]]:
    """Saf fonksiyon. Kendi çevresine göre en çok sıçrayan saniyeleri bulur ve birbiriyle çakışmayan
    (start, end, skor) pencereleri döner. Zirve pencerenin sonlarına denk gelir ki öncesindeki
    kurgu da görülsün."""
    n = len(loud)
    if n < length:
        return []
    kernel = np.ones(baseline) / baseline
    local = np.convolve(np.pad(loud, baseline // 2, mode="edge"), kernel, mode="same")[baseline // 2: baseline // 2 + n]
    spike = loud - local
    order = np.argsort(spike)[::-1]
    chosen: list[tuple[int, int, float]] = []
    for peak in order:
        if len(chosen) >= top_k or spike[peak] <= 0:
            break
        start = int(min(max(0, peak - pre_roll), n - length))
        end = start + length
        if any(not (end <= s or start >= e) for s, e, _ in chosen):
            continue
        chosen.append((start, end, float(spike[peak])))
    return sorted(chosen)
