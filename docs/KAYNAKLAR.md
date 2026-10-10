# Kaynaklar: doğrulanan ve doğrulanması gerekenler

Erişim tarihi: 10.10.2026. "Doğrulandı", bilginin **resmî dokümanda** görüldüğü anlamına gelir; satıcı
sözleşmesi ve güncel panel davranışı yine de pilotta teyit edilmelidir.

## Resmî dokümanda doğrulananlar (Trendyol Developers)

| Bilgi | Kaynak |
|---|---|
| Cari hesap ekstresi: `settlements`, `otherfinancials`, `payment-order` servisleri; işlem tipleri (Sale, Return, CommissionPositive/Negative, SellerRevenuePositive/Negative, DeliveryFee, DeductionInvoices, PaymentOrder, FinancialItem, CommissionAgreementInvoice…); tarih aralığı ≤ 15 gün; finansal kayıtlar teslimden sonra oluşur; ödeme emri istisnalar hariç her çarşamba; Return kaydında `commissionAmount` (+) / `sellerRevenue` (−) | https://developers.trendyol.com/docs/cari-hesap-ekstresi-entegrasyonu |
| `otherfinancials` `transactionSubType=PlatformServiceFee` (platform hizmet bedeli filtresi) | aynı sayfa |
| Kargo faturası kalemleri: `cargo-invoice/{invoiceSerialNumber}/items`, alanlar `shipmentPackageType`, `parcelUniqueId`, `orderNumber`, `amount`, `desi` | https://developers.trendyol.com/docs/kargo-faturas%C4%B1-detaylar%C4%B1 |
| Sipariş paketleri v2 (`/v2/orders`), 15.10.2026'dan itibaren zorunlu; statüler (Created … Cancelled, Delivered, UnDelivered, Returned, UnSupplied …) | https://developers.trendyol.com/docs/sipari%C5%9F-paketlerini-%C3%A7ekme-getshipmentpackages |
| İadeler (getClaims) ve `claimItemStatus` değerleri (Accepted, Rejected, Unresolved…) | https://developers.trendyol.com/docs/i%CC%87adesi-olu%C5%9Fturulan-sipari%C5%9Fleri-%C3%A7ekme-getclaims |
| Ürün `dimensionalWeight` (desi) alanı | https://developers.trendyol.com/docs/%C3%BCr%C3%BCn-filtreleme-filterproducts |
| Basic Auth + `User-Agent` zorunlu, API bilgisi panelde yalnız ana kullanıcıya görünür | https://developers.trendyol.com/v3.0/docs/getting-started-1 |
| iyzico kart saklama / kayıtlı kartla ödeme | https://docs.iyzico.com/ek-servisler/kart-saklama |
| PayTR kart saklama / kayıtlı karttan ödeme | https://dev.paytr.com/direkt-api/kart-saklama-api/kayitli-karttan-odeme |

## Doğrulanmalı (ikincil kaynak veya varsayım → `config.yaml` parametresi)

| Konu | Mevcut bilgi | Kaynak | Parametre |
|---|---|---|---|
| Trendyol iadede komisyonu geri veriyor mu? | Blog: iptal/iade komisyonu nakit değil, sonraki komisyon faturasından mahsupla döner. Resmî Return işaret tablosu bunu destekliyor. | https://ecomiro.com/tr/bilgi/trendyol-komisyon-iadesi | `kurallar.iade_komisyonu.iadede_komisyon_iade_edilir` |
| Desi toleransı | Resmî bir tolerans bulunamadı; kargolar desiyi üst tama yuvarlıyor (ikincil kaynak). | https://saticiportali.com/trendyol-hatali-desi-itirazi-nasil-yapilir/ | `kurallar.desi_farki.tolerans_desi` |
| Desi itirazı yolu ve süresi | İkincil kaynaklar: canlı destek + Excel listesi; bazı kaynaklar aynı gün / 3 iş günü gibi süreler veriyor; resmî süre bulunamadı. | saticiportali.com (yukarıda), https://tiyasis.com/trendyol-desi-itirazi | itiraz son tarihi henüz parametre değil; pilotta netleşmeli |
| Ceza puanı itiraz süresi 3 iş günü | Yalnızca ikincil kaynak | https://ecomiro.com/tr/bilgi/trendyol-komisyon-iadesi | - |
| Kargo tarifesi (desi → TL) | **Örnek değerler**, gerçek tarife değil | - | `kargo_tarifesi` |
| Kesinti açıklama metinleri ("Termin Gecikme Bedeli", "Tedarik Edememe Bedeli"…) | Örnek adlar | - | `kurallar.dayanaksiz_kesinti.*`, `mukerrer_kesinti.siparis_basina_tekil_kesintiler` |
| Teslim edilemeyen siparişte kargo kime ait? | Bilinmiyor → düşük güven | - | `kurallar.iptal_kargo.incelenecek_durumlar`, `guven.iptal_kargo_teslim_edilemedi` |
| Düzeltmenin hangi kayıt tipiyle geldiği (CommissionNegative, FinancialItem…) | Doküman tipleri tanımlıyor ama itiraz sonrası hangisinin kullanıldığı belirsiz | cari hesap ekstresi sayfası | `tahsilat.eslestirme` |
| Panel Excel başlıkları | Örnek | - | `kolon_eslemesi` |
| Hepsiburada muhasebe/iade uç noktaları ve alanları | Resmî portal sayfası açılamadı; üçüncü taraf SDK | https://github.com/loncadev/lonca/tree/main/sdks/hepsiburada | `hepsiburada.islem_tipi_eslemesi` |
| Hizmet faturası KDV oranı %20 | Mali müşavirle teyit | - | `ucret.kdv_orani` |
| Kural güven puanları ve simülasyondaki kabul oranları | **Tahmin / varsayım** | - | `guven.*` |
| Başarı ücreti %20-25 | Amazon emsali (AMZFinder, bagengine); Türkiye'de emsal bulunamadı | fikir raporu | `ucret.*` |
