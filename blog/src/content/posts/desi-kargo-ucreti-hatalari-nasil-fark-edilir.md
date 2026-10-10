---
title: "Desi ve Kargo Ücreti Hataları Nasıl Fark Edilir? Satıcı İçin Kontrol Rehberi"
description: "Desi nasıl hesaplanır, hatalı desi kesintisi nasıl tespit edilir ve itiraz için hangi kanıtlar gerekir? Pazaryeri satıcıları için adım adım kontrol."
date: 2026-10-10
category: "Kargo"
tags: ["desi", "kargo", "trendyol", "itiraz", "hakediş"]
draft: false
aiGenerated: false
sources:
  - title: "Sentos — Desi Hesaplama Nasıl Yapılır? (formül ve yurt içi/yurt dışı bölen)"
    url: "https://www.sentos.com.tr/kargo-desi-bilgisi-nasil-hesaplanir/"
  - title: "Tiyasis — Trendyol Desi İtirazı Nasıl Yapılır? (ölçüm ve kanıt önerileri)"
    url: "https://tiyasis.com/trendyol-desi-itirazi"
  - title: "Ecomiro — Trendyol Desi İtirazı (yuvarlama ve süre iddiaları)"
    url: "https://ecomiro.com/tr/bilgi/kargo-itirazi-nasil-yapilir"
  - title: "Yengeç — 2026 Trendyol Kargo Ücretleri ve Barem uygulaması"
    url: "https://yengec.co/blog/trendyol-kargo-ucretleri/"
  - title: "Verimle — Trendyol Haksız Kesinti İtirazı"
    url: "https://verimle.com/blog/trendyol-haksiz-kesinti-itiraz"
  - title: "Trendyol Developers — Cari Hesap Ekstresi Entegrasyonu"
    url: "https://developers.trendyol.com/docs/cari-hesap-ekstresi-entegrasyonu"
---

Pazaryerinde kârı sessizce eriten kalemlerden biri kargo ücretidir. Çoğu satıcı komisyonu ürün kartında görür, ama kargo kesintisi siparişten günler sonra cari hesaba düşer ve "zaten böyleymiş" diye geçilir. Oysa kargo şubesinde pakete yanlış desi yazılması, aynı ürünü göndermenize rağmen bazı siparişlerde kargo maliyetinizin neden yükseldiğinin en yaygın açıklamalarından biridir.

Bu rehberde desinin nasıl hesaplandığını, hatalı desiyi raporlardan nasıl yakalayacağınızı ve itiraz ederken hangi kanıtları toplamanız gerektiğini anlatıyoruz. Kargo tarifelerine ait rakamlar sık değiştiği için bu yazıda **güncel fiyat tablosu vermiyoruz**; panelinizdeki anlaşmalı kargo listesini esas alın.

## Desi nedir, nasıl hesaplanır?

Desi, paketin kapladığı hacmi ağırlık birimine çeviren bir ölçüdür. Kargo firmaları büyük ama hafif bir koliyle küçük ama ağır bir paketi aynı fiyattan taşımak istemediği için hem gerçek ağırlığa hem hacme bakar.

Yurt içi gönderilerde yaygın olarak kullanılan formül:

`Desi = (En × Boy × Yükseklik, cm) ÷ 3000`

