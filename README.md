# tayma-lab / hakedis

**Trendyol ve Hepsiburada satıcıları için hakediş geri kazanım aracı - proje iskeleti ve simülasyon.**

Satıcının sipariş, iade, kargo faturası ve cari hesap ekstresi (hakediş) verilerini karşılaştırarak
pazaryerinin satıcıya borçlu kalmış olabileceği tutarları bulur, her bulguyu kanıtıyla puanlar, Türkçe itiraz
metni + kanıt Excel'i hazırlar, vakaları takip eder, geri ödeme sonraki hakedişte görüldüğünde başarı ücreti
fatura taslağı üretir. İş modeli: **yalnızca başarı ücreti** (geri alınan tutarın %20-25'i, bkz.
[docs/GELIR_MODELI.md](docs/GELIR_MODELI.md)).

> ⚠️ **Uyarı**
> - Bu repodaki tüm veriler (`ornek_veri/`, `cikti/ornek_sonuc/`) **ÖRNEK VERİ - SENTETİK**tir. Satıcı, sipariş,
>   barkod ve takip numaraları uydurmadır ve `ORNEK-` önekiyle başlar.
> - Kod **hiçbir pazaryerine, satıcıya veya kişiye hiçbir şey göndermez.** Trendyol/Hepsiburada API istemcileri
>   yalnızca istek planı üreten taslaklardır ve ağ çağrısı yapmaz (`CANLI_API_KAPALI = True`).
> - Pazaryeri politikasıyla ilgili belirsiz kurallar `config.yaml` içinde parametredir ve **doğrulanmalı** olarak
>   işaretlidir ([docs/KAYNAKLAR.md](docs/KAYNAKLAR.md)). Bu yazılım hukuki/mali danışmanlık değildir.

## Ne kontrol ediliyor?

| Kontrol | Modül |
|---|---|
| İadede geri verilmeyen / eksik verilen komisyon | `hakedis/rules/iade_komisyonu.py` |
| Ürün desisinden fazla desi ile kesilen kargo (gönderi + iade) | `hakedis/rules/desi_farki.py` |
| İptal / tedarik edilemeyen / teslim edilemeyen siparişe kesilen kargo | `hakedis/rules/iptal_kargo.py` |
| Mükerrer kargo veya kesinti | `hakedis/rules/mukerrer_kesinti.py` |
| Dayanağı olmayan hizmet / ceza bedeli | `hakedis/rules/dayanaksiz_kesinti.py` |
| Teslim edilmiş ama ödenmemiş hakediş | `hakedis/rules/odenmeyen_hakedis.py` |

Akışın tamamı (mermaid diyagramı dahil): [docs/AKIS.md](docs/AKIS.md)

## Kurulum

```bash
git clone https://github.com/Tayma96/tayma-lab && cd tayma-lab
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # veya: pip install -e ".[dev]"
pytest -q
```

## Kullanım

```bash
# 1) Tarama: bulgular + itiraz taslakları + vaka listesi
python -m hakedis scan --input ornek_veri/ --out cikti/

# 2) Uçtan uca simülasyon: tarama + (varsayımsal) itiraz + sonraki dönem tahsilat tespiti + ücret fatura taslağı
python -m hakedis simule --input ornek_veri/ --sonraki ornek_veri/sonraki_donem/ --out cikti/ornek_sonuc/

# 3) Vaka durumunu elle güncelleme
python -m hakedis durum --vakalar cikti/ --vaka TY-IKO-0001 --yeni itiraz_edildi

# 4) Gerçek akışta sonraki dönem verisiyle tahsilat tespiti
python -m hakedis tahsilat --vakalar cikti/ --sonraki <sonraki_donem_klasoru> --out cikti/

# Örnek veriyi yeniden üretme (sabit seed)
python scripts/ornek_veri_uret.py
```

Girdi klasörü yapısı: `<girdi>/trendyol/` (`siparisler`, `urunler`, `settlements`, `otherfinancials`,
`kargo_fatura_detay`, `claims` - `.csv` veya `.xlsx`) ve `<girdi>/hepsiburada/` (`siparisler`, `urunler`,
`muhasebe_islemleri`, `iadeler`). Panel Excel başlıkları `config.yaml > kolon_eslemesi` ile eşlenir.

