---
name: viral-shorts
description: Oyun yayını kliplerinden viral Shorts/TikTok yapma ilkeleri - hangi an seçilir, kanca (hook), başlık, açıklama, hashtag, süre, kurgu düzeni. Klip seçerken, başlık/kanca yazarken veya düzeltirken, metadata.py ya da highlights.py prompt'larını ayarlarken kullan.
---

# Viral Kısa Video İlkeleri (GTA 6 yayın klipleri)

Ölçütler [AI-Youtube-Shorts-Generator](https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator)'ın (MIT)
"virality criteria" çerçevesinden ve yutu `youtube` skill'inin SEO rehberinden uyarlandı; oyun yayınına göre yeniden yazıldı.
Koddaki karşılıkları: `highlights.VIRALITY_SYSTEM` (an seçimi) ve `metadata.SYSTEM` (başlık/kanca/açıklama).
Bu ilkeleri değiştirirsen ikisini de güncelle.

## Hangi an? (etkisine göre sıralı)
1. **Ham tepki**: gerçek çığlık, kahkaha, şok, öfke; yayıncının kendini kaybettiği an
2. **Kaos sonucu**: kaza, patlama, polis kovalamacası, planın feci şekilde ters gitmesi
3. **İlk keşif**: yeni bir GTA 6 özelliği, mekan ya da easter egg'i ilk kez görmek (çıkış haftasında en değerli tür)
4. **Komik tek cümle**: tek başına alıntılanabilecek bir laf
5. **Beceri anı**: imkansız kaçış, akrobasi, son saniye kurtarış
6. **Sohbet/arkadaş etkileşimi**: laf sokma, tartışma, tutan bir gönderme

Kötü: sessizlik, menüler, yükleme ekranları, bağış okuma, tekrarlayan sürüş, bağlamsız anlar.

## Yapı
- **İlk 3 saniye her şeydir**: kanca hem ekranda (büyük metin) hem de içerikte olmalı. Klibi zirveden 15-20 sn önce başlat, zirve sonda gelsin.
- **Süre**: 15-45 sn ideal. Twitch klipleri zaten ≤60 sn. VOD kesitlerinde `--length 30` iyi bir başlangıç.
- **Kendi başına anlaşılır olmalı**: cümlenin ortasında başlama ya da bitme.
- **Döngü**: son kare ile ilk kare uyumluysa tekrar izlenme artar.

## Metin
- **Başlık**: ≤60-70 karakter, merak boşluğu ama yanıltıcı olmayan; anahtar kelimeyi öne koy ("GTA 6", yayıncı adı). En fazla bir emoji.
- **Kanca (ekran metni)**: 2-6 kelime, büyük harf, emoji yok. Örn: "HE DID NOT SEE THAT COMING", "GTA 6 COPS ARE INSANE".
- **Açıklama**: ilk 2 satır aramada görünür; içinde mutlaka `Streamer: twitch.tv/<ad>` kredisi.
- **Hashtag**: 5-8 tane; her zaman `GTA6` ve yayıncı adı, ilk 2-3 etiket en çok ağırlık taşır. YouTube'da `#Shorts` ekle.

## Yayın
- Çıkış haftasında hacim önemli ama kalite düşmesin: zayıf klipleri yükleme (`min_views` yükselt).
- Platform limitleri içinde dağıt (`min_gap_minutes`); ABD akşam saatleri (UTC 23:00-04:00) en yoğun.
- YouTube'da ilk saatte yorumlara yanıt ver, soruyla sabitlenmiş yorum bırak (yutu `commentThread-insert`).
