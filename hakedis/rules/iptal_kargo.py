"""Kural: İptal edilmiş / tedarik edilememiş siparişe gönderi kargo bedeli kesilmiş.

Teslim edilemeyen (UnDelivered) siparişlerde kargonun kime ait olduğu belirsiz
olduğu için bu durumlar düşük güvenle "incelenecek" olarak raporlanır.
"""
from __future__ import annotations

from typing import Any

from hakedis.modeller import Bulgu, VeriSeti
from hakedis.rules.ortak import durum_adi, tl, guven, kural_ayari, satir

KURAL = "iptal_kargo"


def kontrol(vs: VeriSeti, ayar: dict[str, Any]) -> list[Bulgu]:
    ka = kural_ayari(ayar, KURAL)
    kesin = set(ka.get("kargo_kesilmemesi_gereken_durumlar", ["IPTAL"]))
    incele = set(ka.get("incelenecek_durumlar", ["TESLIM_EDILEMEDI"]))
    if vs.kargo.empty or vs.siparisler.empty:
        return []
    durumlar = vs.siparisler.groupby(["platform", "siparis_no"])["durum"].first().reset_index()
    k = vs.kargo[vs.kargo.kargo_tipi == "GONDERI"].merge(durumlar, on=["platform", "siparis_no"], how="inner")
    k = k[k.durum.isin(kesin | incele)]
    bulgular = []
    for (platform, sip), grp in k.groupby(["platform", "siparis_no"]):
        durum = grp.durum.iloc[0]
        tutar = round(float(grp.tutar.sum()), 2)
        if tutar <= 0:
            continue
        kesin_mi = durum in kesin
        bulgular.append(Bulgu(
            kural=KURAL, alt_tip="iptal" if kesin_mi else "teslim_edilemedi", platform=platform,
            siparis_no=sip, tutar_tl=tutar,
            guven=guven(ayar, "iptal_kargo_iptal" if kesin_mi else "iptal_kargo_teslim_edilemedi"),
            aciklama=(f"Sipariş durumu '{durum_adi(durum)}'; buna rağmen {len(grp)} adet gönderi kargo bedeli "
                      f"({tl(tutar)}) kesilmiş."),
            kanit=[satir(r, ["satir_id", "fatura_no", "kargo_tipi", "takip_no", "siparis_no", "desi",
                             "tutar", "durum"]) for _, r in grp.iterrows()],
            kaynak_anahtarlar=[f"kargo:{x}" for x in grp.satir_id],
            referans=",".join(str(x) for x in grp.takip_no),
        ))
    return bulgular
