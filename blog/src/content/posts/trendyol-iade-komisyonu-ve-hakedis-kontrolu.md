---
title: "Trendyol'da İade Komisyonu ve Hakediş Kontrolü: Adım Adım Mutabakat"
description: "İade edilen siparişte komisyon geri geliyor mu, hakedişe nasıl yansıyor? Cari hesap ekstresiyle iade ve komisyon satırlarını eşleştirme rehberi."
date: 2026-10-10
category: "Hakediş"
tags: ["trendyol", "iade", "komisyon", "hakediş", "mutabakat"]
draft: false
aiGenerated: false
sources:
  - title: "Trendyol Developers — Cari Hesap Ekstresi Entegrasyonu (işlem türleri)"
    url: "https://developers.trendyol.com/docs/cari-hesap-ekstresi-entegrasyonu"
  - title: "Trendyol Developers — İadesi Oluşturulan Siparişleri Çekme (getClaims)"
    url: "https://developers.trendyol.com/docs/i%CC%87adesi-olu%C5%9Fturulan-sipari%C5%9Fleri-%C3%A7ekme-getclaims"
  - title: "Trendyol — Ürünümü Nasıl İade Ederim? (müşteri iade sayfası)"
    url: "https://www.trendyol.com/s/trendyol-iade"
  - title: "Mesafeli Sözleşmeler Yönetmeliği (mevzuat.gov.tr)"
    url: "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20237&MevzuatTertip=5&MevzuatTur=7"
  - title: "Verimle — Trendyol Cari Hesap Ekstresi Nasıl Okunur? (ikincil kaynak)"
    url: "https://verimle.com/blog/trendyol-cari-hesap-ekstresi-okuma"
  - title: "Buyboxla — Trendyol Hakediş Takibi (ikincil kaynak)"
    url: "https://buyboxla.com/blog/trendyol-hakedis-takibi"
---

Bir siparişi kargoladınız, ürün teslim edildi, komisyon kesildi… ve birkaç gün sonra müşteri ürünü iade etti. Bu noktada satıcıların en sık sorduğu soru şu: **"Kesilen komisyon bana geri döndü mü, yoksa hem ürünü hem komisyonu mu kaybettim?"**

Bu rehberde Trendyol'da iade edilen bir siparişin hakedişe nasıl yansıdığını, komisyon iadesini cari hesap ekstresinde nasıl doğrulayacağınızı ve fark gördüğünüzde nasıl itiraz dosyası hazırlayacağınızı adım adım anlatıyoruz. Amaç, "bir şeyler eksik ama ne olduğunu bilmiyorum" hissini somut bir kontrol listesine dönüştürmek.

> Trendyol'un satıcı sözleşmesi, ekran adları ve süreçleri zaman zaman değişir. Aşağıdaki adımlar genel mantığı anlatır; panelinizdeki güncel ekran adları farklı olabilir.

## İade bir siparişin hakedişini nasıl değiştirir?

Hakediş, kabaca bir satıştan komisyon, kargo, hizmet bedeli ve varsa diğer kesintiler düşüldükten sonra size ödenen net tutardır. Sipariş iade edildiğinde sistem, satış sırasında oluşan kayıtları **ters yönde** kaydeder:

- Ürün bedeli sizden geri alınır (satış satırının tersi).
- Satışta kesilen komisyon, iade kaydıyla birlikte size geri yansıtılır (komisyonun tersi).
- Kargo maliyetleri ise çoğu senaryoda geri gelmez; üstelik iade kargo ücreti ayrıca yansıyabilir.

Trendyol'un geliştirici dokümantasyonundaki [cari hesap ekstresi işlem türleri](https://developers.trendyol.com/docs/cari-hesap-ekstresi-entegrasyonu) bu yapıyı açıkça gösterir: "Komisyon Pozitif/Negatif Düzeltme", "Hakediş Pozitif/Negatif Düzeltme" gibi düzeltme kayıtları ve vadesi gelen işlemlerden hesaplanan hakediş ödemesi (PaymentOrder) ayrı satır türleridir. Aynı dokümanda dikkat çekici bir kayıt türü daha var: **Komisyon Mutabakat Faturası (CommissionAgreementInvoice)** — satıcının mahsuplaşma yapılacak alacağı olmadığında, iade gelen ürünler için satıcıdan alınan komisyon mutabakat faturası olarak tanımlanıyor. Yani iade sonrası komisyon düzeltmesi her zaman "nakit iade" şeklinde değil, çoğu zaman **mahsuplaşma** şeklinde gerçekleşir.

