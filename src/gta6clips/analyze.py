"""Claude ile klip analizi: karelere bakar + konuşmayı okur, tek çağrıda
  - kalite puanı (1-10) ve gerçekten GTA 6 olup olmadığı,
  - klibin en güçlü bölümü (kırpma önerisi),
  - başlık, ekran kancası, açıklama, hashtag
üretir. Düşük puanlı klipler hiç kurgulanmaz/yüklenmez."""
from __future__ import annotations

import base64
import logging
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from . import metadata
from .config import env
from .highlights import VIRALITY_SYSTEM
from .transcribe import Word

log = logging.getLogger(__name__)

SYSTEM = VIRALITY_SYSTEM + """

You now review ONE clip. You see evenly spaced frames (with timestamps) and a timestamped transcript.
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
    """Saf fonksiyon. Claude'un önerdiği kırpmayı güvenli aralığa çeker."""
    start = max(0.0, min(start, duration))
    end = min(duration, max(end, 0.0))
    if end - start < min_len:
        mid = (start + end) / 2
        start = max(0.0, mid - min_len / 2)
        end = min(duration, start + min_len)
        start = max(0.0, end - min_len)
    return round(start, 2), round(end, 2)


def heuristic(broadcaster: str, clip_title: str, duration: float) -> dict:
    """Claude yoksa: her klibi orta puanla geçir, kırpma yok, şablon metin."""
    meta = metadata.finalize(metadata.fallback_meta(broadcaster, clip_title), broadcaster)
    return {"score": 6, "is_gta6": True, "category": "other", "reason": "no analysis (no API key)",
            "best_start": 0.0, "best_end": duration, "meta": meta}


def analyze(video: Path, duration: float, words: list[Word], broadcaster: str, clip_title: str, views: int,
            cfg: dict) -> dict:
    if not env("ANTHROPIC_API_KEY") and not env("ANTHROPIC_AUTH_TOKEN"):
        return heuristic(broadcaster, clip_title, duration)
    import anthropic

    content: list[dict] = []
    for t, jpg in extract_frames(video, duration, cfg["quality"]["frames"]):
        content.append({"type": "text", "text": f"Frame at {t:.1f}s:"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.b64encode(jpg).decode()}})
    content.append({"type": "text", "text": (
        f"Streamer: {broadcaster}\nClip title (written by a viewer or the stream title): {clip_title}\n"
        f"Twitch views: {views}\nDuration: {duration:.1f}s\nTranscript:\n{timed_transcript(words)}")})
    try:
        resp = anthropic.Anthropic().beta.messages.parse(
            model=cfg["metadata"]["model"], max_tokens=8000,
            output_config={"effort": cfg["quality"]["effort"]},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            system=SYSTEM, messages=[{"role": "user", "content": content}],
            output_format=ClipAnalysis,
        )
    except anthropic.APIError as e:
        log.warning("Claude analiz hatası, sezgisel değerlendirme kullanılıyor: %s", e)
        return heuristic(broadcaster, clip_title, duration)
    a = resp.parsed_output
    if resp.stop_reason == "refusal" or a is None:
        return heuristic(broadcaster, clip_title, duration)
    start, end = clamp_trim(a.best_start, a.best_end, duration)
    meta = metadata.finalize(metadata.ClipMeta(title=a.title, hook=a.hook, description=a.description,
                                               hashtags=a.hashtags), broadcaster)
    return {"score": a.score, "is_gta6": a.is_gta6, "category": a.category, "reason": a.reason,
            "best_start": start, "best_end": end, "meta": meta}
