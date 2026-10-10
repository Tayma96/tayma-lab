# ÖRNEK VERİ - SENTETİK

Bu klasördeki **tüm** dosyalar `scripts/ornek_veri_uret.py` ile sabit tohum (seed=20261010) kullanılarak
üretilmiş **sentetik örnek veridir**. Gerçek bir satıcıya, siparişe, müşteriye veya kişiye ait değildir.
Tüm kimlikler `ORNEK-` önekiyle başlar. Tutarlar ve kargo tarifesi uydurmadır.

- `trendyol/` : Trendyol Partner API yanıt alanlarını taklit eden CSV/XLSX dosyaları (160 sipariş).
  `siparisler.xlsx` panel Excel fallback senaryosunu (Türkçe başlıklar) taklit eder.
- `hepsiburada/` : Hepsiburada muhasebe/sipariş verisini taklit eden CSV dosyaları (40 sipariş, alan adları doğrulanmalı).
- `beklenen_bulgular.csv` : Bilerek eklenen hatalar ve tutarları (testlerde doğruluk kontrolü için).
- `sonraki_donem/` : Sonraki hakediş dönemi için **VARSAYIMSAL** pazaryeri yanıtları/düzeltme kayıtları
  (gerçek başarı oranı değildir).
