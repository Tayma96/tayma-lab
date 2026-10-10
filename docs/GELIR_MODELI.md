# Gelir modeli: yalnızca başarı ücreti

> Buradaki oranlar, eşikler ve senaryolar **öneri / tahmin**dir. Rakamlar `cikti/ornek_sonuc/` altındaki
> **ÖRNEK VERİ (sentetik) simülasyonundan** alınmıştır. Ekilen hata oranları uydurmadır; gerçek bir satıcının
> ne kadar alacağı olduğunu göstermez. Tek dış emsal: ABD'de Amazon FBA tazmin servisleri (GETIDA, Seller
> Investigators) geri alınan tutarın **%25**'ini alıyor ve aylık ücret almıyor
> ([AMZFinder](https://www.amzfinder.com/blog/getida-review/),
> [bagengine](https://bagengine.com/articles/fba-reimbursement-services-getida-seller-investigators-dimetyd-compared)).

## 1. Özet

| Bileşen | Öneri |
|---|---|
| Kanca | **Ücretsiz tarama**: "Trendyol / Hepsiburada size ne kadar borçlu?" raporu. Kategori bazında tutar ve örnek bulgular gösterilir; itiraz paketleri ücretli adımda açılır. |
| Standart oran | Geri alınan tutarın **%25**'i (+KDV) |
| Hacim oranı | Takvim ayında tahsil edilen tutarın **50.000 TL'yi aşan kısmına %20** (kademeli, uçurum etkisi yok) |
| Ödenmeyen hakediş | **%10** (özel oran). Bu para çoğunlukla "kayıp" değil "gecikme"; %25 almak satıcıya adil görünmez ve itibar riski taşır. |
| Ne zaman faturalanır | **Yalnızca** düzeltme sonraki hakediş / cari hesap ekstresinde görüldüğünde (`tahsil_edildi`). Kabul edildi ama yansımadı → ücret yok. |
| Aylık ücret | Yok (ileride isteğe bağlı "sürekli izleme" paketi düşünülebilir) |
| Tahsilat | Onboarding'de kayıtlı kart (iyzico Kart Saklama / PayTR Kart Saklama API), aylık e-Arşiv fatura + otomatik çekim |

Parametreler `config.yaml > ucret` altında: `standart_oran: 0.25`, `hacim_orani: 0.20`, `hacim_esigi_tl: 50000`,
`kural_oranlari.odenmeyen_hakedis: 0.10`, `kdv_orani: 0.20` (KDV oranı mali müşavirle **doğrulanmalı**).

## 2. Minimum tutar eşikleri (öneri)

| Eşik | Değer | Gerekçe (tahmin) |
|---|---|---|
| `min_bulgu_tutari_tl` | **10 TL** | Bunun altındaki tekil satırlar (ör. 1 desi farkı ≈ 5-8 TL örnek tarifede) itirazı kalabalıklaştırır, pazaryeri tarafında "önemsiz" görülüp tüm paketin reddedilme riskini artırır. Ücreti 2,5 TL'nin altında kalır. Bulgu silinmez, raporda `esik_alti` olarak görünür. |
| `min_guven` | **0,5** | Belirsiz kurallar (teslim edilemeyen siparişe kargo, bilinmeyen kesinti tipi) satıcıya "incelenmeli" diye gösterilir, otomatik pakete girmez. Zayıf itirazlar satıcının pazaryeri nezdindeki güvenilirliğini düşürür. |
| `min_paket_tutari_tl` | **250 TL** | Bir paket (platform + kategori) hazırlama, satıcı kontrolü ve takip için ~15-20 dk emek varsayımı. %25 ile ~62,5 TL ücret, bu emeği karşılayan alt sınır. Altında kalan bulgular `devreden` olur, sonraki dönemle birleşir. |
| `min_donem_tutari_tl` | **500 TL** / satıcı / dönem | Ödeme sağlayıcı komisyonu, fatura ve destek maliyetinden sonra anlamlı kalması için en az ~125 TL (+KDV) ücret. Altında: ücretsiz rapor verilir, itiraz yürütülmez. |

Simülasyonda bu eşiklerin etkisi: 70 bulgu → 55 dosyalanacak (8.219,69 TL), 7 devreden (285,00 TL),
5 eşik altı (34,99 TL), 3 incelenmeli (225,50 TL).

## 3. Süreç: tespit → itiraz → tahsil → fatura

1. **Onboarding:** hizmet sözleşmesi (başarı ücreti tanımı, "tahsil edildi" tanımı = düzeltme kaydının ekstrede
   görülmesi), KVKK aydınlatma metni, salt okunur API anahtarı ya da Excel yükleme, kartın ödeme sağlayıcıda
   saklanması (kart bilgisi bizde tutulmaz; token tutulur).
2. **Ücretsiz tarama** → rapor. Satıcı itiraz yürütmeyi onaylar.
3. **İtiraz paketleri** satıcıya teslim edilir; satıcı kontrol edip **kendi panelinden** gönderir → `itiraz_edildi`.
4. **Sonraki hakediş dönemi** verisi çekilir; düzeltme kayıtları vakalarla eşleşir → `tahsil_edildi`.
5. **Ay sonu:** `billing.fatura_taslagi` → kontrol → e-Arşiv fatura (yetkili entegratör üzerinden) → satıcıya
   bildirim ve **3 iş günü itiraz penceresi** (öneri) → kayıtlı karttan çekim
   (iyzico: kayıtlı kartla ödeme `cardUserKey` + `cardToken`; PayTR: `utoken` + `ctoken`).
6. **Ödeme alınamazsa:** 3 deneme + e-posta hatırlatma, sonrasında yeni tarama/itiraz hizmeti durdurulur.
   Kart yoksa, ilk tahsilattan önce kart kaydı zorunlu tutulur (tahsilat riskini azaltmak için).

Bu repoda 5. adımın yalnızca **taslak** kısmı vardır; fatura kesme ve karttan çekim **uygulanmamıştır**.

## 4. Simülasyondan örnek hesaplar (ÖRNEK VERİ)

### Örnek 1: Simülasyon satıcısı (200 sipariş, 3 ay)
Varsayımsal sonraki dönemde 41 vaka hakedişe yansıdı:

| Kalem | Tutar |
|---|---:|
| Tahsil edilen toplam | 7.496,62 TL |
| - kademeli orana tabi (komisyon, kargo, kesinti) | 2.725,58 TL × %25 = 681,40 TL |
| - ödenmeyen hakediş (özel oran) | 4.771,04 TL × %10 = 477,10 TL |
| **Net ücret** | **1.158,49 TL** (efektif %15,4) |
| KDV (%20) | 231,70 TL |
| Fatura toplamı | 1.390,19 TL |
| Satıcıya net kalan | 6.338,13 TL |

Karşılaştırma: tüm tahsilata düz %25 uygulansaydı ücret 1.874,16 TL olurdu; ödenmeyen hakedişe düşük oran
satıcıya 715 TL daha az fatura demek ve "zaten gelecek parayı faturalıyorlar" itirazını önler.

Tarama aşamasında gösterilen tahmini ücret: tüm itirazlar kabul edilirse 1.339,26 TL + KDV;
güven ağırlıklı senaryoda 1.065,39 TL + KDV (**tahmin**).

### Örnek 2: Hacim kademesi (varsayımsal ajans / büyük satıcı)
Ayda 80.000 TL tahsilat: 50.000 × %25 + 30.000 × %20 = **18.500 TL** net (efektif %23,1), + 3.700 TL KDV.
150.000 TL tahsilat: 12.500 + 20.000 = **32.500 TL** (efektif %21,7).

### Örnek 3: Küçük satıcı
Dönem toplamı 400 TL (< 500 TL eşik) → itiraz yürütülmez, ücretsiz rapor ve "kendin yap" itiraz metni verilir.
Eşik üstü bir dönemde 3.000 TL tahsil edilirse ücret 750 TL + 150 TL KDV.

## 5. Riskler ve açık sorular

- **Gerçek başarı oranı bilinmiyor.** Simülasyondaki kabul oranları varsayımdır. İlk iş: 5 pilot satıcının
  gerçek raporlarıyla elle doğrulama (bkz. fikir raporu Öneri 2).
- "Tahsil edildi" kanıtı pazaryerinin düzeltmeyi hangi kayıt tipiyle attığına bağlı (doğrulanmalı).
- Satıcı itirazı kendi gönderdiği için "biz olmasak da bulurdu" itirazı → sözleşmede "rapordaki bulgu kaynaklı
  geri ödemeler ücretlidir" ve 90 günlük kapsam penceresi (öneri).
- Rakiplerin (Tiyasis, EZV, Bulutegra, KarPanel gibi abonelik araçları) modeli kopyalaması.
- Ödeme sağlayıcı komisyonları ve e-Arşiv maliyeti marjdan düşülmeli (oranlar **doğrulanmalı**).
