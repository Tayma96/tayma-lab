# Kanal stratejisi

Gerekçeler ve kaynaklar: [ARASTIRMA.md](ARASTIRMA.md). Ayarlar: [`kanal/kanal.yaml`](../kanal/kanal.yaml).

## Karar

| | Seçim | Neden |
|---|---|---|
| Niş | **Şirket hikayeleri** — şirketler nasıl yükseldi, nasıl battı, parayı nereden kazanıyor | İş dünyası reklamlarını çeker (RPM tahmini ~5–19 $); belgesel gibi izlenir, genele hitap eder; videolar eskimez. |
| Kitle | Yetişkin, 25–54 | Reklamverenin en çok ödediği kitle. Çocuk/ergen değil. |
| Ülke / dil | ABD, İngiltere, Kanada, Avustralya — **İngilizce** | En yüksek RPM'li ülkeler tek dilde. |
| Format | **Uzun video ana ürün (8–14 dk), Shorts sadece fragman** | Para ve 4.000 saat uzun videodan gelir. |
| Görsel | Yüzsüz; **gerçek ve arşiv görüntü + harita, zaman çizelgesi, grafik, belge** | Gerçek görüntü "insan işi" hissini verir, grafik özgün değeri. Tek tip görsel = şablon. Logo ve reklam görüntüsü yok. |
| Ses | **Chatterbox** (açık kaynak, ücretsiz, ticari kullanım serbest), satır satır yönetilmiş okuma | Duygu ayarı var; kimseyi taklit etmiyor. Kanal kazanınca ElevenLabs v4'e geçilebilir. |
| Tempo | Haftada **2 uzun video + her birinden 2–3 Shorts** | Kalite kontrolüne zaman kalan en yüksek tempo. |

Yedek niş: **teknoloji ve bilim açıklamaları** — aynı üretim hattıyla yapılır.

## İçerik türleri (dönüşümlü)

1. **Yükseliş:** "How a $X idea became a $Y company" — kuruluş, kırılma anı, bugünkü gelir.
2. **Çöküş:** "Why X collapsed" — en çok izlenen tür; tek hatanın hikayesi.
3. **Para nereden geliyor:** "How X actually makes money" — gelir kalemleri grafikle.
4. **Kafa kafaya:** "X vs Y" — iki rakibin stratejisi, aynı grafikte.

Konular `/yt-viral` ile nişte kendi kanal ortalamasının 3+ katı izlenen videolardan seçilir.

## Önceki otomasyondan farkı

| Önce | Şimdi |
|---|---|
| 700 Shorts, tek şablon | Haftada 2 uzun video, her biri ayrı bir şirket ve soru |
| Konu: rastgele | Konu: kanıtlanmış talep (`/yt-viral`) |
| Otomatik yayın | **Her video yayından önce bir insan onayından geçer** |
| Shorts tek başına | Shorts = uzun videonun fragmanı, izleyiciyi uzun videoya taşır |
| Kaynak yok | Her rakamın ve iddianın kaynağı açıklamada |

## Dürüst hesap

Rakamlar tahmin; gerçek değerler kanal açıldıktan 2–3 ay sonra Studio'dan okunmalı.

- İngilizce iş/şirket hikayesi uzun video için temkinli RPM: **4–10 $**.
- Ayda 100.000 uzun video izlenmesi → **≈ 400–1.000 $/ay**.
- Ayda 1.000.000 izlenme → **≈ 4.000–10.000 $/ay**.
- Bu nişte izlenme, finansa göre daha kolay gelir; RPM biraz düşük ama hacim telafi eder.
- İlk 3–6 ay gelir **sıfır**: önce 1.000 abone + 4.000 saat eşiği aşılmalı.
- Maliyet: **0 $** (aşağıdaki araç seti).

Reklam dışı gelir: ileride sponsorluk (iş yazılımları bu nişe sponsor olur) ve açıklamada
gerçekten önerilecek kitap/araç affiliate linkleri, "affiliate" diye belirtilerek.

## Sıfır bütçe araç seti

| İş | Araç | Not |
|---|---|---|
| Ses | Chatterbox (MIT) | GPU yoksa Nano modeli bilgisayarın işlemcisinde çalışır; GPU gerekirse Google Colab'ın ücretsiz GPU'su. **ElevenLabs'in ücretsiz planı ticari kullanıma kapalı**, para kazanan kanalda kullanılamaz. |
| Gerçek görüntü | Pexels, Pixabay (ücretsiz API anahtarı) | Ticari kullanım serbest. |
| Arşiv görüntü | Wikimedia Commons, Internet Archive, Library of Congress, NASA | Yalnızca kamu malı veya CC BY lisanslı dosyalar. |
| Müzik / efekt | YouTube Ses Kitaplığı, Pixabay Music, Freesound (CC0) | |
| Grafik ve animasyon | Remotion | Bireysel kullanımda ücretsiz. |
| Kurgu | FFmpeg + `ffmpeg-skill` | Tamamen yerel, ücretsiz. |
| Kalite kontrol | `insan-isi` skill'i | Şablon izlerini yayından önce yakalar. |

Her kullanılan dosya `lisanslar.csv`'ye yazılır; kaynağı belli olmayan dosya videoya girmez.

## Kırmızı çizgiler

- Gerçek kişi ve şirketler hakkında yalnızca kaynaklı bilgi; dedikodu ve iftira yok.
- Şirket logosu, ürün fotoğrafı, reklam görüntüsü süs olarak kullanılmaz.
- Yatırım tavsiyesi yok; uydurma rakam yok.
- Gerçek kişinin sesi veya yüzü taklit edilmez; Chatterbox'ın gizli filigranı silinmez.
- YouTube'un yapay zekâ sorusu her yüklemede dürüstçe cevaplanır.
- Aynı videonun varyasyonları seri halinde yüklenmez.
- Hiçbir video insan onayı olmadan herkese açık yayınlanmaz.
