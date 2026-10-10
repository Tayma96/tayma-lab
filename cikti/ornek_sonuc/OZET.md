> **ÖRNEK VERİ / SİMÜLASYON** - Bu çıktı tamamen sentetik örnek veriden üretilmiştir. Satıcı, sipariş ve tutarlar gerçek değildir. Hiçbir pazaryerine, satıcıya veya kişiye hiçbir şey gönderilmemiştir.

# Hakediş tarama özeti - ÖRNEK Mağaza Ltd. (sentetik)

- Dönem: Temmuz-Eylül 2026  |  Analiz tarihi: 2026-10-10
- Taranan sipariş: **200** (hepsiburada: 40, trendyol: 160)
- Toplam bulgu: 70 / tespit edilen tutar: 8.765,18 TL
- **İtiraza hazır (geri alınabilir) tutar: 8.219,69 TL**
- Güven ağırlıklı beklenen geri kazanım (tahmin): 6.328,18 TL

## Kategori bazında

| Kategori | Tespit | Tespit TL | İtiraza hazır | İtiraza hazır TL | Beklenen TL (tahmin) |
|---|---:|---:|---:|---:|---:|
| İadede geri verilmeyen komisyon | 15 | 1.754,15 TL | 15 | 1.754,15 TL | 1.578,72 TL |
| Hatalı (fazla) desi ile kesilen kargo | 26 | 552,00 TL | 18 | 464,50 TL | 272,90 TL |
| İptal / teslim edilemeyen siparişe kesilen kargo | 11 | 793,00 TL | 7 | 507,00 TL | 430,96 TL |
| Mükerrer (çift) kesinti | 6 | 349,99 TL | 4 | 273,00 TL | 245,70 TL |
| Dayanağı olmayan hizmet / ceza bedeli | 6 | 545,00 TL | 5 | 450,00 TL | 355,50 TL |
| Teslim edilen siparişin ödenmeyen hakedişi | 6 | 4.771,04 TL | 6 | 4.771,04 TL | 3.444,40 TL |
| **TOPLAM** | 70 | 8.765,18 TL | 55 | 8.219,69 TL | 6.328,18 TL |

## Karar dağılımı

| Karar | Açıklama | Adet | Tutar |
|---|---|---:|---:|
| devreden | Paket eşiğinin altında, sonraki döneme devreder | 7 | 285,00 TL |
| dosyalanacak | İtiraz paketine girer | 55 | 8.219,69 TL |
| esik_alti | Tekil bulgu eşiğinin altında | 5 | 34,99 TL |
| incelenmeli | Güven düşük, manuel inceleme | 3 | 225,50 TL |

## Tahmini başarı ücreti (TAHMİN)

- Tüm itirazlar kabul edilirse: net ücret 1.339,26 TL + KDV 267,85 TL (satıcıya kalan: 6.880,43 TL)
- Güven ağırlıklı senaryo: net ücret 1.065,39 TL + KDV 213,08 TL
- Ücret yalnızca geri ödeme sonraki hakedişte görüldüğünde faturalanır.

## İtiraz paketleri (TASLAK, gönderilmedi)

- `itiraz/hepsiburada_iade_komisyonu_itiraz.txt` + `itiraz/hepsiburada_iade_komisyonu_kanit.xlsx`: 3 kayıt, 369,32 TL
- `itiraz/hepsiburada_odenmeyen_hakedis_itiraz.txt` + `itiraz/hepsiburada_odenmeyen_hakedis_kanit.xlsx`: 1 kayıt, 386,14 TL
- `itiraz/trendyol_dayanaksiz_kesinti_itiraz.txt` + `itiraz/trendyol_dayanaksiz_kesinti_kanit.xlsx`: 5 kayıt, 450,00 TL
- `itiraz/trendyol_desi_farki_itiraz.txt` + `itiraz/trendyol_desi_farki_kanit.xlsx`: 18 kayıt, 464,50 TL
- `itiraz/trendyol_iade_komisyonu_itiraz.txt` + `itiraz/trendyol_iade_komisyonu_kanit.xlsx`: 12 kayıt, 1.384,83 TL
- `itiraz/trendyol_iptal_kargo_itiraz.txt` + `itiraz/trendyol_iptal_kargo_kanit.xlsx`: 7 kayıt, 507,00 TL
- `itiraz/trendyol_mukerrer_kesinti_itiraz.txt` + `itiraz/trendyol_mukerrer_kesinti_kanit.xlsx`: 4 kayıt, 273,00 TL
- `itiraz/trendyol_odenmeyen_hakedis_itiraz.txt` + `itiraz/trendyol_odenmeyen_hakedis_kanit.xlsx`: 5 kayıt, 4.384,90 TL
