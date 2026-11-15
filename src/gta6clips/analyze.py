"""Klip analizi: kalite puanı (1-10), GTA 6 kontrolü, en iyi bölüm (kırpma) ve başlık/kanca/hashtag.

Önce config'teki yapay zeka sağlayıcısı denenir (varsayılan: ücretsiz yerel Ollama).
Ulaşılamazsa ya da ai.provider=none ise tamamen ÜCRETSİZ sezgisel analiz yapılır:
  - popülerlik  : izlenme hızı ya da canlı sohbet patlamasının gücü
  - ses         : klibin içindeki ses zirvesi (bağırma/gülme/patlama)
  - hareket     : kareler arası değişim (menü, yükleme ekranı, AFK anlarını eler)
  - konuşma     : saniye başına kelime
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
import subprocess
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field

from . import llm, metadata
from .highlights import VIRALITY_SYSTEM, loudness_per_second, pick_windows
from .transcribe import Word

log = logging.getLogger(__name__)

SYSTEM = VIRALITY_SYSTEM + """

You now review ONE clip. You see evenly spaced frames (timestamps listed in the text) and a timestamped transcript.
Return:
- score 1-10: 9-10 = would go viral, 7-8 = strong, 5-6 = ok filler, 1-4 = do not post.
  Be strict: most clips are 4-7. Silence, menus, loading screens, unclear context, or nothing happening score low.
- is_gta6: true only if the footage is clearly Grand Theft Auto VI gameplay (not GTA V, not another game,
  not just a facecam or a menu).
- category: one of reaction, chaos, discovery, funny, skill, interaction, other.
- best_start / best_end (seconds): the tightest section that still has the full setup and payoff, ideally 12-45s.
  Start 1-3 seconds before the setup so the hook lands immediately. If the whole clip is good, use 0 and its end.
- reason: one sentence on why it works or why not.