Çıktılar: `OZET.md`, `ozet.json`, `bulgular.csv/.xlsx`, `kategori_ozeti.csv`, `itiraz/*_itiraz.txt` +
`itiraz/*_kanit.xlsx`, `vakalar.csv/.json`; simülasyonda ayrıca `SIMULASYON.md`, `tahsilat_eslesmeleri.csv`,
`fatura_taslagi.json`.

## Örnek simülasyon sonucu (ÖRNEK VERİ)

200 sentetik sipariş (Trendyol 160, Hepsiburada 40), 70 bilerek eklenmiş hata. Ayrıntı:
[cikti/ornek_sonuc/OZET.md](cikti/ornek_sonuc/OZET.md), [cikti/ornek_sonuc/SIMULASYON.md](cikti/ornek_sonuc/SIMULASYON.md)

| Kategori | Tespit | Tespit TL | İtiraza hazır TL |
|---|---:|---:|---:|
| İadede geri verilmeyen komisyon | 15 | 1.754,15 | 1.754,15 |
| Hatalı (fazla) desi | 26 | 552,00 | 464,50 |
| İptal / teslim edilemeyen siparişe kargo | 11 | 793,00 | 507,00 |
| Mükerrer kesinti | 6 | 349,99 | 273,00 |
| Dayanaksız hizmet/ceza bedeli | 6 | 545,00 | 450,00 |
| Ödenmeyen hakediş | 6 | 4.771,04 | 4.771,04 |
| **Toplam** | **70** | **8.765,18** | **8.219,69** |

Varsayımsal sonraki dönemde 7.496,62 TL hakedişe yansır → başarı ücreti 1.158,49 TL + KDV (taslak).

## Proje yapısı

```
hakedis/
  ingest/        okuyucu.py, trendyol_dosya.py, hepsiburada_dosya.py, api_istemci.py (STUB, çağrı yapmaz)
  normalize.py   ortak şema
  rules/         6 kontrol + ortak.py
  puanlama.py    güven, beklenen TL, çakışma önleme, eşikler
  appeal.py      Türkçe itiraz metni + kanıt Excel'i (LLM opsiyonel, kapalı)
  takip.py       vaka durum makinesi
  tahsilat.py    sonraki dönemde geri ödeme tespiti
  billing.py     başarı ücreti + fatura taslağı
  report.py      özet ve raporlar
  cli.py         komut satırı
config.yaml      eşikler, güven puanları, politika parametreleri (doğrulanmalı)
ornek_veri/      SENTETİK örnek veri + beklenen_bulgular.csv
cikti/ornek_sonuc/  örnek simülasyon çıktısı
docs/            AKIS.md, GELIR_MODELI.md, KAYNAKLAR.md
scripts/         ornek_veri_uret.py
tests/           pytest
```

## Yol haritası

1. **Pilot doğrulama (önce bu):** 5 gerçek satıcının raporlarını (yazılı onay + KVKK ile) offline taramak,
   itirazları satıcıların kendisinin göndermesi, gerçek kabul oranlarını ve düzeltme kayıt tiplerini görmek;
   `config.yaml` güven puanlarını ve "doğrulanmalı" parametreleri kalibre etmek.
2. Gerçek panel Excel başlıklarına göre `kolon_eslemesi`; satıcıya özel kargo tarifesi girişi.
3. Trendyol salt okunur API entegrasyonu (ayrı güvenlik incelemesi, anahtarların şifreli saklanması, rate limit).
4. Web paneli (FastAPI + Postgres + kuyruk; RN Web / Next.js), satıcı onay ekranı, vaka panosu.
5. Hepsiburada resmî dokümanla doğrulama ve entegrasyon.
6. e-Arşiv fatura (yetkili entegratör) + iyzico/PayTR kayıtlı kart tahsilatı.
7. İsteğe bağlı LLM ile itiraz metni üslup iyileştirme (tutarlar her zaman şablondan).

## Lisans / sorumluluk

İskelet ve araştırma amaçlıdır. Gerçek satıcı verisi bu repoya konmaz (`.gitignore`). Pazaryeri politikaları
değişebilir; her kural kullanılmadan önce güncel sözleşme ve dokümanla teyit edilmelidir.
