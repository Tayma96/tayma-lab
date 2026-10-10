"""Pazaryeri OKUMA API istemcileri - TASLAK (STUB).

!!! Bu modül hiçbir ağ çağrısı YAPMAZ. !!!
Yalnızca hangi uç noktaların hangi parametrelerle çağrılacağını belgeleyen
istek planları (IstekPlani) üretir. `calistir()` her zaman CanliApiKapali
hatası fırlatır. Canlı entegrasyon, satıcının yazılı onayı ve ayrı bir
güvenlik incelemesi olmadan eklenmemelidir.

Kaynaklar (erişim: 10.10.2026):
- Trendyol Cari Hesap Ekstresi: https://developers.trendyol.com/docs/cari-hesap-ekstresi-entegrasyonu
- Trendyol Kargo Faturası Detayları: https://developers.trendyol.com/docs/kargo-faturas%C4%B1-detaylar%C4%B1
- Trendyol getShipmentPackages: https://developers.trendyol.com/docs/sipari%C5%9F-paketlerini-%C3%A7ekme-getshipmentpackages
- Trendyol getClaims: https://developers.trendyol.com/docs/i%CC%87adesi-olu%C5%9Fturulan-sipari%C5%9Fleri-%C3%A7ekme-getclaims
- Trendyol filterProducts: https://developers.trendyol.com/docs/%C3%BCr%C3%BCn-filtreleme-filterproducts
- Hepsiburada (doğrulanmalı, üçüncü taraf SDK üzerinden): https://github.com/loncadev/lonca/tree/main/sdks/hepsiburada
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

CANLI_API_KAPALI = True  # Bu iskelette değiştirilmez.


class CanliApiKapali(RuntimeError):
    pass


@dataclass
class IstekPlani:
    metod: str
    url: str
    parametreler: dict = field(default_factory=dict)
    not_: str = ""

    def calistir(self):  # pragma: no cover - bilinçli olarak devre dışı
        raise CanliApiKapali(
            "Canlı API çağrıları bu iskelette devre dışıdır. Hiçbir pazaryerine istek atılmaz."
        )


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _pencereler(baslangic: datetime, bitis: datetime, gun: int):
    """Trendyol finans servisleri en fazla 15 gün, sipariş servisi en fazla 2 hafta aralık kabul eder."""
    s = baslangic
    while s < bitis:
        e = min(s + timedelta(days=gun), bitis)
        yield s, e
        s = e


class TrendyolOkumaIstemcisi:
    """Trendyol Partner API (yalnızca GET). Basic Auth + User-Agent başlığı gerekir (dokümana göre)."""

    TABAN = "https://apigw.trendyol.com/integration"

    def __init__(self, satici_id: int):
        self.satici_id = satici_id

    def siparis_paketleri(self, baslangic: datetime, bitis: datetime) -> list[IstekPlani]:
        return [
            IstekPlani("GET", f"{self.TABAN}/order/sellers/{self.satici_id}/v2/orders",
                       {"startDate": _ms(s), "endDate": _ms(e), "page": 0, "size": 200,
                        "orderByField": "PackageLastModifiedDate", "orderByDirection": "ASC"},
                       "v2 uç noktası 15.10.2026'dan itibaren zorunlu; en fazla 2 haftalık aralık")
            for s, e in _pencereler(baslangic, bitis, 14)
        ]

    def iadeler(self, baslangic: datetime, bitis: datetime) -> list[IstekPlani]:
        return [
            IstekPlani("GET", f"{self.TABAN}/order/sellers/{self.satici_id}/claims",
                       {"startDate": _ms(s), "endDate": _ms(e), "page": 0, "size": 200})
            for s, e in _pencereler(baslangic, bitis, 14)
        ]

    def urunler(self) -> list[IstekPlani]:
        return [IstekPlani("GET", f"{self.TABAN}/product/sellers/{self.satici_id}/products",
                           {"page": 0, "size": 100}, "dimensionalWeight = ürün desisi")]

    def settlements(self, baslangic: datetime, bitis: datetime, tipler: list[str]) -> list[IstekPlani]:
        return [
            IstekPlani("GET", f"{self.TABAN}/finance/che/sellers/{self.satici_id}/settlements",
                       {"startDate": _ms(s), "endDate": _ms(e), "transactionTypes": ",".join(tipler),
                        "page": 0, "size": 1000})
            for s, e in _pencereler(baslangic, bitis, 15)
        ]

    def otherfinancials(self, baslangic: datetime, bitis: datetime, tipler: list[str]) -> list[IstekPlani]:
        return [
            IstekPlani("GET", f"{self.TABAN}/finance/che/sellers/{self.satici_id}/otherfinancials",
                       {"startDate": _ms(s), "endDate": _ms(e), "transactionTypes": ",".join(tipler),
                        "page": 0, "size": 1000})
            for s, e in _pencereler(baslangic, bitis, 15)
        ]

    def odeme_emirleri(self) -> list[IstekPlani]:
        return [IstekPlani("GET", f"{self.TABAN}/finance/che/sellers/{self.satici_id}/payment-order",
                           {"page": 0, "size": 10})]

    def kargo_fatura_detay(self, fatura_seri_no: str) -> list[IstekPlani]:
        return [IstekPlani("GET",
                           f"{self.TABAN}/finance/che/sellers/{self.satici_id}/cargo-invoice/{fatura_seri_no}/items",
                           {"page": 0, "size": 500},
                           "fatura_seri_no: otherfinancials DeductionInvoices içindeki 'Kargo Faturası' kayıtlarının id'si")]


class HepsiburadaOkumaIstemcisi:
    """Hepsiburada Merchant API - uç noktalar doğrulanmalı (resmî portal sayfası bu çalışmada açılamadı)."""

    TABAN = "https://oms-external.hepsiburada.com"

    def __init__(self, merchant_id: str):
        self.merchant_id = merchant_id

    def muhasebe_islemleri(self, baslangic: str, bitis: str) -> list[IstekPlani]:
        return [IstekPlani("GET", f"{self.TABAN}/transactions/merchantId/{self.merchant_id}",
                           {"beginDate": baslangic, "endDate": bitis, "offset": 0, "limit": 100},
                           "doğrulanmalı")]

    def iadeler(self, baslangic: str, bitis: str) -> list[IstekPlani]:
        return [IstekPlani("GET", f"{self.TABAN}/claims/merchantId/{self.merchant_id}",
                           {"beginDate": baslangic, "endDate": bitis, "offset": 0, "limit": 100},
                           "doğrulanmalı")]