Then write the metadata for the section you selected:
""" + metadata.RULES


class ClipAnalysis(BaseModel):
    score: int = Field(ge=1, le=10)
    is_gta6: bool
    category: str
    reason: str
    best_start: float
    best_end: float
    title: str
    hook: str
    description: str
    hashtags: list[str]


# ------------------------------------------------------------------ yardımcılar
def extract_frames(video: Path, duration: float, n: int = 6, width: int = 640) -> list[tuple[float, bytes]]:
    frames = []
    for i in range(n):
        t = duration * (i + 0.5) / n
        res = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                              "-vf", f"scale={width}:-2", "-f", "image2pipe", "-c:v", "mjpeg", "-q:v", "4", "-"],
                             capture_output=True)
        if res.returncode == 0 and res.stdout:
            frames.append((t, res.stdout))
    return frames


def timed_transcript(words: list[Word], every: float = 3.0) -> str:
    """'[0.0] kelimeler ... [3.1] kelimeler ...' biçimi (kırpma için zaman bilgisi)."""
    lines, cur, start = [], [], None
    for w in words:
        if start is None:
            start = w.start
        cur.append(w.text)
        if w.end - start >= every:
            lines.append(f"[{start:.1f}] {' '.join(cur)}")
            cur, start = [], None
    if cur:
        lines.append(f"[{start:.1f}] {' '.join(cur)}")
    return "\n".join(lines) or "(no speech detected)"


def clamp_trim(start: float, end: float, duration: float, min_len: float = 8.0) -> tuple[float, float]:
    """Saf fonksiyon. Önerilen kırpmayı güvenli aralığa çeker."""
    start = max(0.0, min(start, duration))
    end = min(duration, max(end, 0.0))
    if end - start < min_len:
        mid = (start + end) / 2
        start = max(0.0, mid - min_len / 2)
        end = min(duration, start + min_len)
        start = max(0.0, end - min_len)
    return round(start, 2), round(end, 2)


# ------------------------------------------------------------------ ücretsiz sezgisel analiz
def motion_level(video: Path, samples: int = 16) -> float:
    """Ardışık örnek kareler arasındaki ortalama piksel farkı (0-1). Menü/yükleme ekranı ~0."""
    import cv2

    cap = cv2.VideoCapture(str(video))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    prev, diffs = None, []
    for i in range(samples):
        if total:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * i / samples))
        ok, frame = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.float32)
        if prev is not None:
            diffs.append(float(np.abs(g - prev).mean()) / 255.0)
        prev = g
    cap.release()
    return float(np.mean(diffs)) if diffs else 0.0


def clip_features(video: Path, duration: float, words: list[Word]) -> dict:
    loud = loudness_per_second(video)
    spike = float(loud.max() - np.median(loud)) if len(loud) else 0.0
    try:
        motion = motion_level(video)
    except ImportError:
        motion = 0.05  # opencv yoksa nötr
    return {"loud": loud, "spike_db": spike, "motion": motion,
            "wps": len(words) / max(duration, 1.0)}


def popularity(signals: dict) -> float:
    """0-1. Canlı klipte sohbet patlaması puanı, diğerlerinde izlenme hızı (keşifteki puan)."""
    s = float(signals.get("score") or 0)
    if signals.get("source") == "live":
        return min(1.0, s / 30000)
    return min(1.0, math.log10(s + 1) / 4)  # saatte ~10 bin izlenme = 1.0


def heuristic_score(f: dict, signals: dict) -> tuple[int, str]:
    """Saf fonksiyon. Ücretsiz sinyallerden 1-10 puan ve kısa gerekçe."""
    if f["motion"] < 0.008:
        return 2, "almost no motion (menu, loading screen or AFK)"
    parts = {
        "popularity": 2.0 * popularity(signals),
        "audio": 2.0 * min(1.0, f["spike_db"] / 15),
        "motion": 1.5 * min(1.0, f["motion"] / 0.08),
        "speech": 1.5 * min(1.0, f["wps"] / 2.0),
    }
    score = round(min(10.0, 3.0 + sum(parts.values())))
    best = max(parts, key=parts.get)
    return int(score), f"heuristic: strongest signal = {best} ({', '.join(f'{k} {v:.1f}' for k, v in parts.items())})"


def heuristic_trim(loud: np.ndarray, duration: float, target: int = 30) -> tuple[float, float]:
    """Uzun kliplerde en yüksek ses zirvesini sona yakın tutan ~30 sn'lik pencere."""
    if duration <= target + 5 or len(loud) < target:
        return 0.0, duration
    w = pick_windows(loud, length=target, top_k=1, pre_roll=int(target * 0.65), baseline=max(10, len(loud) // 2))
    return clamp_trim(w[0][0], w[0][1], duration) if w else (0.0, duration)


_JUNK = re.compile(r"(![a-z]+|\||#\w+|\bdrops?\b|\bsub(scribe)?\b|\bgiveaway\b|\bday \d+\b)", re.I)
HOOKS = ["WAIT FOR IT", "HE WAS NOT READY", "GTA 6 IS INSANE", "THIS CAN'T BE REAL", "WATCH TILL THE END",
         "NOBODY EXPECTED THIS", "GTA 6 COPS ARE CRAZY", "HE ACTUALLY DID IT"]
TITLE_TEMPLATES = ["{s} was NOT ready for this in GTA 6 😂", "GTA 6 got {s} like this 💀",
                   "{s} can't believe what just happened in GTA 6", "This GTA 6 moment broke {s} 😭",
                   "{s}'s most insane GTA 6 moment yet"]


def heuristic_meta(broadcaster: str, clip_title: str, clip_id: str) -> dict:
    """Twitch klip başlığı iyi ise onu kullanır (genelde klibi açan izleyicinin yazdığı vurucu bir cümle);
    yayın başlığına benziyorsa (komutlar, |, aşırı uzun) şablona geçer."""
    h = int(hashlib.md5(clip_id.encode()).hexdigest(), 16)
    t = (clip_title or "").strip()
    good = 3 <= len(t) <= 70 and not _JUNK.search(t)
    title = f"{t} | {broadcaster} GTA 6" if good else TITLE_TEMPLATES[h % len(TITLE_TEMPLATES)].format(s=broadcaster)
    m = metadata.ClipMeta(title=title[:90], hook=HOOKS[h % len(HOOKS)],
                          description=f"{t if good else title}\nStreamer: twitch.tv/{broadcaster.lower()}",
                          hashtags=["GTA6", "GTAVI", "GTA6Clips", "GTA", "Gaming", "Twitch", broadcaster])
    return metadata.finalize(m, broadcaster)


def heuristic(video: Path, duration: float, words: list[Word], broadcaster: str, clip_title: str,
              clip_id: str, signals: dict) -> dict:
    f = clip_features(video, duration, words)
    score, reason = heuristic_score(f, signals)
    start, end = heuristic_trim(f["loud"], duration)
    return {"score": score, "is_gta6": True, "category": "other", "reason": reason, "best_start": start,
            "best_end": end, "meta": heuristic_meta(broadcaster, clip_title, clip_id), "engine": "heuristic"}


# ------------------------------------------------------------------ giriş noktası
def analyze(video: Path, duration: float, words: list[Word], broadcaster: str, clip_title: str, views: int,
            cfg: dict, clip_id: str = "", signals: dict | None = None) -> dict:
    signals = signals or {"views": views}
    if llm.provider(cfg) != "none":
        frames = extract_frames(video, duration, cfg["quality"]["frames"])
        text = (f"Frames are at: {', '.join(f'{t:.1f}s' for t, _ in frames)}\n"
                f"Streamer: {broadcaster}\nClip title (by a viewer or the stream title): {clip_title}\n"
                f"Twitch views: {views}\nDuration: {duration:.1f}s\nTranscript:\n{timed_transcript(words)}")
        a = llm.structured(cfg, SYSTEM, text, ClipAnalysis, [j for _, j in frames], cfg["quality"]["effort"])
        if a is not None:
            start, end = clamp_trim(a.best_start, a.best_end, duration)
            meta = metadata.finalize(metadata.ClipMeta(title=a.title, hook=a.hook, description=a.description,
                                                       hashtags=a.hashtags), broadcaster)
            return {"score": a.score, "is_gta6": a.is_gta6, "category": a.category, "reason": a.reason,
                    "best_start": start, "best_end": end, "meta": meta, "engine": llm.provider(cfg)}
    return heuristic(video, duration, words, broadcaster, clip_title, clip_id or video.stem, signals)
