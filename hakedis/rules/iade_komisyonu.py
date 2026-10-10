"""Kural: İade edilen siparişte komisyon geri verilmemiş / eksik verilmiş.

Mantık: İadesi KABUL edilen siparişte IADE (Return) kaydı varsa (satıcı hakedişi
geri alınmışsa), iade kaydındaki komisyon iadesi satış kaydındaki komisyondan
az olmamalıdır. Fark = geri alınabilir tutar.

Dayanak (doğrulanmalı): Trendyol cari hesap ekstresi dokümanında Return kaydı
için commissionAmount (+) / sellerRevenue (-) gösterilir.
"""
from __future__ import annotations

from typing import Any

from hakedis.modeller import Bulgu, VeriSeti
from hakedis.rules.ortak import tl, guven, kural_ayari, satir

KURAL = "iade_komisyonu"


def kontrol(vs: VeriSeti, ayar: dict[str, Any]) -> list[Bulgu]:
    ka = kural_ayari(ayar, KURAL)
    if not ka.get("iadede_komisyon_iade_edilir", True):
        return []
    tol = float(ka.get("tolerans_tl", 0.05))
    h = vs.hareketler
    if h.empty or vs.iadeler.empty:
        return []
    bulgular = []
    kabul = vs.iadeler[vs.iadeler.durum == "KABUL"]
    for (platform, sip), _grp in kabul.groupby(["platform", "siparis_no"]):
        hs = h[(h.platform == platform) & (h.siparis_no == sip)]
        satis = hs[hs.tip == "SATIS"]
        iade = hs[hs.tip == "IADE"]
        if satis.empty or iade.empty:
            continue  # satış kaydı ya da iade (hakediş geri alma) kaydı yoksa kayıp yok
        kesilen = float(satis.komisyon_tutari.sum())
        iade_edilen = float(iade.komisyon_tutari.sum())
        fark = round(kesilen - iade_edilen, 2)
        if fark > tol:
            alt = "hic_iade_edilmedi" if iade_edilen <= tol else "eksik_iade"
            bulgular.append(Bulgu(
                kural=KURAL, alt_tip=alt, platform=platform, siparis_no=sip, tutar_tl=fark,
                guven=guven(ayar, "iade_komisyonu"),
                aciklama=(f"Satışta {tl(kesilen)} komisyon kesilmiş; iade kaydında yalnızca "
                          f"{tl(iade_edilen)} komisyon iadesi var. Eksik: {tl(fark)}."),
                kanit=[satir(r) for _, r in satis.iterrows()] + [satir(r) for _, r in iade.iterrows()],
                kaynak_anahtarlar=[f"{platform}:komisyon:{sip}"],
                referans=",".join(str(x) for x in iade.islem_id.tolist()),
            ))
    return bulgular
