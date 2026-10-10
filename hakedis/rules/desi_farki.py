"""Kural: Kargo faturasındaki desi, ürünün kayıtlı desisinden fazla.

beklenen_desi = yukarı_yuvarla( sum(urun_desi * adet) )   (paket bazında)
Faturalanan desi > beklenen_desi + tolerans ise:
  fark = faturalanan_tutar - tarife(beklenen_desi)
Tarife config.kargo_tarifesi'nden gelir (ÖRNEK, doğrulanmalı).
"""
from __future__ import annotations

import math
from typing import Any

from hakedis.modeller import Bulgu, VeriSeti
from hakedis.rules.ortak import tl, guven, kural_ayari, satir, tarife

KURAL = "desi_farki"


def kontrol(vs: VeriSeti, ayar: dict[str, Any]) -> list[Bulgu]:
    ka = kural_ayari(ayar, KURAL)
    tol = float(ka.get("tolerans_desi", 0))
    tipler = ["GONDERI"] + (["IADE"] if ka.get("iade_kargolarini_kontrol_et", True) else [])
    if vs.kargo.empty or vs.siparisler.empty or vs.urunler.empty:
        return []
    sip = vs.siparisler.merge(vs.urunler[["platform", "barkod", "urun_desi"]],
                              on=["platform", "barkod"], how="left")
    sip["satir_desi"] = sip.urun_desi * sip.adet
    paket_desi = sip.groupby(["platform", "siparis_no"]).agg(
        urun_desi_toplam=("satir_desi", "sum"), eksik=("urun_desi", lambda s: s.isna().any()),
        durum=("durum", "first")).reset_index()
    k = vs.kargo[vs.kargo.kargo_tipi.isin(tipler)].merge(paket_desi, on=["platform", "siparis_no"], how="inner")
    bulgular = []
    for _, r in k.iterrows():
        if r.eksik or not r.urun_desi_toplam or r.urun_desi_toplam <= 0:
            continue
        beklenen = int(math.ceil(r.urun_desi_toplam - 1e-9))
        if r.desi <= beklenen + tol:
            continue
        olmasi_gereken = tarife(beklenen, ayar, r.platform)
        fark = round(float(r.tutar) - olmasi_gereken, 2)
        if fark <= 0:
            continue
        gonderi = r.kargo_tipi == "GONDERI"
        bulgular.append(Bulgu(
            kural=KURAL, alt_tip="gonderi" if gonderi else "iade_kargosu", platform=r.platform,
            siparis_no=r.siparis_no, tutar_tl=fark,
            guven=guven(ayar, "desi_farki_gonderi" if gonderi else "desi_farki_iade"),
            aciklama=(f"{'Gönderi' if gonderi else 'İade'} kargosu {r.desi:g} desi üzerinden "
                      f"{tl(r.tutar)} faturalanmış; ürün kaydına göre paket {beklenen} desi "
                      f"(tarife: {tl(olmasi_gereken)}). Fark: {tl(fark)}."),
            kanit=[satir(r, ["satir_id", "fatura_no", "kargo_tipi", "takip_no", "siparis_no", "desi",
                             "tutar", "urun_desi_toplam"]) | {"beklenen_desi": beklenen,
                                                             "tarife_tutari": olmasi_gereken}],
            kaynak_anahtarlar=[f"kargo:{r.satir_id}"], referans=str(r.takip_no),
        ))
    return bulgular
