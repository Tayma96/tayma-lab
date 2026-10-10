> **ÖRNEK VERİ / SİMÜLASYON** - Bu çıktı tamamen sentetik örnek veriden üretilmiştir. Satıcı, sipariş ve tutarlar gerçek değildir. Hiçbir pazaryerine, satıcıya veya kişiye hiçbir şey gönderilmemiştir.

# Uçtan uca simülasyon (örnek veri)

Varsayımlar (SİMÜLASYON): satıcının itiraza hazır tüm paketleri kendi paneli üzerinden gönderdiği varsayılmıştır; pazaryeri yanıtları ve sonraki dönem düzeltme kayıtları SENTETİKTİR (varsayımsal kabul oranları, gerçek başarı oranı değildir).

## Vaka durumları

| Durum | Adet | Talep TL | Tahsil TL |
|---|---:|---:|---:|
| itiraz_edildi | 9 | 371,50 TL | 0,00 TL |
| kabul | 1 | 233,82 TL | 0,00 TL |
| red | 4 | 97,50 TL | 0,00 TL |
| tahsil_edildi | 41 | 7.516,87 TL | 7.496,62 TL |
| **Toplam** | 55 | 8.219,69 TL | 7.496,62 TL |

## Kategori bazında tahsilat

| Kategori | Vaka | Talep TL | Tahsil TL | Tahsil oranı |
|---|---:|---:|---:|---:|
| Dayanağı olmayan hizmet / ceza bedeli | 5 | 450,00 TL | 390,00 TL | %87 |
| Hatalı (fazla) desi ile kesilen kargo | 18 | 464,50 TL | 177,75 TL | %38 |
| İadede geri verilmeyen komisyon | 15 | 1.754,15 TL | 1.520,33 TL | %87 |
| İptal / teslim edilemeyen siparişe kesilen kargo | 7 | 507,00 TL | 364,50 TL | %72 |
| Mükerrer (çift) kesinti | 4 | 273,00 TL | 273,00 TL | %100 |
| Teslim edilen siparişin ödenmeyen hakedişi | 6 | 4.771,04 TL | 4.771,04 TL | %100 |

Eşleşmeyen düzeltme kaydı: 1 adet (33,00 TL) - vaka ile ilişkisi olmadığı için ücretlendirilmez.

## Başarı ücreti fatura taslağı

- Fatura no: `TASLAK-2026-0001` (TASLAK - kesilmedi, gönderilmedi, kart çekimi yapılmadı)
- Tahsil edilen (hakedişe yansıyan) toplam: **7.496,62 TL**
- Kademeli orana (%25 / hacim üstü %20) tabi tutar: 2.725,58 TL
- Özel oranlı tutar (ödenmeyen hakediş, %10): 4.771,04 TL -> ücret 477,10 TL
- Net ücret: 1.158,49 TL (efektif oran %15.4)
- KDV: 231,70 TL  |  Toplam fatura: **1.390,19 TL**
- Satıcıya net kalan: 6.338,13 TL
- Ödeme yöntemi: kayitli_kart (iyzico / PayTR) - SIMULASYON: gerçek çekim yapılmaz
