"""config.yaml yükleyici."""
from __future__ import annotations

import copy
from datetime import date
from pathlib import Path
from typing import Any

import yaml

VARSAYILAN_YOL = Path(__file__).resolve().parent.parent / "config.yaml"


def yukle(yol: str | Path | None = None) -> dict[str, Any]:
    yol = Path(yol) if yol else VARSAYILAN_YOL
    with open(yol, encoding="utf-8") as f:
        ayar = yaml.safe_load(f) or {}
    return ayar


def analiz_tarihi(ayar: dict[str, Any]) -> date:
    deger = (ayar.get("genel") or {}).get("analiz_tarihi")
    if not deger:
        return date.today()
    return date.fromisoformat(str(deger))


def guncelle(ayar: dict[str, Any], **yollar: Any) -> dict[str, Any]:
    """Testler için: guncelle(ayar, **{"esikler.min_guven": 0.1})"""
    yeni = copy.deepcopy(ayar)
    for anahtar, deger in yollar.items():
        hedef = yeni
        parcalar = anahtar.split(".")
        for p in parcalar[:-1]:
            hedef = hedef.setdefault(p, {})
        hedef[parcalar[-1]] = deger
    return yeni
