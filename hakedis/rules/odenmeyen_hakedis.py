"""Kural: Teslim edilmiş siparişin hakedişi ödenmemiş.

- Satış kaydı var, vade (odeme_tarihi) + tolerans geçmiş, ödeme emri yok -> yüksek güven.
- Teslimattan bu yana kayit_olusma_tolerans_gun geçmiş, satış kaydı hiç yok -> orta güven
  (tutar tahminidir: satis_tutari * (1 - komisyon_orani)).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd

from hakedis.config import analiz_tarihi
from hakedis.modeller import Bulgu, VeriSeti
from hakedis.rules.ortak import tl, guven, kural_ayari, satir

KURAL = "odenmeyen_hakedis"


def kontrol(vs: VeriSeti, ayar: dict[str, Any]) -> list[Bulgu]:
    ka = kural_ayari(ayar, KURAL)
    bugun = pd.Timestamp(analiz_tarihi(ayar))
    kayit_tol = timedelta(days=int(ka.get("kayit_olusma_tolerans_gun", 10)))
    odeme_tol = timedelta(days=int(ka.get("odeme_tolerans_gun", 7)))
    vars_oran = float(ka.get("varsayilan_komisyon_orani", 0.18))
    if vs.siparisler.empty:
        return []
    teslim = vs.siparisler[vs.siparisler.durum == "TESLIM_EDILDI"]
    h = vs.hareketler
    bulgular = []
    for (platform, sip), grp in teslim.groupby(["platform", "siparis_no"]):
        hs = h[(h.platform == platform) & (h.siparis_no == sip)] if not h.empty else h
        satis = hs[hs.tip == "SATIS"] if not hs.empty else hs
        if satis.empty:
            teslim_t = grp.teslim_tarihi.max()
            if pd.isna(teslim_t) or teslim_t + kayit_tol >= bugun:
                continue
            oran = grp.komisyon_orani.iloc[0] or vars_oran
            tahmin = round(float((grp.satis_tutari * (1 - oran)).sum()), 2)
            bulgular.append(Bulgu(
                kural=KURAL, alt_tip="satis_kaydi_yok", platform=platform, siparis_no=sip, tutar_tl=tahmin,
                guven=guven(ayar, "odenmeyen_hakedis_kayit_yok"),
                aciklama=(f"Sipariş {teslim_t.date()} tarihinde teslim edilmiş; cari hesap ekstresinde satış "
                          f"kaydı yok. Tahmini hakediş: {tl(tahmin)} (tahmin)."),
                kanit=[satir(r, ["siparis_no", "barkod", "durum", "teslim_tarihi", "satis_tutari", "komisyon_orani"])
                       for _, r in grp.iterrows()],
                kaynak_anahtarlar=[f"{platform}:hakedis:{sip}"],
            ))
            continue
        odenmemis = satis[(~satis.odendi.astype(bool)) & satis.odeme_tarihi.notna()
                          & (satis.odeme_tarihi + odeme_tol < bugun)]
        if odenmemis.empty:
            continue
        tutar = round(float(odenmemis.satici_hakedis.sum()), 2)
        if tutar <= 0:
            continue
        bulgular.append(Bulgu(
            kural=KURAL, alt_tip="odeme_yok", platform=platform, siparis_no=sip, tutar_tl=tutar,
            guven=guven(ayar, "odenmeyen_hakedis_odeme_yok"),
            aciklama=(f"Satış kaydının vadesi {odenmemis.odeme_tarihi.min().date()} olmasına rağmen ödeme "
                      f"emri (paymentOrderId) oluşmamış. Ödenmeyen hakediş: {tl(tutar)}."),
            kanit=[satir(r) for _, r in odenmemis.iterrows()],
            kaynak_anahtarlar=[f"{platform}:hakedis:{sip}"],
            referans=",".join(str(x) for x in odenmemis.islem_id),
        ))
    return bulgular
