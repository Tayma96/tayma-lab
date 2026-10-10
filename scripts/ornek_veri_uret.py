"""SENTETİK örnek veri üretici (ÖRNEK VERİ).

Trendyol (160 sipariş) + Hepsiburada (40 sipariş) = 200 sipariş üretir ve
bilinen tutarlarda hatalar "eker". Ekilen hataların listesi
ornek_veri/beklenen_bulgular.csv dosyasına yazılır (testler bunu kullanır).
Ardından tarama mantığıyla dosyalanacak vakaları belirleyip, VARSAYIMSAL
pazaryeri yanıtlarıyla ornek_veri/sonraki_donem/ verisini üretir.

Tüm satıcı/sipariş/barkod/takip numaraları SAHTEDİR ve 'ORNEK' önekiyle başlar.

Kullanım:  python scripts/ornek_veri_uret.py [--out ornek_veri]
"""
from __future__ import annotations

import argparse
import math
import random
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from hakedis import config, normalize, puanlama  # noqa: E402
from hakedis.rules import tum_kurallari_calistir  # noqa: E402
from hakedis.rules.ortak import tarife  # noqa: E402

ETIKET = ("# ÖRNEK VERİ - SENTETİK. Gerçek satıcı, sipariş veya kişi bilgisi içermez. "
          "Kolon adları Trendyol/Hepsiburada API alanlarını taklit eder; değerler uydurmadır.")
ANALIZ = date(2026, 10, 10)
SEED = 20261010


def iso(d: date | None) -> str:
    return d.isoformat() if d else ""


def sonraki_carsamba(d: date) -> date:
    return d + timedelta(days=(2 - d.weekday()) % 7)


def csv_yaz(df: pd.DataFrame, yol: Path) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "w", encoding="utf-8", newline="") as f:
        f.write(ETIKET + "\n")
        df.to_csv(f, index=False)


def xlsx_yaz(df: pd.DataFrame, yol: Path, sayfa: str) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(yol, engine="openpyxl") as w:
        df.to_excel(w, sheet_name=sayfa, index=False)
        pd.DataFrame({"BILGI": [ETIKET.lstrip("# "),
                                "Bu dosya panel Excel raporu fallback senaryosunu taklit eder; başlıklar doğrulanmalı."]}
                     ).to_excel(w, sheet_name="BILGI", index=False)


