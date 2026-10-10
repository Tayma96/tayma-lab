"""Ortak veri modelleri."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

# Ortak şema kolonları (normalize katmanının çıktısı)
SIPARIS_KOLONLARI = [
    "platform", "siparis_no", "paket_no", "barkod", "urun_adi", "adet",
    "siparis_tarihi", "termin_tarihi", "sevk_tarihi", "teslim_tarihi",
    "durum", "ham_durum", "satis_tutari", "komisyon_orani",
]
URUN_KOLONLARI = ["platform", "barkod", "urun_adi", "urun_desi"]
HAREKET_KOLONLARI = [
    "platform", "islem_id", "siparis_no", "barkod", "tip", "ham_tip", "tutar",
    "komisyon_tutari", "satici_hakedis", "odeme_no", "odendi", "odeme_tarihi",
    "islem_tarihi", "aciklama",
]
KARGO_KOLONLARI = [
    "platform", "satir_id", "fatura_no", "kargo_tipi", "takip_no", "siparis_no",
    "desi", "tutar",
]
KESINTI_KOLONLARI = [
    "platform", "satir_id", "kesinti_id", "fatura_no", "tip", "siparis_no",
    "tutar", "tarih", "aciklama",
]
IADE_KOLONLARI = ["platform", "iade_id", "siparis_no", "barkod", "durum", "ham_durum", "tarih", "neden"]
ODEME_KOLONLARI = ["platform", "odeme_no", "odeme_tarihi", "tutar"]


def bos_df(kolonlar: list[str]) -> pd.DataFrame:
    return pd.DataFrame({k: pd.Series(dtype="object") for k in kolonlar})


@dataclass
class VeriSeti:
    """Normalize edilmiş, platformdan bağımsız veri seti."""

    siparisler: pd.DataFrame = field(default_factory=lambda: bos_df(SIPARIS_KOLONLARI))
    urunler: pd.DataFrame = field(default_factory=lambda: bos_df(URUN_KOLONLARI))
    hareketler: pd.DataFrame = field(default_factory=lambda: bos_df(HAREKET_KOLONLARI))
    kargo: pd.DataFrame = field(default_factory=lambda: bos_df(KARGO_KOLONLARI))
    kesintiler: pd.DataFrame = field(default_factory=lambda: bos_df(KESINTI_KOLONLARI))
    iadeler: pd.DataFrame = field(default_factory=lambda: bos_df(IADE_KOLONLARI))
    odemeler: pd.DataFrame = field(default_factory=lambda: bos_df(ODEME_KOLONLARI))

    TABLOLAR = ("siparisler", "urunler", "hareketler", "kargo", "kesintiler", "iadeler", "odemeler")

    def birlestir(self, diger: "VeriSeti") -> "VeriSeti":
        yeni = VeriSeti()
        for ad in self.TABLOLAR:
            a, b = getattr(self, ad), getattr(diger, ad)
            parcalar = [x for x in (a, b) if not x.empty]
            setattr(yeni, ad, pd.concat(parcalar, ignore_index=True) if parcalar else a.copy())
        return yeni


@dataclass
class Bulgu:
    kural: str
    alt_tip: str
    platform: str
    siparis_no: str | None
    tutar_tl: float
    guven: float
    aciklama: str
    kanit: list[dict[str, Any]] = field(default_factory=list)
    kaynak_anahtarlar: list[str] = field(default_factory=list)
    referans: str | None = None
    # puanlama tarafından doldurulur
    bulgu_id: str = ""
    beklenen_tl: float = 0.0
    oncelik: str = ""
    karar: str = ""  # dosyalanacak / esik_alti / incelenmeli / devreden / cakisma / donem_esik_alti

    def sozluk(self) -> dict[str, Any]:
        d = asdict(self)
        d["tutar_tl"] = round(self.tutar_tl, 2)
        d["beklenen_tl"] = round(self.beklenen_tl, 2)
        return d
