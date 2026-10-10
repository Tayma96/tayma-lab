"""Ham pazaryeri tablolarını ortak şemaya (modeller.VeriSeti) dönüştürür."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from hakedis.ingest import hepsiburada_dosya, trendyol_dosya
from hakedis.modeller import (
    HAREKET_KOLONLARI, IADE_KOLONLARI, KARGO_KOLONLARI, KESINTI_KOLONLARI,
    ODEME_KOLONLARI, SIPARIS_KOLONLARI, URUN_KOLONLARI, VeriSeti, bos_df,
)

TRENDYOL_DURUM = {
    "Delivered": "TESLIM_EDILDI", "Returned": "IADE", "Cancelled": "IPTAL",
    "UnDelivered": "TESLIM_EDILEMEDI", "Shipped": "KARGODA", "UnSupplied": "TEDARIK_EDILEMEDI",
    "Created": "YENI", "Picking": "HAZIRLANIYOR", "Invoiced": "HAZIRLANIYOR",
    "AtCollectionPoint": "KARGODA",
}
HEPSIBURADA_DURUM = {  # ÖRNEK, doğrulanmalı
    "Teslim Edildi": "TESLIM_EDILDI", "İade Edildi": "IADE", "İptal Edildi": "IPTAL",
    "Teslim Edilemedi": "TESLIM_EDILEMEDI", "Kargoda": "KARGODA", "Tedarik Edilemedi": "TEDARIK_EDILEMEDI",
}
TRENDYOL_IADE_DURUM = {"Accepted": "KABUL", "Rejected": "RED"}
HEPSIBURADA_IADE_DURUM = {"Kabul Edildi": "KABUL", "Reddedildi": "RED"}
KARGO_TIPI = {"Gönderi Kargo Bedeli": "GONDERI", "İade Kargo Bedeli": "IADE"}


def _sayi(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


def _tarih(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.normalize()


def _kol(df: pd.DataFrame, ad: str) -> pd.Series:
    return df[ad] if ad in df.columns else pd.Series([None] * len(df), index=df.index, dtype="object")


def _sec(df: pd.DataFrame, kolonlar: list[str]) -> pd.DataFrame:
    if df.empty:
        return bos_df(kolonlar)
    return df.reindex(columns=kolonlar).reset_index(drop=True)


# --------------------------------------------------------------------------- Trendyol
def trendyol(ham: dict[str, pd.DataFrame]) -> VeriSeti:
    p = "trendyol"
    vs = VeriSeti()

    s = ham.get("siparisler", pd.DataFrame())
    if not s.empty:
        vs.siparisler = _sec(pd.DataFrame({
            "platform": p,
            "siparis_no": _kol(s, "orderNumber").astype(str),
            "paket_no": _kol(s, "shipmentPackageId"),
            "barkod": _kol(s, "barcode"),
            "urun_adi": _kol(s, "productName"),
            "adet": _sayi(_kol(s, "quantity")).replace(0, 1),
            "siparis_tarihi": _tarih(_kol(s, "orderDate")),
            "termin_tarihi": _tarih(_kol(s, "agreedDeliveryDate")),
            "sevk_tarihi": _tarih(_kol(s, "shippedDate")),
            "teslim_tarihi": _tarih(_kol(s, "deliveredDate")),
            "ham_durum": _kol(s, "status"),
            "durum": _kol(s, "status").map(TRENDYOL_DURUM).fillna("DIGER"),
            "satis_tutari": _sayi(_kol(s, "amount")),
            "komisyon_orani": _sayi(_kol(s, "commissionRate")) / 100.0,
        }), SIPARIS_KOLONLARI)

    u = ham.get("urunler", pd.DataFrame())
    if not u.empty:
        vs.urunler = _sec(pd.DataFrame({
            "platform": p, "barkod": _kol(u, "barcode"), "urun_adi": _kol(u, "title"),
            "urun_desi": _sayi(_kol(u, "dimensionalWeight")),
        }), URUN_KOLONLARI)

    hareket_parcalari = []
    st = ham.get("settlements", pd.DataFrame())
    if not st.empty:
        kod = _kol(st, "transactionTypeCode").fillna(_kol(st, "transactionType"))
        tip = kod.map({"Sale": "SATIS", "Return": "IADE"}).fillna(kod)
        borc, alacak = _sayi(_kol(st, "debt")), _sayi(_kol(st, "credit"))
        hareket_parcalari.append(pd.DataFrame({
            "platform": p, "islem_id": _kol(st, "id"), "siparis_no": _kol(st, "orderNumber"),
            "barkod": _kol(st, "barcode"), "tip": tip, "ham_tip": _kol(st, "transactionType"),
            "tutar": alacak - borc,
            "komisyon_tutari": _sayi(_kol(st, "commissionAmount")),
            "satici_hakedis": _sayi(_kol(st, "sellerRevenue")),
            "odeme_no": _kol(st, "paymentOrderId"),
            "odendi": _kol(st, "paymentOrderId").notna(),
            "odeme_tarihi": _tarih(_kol(st, "paymentDate")),
            "islem_tarihi": _tarih(_kol(st, "transactionDate")),
            "aciklama": _kol(st, "description"),
        }))

    of = ham.get("otherfinancials", pd.DataFrame())
    if not of.empty:
        kod = _kol(of, "transactionTypeCode")
        borc, alacak = _sayi(_kol(of, "debt")), _sayi(_kol(of, "credit"))
        aciklama = _kol(of, "description").fillna("")
        kes_mask = (kod == "DeductionInvoices") & ~aciklama.isin(["Kargo Faturası", "Kargo Fatura"])
        kes = of[kes_mask]
        if not kes.empty:
            vs.kesintiler = _sec(pd.DataFrame({
                "platform": p, "satir_id": "trendyol-S-" + _kol(kes, "id").astype(str),
                "kesinti_id": _kol(kes, "id"), "fatura_no": _kol(kes, "invoiceSerialNumber"),
                "tip": aciklama[kes_mask], "siparis_no": _kol(kes, "orderNumber"),
                "tutar": borc[kes_mask], "tarih": _tarih(_kol(kes, "transactionDate")),
                "aciklama": aciklama[kes_mask],
            }), KESINTI_KOLONLARI)
        od_mask = kod == "PaymentOrder"
        if od_mask.any():
            od = of[od_mask]
            vs.odemeler = _sec(pd.DataFrame({
                "platform": p, "odeme_no": _kol(od, "paymentOrderId"),
                "odeme_tarihi": _tarih(_kol(od, "transactionDate")), "tutar": borc[od_mask],
            }), ODEME_KOLONLARI)
        diger_mask = ~(kod.isin(["DeductionInvoices", "PaymentOrder"]))
        if diger_mask.any():
            d = of[diger_mask]
            hareket_parcalari.append(pd.DataFrame({
                "platform": p, "islem_id": _kol(d, "id"), "siparis_no": _kol(d, "orderNumber"),
                "barkod": None, "tip": kod[diger_mask], "ham_tip": _kol(d, "transactionType"),
                "tutar": (alacak - borc)[diger_mask], "komisyon_tutari": 0.0, "satici_hakedis": 0.0,
                "odeme_no": _kol(d, "paymentOrderId"), "odendi": _kol(d, "paymentOrderId").notna(),
                "odeme_tarihi": pd.NaT, "islem_tarihi": _tarih(_kol(d, "transactionDate")),
                "aciklama": aciklama[diger_mask],
            }))
    if hareket_parcalari:
        vs.hareketler = _sec(pd.concat(hareket_parcalari, ignore_index=True), HAREKET_KOLONLARI)

    k = ham.get("kargo", pd.DataFrame())
    if not k.empty:
        k = k.reset_index(drop=True)
        vs.kargo = _sec(pd.DataFrame({
            "platform": p, "satir_id": [f"trendyol-K-{i}" for i in range(len(k))],
            "fatura_no": _kol(k, "invoiceSerialNumber"),
            "kargo_tipi": _kol(k, "shipmentPackageType").map(KARGO_TIPI).fillna("DIGER"),
            "takip_no": _kol(k, "parcelUniqueId"), "siparis_no": _kol(k, "orderNumber"),
            "desi": _sayi(_kol(k, "desi")), "tutar": _sayi(_kol(k, "amount")),
        }), KARGO_KOLONLARI)

    c = ham.get("claims", pd.DataFrame())
    if not c.empty:
        vs.iadeler = _sec(pd.DataFrame({
            "platform": p, "iade_id": _kol(c, "claimId"), "siparis_no": _kol(c, "orderNumber"),
            "barkod": _kol(c, "barcode"), "ham_durum": _kol(c, "claimItemStatus"),
            "durum": _kol(c, "claimItemStatus").map(TRENDYOL_IADE_DURUM).fillna("DIGER"),
            "tarih": _tarih(_kol(c, "claimDate")), "neden": _kol(c, "reason"),
        }), IADE_KOLONLARI)
    return vs


# --------------------------------------------------------------------------- Hepsiburada
def hepsiburada(ham: dict[str, pd.DataFrame], ayar: dict[str, Any]) -> VeriSeti:
    p = "hepsiburada"
    vs = VeriSeti()
    esleme = (ayar.get("hepsiburada") or {}).get("islem_tipi_eslemesi") or {}

    s = ham.get("siparisler", pd.DataFrame())
    if not s.empty:
        vs.siparisler = _sec(pd.DataFrame({
            "platform": p, "siparis_no": _kol(s, "orderNumber").astype(str),
            "paket_no": _kol(s, "packageNumber"), "barkod": _kol(s, "sku"),
            "urun_adi": _kol(s, "productName"), "adet": _sayi(_kol(s, "quantity")).replace(0, 1),
            "siparis_tarihi": _tarih(_kol(s, "orderDate")), "termin_tarihi": _tarih(_kol(s, "dueDate")),
            "sevk_tarihi": _tarih(_kol(s, "shippedDate")), "teslim_tarihi": _tarih(_kol(s, "deliveredDate")),
            "ham_durum": _kol(s, "status"),
            "durum": _kol(s, "status").map(HEPSIBURADA_DURUM).fillna("DIGER"),
            "satis_tutari": _sayi(_kol(s, "totalPrice")),
            "komisyon_orani": _sayi(_kol(s, "commissionRate")) / 100.0,
        }), SIPARIS_KOLONLARI)

    u = ham.get("urunler", pd.DataFrame())
    if not u.empty:
        vs.urunler = _sec(pd.DataFrame({
            "platform": p, "barkod": _kol(u, "sku"), "urun_adi": _kol(u, "productName"),
            "urun_desi": _sayi(_kol(u, "desi")),
        }), URUN_KOLONLARI)

    i = ham.get("islemler", pd.DataFrame())
    if not i.empty:
        i = i.copy()
        i["kod"] = _kol(i, "type").map(esleme).fillna("DIGER")
        i["tutar_f"] = _sayi(_kol(i, "amount")).abs()
        i["tarih_f"] = _tarih(_kol(i, "transactionDate"))
        i["odeme_f"] = _tarih(_kol(i, "paymentDate"))
        kom = i[i.kod == "KOMISYON"].groupby("orderNumber")["tutar_f"].sum()
        kom_iade = i[i.kod == "KOMISYON_IADE"].groupby("orderNumber")["tutar_f"].sum()
        satirlar = []
        for _, r in i.iterrows():
            sip = r.get("orderNumber")
            odendi = (r.get("paymentStatus") or "") == "Ödendi"
            ortak = dict(platform=p, islem_id=r.get("transactionId"), siparis_no=sip,
                         barkod=r.get("sku"), ham_tip=r.get("type"), odendi=odendi,
                         odeme_no=r.get("transactionId") if odendi else None,
                         odeme_tarihi=r["odeme_f"], islem_tarihi=r["tarih_f"],
                         aciklama=r.get("description"))
            if r.kod == "SATIS":
                k_ = float(kom.get(sip, 0.0))
                satirlar.append(dict(ortak, tip="SATIS", tutar=r.tutar_f, komisyon_tutari=k_,
                                     satici_hakedis=r.tutar_f - k_))
            elif r.kod == "IADE":
                k_ = float(kom_iade.get(sip, 0.0))
                satirlar.append(dict(ortak, tip="IADE", tutar=-r.tutar_f, komisyon_tutari=k_,
                                     satici_hakedis=-(r.tutar_f - k_)))
            elif r.kod.endswith("_DUZELTME"):
                satirlar.append(dict(ortak, tip=r.kod, tutar=r.tutar_f, komisyon_tutari=0.0,
                                     satici_hakedis=0.0))
        if satirlar:
            vs.hareketler = _sec(pd.DataFrame(satirlar), HAREKET_KOLONLARI)

        kg = i[i.kod.isin(["KARGO_GONDERI", "KARGO_IADE"])]
        if not kg.empty:
            vs.kargo = _sec(pd.DataFrame({
                "platform": p, "satir_id": "hepsiburada-K-" + _kol(kg, "transactionId").astype(str),
                "fatura_no": _kol(kg, "transactionId"),
                "kargo_tipi": kg.kod.map({"KARGO_GONDERI": "GONDERI", "KARGO_IADE": "IADE"}),
                "takip_no": _kol(kg, "cargoTrackingNumber"), "siparis_no": _kol(kg, "orderNumber"),
                "desi": _sayi(_kol(kg, "desi")), "tutar": kg.tutar_f,
            }), KARGO_KOLONLARI)

        ks = i[i.kod == "KESINTI"]
        if not ks.empty:
            vs.kesintiler = _sec(pd.DataFrame({
                "platform": p, "satir_id": "hepsiburada-S-" + _kol(ks, "transactionId").astype(str),
                "kesinti_id": _kol(ks, "transactionId"), "fatura_no": None,
                "tip": _kol(ks, "description"), "siparis_no": _kol(ks, "orderNumber"),
                "tutar": ks.tutar_f, "tarih": ks.tarih_f, "aciklama": _kol(ks, "description"),
            }), KESINTI_KOLONLARI)

    c = ham.get("iadeler", pd.DataFrame())
    if not c.empty:
        vs.iadeler = _sec(pd.DataFrame({
            "platform": p, "iade_id": _kol(c, "claimNumber"), "siparis_no": _kol(c, "orderNumber"),
            "barkod": _kol(c, "sku"), "ham_durum": _kol(c, "status"),
            "durum": _kol(c, "status").map(HEPSIBURADA_IADE_DURUM).fillna("DIGER"),
            "tarih": _tarih(_kol(c, "claimDate")), "neden": _kol(c, "reason"),
        }), IADE_KOLONLARI)
    return vs


def klasorden_yukle(girdi: Path | str, ayar: dict[str, Any]) -> VeriSeti:
    """<girdi>/trendyol ve <girdi>/hepsiburada klasörlerini okuyup birleştirir."""
    girdi = Path(girdi)
    vs = VeriSeti()
    if (girdi / "trendyol").is_dir():
        vs = vs.birlestir(trendyol(trendyol_dosya.oku(girdi / "trendyol", ayar)))
    if (girdi / "hepsiburada").is_dir():
        vs = vs.birlestir(hepsiburada(hepsiburada_dosya.oku(girdi / "hepsiburada", ayar), ayar))
    return vs
