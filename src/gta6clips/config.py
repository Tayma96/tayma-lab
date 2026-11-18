from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULTS: dict[str, Any] = {
    "game_name": "Grand Theft Auto VI",
    "discovery": {
        "language": "en",
        "lookback_hours": 24,
        "min_views": 500,
        "min_duration": 8,
        "max_clips_per_run": 15,
        "top_streamers_boost": 30,
        "languages": ["en", "tr"],   # en: global (YouTube + TikTok), tr: Türk yayıncılar (sadece TikTok)
    },
    "blocklist": [],
    "facecams": {},
    "render": {
        "zoom": 1.15,
        "auto_facecam": True,
        "captions": True,
        "whisper_model": "small",
        "hook": True,
        "credit": True,
        "progress_bar": True,
        "brand": "",
    },
    "metadata": {"model": "claude-opus-5-5", "effort": "low"},
    "ai": {
        "provider": "github",              # github (ücretsiz) | none | ollama | claude (ücretli)
        "github_model": "openai/gpt-4o-mini",
        "max_images": 4,
        "ollama_url": "http://localhost:11434",
        "ollama_model": "qwen2.5vl:7b",
    },
    "quality": {"min_score": 6, "frames": 6, "effort": "medium"},
    "live": {
        "enabled": True,
        "top_channels": 25,
        "min_viewers": 1500,
        "refresh_minutes": 5,
        "spike_ratio": 3.0,
        "min_weight": 15,
        "cooldown_seconds": 120,
        "max_clips_per_hour": 20,
        "local_channels": 8,         # ayrıca en büyük kaç Türkçe yayın dinlensin
        "local_min_viewers": 300,
        # Twitch klibi isteğin yapıldığı andan önceki ~30 sn'yi alır. Sohbet patlaması anın ~7 sn
        # gerisinden gelir (yayın gecikmesi + yazma süresi). İstek patlamadan 30-10-7=13 sn sonra yapılır:
        # klip andan 10 sn önce başlar, ardından ~20 sn tepki kalır.
        "pre_roll_seconds": 10,
        "chat_lag_seconds": 7,
        "twitch_clip_seconds": 30,
    },
    "cut": {
        "min_length": 12,          # Shorts için en kısa
        "max_length": 45,          # en uzun (izlenme oranı düşmesin)
        "min_after_moment": 8,     # andan sonra en az bu kadar tepki kalsın
        "max_shift": 3.0,          # cümle/bağırış bitsin diye kesim en fazla bu kadar kayabilir
    },
    "schedule": {"discover_minutes": 15, "stats_hours": 3},
    "upload": {
        "youtube": {"enabled": True, "max_per_day": 6, "privacy": "public", "category_id": "20",
                    "languages": ["en"]},                        # YouTube: sadece global içerik
        "tiktok": {"enabled": True, "max_per_day": 10, "method": "browser", "headless": True,
                   "browser": "chromium", "visibility": "everyone",
                   "languages": ["en", "tr"], "subtitles": "tr"},  # TikTok: Türkçe altyazı + Türk yayıncılar
        "min_gap_minutes": 45,
        "peak_hours_utc": [],
        "max_age_hours": 36,
    },
    "launch": {
        "enabled": True,
        # GTA 6 yerel gece yarısı açılıyor: İngiltere, ABD doğu (en büyük yayıncılar), ABD batı
        "moments_utc": ["2026-11-18T21:00:00Z", "2026-11-19T00:00:00Z", "2026-11-19T05:00:00Z",
                        "2026-11-19T08:00:00Z"],
        "before_minutes": 20,
        "after_minutes": 90,
        "watch_channels": [],
        "watch_channels_tr": [],
        "top_channels": 12,
        "min_viewers": 3000,
        "spike_ratio": 2.0,
        "min_weight": 12,
        "cooldown_seconds": 60,
        "max_clips_per_hour": 40,
        "refresh_minutes": 2,
        "bypass_quality": True,
        "reserve": {"youtube": 3, "tiktok": 5},
        "reserve_hours": 24,
    },
    "notify": {"telegram": True, "min_quality": 8},
    "paths": {"data_dir": "data"},
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | os.PathLike = "config.yaml") -> dict[str, Any]:
    load_dotenv()
    p = Path(path)
    user = yaml.safe_load(p.read_text()) if p.exists() else {}
    cfg = _merge(DEFAULTS, user or {})
    cfg["blocklist"] = [b.lower() for b in cfg.get("blocklist") or []]
    cfg["facecams"] = {k.lower(): v for k, v in (cfg.get("facecams") or {}).items()}
    data_dir = Path(cfg["paths"]["data_dir"])
    for sub in ("raw", "out", "tmp"):
        (data_dir / sub).mkdir(parents=True, exist_ok=True)
    return cfg


def bootstrap_secrets() -> None:
    """Bilgisayarsız kurulum: GitHub Secrets'tan gelen ortam değişkenlerini, kodun beklediği token
    dosyalarına çevirir. Dosyadaki refresh token secret'takiyle aynıysa dokunmaz (yenilenmiş erişim
    token'ı korunur); secret değiştiyse (ör. 7 günde bir yenilenen test modu girişi) yenisini yazar."""
    import json

    yt = Path(env("YOUTUBE_TOKEN_FILE", "secrets/youtube_token.json"))
    new_rt = env("YOUTUBE_REFRESH_TOKEN")
    if not new_rt or not env("YOUTUBE_CLIENT_ID"):
        return
    current: dict = {}
    if yt.exists():
        try:
            current = json.loads(yt.read_text())
        except ValueError:
            current = {}
    if (current.get("refresh_token") != new_rt or current.get("client_id") != env("YOUTUBE_CLIENT_ID")
            or current.get("client_secret") != env("YOUTUBE_CLIENT_SECRET")):
        yt.parent.mkdir(parents=True, exist_ok=True)
        yt.write_text(json.dumps({
            "type": "authorized_user", "client_id": env("YOUTUBE_CLIENT_ID"),
            "client_secret": env("YOUTUBE_CLIENT_SECRET"), "refresh_token": env("YOUTUBE_REFRESH_TOKEN"),
            "token_uri": "https://oauth2.googleapis.com/token"}))


def env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name)
    return val if val else default
