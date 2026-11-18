"""Lansman modu: GTA 6'nın açıldığı anları (yerel gece yarısı) kaçırmamak için.

Her an (`launch.moments_utc`) etrafında bir pencere açılır (`before_minutes` önce, `after_minutes` sonra).
Pencere içinde:
  - canlı avcı en büyük yayınlara odaklanır, `watch_channels` listesindeki tanınmış yayıncıları kategori
    fark etmeksizin (Just Chatting'de açsa bile) dinler, daha hassas ve daha sık klip alır,
  - bu klipler `source='launch'` olarak işaretlenir: kalite kapısına takılmaz (yükleme ekranı/menü tepkisi
    "GTA 6 oynanışı değil" diye elenmesin), kurgu ve yükleme sırasında en öne geçer, yüklemeler arası
    bekleme süresini atlar,
  - Telegram açıksa video anında telefona gönderilir (YouTube/Instagram/X'e elle paylaşım için).
Kampanya süresince (ilk pencerenin başından son pencerenin sonuna) keşif durur ki kurgu kuyruğu ve ücretsiz
yapay zeka hakkı lansman kliplerine kalsın. Lansmandan önceki `reserve_hours` saat içinde sıradan klipler
günlük hakkın `reserve` kadarını lansmana bırakır.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .db import now_utc, parse_ts


def _cfg(cfg: dict) -> dict:
    return cfg.get("launch") or {}


def enabled(cfg: dict) -> bool:
    return bool(_cfg(cfg).get("enabled")) and bool(_cfg(cfg).get("moments_utc"))


def moments(cfg: dict) -> list[datetime]:
    out = [parse_ts(m) for m in _cfg(cfg).get("moments_utc") or []]
    return sorted(m for m in out if m)


def windows(cfg: dict) -> list[tuple[datetime, datetime]]:
    lc = _cfg(cfg)
    before = timedelta(minutes=lc.get("before_minutes", 20))
    after = timedelta(minutes=lc.get("after_minutes", 90))
    return [(m - before, m + after) for m in moments(cfg)]


def active(cfg: dict, now: datetime | None = None) -> bool:
    """Şu an bir lansman penceresinin içinde miyiz?"""
    if not enabled(cfg):
        return False
    now = now or now_utc()
    return any(a <= now <= b for a, b in windows(cfg))


def in_campaign(cfg: dict, now: datetime | None = None) -> bool:
    """İlk pencerenin başı ile son pencerenin sonu arası (keşif bu sürede durur)."""
    if not enabled(cfg):
        return False
    now = now or now_utc()
    w = windows(cfg)
    return bool(w) and w[0][0] <= now <= w[-1][1]


def hours_until_next(cfg: dict, now: datetime | None = None) -> float | None:
    """Sıradaki (ya da şu an süren) lansman penceresine kalan saat; yoksa None. İçindeysek 0."""
    if not enabled(cfg):
        return None
    now = now or now_utc()
    for a, b in windows(cfg):
        if now <= b:
            return max(0.0, (a - now).total_seconds() / 3600)
    return None


def reserve_for(cfg: dict, platform: str, now: datetime | None = None) -> int:
    """Sıradaki lansmana `reserve_hours` saatten az kaldıysa, sıradan kliplerin bırakması gereken hak."""
    h = hours_until_next(cfg, now)
    if h is None or h > _cfg(cfg).get("reserve_hours", 24):
        return 0
    return int((_cfg(cfg).get("reserve") or {}).get(platform, 0))


def live_settings(cfg: dict, now: datetime | None = None) -> dict:
    """Canlı avcı ayarları: pencere içindeysek lansman ayarları normal ayarların üstüne yazılır."""
    lc = dict(cfg["live"])
    if active(cfg, now):
        for k in ("top_channels", "min_viewers", "spike_ratio", "min_weight", "cooldown_seconds",
                  "max_clips_per_hour", "refresh_minutes"):
            if k in _cfg(cfg):
                lc[k] = _cfg(cfg)[k]
    return lc


def watch_channels(cfg: dict) -> list[str]:
    names = (_cfg(cfg).get("watch_channels") or []) + (_cfg(cfg).get("watch_channels_tr") or [])
    return list(dict.fromkeys(c.strip().lower() for c in names if c and c.strip()))


def adjust_run_minutes(cfg: dict, minutes: float, now: datetime | None = None, max_minutes: float = 340,
                       warmup_minutes: float = 25, min_run: float = 30) -> float:
    """GitHub Actions turu bir lansman penceresinin ortasında bitmesin: bitiş bir pencereye denk geliyorsa
    turu pencere bitene kadar uzat (izin verilen süreye sığıyorsa), sığmıyorsa pencereden `warmup_minutes`
    önce bitir ki sıradaki tur ısınmış olarak başlasın (sohbet ortalaması oturur)."""
    if not enabled(cfg) or minutes < 60:  # kısa (elle başlatılan deneme) turlarına dokunma
        return minutes
    now = now or now_utc()
    end = now + timedelta(minutes=minutes)
    for a, b in windows(cfg):
        start_guard = a - timedelta(minutes=warmup_minutes)
        if start_guard < end < b:
            extended = (b - now).total_seconds() / 60 + 2
            if extended <= max_minutes:
                return round(extended, 1)
            shortened = (start_guard - now).total_seconds() / 60
            if shortened >= min_run:
                return round(shortened, 1)
            return minutes
    return minutes


def describe(cfg: dict, now: datetime | None = None) -> str:
    if not enabled(cfg):
        return "Lansman modu kapalı"
    now = now or now_utc()
    if active(cfg, now):
        return "Lansman penceresi AÇIK"
    h = hours_until_next(cfg, now)
    if h is None:
        return "Lansman anları geçti"
    nxt = next(a for a, b in windows(cfg) if now <= b)
    return f"Sıradaki lansman penceresi {nxt.astimezone(timezone.utc):%d.%m %H:%M} UTC ({h:.1f} saat sonra)"