Bazı ikincil kaynaklar, iade edilen siparişin komisyonunun bir sonraki dönem komisyon faturasından mahsup edildiğini ve iade tarihi ile fatura döneminin örtüşmemesi halinde düzeltmenin bir sonraki döneme sarkabileceğini belirtiyor ([Buyboxla](https://buyboxla.com/blog/trendyol-hakedis-takibi)). Bu, kontrol yaparken **tek bir haftaya bakıp sonuç çıkarmamanız** gerektiği anlamına gelir.

## İade süreci satıcı tarafında nasıl ilerler?

Sürecin zamanlamasını bilmek, hangi haftanın ekstresine bakacağınızı belirler:

1. **Müşteri iade talebi oluşturur.** Trendyol'un müşteri sayfasında iade süresi, ürünün müşteriye ulaşmasından itibaren 15 gün olarak belirtiliyor ([Trendyol iade sayfası](https://www.trendyol.com/s/trendyol-iade)). Yasal cayma hakkı süresi ise [Mesafeli Sözleşmeler Yönetmeliği](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=20237&MevzuatTertip=5&MevzuatTur=7) ile düzenlenir; platformun tanıdığı süre yasal asgariden uzun olabilir.
2. **Ürün size ulaşır ve iade "aksiyon bekliyor" durumuna geçer.** Geliştirici dokümantasyonuna göre iade kayıtlarının durumları arasında Oluşturuldu, Aksiyon Bekliyor, Kabul, Ret, İhtilaflı ve Analizde gibi statüler bulunuyor ([getClaims](https://developers.trendyol.com/docs/i%CC%87adesi-olu%C5%9Fturulan-sipari%C5%9Fleri-%C3%A7ekme-getclaims)).
3. **Onay veya itiraz.** Aynı dokümantasyonda, 48 saat boyunca aksiyon alınmayan iadelerin otomatik olarak kabul edildiği belirtiliyor. Ürün hasarlı, kullanılmış veya eksik geldiyse bu süre içinde "sorun bildir" yoluyla itiraz etmeniz önemlidir; süre geçtikten sonra itiraz şansınız azalır.
4. **Finansal düzeltme.** İade kabul edildiğinde ürün bedeli ve komisyon düzeltmesi cari hesaba işlenir, sonraki hakediş hesaplamasında dikkate alınır.

## Adım adım iade–komisyon mutabakatı

Aşağıdaki yöntem, panelden indirdiğiniz ekstre ve sipariş listesiyle bir tablo programında (Excel, Google E-Tablolar) kolayca uygulanabilir.

### 1. Doğru raporları indirin

- **Cari hesap ekstresi:** Satıcı panelindeki ödeme/fatura bölümünden ilgili dönemleri indirin. İkincil kaynaklar bu ekranın "Ödeme ve Fatura → Ekstre Listeleme" altında olduğunu ve ekstrelerin haftalık dönemlerle oluştuğunu belirtiyor ([Verimle](https://verimle.com/blog/trendyol-cari-hesap-ekstresi-okuma)).
- **İade listesi:** İade/talep yönetimi ekranından, iadesi kabul edilen siparişleri tarih aralığıyla dışa aktarın.
- **Komisyon faturaları:** Fatura listesinden ilgili dönemlerin komisyon faturalarını indirin.

İpucu: İade düzeltmeleri sonraki döneme sarkabildiği için, kontrol ettiğiniz haftanın **en az bir sonraki dönemini** de indirin.

### 2. Sipariş numarasını anahtar yapın

Her üç raporda da sipariş numarası (veya paket numarası) bulunur. Bu sütunu ortak anahtar olarak kullanın. Tablo programında `DÜŞEYARA`/`XLOOKUP` ile iade listesindeki her siparişin ekstredeki satırlarını getirin.

### 3. Her iade için "çift" arayın

Her kabul edilmiş iade için ekstrede şu eşleşmeyi bekleriz:

| Kontrol | Beklenen | Sorun işareti |
|---|---|---|
| Ürün bedeli iadesi | Satış tutarının tersi olarak bir satır | Satır yok veya tutar farklı |
| Komisyon düzeltmesi | Satışta kesilen komisyonun tersi (alacak yönünde) | Satır yok, tutar eksik, iki dönem sonra hâlâ yok |
| İade kargo ücreti | Sözleşmenize göre ayrı bir kesinti satırı | Beklenmeyen veya mükerrer kesinti |
| Mükerrer kayıt | Her siparişte bir kez | Aynı iade için iki kez ürün bedeli düşülmesi |

Komisyon düzeltmesinin tutarını kontrol ederken, **satışta kesilen komisyon tutarını** referans alın; komisyon oranını kendiniz yeniden hesaplamaya çalışmak, kampanya ve kategori farkları nedeniyle yanıltıcı olabilir. Kısmi iadelerde (ör. çok ürünlü siparişte tek ürün) düzeltmenin yalnızca iade edilen ürün satırına ait olması gerekir.

### 4. Net etkiyi hesaplayın

Her iade için basit bir formül kurun:

`Net etki = − Ürün bedeli + Komisyon düzeltmesi − İade kargo ücreti − (varsa) diğer kesintiler`

Bu tutar, o iadenin size gerçek maliyetidir. İade kaynaklı kaybınızı kategori veya ürün bazında toplamak, hangi ürünlerin fiyatına "iade payı" eklemeniz gerektiğini de gösterir. (Fiyatlandırmada kargo kalemini doğru hesaplamak için [desi ve kargo ücreti hataları rehberimize](https://tayma96.github.io/tayma-lab/yazilar/desi-kargo-ucreti-hatalari-nasil-fark-edilir/) göz atın.)

### 5. Farkları listeleyin

"Komisyon düzeltmesi yok" veya "tutar farklı" çıkan siparişleri ayrı bir sekmede toplayın: sipariş no, iade kabul tarihi, satıştaki komisyon tutarı, ekstrede görünen düzeltme, fark.

## Fark bulursanız: itiraz dosyası nasıl hazırlanır?

Trendyol'un resmi itiraz kanalı ve ekran adları panelde değişebildiğinden, buradaki öneriler genel niteliktedir:

- **Önce bekleme süresini doldurun.** Düzeltme bir sonraki döneme sarkıyor olabilir; en az bir sonraki ekstreyi kontrol etmeden talep açmayın.
- **Toplu ve düzenli gönderin.** Tek tek talep yerine sipariş numaralı bir tablo hazırlayın; her satırda beklenen ve görünen tutarı yazın.
- **Kanıt ekleyin.** İlgili ekstre satırları, iade kabul ekranı görüntüsü ve komisyon faturası numarası talebi hızlandırır.
- **Talep numarasını kaydedin** ve sonuçlandığında düzeltmenin gerçekten cari hesaba yansıyıp yansımadığını tekrar kontrol edin. Destek yanıtı tek başına finansal düzeltmenin yapıldığını göstermez.

İnternette "komisyon iadesi için X gün içinde başvurmalısınız" gibi kesin süreler paylaşılıyor; ancak bu sürelerin Trendyol tarafından resmi olarak açıklandığı bir kaynağa ulaşamadık. Güvenli yaklaşım, mutabakatı **her ay düzenli** yapmak ve farkları biriktirmemektir.

## Sık yapılan hatalar

1. **Tek haftaya bakmak:** İade ile komisyon düzeltmesi farklı dönemlere düşebilir.
2. **"Alacak" satırını hata sanmak:** Komisyon düzeltmesinin alacak yönünde görünmesi normaldir; ürün bedelinin borç yönünde görünmesi de öyle.
3. **İade kargo maliyetini hesaba katmamak:** Komisyon geri gelse bile kargo maliyeti çoğu zaman sizde kalır.
4. **48 saati kaçırmak:** Hasarlı/kullanılmış ürün iadesinde otomatik kabul gerçekleşirse itiraz imkânınız daralır.
5. **API ve panel saat farkı:** API ile kendi raporunu üreten satıcılar için not: geliştirici dokümanına göre iade tarihleri GMT olarak döner; panelle eşlemek için GMT+3'e çevirmek gerekir.

## Kısa kontrol listesi

- [ ] Kontrol edilen dönem + bir sonraki dönemin ekstresi indirildi
- [ ] İade listesi ve komisyon faturaları indirildi
- [ ] Her iade için ürün bedeli ve komisyon düzeltmesi eşleşti
- [ ] İade kargo ve diğer kesintiler sözleşmeyle karşılaştırıldı
- [ ] Farklar sipariş numaralı tabloda toplandı, talep numarası kaydedildi

## Sık sorulan sorular

**İade edilen siparişin komisyonu otomatik geri gelir mi?**
Genel işleyişte iade kabul edildiğinde komisyon düzeltmesi otomatik olarak cari hesaba yansır; ancak zamanlama ve mahsuplaşma şekli dönemlere göre değişebilir. Gelmediyse yukarıdaki adımlarla kontrol edip talep açın.

**Kargo ücreti de geri gelir mi?**
Çoğu senaryoda hayır. İade kargo ücretinin kimden ve hangi tarifeyle alındığı sözleşmenize ve iade nedenine bağlıdır; panelinizdeki güncel koşulları kontrol edin.

**Hizmet bedeli iade edilir mi?**
İkincil kaynaklar bu konuda farklı bilgiler veriyor; resmi bir açıklamaya ulaşamadık. Satıcı sözleşmenizi ve panel duyurularını esas alın.

---

> **Önemli:** Bu yazı bilgilendirme amaçlıdır, güncel kuralları platformdan doğrulayın. Oranlar, ekran adları ve süreler değişebilir; muhasebe kayıtları için mali müşavirinize danışın.
