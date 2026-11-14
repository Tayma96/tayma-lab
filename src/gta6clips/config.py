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
    },
    "metadata": {"model": "claude-opus-5-5", "effort": "low"},
    "upload": {
        "youtube": {"enabled": True, "max_per_day": 6, "privacy": "public", "category_id": "20"},
        "tiktok": {"enabled": True, "max_per_day": 10, "method": "browser", "headless": True,
                   "browser": "chromium", "visibility": "everyone"},
        "min_gap_minutes": 45,
    },
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


def env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name)
    return val if val else default
