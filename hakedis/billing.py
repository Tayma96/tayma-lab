"""Başarı ücreti hesabı ve fatura TASLAĞI.

Ücret yalnızca sonraki hakedişte tespit edilen (tahsil_edildi) tutar üzerinden
hesaplanır. Kademeli: aylık tahsilatın hacim_esigi_tl'ye kadar olan kısmına
standart_oran, aşan kısmına hacim_orani uygulanır.
Bu modül fatura KESMEZ ve ödeme ÇEKMEZ; sadece taslak üretir.
"""
from __future__ import annotations

from typing import Any

from hakedis.takip import VakaDefteri


def ucret_hesapla(tahsil_tutari: float, ayar: dict[str, Any],
                  ozel_kalemler: dict[str, float] | None = None) -> dict[str, float]:
    """tahsil_tutari: kademeli orana tabi tutar. ozel_kalemler: {kural: tutar} - config.ucret.kural_oranlari
    içinde özel oranı olan kuralların tahsil tutarları (ör. ödenmeyen hakediş için düşük oran)."""
    u = ayar.get("ucret") or {}
    ozel_oranlar = u.get("kural_oranlari") or {}
    ozel_kalemler = ozel_kalemler or {}
    ozel_net = round(sum(t * float(ozel_oranlar.get(k, u.get("standart_oran", 0.25)))
                         for k, t in ozel_kalemler.items()), 2)
    ozel_toplam = round(sum(ozel_kalemler.values()), 2)
    std, hacim = float(u.get("standart_oran", 0.25)), float(u.get("hacim_orani", 0.20))
    esik, kdv = float(u.get("hacim_esigi_tl", 50000)), float(u.get("kdv_orani", 0.20))
    t1 = min(tahsil_tutari, esik)
    t2 = max(0.0, tahsil_tutari - esik)
    net = round(t1 * std + t2 * hacim + ozel_net, 2)
    kdv_tutari = round(net * kdv, 2)
    toplam_tahsil = round(tahsil_tutari + ozel_toplam, 2)
    return {
        "tahsil_tutari": toplam_tahsil, "standart_kademe_tutari": round(t1, 2),
        "hacim_kademe_tutari": round(t2, 2), "ozel_oranli_tutar": ozel_toplam, "ozel_oranli_ucret": ozel_net,
        "net_ucret": net, "kdv": kdv_tutari, "toplam_ucret": round(net + kdv_tutari, 2),
        "efektif_oran": round(net / toplam_tahsil, 4) if toplam_tahsil else 0.0,
        "saticiya_kalan_net": round(toplam_tahsil - net, 2),
    }


def kural_bazli_ayir(kalemler: list[tuple[str, float]], ayar: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """[(kural, tutar)] -> (kademeli tutar, {kural: özel oranlı tutar})"""
    ozel = (ayar.get("ucret") or {}).get("kural_oranlari") or {}
    kademeli, ozel_k = 0.0, {}
    for kural, tutar in kalemler:
        if kural in ozel:
            ozel_k[kural] = ozel_k.get(kural, 0.0) + tutar
        else:
            kademeli += tutar
    return kademeli, ozel_k


def ucret_kalemlerden(kalemler: list[tuple[str, float]], ayar: dict[str, Any]) -> dict[str, float]:
    kademeli, ozel = kural_bazli_ayir(kalemler, ayar)
    return ucret_hesapla(kademeli, ayar, ozel)


def fatura_taslagi(defter: VakaDefteri, satici: dict[str, str], donem: str, ayar: dict[str, Any],
                   fatura_no: str) -> dict[str, Any] | None:
    kalemler = [v for v in defter.vakalar.values() if v.durum == "tahsil_edildi" and not v.faturalandi]
    if not kalemler:
        return None
    hesap = ucret_kalemlerden([(v.kural, v.tahsil_tutari) for v in kalemler], ayar)
    for v in kalemler:
        v.faturalandi, v.fatura_no = True, fatura_no
    return {
        "fatura_no": fatura_no,
        "durum": "TASLAK - kesilmedi, gönderilmedi, kart çekimi yapılmadı",
        "satici": satici, "donem": donem,
        "odeme_yontemi": (ayar.get("ucret") or {}).get("odeme_yontemi"),
        "kalemler": [{"vaka_id": v.vaka_id, "platform": v.platform, "kural": v.kural, "siparis_no": v.siparis_no,
                      "talep_tutari": v.talep_tutari, "tahsil_tutari": v.tahsil_tutari,
                      "referanslar": v.tahsil_referanslari} for v in kalemler],
        "hesap": hesap,
    }