class Uretici:
    def __init__(self, ayar: dict):
        self.ayar = ayar
        self.rng = random.Random(SEED)
        self.beklenen: list[dict] = []
        self.kullanilan: set[str] = set()

    def ek(self, platform, kural, alt_tip, siparis_no, tutar, not_=""):
        self.beklenen.append({"platform": platform, "kural": kural, "alt_tip": alt_tip,
                              "siparis_no": siparis_no, "tutar_tl": round(tutar, 2), "not": not_})

    def sec(self, havuz: list[dict], n: int) -> list[dict]:
        uygun = [o for o in havuz if o["no"] not in self.kullanilan]
        secilen = self.rng.sample(uygun, n)
        self.kullanilan.update(o["no"] for o in secilen)
        return secilen

    # ------------------------------------------------------------------ TRENDYOL
    def trendyol(self, out: Path) -> None:
        rng = self.rng
        urunler = []
        for i in range(1, 21):
            urunler.append({"barcode": f"ORNEK-BRK-{i:03d}", "title": f"Örnek Ürün {i:02d} (sentetik)",
                            "dimensionalWeight": rng.choice([0.6, 0.9, 1.0, 1.4, 2.0, 2.6, 3.0, 3.8, 4.5, 5.2, 6.4]),
                            "fiyat": rng.choice([149.9, 239.9, 349.0, 459.9, 599.0, 799.0, 1099.0, 1499.0, 2299.0]),
                            "oran": rng.choice([10, 12, 15, 17, 19, 21])})
        u = {x["barcode"]: x for x in urunler}
        durumlar = (["Delivered"] * 112 + ["Returned"] * 22 + ["Cancelled"] * 10 + ["UnDelivered"] * 5
                    + ["Shipped"] * 6 + ["UnSupplied"] * 5)
        rng.shuffle(durumlar)
        siparisler = []
        for i, durum in enumerate(durumlar):
            urun = rng.choice(urunler)
            if durum == "Shipped":
                sd = date(2026, 10, 3) + timedelta(days=rng.randint(0, 4))
            else:
                sd = date(2026, 7, 1) + timedelta(days=rng.randint(0, 86))
            sevk = sd + timedelta(days=1) if durum not in ("Cancelled", "UnSupplied") else None
            teslim = sevk + timedelta(days=2) if durum in ("Delivered", "Returned") else None
            siparisler.append({"no": f"ORNEK-TY-{100001 + i}", "paket": f"ORNEK-PKT-{500001 + i}",
                               "barkod": urun["barcode"], "durum": durum, "sd": sd, "termin": sd + timedelta(days=2),
                               "sevk": sevk, "teslim": teslim, "fiyat": urun["fiyat"], "oran": urun["oran"],
                               "desi": math.ceil(urun["dimensionalWeight"] - 1e-9)})
        by = lambda d: [o for o in siparisler if o["durum"] == d]  # noqa: E731
        teslim_edilen, iade_edilen = by("Delivered"), by("Returned")

        # iade talepleri: 18 kabul, 4 red
        claims = []
        for j, o in enumerate(iade_edilen):
            o["iade_kabul"] = j < 18
            o["claim_tarih"] = o["teslim"] + timedelta(days=5)
            claims.append({"claimId": f"ORNEK-CLM-{j + 1:04d}", "orderNumber": o["no"], "barcode": o["barkod"],
                           "claimItemStatus": "Accepted" if o["iade_kabul"] else "Rejected",
                           "claimDate": iso(o["claim_tarih"]), "reason": rng.choice(["Beden uymadı", "Vazgeçtim",
                                                                                    "Kusurlu ürün"])})

        # ---- ekilen hatalar
        iko = self.sec([o for o in iade_edilen if o["iade_kabul"]], 12)
        for k, o in enumerate(iko):
            o["iko_iade_orani"] = 0.0 if k < 10 else 0.5
        desi_g = self.sec(teslim_edilen, 15)
        for o in desi_g:
            o["fatura_desi"] = o["desi"] + rng.choice([2, 3, 4, 5])
        desi_kucuk = self.sec(teslim_edilen, 4)
        for o in desi_kucuk:
            o["fatura_desi"] = o["desi"] + 1
        desi_i = self.sec([o for o in iade_edilen if o["iade_kabul"]], 3)
        for o in desi_i:
            o["iade_fatura_desi"] = o["desi"] + 3
        iptal_kargo = self.sec(by("Cancelled"), 6) + self.sec(by("UnSupplied"), 1)
        teslim_edilemedi_kargo = self.sec(by("UnDelivered"), 2)
        muk_kargo = self.sec(teslim_edilen, 4)
        muk_kesinti = self.sec(teslim_edilen, 1)
        termin_hakli = self.sec(teslim_edilen, 4)
        for o in termin_hakli:
            o["sevk"] = o["sd"] + timedelta(days=3)
            o["teslim"] = o["sevk"] + timedelta(days=2)
        termin_haksiz = self.sec(teslim_edilen, 3)
        tedarik_haksiz = self.sec(teslim_edilen, 2)
        uygun_odeme = [o for o in teslim_edilen
                       if sonraki_carsamba(o["teslim"] + timedelta(days=28)) < ANALIZ - timedelta(days=7)]
        odenmeyen = self.sec(uygun_odeme, 4)
        kayit_yok = self.sec([o for o in teslim_edilen if o["teslim"] < date(2026, 9, 20)], 1)
        tedarik_hakli = by("UnSupplied")[:5]

        # ---- settlements
        st, pay_tot = [], {}
        sid = 900000

        def odeme(t: date):
            pd_ = sonraki_carsamba(t + timedelta(days=28))
            return pd_, (int(pd_.strftime("%Y%m%d")) if pd_ <= ANALIZ else None)

        for o in teslim_edilen + iade_edilen:
            kom = round(o["fiyat"] * o["oran"] / 100, 2)
            rev = round(o["fiyat"] - kom, 2)
            o["kom"], o["rev"] = kom, rev
            if o in kayit_yok:
                self.ek("trendyol", "odenmeyen_hakedis", "satis_kaydi_yok", o["no"],
                        round(o["fiyat"] * (1 - o["oran"] / 100), 2))
                continue
            pdate, poid = odeme(o["teslim"])
            if o in odenmeyen:
                poid = None
                self.ek("trendyol", "odenmeyen_hakedis", "odeme_yok", o["no"], rev)
            sid += 1
            st.append({"id": f"ORNEK-TRX-{sid}", "transactionDate": iso(o["teslim"]), "barcode": o["barkod"],
                       "transactionType": "Satış", "transactionTypeCode": "Sale", "receiptId": "",
                       "description": "Satış", "debt": 0.0, "credit": o["fiyat"], "paymentPeriod": 28,
                       "commissionRate": o["oran"], "commissionAmount": kom, "sellerRevenue": rev,
                       "orderNumber": o["no"], "paymentOrderId": poid or "", "paymentDate": iso(pdate),
                       "sellerId": "ORNEK-999000001", "shipmentPackageId": o["paket"]})
            if poid:
                pay_tot[(poid, pdate)] = pay_tot.get((poid, pdate), 0) + rev
            if o["durum"] == "Returned" and o["iade_kabul"]:
                oran = o.get("iko_iade_orani", 1.0)
                iade_kom = round(kom * oran, 2)
                if oran < 1.0:
                    self.ek("trendyol", "iade_komisyonu", "hic_iade_edilmedi" if oran == 0 else "eksik_iade",
                            o["no"], kom - iade_kom)
                rt = o["claim_tarih"] + timedelta(days=3)
                rpd, rpoid = odeme(rt)
                sid += 1
                st.append({"id": f"ORNEK-TRX-{sid}", "transactionDate": iso(rt), "barcode": o["barkod"],
                           "transactionType": "İade", "transactionTypeCode": "Return", "receiptId": "",
                           "description": "İade", "debt": o["fiyat"], "credit": 0.0, "paymentPeriod": 28,
                           "commissionRate": o["oran"], "commissionAmount": iade_kom,
                           "sellerRevenue": round(-(o["fiyat"] - iade_kom), 2), "orderNumber": o["no"],
                           "paymentOrderId": rpoid or "", "paymentDate": iso(rpd), "sellerId": "ORNEK-999000001",
                           "shipmentPackageId": o["paket"]})

        # ---- kargo faturası detayları
        kargo = []

        def kargo_satir(o, tip, desi, gun, fatura_ay=None):
            ay = fatura_ay or gun.strftime("%Y%m")
            kargo.append({"invoiceSerialNumber": f"ORNEK-KF-{ay}", "shipmentPackageType": tip,
                          "parcelUniqueId": f"ORNEK-TKP-{o['paket'][-6:]}{'-I' if 'İade' in tip else ''}",
                          "orderNumber": o["no"], "amount": tarife(desi, self.ayar), "desi": desi})

        for o in siparisler:
            if o["durum"] in ("Delivered", "Returned"):
                fd = o.get("fatura_desi", o["desi"])
                kargo_satir(o, "Gönderi Kargo Bedeli", fd, o["sevk"])
                if "fatura_desi" in o:
                    alt = "gonderi"
                    self.ek("trendyol", "desi_farki", alt, o["no"],
                            tarife(fd, self.ayar) - tarife(o["desi"], self.ayar),
                            "küçük fark (eşik altı beklenir)" if o in desi_kucuk else "")
                if o["durum"] == "Returned":
                    idesi = o.get("iade_fatura_desi", o["desi"])
                    kargo_satir(o, "İade Kargo Bedeli", idesi, o["claim_tarih"])
                    if "iade_fatura_desi" in o:
                        self.ek("trendyol", "desi_farki", "iade_kargosu", o["no"],
                                tarife(idesi, self.ayar) - tarife(o["desi"], self.ayar))
                if o in muk_kargo:
                    sonraki_ay = (o["sevk"].replace(day=1) + timedelta(days=32)).strftime("%Y%m")
                    kargo_satir(o, "Gönderi Kargo Bedeli", o["desi"], o["sevk"], sonraki_ay)
                    self.ek("trendyol", "mukerrer_kesinti", "kargo", o["no"], tarife(o["desi"], self.ayar))
        for o in iptal_kargo:
            kargo_satir(o, "Gönderi Kargo Bedeli", o["desi"], o["sd"])
            self.ek("trendyol", "iptal_kargo", "iptal", o["no"], tarife(o["desi"], self.ayar))
        for o in teslim_edilemedi_kargo:
            kargo_satir(o, "Gönderi Kargo Bedeli", o["desi"], o["sevk"])
            self.ek("trendyol", "iptal_kargo", "teslim_edilemedi", o["no"], tarife(o["desi"], self.ayar),
                    "düşük güven, incelenmeli beklenir")

        # ---- otherfinancials: kesinti faturaları + ödeme emirleri
        of = []
        oid = 0

        def kesinti(tip, tutar, gun, siparis=None):
            nonlocal oid
            oid += 1
            of.append({"id": f"ORNEK-OF-{oid:05d}", "transactionDate": iso(gun), "transactionType": "Kesinti Faturası",
                       "transactionTypeCode": "DeductionInvoices", "description": tip, "debt": tutar, "credit": 0.0,
                       "orderNumber": siparis or "", "paymentOrderId": "", "invoiceSerialNumber": f"ORNEK-DF-{oid:05d}"})

        for o in teslim_edilen + iade_edilen:
            kesinti("Platform Hizmet Bedeli", 8.49, o["sevk"], o["no"])
        for o in muk_kesinti:
            kesinti("Platform Hizmet Bedeli", 8.49, o["sevk"] + timedelta(days=7), o["no"])
            self.ek("trendyol", "mukerrer_kesinti", "kesinti", o["no"], 8.49)
        for o in termin_hakli:
            kesinti("Termin Gecikme Bedeli", 45.0, o["sevk"], o["no"])
        for o, t in zip(termin_haksiz, [45.0, 60.0, 75.0]):
            kesinti("Termin Gecikme Bedeli", t, o["sevk"], o["no"])
            self.ek("trendyol", "dayanaksiz_kesinti", "termin_cezasi", o["no"], t)
        for o in tedarik_hakli:
            kesinti("Tedarik Edememe Bedeli", 120.0, o["termin"], o["no"])
        for o, t in zip(tedarik_haksiz, [120.0, 150.0]):
            kesinti("Tedarik Edememe Bedeli", t, o["teslim"], o["no"])
            self.ek("trendyol", "dayanaksiz_kesinti", "tedarik_cezasi", o["no"], t)
        kesinti("Reklam Bedeli", 750.0, date(2026, 8, 31))
        kesinti("Operasyonel Düzeltme Bedeli", 95.0, date(2026, 9, 15))
        self.ek("trendyol", "dayanaksiz_kesinti", "bilinmeyen_tip", None, 95.0, "düşük güven, incelenmeli beklenir")
        for (poid, pdate), tutar in sorted(pay_tot.items()):
            oid += 1
            of.append({"id": f"ORNEK-OF-{oid:05d}", "transactionDate": iso(pdate), "transactionType": "Ödeme",
                       "transactionTypeCode": "PaymentOrder", "description": "Hakediş ödemesi",
                       "debt": round(tutar, 2), "credit": 0.0, "orderNumber": "", "paymentOrderId": poid,
                       "invoiceSerialNumber": ""})

        # ---- yaz
        ty = out / "trendyol"
        sip_df = pd.DataFrame([{
            "Sipariş Numarası": o["no"], "Paket No": o["paket"], "Barkod": o["barkod"],
            "Ürün Adı": u[o["barkod"]]["title"], "Adet": 1, "Sipariş Tarihi": iso(o["sd"]),
            "Termin Tarihi": iso(o["termin"]), "Kargoya Veriliş Tarihi": iso(o["sevk"]),
            "Teslim Tarihi": iso(o["teslim"]), "Sipariş Statüsü": o["durum"], "Faturalanacak Tutar": o["fiyat"],
            "Komisyon Oranı": o["oran"]} for o in siparisler])
        xlsx_yaz(sip_df, ty / "siparisler.xlsx", "Siparisler")
        xlsx_yaz(pd.DataFrame([{k: x[k] for k in ("barcode", "title", "dimensionalWeight")} for x in urunler]),
                 ty / "urunler.xlsx", "Urunler")
        csv_yaz(pd.DataFrame(st), ty / "settlements.csv")
        csv_yaz(pd.DataFrame(of), ty / "otherfinancials.csv")
        csv_yaz(pd.DataFrame(kargo), ty / "kargo_fatura_detay.csv")
        csv_yaz(pd.DataFrame(claims), ty / "claims.csv")
        self.ty_siparisler = siparisler

    # ------------------------------------------------------------------ HEPSIBURADA
    def hepsiburada(self, out: Path) -> None:
        rng = self.rng
        urunler = [{"sku": f"ORNEK-SKU-{i:02d}", "productName": f"HB Örnek Ürün {i:02d} (sentetik)",
                    "desi": rng.choice([0.8, 1.2, 2.0, 2.7, 3.5, 4.9]),
                    "fiyat": rng.choice([279.0, 449.0, 649.0, 899.0, 1299.0, 1899.0]),
                    "oran": rng.choice([12, 14, 16, 18, 20])} for i in range(1, 9)]
        durumlar = ["Teslim Edildi"] * 26 + ["İade Edildi"] * 7 + ["İptal Edildi"] * 4 + ["Kargoda"] * 3
        rng.shuffle(durumlar)
        sip = []
        for i, d in enumerate(durumlar):
            ur = rng.choice(urunler)
            sd = (date(2026, 10, 4) if d == "Kargoda" else date(2026, 7, 5) + timedelta(days=rng.randint(0, 80)))
            sevk = sd + timedelta(days=1) if d != "İptal Edildi" else None
            teslim = sevk + timedelta(days=2) if d in ("Teslim Edildi", "İade Edildi") else None
            sip.append({"no": f"ORNEK-HB-{200001 + i}", "paket": f"ORNEK-HBP-{700001 + i}", "sku": ur["sku"],
                        "ad": ur["productName"], "durum": d, "sd": sd, "sevk": sevk, "teslim": teslim,
                        "fiyat": ur["fiyat"], "oran": ur["oran"], "desi": math.ceil(ur["desi"] - 1e-9)})
        teslim_edilen = [o for o in sip if o["durum"] == "Teslim Edildi"]
        iadeler = [o for o in sip if o["durum"] == "İade Edildi"]
        for j, o in enumerate(iadeler):
            o["kabul"] = j < 6
        iko = self.sec([o for o in iadeler if o["kabul"]], 3)
        desi = self.sec(teslim_edilen, 4)
        for o in desi:
            o["fatura_desi"] = o["desi"] + rng.choice([2, 3])
        iptal = self.sec([o for o in sip if o["durum"] == "İptal Edildi"], 2)
        muk = self.sec(teslim_edilen, 1)
        odenmeyen = self.sec([o for o in teslim_edilen if o["teslim"] + timedelta(days=21) < date(2026, 9, 25)], 1)

        isl, n = [], 0

        def satir(o, tip, tutar, gun, odeme_gun=None, desi_=None, takip=None):
            nonlocal n
            n += 1
            odendi = odeme_gun is not None and odeme_gun <= ANALIZ and o not in odenmeyen
            isl.append({"transactionId": f"ORNEK-HBT-{n:05d}", "transactionDate": iso(gun),
                        "paymentDate": iso(odeme_gun), "paymentStatus": "Ödendi" if odendi else "Bekliyor",
                        "type": tip, "amount": tutar, "orderNumber": o["no"], "sku": o["sku"],
                        "desi": desi_ if desi_ is not None else "", "cargoTrackingNumber": takip or "",
                        "description": tip})

        for o in teslim_edilen + iadeler:
            kom = round(o["fiyat"] * o["oran"] / 100, 2)
            od = o["teslim"] + timedelta(days=21)
            satir(o, "Satış", o["fiyat"], o["teslim"], od)
            satir(o, "Komisyon", kom, o["teslim"], od)
            if o in odenmeyen:
                self.ek("hepsiburada", "odenmeyen_hakedis", "odeme_yok", o["no"], o["fiyat"] - kom)
            fd = o.get("fatura_desi", o["desi"])
            takip = f"ORNEK-HBK-{o['paket'][-6:]}"
            satir(o, "Kargo Bedeli", tarife(fd, self.ayar), o["sevk"], od, fd, takip)
            if "fatura_desi" in o:
                self.ek("hepsiburada", "desi_farki", "gonderi", o["no"],
                        tarife(fd, self.ayar) - tarife(o["desi"], self.ayar))
            if o in muk:
                satir(o, "Kargo Bedeli", tarife(o["desi"], self.ayar), o["sevk"] + timedelta(days=10), od,
                      o["desi"], takip)
                self.ek("hepsiburada", "mukerrer_kesinti", "kargo", o["no"], tarife(o["desi"], self.ayar))
            if o["durum"] == "İade Edildi" and o["kabul"]:
                it = o["teslim"] + timedelta(days=6)
                satir(o, "İade", o["fiyat"], it, it + timedelta(days=21))
                if o in iko:
                    self.ek("hepsiburada", "iade_komisyonu", "hic_iade_edilmedi", o["no"], kom)
                else:
                    satir(o, "Komisyon İadesi", kom, it, it + timedelta(days=21))
                satir(o, "İade Kargo Bedeli", tarife(o["desi"], self.ayar), it, it + timedelta(days=21), o["desi"],
                      f"ORNEK-HBK-{o['paket'][-6:]}-I")
        for o in iptal:
            satir(o, "Kargo Bedeli", tarife(o["desi"], self.ayar), o["sd"], o["sd"] + timedelta(days=21), o["desi"],
                  f"ORNEK-HBK-{o['paket'][-6:]}")
            self.ek("hepsiburada", "iptal_kargo", "iptal", o["no"], tarife(o["desi"], self.ayar))

        hb = out / "hepsiburada"
        csv_yaz(pd.DataFrame([{"orderNumber": o["no"], "packageNumber": o["paket"], "sku": o["sku"],
                               "productName": o["ad"], "quantity": 1, "orderDate": iso(o["sd"]),
                               "dueDate": iso(o["sd"] + timedelta(days=2)), "shippedDate": iso(o["sevk"]),
                               "deliveredDate": iso(o["teslim"]), "status": o["durum"], "totalPrice": o["fiyat"],
                               "commissionRate": o["oran"]} for o in sip]), hb / "siparisler.csv")
        csv_yaz(pd.DataFrame([{k: x[k] for k in ("sku", "productName", "desi")} for x in urunler]),
                hb / "urunler.csv")
        csv_yaz(pd.DataFrame(isl), hb / "muhasebe_islemleri.csv")
        csv_yaz(pd.DataFrame([{"claimNumber": f"ORNEK-HBC-{j + 1:03d}", "orderNumber": o["no"], "sku": o["sku"],
                               "status": "Kabul Edildi" if o["kabul"] else "Reddedildi",
                               "claimDate": iso(o["teslim"] + timedelta(days=4)), "reason": "Vazgeçtim"}
                              for j, o in enumerate(iadeler)]), hb / "iadeler.csv")

    # ------------------------------------------------------------------ SONRAKİ DÖNEM (VARSAYIMSAL)
    def sonraki_donem(self, out: Path) -> None:
        """Dosyalanacak vakalar için VARSAYIMSAL pazaryeri yanıtları üretir."""
        vs = normalize.klasorden_yukle(out, self.ayar)
        bulgular = puanlama.puanla(tum_kurallari_calistir(vs, self.ayar), self.ayar)
        dosya = [b for b in bulgular if b.karar == "dosyalanacak"]
        # Varsayımsal kabul olasılıkları (GERÇEK BAŞARI ORANI DEĞİLDİR)
        olasilik = {"iade_komisyonu": 0.9, "desi_farki": 0.5, "iptal_kargo": 0.8, "mukerrer_kesinti": 1.0,
                    "dayanaksiz_kesinti": 0.6, "odenmeyen_hakedis": 1.0}
        rng = random.Random(SEED + 1)
        ty_st, ty_of, hb, sonuc = [], [], [], []
        gun = "2026-10-28"
        kismi_yapildi = bekleyen_kabul = False
        for i, b in enumerate(dosya):
            kabul = rng.random() < olasilik[b.kural]
            if not kabul:
                if i % 2 == 0:
                    sonuc.append({"platform": b.platform, "siparis_no": b.siparis_no, "kural": b.kural,
                                  "sonuc": "red", "not": "VARSAYIMSAL: pazaryeri talebi reddetti"})
                continue
            tutar = b.tutar_tl
            if b.kural == "desi_farki" and not kismi_yapildi:
                tutar, kismi_yapildi = round(tutar / 2, 2), True
            if b.kural == "iade_komisyonu" and not bekleyen_kabul:
                bekleyen_kabul = True
                sonuc.append({"platform": b.platform, "siparis_no": b.siparis_no, "kural": b.kural,
                              "sonuc": "kabul", "not": "VARSAYIMSAL: kabul edildi, düzeltme henüz yansımadı"})
                continue
            if b.platform == "trendyol":
                if b.kural in ("iade_komisyonu", "odenmeyen_hakedis"):
                    kod = "CommissionNegative" if b.kural == "iade_komisyonu" else "SellerRevenuePositive"
                    ty_st.append({"id": f"ORNEK-TRX-D{i:04d}", "transactionDate": gun, "barcode": "",
                                  "transactionType": "Düzeltme", "transactionTypeCode": kod,
                                  "description": f"VARSAYIMSAL düzeltme ({b.bulgu_id})", "debt": 0.0, "credit": tutar,
                                  "commissionAmount": 0.0, "sellerRevenue": tutar, "orderNumber": b.siparis_no,
                                  "paymentOrderId": 20261104, "paymentDate": "2026-11-04"})
                else:
                    ty_of.append({"id": f"ORNEK-OF-D{i:04d}", "transactionDate": gun, "transactionType": "Düzeltme",
                                  "transactionTypeCode": "FinancialItem",
                                  "description": f"VARSAYIMSAL düzeltme ({b.bulgu_id})", "debt": 0.0, "credit": tutar,
                                  "orderNumber": b.siparis_no or "", "paymentOrderId": 20261104,
                                  "invoiceSerialNumber": ""})
            else:
                tip = {"iade_komisyonu": "Düzeltme - Komisyon", "odenmeyen_hakedis": "Düzeltme - Hakediş",
                       "dayanaksiz_kesinti": "Düzeltme - Kesinti"}.get(b.kural, "Düzeltme - Kargo")
                hb.append({"transactionId": f"ORNEK-HBT-D{i:04d}", "transactionDate": gun, "paymentDate": "2026-11-04",
                           "paymentStatus": "Ödendi", "type": tip, "amount": tutar, "orderNumber": b.siparis_no,
                           "sku": "", "desi": "", "cargoTrackingNumber": "", "description": "VARSAYIMSAL düzeltme"})
        # vaka ile ilgisi olmayan bir düzeltme (ücretlendirilmemeli): bulgusu olmayan bir sipariş
        bulgulu = {b.siparis_no for b in bulgular}
        ilgisiz = next(o["no"] for o in self.ty_siparisler if o["no"] not in bulgulu)
        ty_of.append({"id": "ORNEK-OF-D9999", "transactionDate": gun, "transactionType": "Düzeltme",
                      "transactionTypeCode": "FinancialItem", "description": "VARSAYIMSAL ilgisiz düzeltme",
                      "debt": 0.0, "credit": 33.0, "orderNumber": ilgisiz, "paymentOrderId": 20261104,
                      "invoiceSerialNumber": ""})
        sd = out / "sonraki_donem"
        csv_yaz(pd.DataFrame(ty_st), sd / "trendyol" / "settlements.csv")
        csv_yaz(pd.DataFrame(ty_of), sd / "trendyol" / "otherfinancials.csv")
        csv_yaz(pd.DataFrame(hb), sd / "hepsiburada" / "muhasebe_islemleri.csv")
        csv_yaz(pd.DataFrame(sonuc), sd / "itiraz_sonuclari.csv")


