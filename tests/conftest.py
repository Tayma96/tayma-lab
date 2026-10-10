"""Test yardımcıları: küçük, elle kurulmuş ÖRNEK veri setleri."""
from __future__ import annotations

import pandas as pd
import pytest

from hakedis import config
from hakedis.modeller import (
    HAREKET_KOLONLARI, IADE_KOLONLARI, KARGO_KOLONLARI, KESINTI_KOLONLARI, SIPARIS_KOLONLARI,
    URUN_KOLONLARI, VeriSeti,
)

T = pd.Timestamp


def df(satirlar: list[dict], kolonlar: list[str], varsayilan: dict | None = None) -> pd.DataFrame:
    varsayilan = varsayilan or {}
    return pd.DataFrame([{k: s.get(k, varsayilan.get(k)) for k in kolonlar} for s in satirlar], columns=kolonlar)


def siparis(no, durum="TESLIM_EDILDI", barkod="B1", **kw):
    d = dict(platform="trendyol", siparis_no=no, paket_no=f"P{no}", barkod=barkod, urun_adi="x", adet=1,
             siparis_tarihi=T("2026-08-01"), termin_tarihi=T("2026-08-03"), sevk_tarihi=T("2026-08-02"),
             teslim_tarihi=T("2026-08-04"), durum=durum, ham_durum=durum, satis_tutari=1000.0, komisyon_orani=0.15)
    d.update(kw)
    return d


def hareket(no, tip, **kw):
    d = dict(platform="trendyol", islem_id=f"{tip}-{no}", siparis_no=no, barkod="B1", tip=tip, ham_tip=tip,
             tutar=0.0, komisyon_tutari=0.0, satici_hakedis=0.0, odeme_no=None, odendi=False,
             odeme_tarihi=pd.NaT, islem_tarihi=T("2026-08-05"), aciklama="")
    d.update(kw)
    return d


def kargo(sid, no, desi, tutar, tip="GONDERI", takip=None, **kw):
    d = dict(platform="trendyol", satir_id=sid, fatura_no="KF1", kargo_tipi=tip, takip_no=takip or f"TK-{no}",
             siparis_no=no, desi=float(desi), tutar=float(tutar))
    d.update(kw)
    return d


def kesinti(sid, no, tip, tutar, **kw):
    d = dict(platform="trendyol", satir_id=sid, kesinti_id=sid, fatura_no="F1", tip=tip, siparis_no=no,
             tutar=float(tutar), tarih=T("2026-08-05"), aciklama=tip)
    d.update(kw)
    return d


def veri(siparisler=(), urunler=(), hareketler=(), kargolar=(), kesintiler=(), iadeler=()) -> VeriSeti:
    vs = VeriSeti()
    if siparisler:
        vs.siparisler = df(list(siparisler), SIPARIS_KOLONLARI)
    if urunler:
        vs.urunler = df(list(urunler), URUN_KOLONLARI, {"platform": "trendyol", "urun_adi": "x"})
    if hareketler:
        vs.hareketler = df(list(hareketler), HAREKET_KOLONLARI)
    if kargolar:
        vs.kargo = df(list(kargolar), KARGO_KOLONLARI)
    if kesintiler:
        vs.kesintiler = df(list(kesintiler), KESINTI_KOLONLARI)
    if iadeler:
        vs.iadeler = df(list(iadeler), IADE_KOLONLARI, {"platform": "trendyol", "iade_id": "C1", "barkod": "B1",
                                                         "ham_durum": None, "tarih": T("2026-08-10"), "neden": ""})
    return vs


@pytest.fixture
def ayar():
    return config.yukle()
