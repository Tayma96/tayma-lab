"""Claude ile başlık, açılış kancası, açıklama ve hashtag üretimi. API anahtarı yoksa şablon kullanılır."""
from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

INTRO = "You write metadata for short vertical gaming clips (YouTube Shorts and TikTok) from GTA 6 streams.\n"
RULES = """Write the title, hook, description and hashtags in English. Make titles curiosity-driven and punchy, but never misleading: only describe what
actually happens in the clip, based on the clip title and transcript you are given.
Never pretend to be the streamer; the clip is credited to them.

Fields:
- title: at most 70 characters, no hashtags, may use one emoji.
- hook: 2 to 6 words shown as big on-screen text in the first seconds, no emoji.
- description: 1 to 3 short sentences, must contain the credit line "Streamer: twitch.tv/<name>".
- hashtags: 5 to 8 tags without the # sign; always include GTA6 and the streamer's name."""
SYSTEM = INTRO + RULES


class ClipMeta(BaseModel):
    title: str
    hook: str
    description: str
    hashtags: list[str] = Field(default_factory=list)


def _clean_tags(tags: list[str]) -> list[str]:
    out, seen = [], set()
    for t in tags:
        t = re.sub(r"[^\w]", "", t.lstrip("#"))
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def fallback_meta(broadcaster: str, clip_title: str) -> ClipMeta:
    base = clip_title.strip() or "This GTA 6 moment is insane"
    return ClipMeta(
        title=f"{base[:58]} | {broadcaster}"[:70],
        hook="WAIT FOR IT",
        description=f"{base}\nStreamer: twitch.tv/{broadcaster.lower()}",
        hashtags=["GTA6", "GTAVI", "GTA", "Gaming", broadcaster],
    )


def finalize(meta: ClipMeta, broadcaster: str) -> dict:
    tags = _clean_tags(meta.hashtags + ["GTA6", broadcaster])
    credit = f"twitch.tv/{broadcaster.lower()}"
    desc = meta.description if credit in meta.description.lower() else f"{meta.description}\nStreamer: {credit}"
    return {
        "title": meta.title.strip()[:95],
        "hook": " ".join(meta.hook.split()[:6]),
        "description": desc.strip(),
        "hashtags": tags[:10],
    }


def generate(broadcaster: str, clip_title: str, transcript: str, views: int, cfg: dict) -> dict:
    from .config import env

    if not env("ANTHROPIC_API_KEY") and not env("ANTHROPIC_AUTH_TOKEN"):
        return finalize(fallback_meta(broadcaster, clip_title), broadcaster)
    import anthropic

    try:
        client = anthropic.Anthropic()
        response = client.beta.messages.parse(
            model=cfg["metadata"]["model"],
            max_tokens=4000,
            output_config={"effort": cfg["metadata"]["effort"]},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            messages=[{"role": "user", "content": (
                f"Streamer: {broadcaster}\nClip title (written by a viewer): {clip_title}\n"
                f"Clip views on Twitch: {views}\nTranscript:\n{transcript or '(no speech detected)'}")}],
            output_format=ClipMeta,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            log.warning("Claude meta veri üretmedi (%s), şablon kullanılıyor", response.stop_reason)
            return finalize(fallback_meta(broadcaster, clip_title), broadcaster)
        return finalize(response.parsed_output, broadcaster)
    except anthropic.APIError as e:
        log.warning("Claude API hatası, şablon kullanılıyor: %s", e)
        return finalize(fallback_meta(broadcaster, clip_title), broadcaster)
