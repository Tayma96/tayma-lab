"""Kurallar için yardımcılar."""
from __future__ import annotations

import math
from typing import Any

import pandas as pd


def tarife(desi: float, ayar: dict[str, Any], platform: str = "varsayilan") -> float:
    """config.kargo_tarifesi tablosundan desi -> TL (ÖRNEK tarife, doğrulanmalı)."""
    tarifeler = ayar.get("kargo_tarifesi") or {}
    t = tarifeler.get(platform) or tarifeler.get("varsayilan")
    tablo = {int(k): float(v) for k, v in t["tablo"].items()}
    d = max(1, int(math.ceil(desi - 1e-9)))
    if d in tablo:
        return tablo[d]
    en_ust = max(tablo)
    return tablo[en_ust] + (d - en_ust) * float(t.get("ust_desi_artis", 0))


DURUM_ADI = {"IPTAL": "İptal", "TEDARIK_EDILEMEDI": "Tedarik edilemedi", "TESLIM_EDILEMEDI": "Teslim edilemedi",
             "TESLIM_EDILDI": "Teslim edildi", "IADE": "İade", "KARGODA": "Kargoda"}


def durum_adi(d) -> str:
    return DURUM_ADI.get(d, str(d))


def tl(x: float) -> str:
    """Türkçe para biçimi: 1234.5 -> '1.234,50 TL'"""
    s = f"{float(x):,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " TL"


def satir(df_satir: pd.Series, kolonlar: list[str] | None = None) -> dict:
    d = df_satir.to_dict() if kolonlar is None else {k: df_satir.get(k) for k in kolonlar}
    temiz = {}
    for k, v in d.items():
        if isinstance(v, pd.Timestamp):
            v = v.date().isoformat()
        elif v is pd.NaT or (isinstance(v, float) and math.isnan(v)):
            v = None
        temiz[k] = v
    return temiz


def guven(ayar: dict[str, Any], anahtar: str, varsayilan: float = 0.5) -> float:
    return float((ayar.get("guven") or {}).get(anahtar, varsayilan))


def kural_ayari(ayar: dict[str, Any], kural: str) -> dict[str, Any]:
    return (ayar.get("kurallar") or {}).get(kural) or {}