Ardından **gerçek ağırlık (kg) ile desi karşılaştırılır ve büyük olan üzerinden** ücretlendirme yapılır ([Sentos](https://www.sentos.com.tr/kargo-desi-bilgisi-nasil-hesaplanir/)). Aynı kaynak, yurt dışı gönderilerde bölenin 5000 (bazen 6000) olabildiğini belirtiyor.

İki önemli uyarı:

- **Bölen ve yuvarlama kuralı taşıyıcı sözleşmesine göre değişebilir** ([Tiyasis](https://tiyasis.com/trendyol-desi-itirazi)). Hesabı kendi güncel sözleşmenizdeki kuralla yapın.
- Bazı kaynaklar paketlerin **bir üst tam desiye yuvarlandığını** (ör. 0,70 desinin 1 desi olarak faturalandığını) belirtiyor ([Ecomiro](https://ecomiro.com/tr/bilgi/kargo-itirazi-nasil-yapilir)). Kendi kesintilerinizi kontrol ederken yuvarlamayı hesaba katmazsanız, aslında doğru olan kesintileri hatalı sanabilirsiniz.

### Varsayımsal bir örnek

Ölçüleri 30 × 20 × 15 cm, ağırlığı 1,2 kg olan bir koli düşünelim (rakamlar yalnızca örnektir):

- Hacim: 30 × 20 × 15 = 9.000 cm³
- Desi: 9.000 ÷ 3000 = 3
- Gerçek ağırlık 1,2 kg < 3 desi → ücretlendirme **3 desi** üzerinden yapılır.

Aynı ürünü 32 × 22 × 18 cm'lik bir koliye koyarsanız: 12.672 ÷ 3000 ≈ 4,22 → yuvarlama kuralına göre **5 desi** olarak faturalanabilir. Birkaç santimlik koli farkı, tarifede bir üst basamağa geçmenize yol açabilir.

## Ürünün değil, paketin ölçüsü önemlidir

En sık yapılan hata, ürün kartına ürünün kendi ölçülerini girip kargo kesintisini buna göre beklemektir. Taşıyıcı **kapanmış, gönderime hazır koliyi** ölçer; dolgu malzemesi, çift kat koli ve balonlu naylon hacmi değiştirir ([Tiyasis](https://tiyasis.com/trendyol-desi-itirazi)). Bu yüzden:

- Her ürün (veya ürün kombinasyonu) için **kullandığınız standart koliyi** belirleyin.
- Kolinin dış ölçülerini ve dolu ağırlığını bir kez ölçüp tabloya yazın.
- Çok kolili gönderilerde her koliyi ayrı kaydedin.

Bu "referans desi tablosu", hem fiyatlandırmada hem de itirazda en güçlü dayanağınız olacaktır.

## Barem uygulaması: Her kargo satırı desiye göre hesaplanmaz

Trendyol'da düşük tutarlı siparişlerde desi yerine sabit "barem" fiyatları uygulanabildiği biliniyor. Ancak eşik tutarlar konusunda kaynaklar farklı bilgiler veriyor: bir kaynak 300 TL altını ([Yengeç](https://yengec.co/blog/trendyol-kargo-ucretleri/)), bir diğeri 350 TL altı ve 10 desiye kadar gönderileri ([Ecomiro](https://ecomiro.com/tr/bilgi/kargo-itirazi-nasil-yapilir)) anlatıyor. Eşikler dönem dönem güncellendiği için **panelinizdeki güncel barem tablosunu** esas alın.

Kontrol açısından önemi şu: Barem kapsamındaki bir siparişte desi hatası genellikle tutara yansımaz; asıl risk **barem dışı siparişlerde ve iade gönderilerinde** ortaya çıkar. Bazı satıcı kaynakları, iade gönderilerinde de yanlış desi girilebildiğine ve bunun maliyeti katladığına dikkat çekiyor.

## Hatalı desi nasıl fark edilir? 5 adımlı kontrol

### 1. Kargo kesintilerini sipariş bazında dışa aktarın

Cari hesap ekstresi ve kargo faturası detaylarını indirin. Trendyol'un [cari hesap ekstresi dokümantasyonu](https://developers.trendyol.com/docs/cari-hesap-ekstresi-entegrasyonu), kesinti ve faturaların ayrı işlem türleri olarak tutulduğunu gösteriyor; amacınız her siparişin kargo tutarını ve mümkünse faturalanan desiyi tek tabloda görmek.

### 2. Referans desinizle karşılaştırın

Her siparişin ürün(ler)ini referans tablonuzdaki koli desisiyle eşleştirin. Faturalanan desi ile beklenen desi arasına bir "fark" sütunu ekleyin.

### 3. Aykırı değerleri filtreleyin

Aynı ürün aynı koliyle gönderilmesine rağmen farklı desiden faturalanan siparişler en net hata adaylarıdır. Şunlara özellikle bakın:

- Beklenenden **iki veya daha fazla desi** yüksek satırlar (tek desilik farklar yuvarlamadan kaynaklanıyor olabilir)
- Aynı gün aynı şubeden çıkan ve topluca yüksek desi yazılmış gönderiler
- Barem dışına çıkan siparişler ve iade gönderileri

### 4. Tutara çevirin

Fark desiyi panelinizdeki tarife basamaklarıyla tutara çevirin. Böylece hangi itirazın zahmetine değdiğini görürsünüz; çok küçük farklar için tek tek talep açmak yerine dönemlik toplu dosya hazırlamak daha verimlidir.

### 5. Trend takibi yapın

Belirli bir şube veya kargo firmasında hatalar tekrar ediyorsa bunu not edin. Tekrarlayan bir sorun, hem toplu itirazda hem de kargo firması tercihinizde işinize yarar.

## İtiraz için kanıt seti

İtiraz kanalı ve ekran adları panelde değişebilir; bazı kaynaklar canlı destek üzerinden Excel tablosuyla başvurulduğunu ([Verimle](https://verimle.com/blog/trendyol-haksiz-kesinti-itiraz)), bazıları ise panelde ayrı bir itiraz ekranı bulunabildiğini aktarıyor. Hangi kanaldan başvurursanız başvurun, şu kanıtlar dosyanızı güçlendirir:

| Kanıt | Gösterdiği bilgi |
|---|---|
| Sipariş ve paket numarası | Hangi gönderiye ait olduğu |
| Mezura görünür şekilde koli fotoğrafları (en, boy, yükseklik) | Gerçek ölçü |
| Tartı fotoğrafı | Gerçek ağırlık |
| Faturalanan desi / kesinti satırı ekran görüntüsü | İtiraz edilen tutar |
| Hesaplanmış doğru desi ve fark tutarı | Talebinizin net karşılığı |

**Süre konusunda dikkat:** Bazı kaynaklar itirazın paketin kargoya verildiği gün içinde açılması gerektiğini, bazıları ise kargo firması incelemesinin haftalar sürebildiğini belirtiyor. Bu sürelerin Trendyol tarafından herkese açık resmi bir sayfada yayımlandığını doğrulayamadık. En güvenli yol, kanıtı **gönderi anında** toplamak ve kesintiyi gördüğünüz ilk fırsatta başvurmaktır.

## Hatayı baştan azaltmanın yolları

- **Standart koli kullanın:** Ürün başına tek koli tipi, hem ölçümü hem kontrolü kolaylaştırır.
- **Paketleme istasyonunda fotoğraf alışkanlığı:** Özellikle barem dışı ve yüksek tutarlı siparişlerde mezura + tartı fotoğrafını otomatik rutin hâline getirin.
- **Ürün kartındaki desi bilgisini güncel tutun:** Koliyi değiştirdiğinizde kart bilgisini de güncelleyin.
- **Fiyatlamaya gerçekçi kargo maliyeti ekleyin:** Ürünün kendi ölçüsünü değil, paketin desisini kullanın.

İade gönderilerinde oluşan kargo maliyetinin hakedişe nasıl yansıdığını görmek için [Trendyol iade komisyonu ve hakediş kontrolü rehberimize](https://tayma96.github.io/tayma-lab/yazilar/trendyol-iade-komisyonu-ve-hakedis-kontrolu/) bakabilirsiniz.

## Sık sorulan sorular

**Desi ile kilo aynı şey mi?**
Hayır. Desi hacimsel ağırlıktır; kargo ücretinde desi ile gerçek kilodan büyük olan esas alınır.

**Tek desilik fark için itiraz etmeli miyim?**
Önce yuvarlama kuralını kontrol edin; tek desilik farklar çoğu zaman yuvarlamadan kaynaklanır. Tekrarlayan ve iki desi üzeri farklar daha güçlü itiraz adaylarıdır.

**Kabul edilen itirazın parası ne zaman gelir?**
Kaynaklar sonraki hakedişe yansıdığını belirtiyor, ancak zamanlama değişebilir. Talep sonuçlandıktan sonra cari hesabınızda düzeltme satırını mutlaka kontrol edin.

---

> **Önemli:** Bu yazı bilgilendirme amaçlıdır, güncel kuralları platformdan doğrulayın. Kargo tarifeleri, barem eşikleri ve itiraz süreleri sık değişir; kesin değerler için satıcı panelinizi esas alın.
