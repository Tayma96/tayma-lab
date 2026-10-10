"""Sonraki hakediş döneminde geri ödemenin (düzeltme kaydı) tespiti.

Sonraki dönemin cari hesap / muhasebe verisindeki pozitif düzeltme kayıtları,
config.tahsilat.eslestirme'deki kural->kayıt tipi eşlemesine göre açık
vakalarla (aynı platform + sipariş no) eşleştirilir. Eşleşen tutar vakanın
kalan talebini aşamaz. Eşleşen vakalar 'kabul' -> 'tahsil_edildi' olur.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from hakedis.modeller import VeriSeti
from hakedis.takip import VakaDefteri


def sonuclari_uygula(defter: VakaDefteri, sonuclar: pd.DataFrame, tarih: str) -> int:
    """Satıcının girdiği itiraz sonuçlarını (platform, siparis_no, kural, sonuc) uygular."""
    n = 0
    for _, r in sonuclar.iterrows():
        for v in defter.vakalar.values():
            if (v.platform, str(v.siparis_no), v.kural) == (r.platform, str(r.siparis_no), r.kural) \
                    and v.durum == "itiraz_edildi" and r.sonuc in ("kabul", "red"):
                v.gecis(r.sonuc, tarih, str(r.get("not") or "satıcı tarafından girildi"))
                n += 1
    return n


def tespit_et(defter: VakaDefteri, sonraki: VeriSeti, ayar: dict[str, Any], tarih: str) -> pd.DataFrame:
    esleme: dict[str, list[str]] = (ayar.get("tahsilat") or {}).get("eslestirme") or {}
    tum_tipler = {t for tipler in esleme.values() for t in tipler}
    h = sonraki.hareketler
    kayitlar = []
    if h.empty:
        return pd.DataFrame(columns=["islem_id", "platform", "siparis_no", "tip", "tutar", "vaka_id", "eslesen_tutar"])
    duzeltmeler = h[h.tip.isin(tum_tipler) & (h.tutar > 0)].sort_values(["platform", "siparis_no", "islem_id"])
    for _, r in duzeltmeler.iterrows():
        kalan_kayit = float(r.tutar)
        adaylar = sorted(
            (v for v in defter.vakalar.values()
             if v.platform == r.platform and str(v.siparis_no) == str(r.siparis_no)
             and v.durum in ("itiraz_edildi", "kabul", "red") and r.tip in esleme.get(v.kural, [])
             and v.talep_tutari - v.tahsil_tutari > 0.005),
            key=lambda v: v.vaka_id)
        for v in adaylar:
            if kalan_kayit <= 0.005:
                break
            pay = round(min(kalan_kayit, v.talep_tutari - v.tahsil_tutari), 2)
            v.tahsil_tutari = round(v.tahsil_tutari + pay, 2)
            v.tahsil_referanslari.append(f"{r.tip}:{r.islem_id}")
            kalan_kayit -= pay
            kayitlar.append({"islem_id": r.islem_id, "platform": r.platform, "siparis_no": r.siparis_no,
                             "tip": r.tip, "tutar": float(r.tutar), "vaka_id": v.vaka_id, "eslesen_tutar": pay})
        if not adaylar:
            kayitlar.append({"islem_id": r.islem_id, "platform": r.platform, "siparis_no": r.siparis_no,
                             "tip": r.tip, "tutar": float(r.tutar), "vaka_id": None, "eslesen_tutar": 0.0})
    for v in defter.vakalar.values():
        if v.tahsil_tutari > 0 and v.durum != "tahsil_edildi":
            if v.durum in ("itiraz_edildi", "red"):
                v.gecis("kabul", tarih, "düzeltme kaydı tespit edildi")
            kismi = " (kısmi)" if v.tahsil_tutari + 0.005 < v.talep_tutari else ""
            v.gecis("tahsil_edildi", tarih, f"{v.tahsil_tutari:.2f} TL hakedişe yansıdı{kismi}")
    return pd.DataFrame(kayitlar)
