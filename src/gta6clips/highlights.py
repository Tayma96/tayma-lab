"""Uzun yayınlarda (VOD) öne çıkan anları ses yüksekliği sıçramalarından bulur:
bağırma, gülme ve patlamalar genelde ses seviyesinde ani bir zirve yapar."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)
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


# --- Yapay zeka ile viral puanlama -------------------------------------------------------------
# Ölçütler AI-Youtube-Shorts-Generator'ın (MIT) "virality criteria" çerçevesinden uyarlandı;
# podcast yerine oyun yayını anlarına göre yeniden yazıldı.

VIRALITY_SYSTEM = """You are an elite short-form editor who cuts viral GTA 6 stream clips for TikTok and
YouTube Shorts. You get candidate moments from a stream (found by audio spikes) with their transcript.
Score each candidate 0-100 on viral potential, not general quality.

Signals, ranked by impact:
1. RAW REACTIONS: genuine screaming, laughing, shock, rage; the streamer losing it
2. CHAOS PAYOFF: a crash, explosion, police chase, or plan going spectacularly wrong
3. FIRST-TIME DISCOVERY: the streamer seeing a new GTA 6 feature, place, or easter egg
4. FUNNY ONE-LINERS: a line that works as a standalone quote
5. SKILL MOMENTS: an impossible escape, stunt, or clutch play
6. CHAT/FRIEND INTERACTION: a roast, argument, or callback that lands

Low scores: silence, menus, loading screens, reading donations, repetitive driving, unclear context.
A candidate needs a hook in its first 3 seconds and must make sense without the rest of the stream."""


def rank_with_ai(candidates: list[dict], cfg: dict) -> list[dict]:
    """candidates: [{"index", "start", "end", "transcript"}] -> her birine viral_score/hook/reason ekler.
    Yapay zeka yoksa/sınır dolduysa ses puanı sırasıyla döner (ücretsiz)."""
    from pydantic import BaseModel

    from . import llm

    if not candidates:
        return candidates

    class Rated(BaseModel):
        index: int
        score: int
        hook: str
        reason: str

    class Ratings(BaseModel):
        ratings: list[Rated]

    listing = "\n\n".join(f"[{c['index']}] {c['start']}s-{c['end']}s\n{c['transcript'] or '(no speech)'}"
                          for c in candidates)
    res = llm.structured(cfg, VIRALITY_SYSTEM, f"Candidates:\n\n{listing}\n\nRate every candidate.", Ratings,
                         effort="medium")
    if res is None:
        return candidates
    by_idx = {r.index: r for r in res.ratings}
    out = []
    for c in candidates:
        r = by_idx.get(c["index"])
        out.append({**c, "viral_score": r.score if r else 0, "hook": r.hook if r else "",
                    "reason": r.reason if r else ""})
    return sorted(out, key=lambda c: c["viral_score"], reverse=True)


def cut_audio(audio: Path, start: float, end: float, out: Path) -> Path:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start}", "-to", f"{end}", "-i", str(audio),
                    "-ac", "1", "-ar", "16000", str(out)], check=True)
    return out
