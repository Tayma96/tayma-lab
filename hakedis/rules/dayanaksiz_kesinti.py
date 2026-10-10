"""Kural: Dayanağı görünmeyen hizmet / ceza bedelleri.

- Termin (geç kargolama) cezası: sipariş termin tarihinde veya öncesinde kargoya verilmişse.
- Tedarik edememe cezası: sipariş fiilen teslim edilmiş / iade sürecine girmişse.
- Bilinmeyen kesinti tipi: config'teki bilinen tipler listesinde yoksa (düşük güven, incelenmeli).
Kesinti tipi adları ÖRNEKTİR (doğrulanmalı).
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from hakedis.modeller import Bulgu, VeriSeti
from hakedis.rules.ortak import durum_adi, guven, kural_ayari, satir

KURAL = "dayanaksiz_kesinti"
KANIT_KOL = ["satir_id", "kesinti_id", "fatura_no", "tip", "siparis_no", "tutar", "tarih"]


def kontrol(vs: VeriSeti, ayar: dict[str, Any]) -> list[Bulgu]:
    ka = kural_ayari(ayar, KURAL)
    termin = set(ka.get("termin_cezasi_tipleri", []))
    tedarik = set(ka.get("tedarik_cezasi_tipleri", []))
    bilinen = set(ka.get("bilinen_kesinti_tipleri", [])) | termin | tedarik
    if vs.kesintiler.empty:
        return []
    sip = vs.siparisler.groupby(["platform", "siparis_no"]).agg(
        durum=("durum", "first"), termin_tarihi=("termin_tarihi", "first"),
        sevk_tarihi=("sevk_tarihi", "max")).reset_index()
    k = vs.kesintiler.merge(sip, on=["platform", "siparis_no"], how="left")
    bulgular = []
    for _, r in k.iterrows():
        kanit = [satir(r, KANIT_KOL + ["durum", "termin_tarihi", "sevk_tarihi"])]
        ortak = dict(kural=KURAL, platform=r.platform, siparis_no=r.siparis_no, tutar_tl=round(float(r.tutar), 2),
                     kanit=kanit, kaynak_anahtarlar=[f"kesinti:{r.satir_id}"], referans=str(r.kesinti_id))
        if r.tip in termin:
            if pd.notna(r.sevk_tarihi) and pd.notna(r.termin_tarihi) and r.sevk_tarihi <= r.termin_tarihi:
                bulgular.append(Bulgu(alt_tip="termin_cezasi", guven=guven(ayar, "dayanaksiz_termin"),
                                      aciklama=(f"'{r.tip}' kesilmiş ancak sipariş {r.sevk_tarihi.date()} "
                                                f"tarihinde, termin ({r.termin_tarihi.date()}) içinde kargoya verilmiş."),
                                      **ortak))
        elif r.tip in tedarik:
            if r.durum in ("TESLIM_EDILDI", "IADE"):
                bulgular.append(Bulgu(alt_tip="tedarik_cezasi", guven=guven(ayar, "dayanaksiz_tedarik"),
                                      aciklama=(f"'{r.tip}' kesilmiş ancak sipariş durumu '{durum_adi(r.durum)}'; "
                                                f"ürün tedarik edilip gönderilmiş."),
                                      **ortak))
        elif r.tip not in bilinen:
            bulgular.append(Bulgu(alt_tip="bilinmeyen_tip", guven=guven(ayar, "dayanaksiz_bilinmeyen"),
                                  aciklama=(f"'{r.tip}' bilinen kesinti tipleri arasında değil ve dayanağı "
                                            f"raporlarda görünmüyor; manuel inceleme gerekir."),
                                  **ortak))
    return bulgular