OKUBENI = """# ÖRNEK VERİ - SENTETİK

Bu klasördeki **tüm** dosyalar `scripts/ornek_veri_uret.py` ile sabit tohum (seed={seed}) kullanılarak
üretilmiş **sentetik örnek veridir**. Gerçek bir satıcıya, siparişe, müşteriye veya kişiye ait değildir.
Tüm kimlikler `ORNEK-` önekiyle başlar. Tutarlar ve kargo tarifesi uydurmadır.

- `trendyol/` : Trendyol Partner API yanıt alanlarını taklit eden CSV/XLSX dosyaları (160 sipariş).
  `siparisler.xlsx` panel Excel fallback senaryosunu (Türkçe başlıklar) taklit eder.
- `hepsiburada/` : Hepsiburada muhasebe/sipariş verisini taklit eden CSV dosyaları (40 sipariş, alan adları doğrulanmalı).
- `beklenen_bulgular.csv` : Bilerek eklenen hatalar ve tutarları (testlerde doğruluk kontrolü için).
- `sonraki_donem/` : Sonraki hakediş dönemi için **VARSAYIMSAL** pazaryeri yanıtları/düzeltme kayıtları
  (gerçek başarı oranı değildir).
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(KOK / "ornek_veri"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    ayar = config.yukle()
    u = Uretici(ayar)
    u.trendyol(out)
    u.hepsiburada(out)
    (out / "OKUBENI_ORNEK_VERI.md").write_text(OKUBENI.format(seed=SEED), encoding="utf-8")
    csv_yaz(pd.DataFrame(u.beklenen).sort_values(["platform", "kural", "siparis_no"], na_position="last"),
            out / "beklenen_bulgular.csv")
    u.sonraki_donem(out)
    print(f"Üretildi: {out} | ekilen hata: {len(u.beklenen)} | toplam {sum(b['tutar_tl'] for b in u.beklenen):.2f} TL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
