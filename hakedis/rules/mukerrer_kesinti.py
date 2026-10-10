"""Kural: Aynı kargo bedeli veya aynı sipariş-bazlı kesinti birden fazla kez alınmış.

Kargo: (platform, siparis_no, kargo_tipi, takip_no) tekrarı -> ilk kayıt hariç diğerleri.
Kesinti: config'teki sipariş başına tekil tiplerde (platform, siparis_no, tip, tutar) tekrarı.
"""
from __future__ import annotations

from typing import Any

from hakedis.modeller import Bulgu, VeriSeti
from hakedis.rules.ortak import tl, guven, kural_ayari, satir

KURAL = "mukerrer_kesinti"


def kontrol(vs: VeriSeti, ayar: dict[str, Any]) -> list[Bulgu]:
    ka = kural_ayari(ayar, KURAL)
    tekil = set(ka.get("siparis_basina_tekil_kesintiler", []))
    g = guven(ayar, "mukerrer_kesinti")
    bulgular = []

    k = vs.kargo.dropna(subset=["takip_no", "siparis_no"])
    if not k.empty:
        for (platform, sip, tip, takip), grp in k.groupby(["platform", "siparis_no", "kargo_tipi", "takip_no"]):
            if len(grp) < 2:
                continue
            fazlalar = grp.iloc[1:]
            tutar = round(float(fazlalar.tutar.sum()), 2)
            bulgular.append(Bulgu(
                kural=KURAL, alt_tip="kargo", platform=platform, siparis_no=sip, tutar_tl=tutar, guven=g,
                aciklama=(f"{takip} takip numaralı {tip.lower()} kargosu {len(grp)} kez faturalanmış; "
                          f"fazladan alınan: {tl(tutar)}."),
                kanit=[satir(r, ["satir_id", "fatura_no", "kargo_tipi", "takip_no", "siparis_no", "desi", "tutar"])
                       for _, r in grp.iterrows()],
                kaynak_anahtarlar=[f"kargo:{x}" for x in fazlalar.satir_id], referans=str(takip),
            ))

    s = vs.kesintiler.dropna(subset=["siparis_no"])
    s = s[s.tip.isin(tekil)] if not s.empty else s
    if not s.empty:
        for (platform, sip, tip, tutar_), grp in s.groupby(["platform", "siparis_no", "tip", "tutar"]):
            if len(grp) < 2:
                continue
            fazlalar = grp.iloc[1:]
            tutar = round(float(fazlalar.tutar.sum()), 2)
            bulgular.append(Bulgu(
                kural=KURAL, alt_tip="kesinti", platform=platform, siparis_no=sip, tutar_tl=tutar, guven=g,
                aciklama=f"'{tip}' aynı sipariş için {len(grp)} kez kesilmiş; fazladan alınan: {tl(tutar)}.",
                kanit=[satir(r, ["satir_id", "kesinti_id", "fatura_no", "tip", "siparis_no", "tutar", "tarih"])
                       for _, r in grp.iterrows()],
                kaynak_anahtarlar=[f"kesinti:{x}" for x in fazlalar.satir_id],
                referans=",".join(str(x) for x in grp.kesinti_id),
            ))
    return bulgular
