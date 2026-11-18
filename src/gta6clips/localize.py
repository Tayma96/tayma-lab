"""Türkçe sürüm (TikTok): altyazıyı ve başlık/kanca/açıklama/hashtag'leri Türkçeye çevirir.

Tek yapay zeka çağrısı: altyazı öbekleri (1-3 kelimelik gruplar) + metadata birlikte çevrilir. Çevrilen her
öbek, orijinal öbeğin zaman aralığına kelime kelime yayılır; böylece kelime vurgulu altyazı stili korunur.
Yapay zeka yoksa ya da hakkı dolduysa: Türkçe klipte orijinal altyazı, İngilizce klipte altyazısız
(yanlış dilde altyazı yerine) ve şablon Türkçe başlık kullanılır.
"""
from __future__ import annotations

import hashlib
import logging

from pydantic import BaseModel, Field

from . import llm
from .captions import group_words
from .metadata import finalize
from .transcribe import Word

log = logging.getLogger(__name__)

SYSTEM = """You localize short GTA 6 stream clips for a Turkish TikTok audience.
Translate naturally into everyday spoken Turkish (Gen Z TikTok tone, not formal), keep slang energy, keep
names (streamer names, GTA 6, places) as they are. Do not add content that is not there.

- chunks: translate EACH numbered caption chunk separately, same count and same order, short (1-4 words each).
  If the source is already Turkish, return the chunks unchanged.
- title: Turkish TikTok title, max 70 characters, may use one emoji, curiosity-driven but not misleading.
- hook: 2-5 Turkish words shown big on screen in the first seconds, no emoji.
- description: 1-2 short Turkish sentences.
- hashtags: 5-8 tags without '#', mix Turkish and global: always include GTA6 and the streamer's name,
  add Turkish ones like gta6türkiye, keşfet, oyun."""


class Localized(BaseModel):
    chunks: list[str] = Field(default_factory=list)
    title: str
    hook: str
    description: str
    hashtags: list[str] = Field(default_factory=list)


TR_HOOKS = ["BUNU BEKLEMİYORDU", "SONUNA KADAR İZLE", "GTA 6 ÇILDIRMIŞ", "BU NASIL OLDU", "İNANAMADI"]
TR_TITLES = ["{s} GTA 6'da buna hazır değildi 😂", "GTA 6 {s}'i bu hale getirdi 💀",
             "{s} gördüğüne inanamadı 😭", "{s}'in en çılgın GTA 6 anı"]


def tr_upper(text: str) -> str:
    """Türkçe büyük harf: i -> İ, ı -> I."""
    return text.replace("i", "İ").replace("ı", "I").upper()


def spread(chunks_src: list[list[Word]], chunks_tr: list[str]) -> list[Word]:
    """Saf fonksiyon. Her çevrilmiş öbeği, kaynak öbeğin zaman aralığına kelime kelime eşit yayar."""
    out: list[Word] = []
    for group, text in zip(chunks_src, chunks_tr):
        toks = text.split()
        if not toks:
            continue
        a, b = group[0].start, group[-1].end
        step = max(0.05, (b - a) / len(toks))
        for i, t in enumerate(toks):
            out.append(Word(a + i * step, min(b, a + (i + 1) * step), t))
    return out


def fallback(broadcaster: str, clip_id: str) -> dict:
    h = int(hashlib.md5(clip_id.encode()).hexdigest(), 16)
    title = TR_TITLES[h % len(TR_TITLES)].format(s=broadcaster)
    from .metadata import ClipMeta

    return finalize(ClipMeta(title=title, hook=TR_HOOKS[h % len(TR_HOOKS)],
                             description=f"{broadcaster} GTA 6 yayınından.",
                             hashtags=["GTA6", "gta6türkiye", "keşfet", "oyun", "GTA", broadcaster]), broadcaster)


def to_turkish(cfg: dict, words: list[Word], meta_en: dict, broadcaster: str, source_lang: str,
               clip_id: str) -> tuple[list[Word], dict]:
    """(Türkçe altyazı kelimeleri, Türkçe metadata)."""
    groups = group_words(words)
    numbered = "\n".join(f"{i + 1}. {' '.join(w.text for w in g)}" for i, g in enumerate(groups))
    text = (f"Streamer: {broadcaster}\nSource language: {source_lang}\n"
            f"English metadata to localize:\ntitle: {meta_en.get('title')}\nhook: {meta_en.get('hook')}\n"
            f"description: {meta_en.get('description')}\nhashtags: {', '.join(meta_en.get('hashtags') or [])}\n\n"
            f"Caption chunks ({len(groups)}):\n{numbered or '(no speech)'}")
    res = llm.structured(cfg, SYSTEM, text, Localized)
    if res is None:
        if source_lang.startswith("tr"):
            return words, fallback(broadcaster, clip_id)
        # Yapay zeka yok: ücretsiz çevrimdışı modelle altyazıyı çevir, başlık şablondan
        from . import translate_free

        out = translate_free.translate([" ".join(w.text for w in g) for g in groups])
        if out is not None and len(out) == len(groups):
            log.info("Türkçe altyazı ücretsiz modelle çevrildi (%d öbek)", len(groups))
            return spread(groups, out), fallback(broadcaster, clip_id)
        log.info("Türkçe çeviri yapılamadı: altyazısız, şablon başlık")
        return [], fallback(broadcaster, clip_id)
    if source_lang.startswith("tr"):
        tr_words = words
    elif len(res.chunks) == len(groups):
        tr_words = spread(groups, res.chunks)
    else:
        log.info("Çeviri öbek sayısı tutmadı (%d/%d): altyazısız", len(res.chunks), len(groups))
        tr_words = []
    from .metadata import ClipMeta

    meta = finalize(ClipMeta(title=res.title, hook=res.hook, description=res.description,
                             hashtags=res.hashtags), broadcaster)
    return tr_words, meta
