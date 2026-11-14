# GTA 6 Klip Otomasyonu

Twitch'te GTA 6 oynayan en çok izlenen yayıncıların en popüler anlarını bulur, bunları dikey
(9:16) Shorts/TikTok videosuna kurgular, Claude ile başlık/açıklama/hashtag yazar ve YouTube ile
TikTok'a yükler.

```
Twitch (en çok izlenen klipler + canlı yayın sıralaması)
  → yt-dlp ile indir
  → Whisper ile kelime zamanlı döküm
  → Claude: başlık, açılış kancası, açıklama, hashtag
  → ffmpeg: 1080x1920, bulanık arka plan veya yüz kamerası düzeni, kelime vurgulu altyazı, kredi
  → YouTube Shorts + TikTok (günlük limit ve aralıklarla)
```

## Kurulum

```bash
# ffmpeg gerekli (apt install ffmpeg / brew install ffmpeg)
python -m venv .venv && source .venv/bin/activate
pip install -e '.[captions]'
cp config.example.yaml config.yaml
cp .env.example .env      # anahtarları doldur
```

### Anahtarlar
| Ne | Nereden | Not |
|---|---|---|
| `TWITCH_CLIENT_ID/SECRET` | dev.twitch.tv/console/apps | Hemen alınır |
| `ANTHROPIC_API_KEY` | platform.claude.com | Boşsa şablon başlık kullanılır |
| YouTube OAuth JSON | Google Cloud Console → YouTube Data API v3 → OAuth client (Desktop) | `secrets/youtube_client_secret.json` |
| `TIKTOK_CLIENT_KEY/SECRET` | developers.tiktok.com → Content Posting API, `video.publish` | Redirect URI: `http://localhost:8765/callback` |

```bash
gta6clips auth youtube    # tarayıcıda izin ver
gta6clips auth tiktok
```

## Kullanım

```bash
gta6clips discover          # yeni popüler klipleri bul
gta6clips render            # indir + kurgula -> data/out/*.mp4
gta6clips upload            # YouTube + TikTok
gta6clips run --loop --interval 30   # hepsini 30 dakikada bir sürekli çalıştır
gta6clips run --no-upload   # sadece üret, yükleme yapma (kontrol için)
gta6clips status

# Uzun yayından (VOD) ses zirvelerine göre 5 kesit:
gta6clips vod https://www.twitch.tv/videos/123456 --broadcaster yayinci --top 5
```

Docker ile sunucuda:
```bash
docker build -t gta6clips .
docker run -d --restart unless-stopped -v $PWD/data:/app/data -v $PWD/secrets:/app/secrets \
  --env-file .env -v $PWD/config.yaml:/app/config.yaml gta6clips
```

## ⚠️ Bilmen gerekenler

**Otomatik yüklemedeki platform kısıtları**
- **YouTube:** Denetimden geçmemiş API projelerinden yüklenen videoları Google gizli (private) olarak
  kilitliyor. Google Cloud Console'dan *YouTube API Services Audit* başvurusu yap. Varsayılan kota
  günde yaklaşık 6 yüklemeye yetiyor (`max_per_day: 6`).
- **TikTok:** Denetimden geçmemiş uygulamalar sadece `SELF_ONLY` (gizli) paylaşabiliyor. Kod hesabın
  izin verdiği en açık seviyeyi otomatik seçiyor; denetim onaylanınca kendiliğinden herkese açık
  paylaşmaya başlıyor. Denetim haftalar sürebilir, **hemen başvur**.
- İki denetim de bitene kadar en hızlı yol: `run --no-upload` ile üret, `data/out/` içindeki
  videoları elle yükle. Başlık ve hashtag'ler `gta6clips status` / veritabanında hazır duruyor.

**Telif hakkı**
- Yayınların hakkı yayıncılara ait. İzinsiz yeniden yüklemeler Content ID talebi ve DMCA uyarısı
  alabilir; YouTube'da 3 uyarı kanalın kapanması demek. Ayrıca sadece başkasının içeriğini yükleyen
  kanallar YouTube'un "yeniden kullanılmış içerik" kuralı yüzünden para kazanamayabilir.
- Riski azaltan şeyler: her klipte görünür kredi var (`credit: true`), kurgu (altyazı ve kanca)
  klibi birebir kopya olmaktan çıkarıyor. Şikayet eden yayıncıyı `blocklist`'e ekle.
- En güvenlisi: clipping programı olan ya da izin veren yayıncılarla çalışmak.

## Yapı
```
src/gta6clips/
  twitch.py       Helix API + klip puanlama/filtreleme
  download.py     yt-dlp
  transcribe.py   faster-whisper (kelime zamanları)
  captions.py     ASS altyazı (kelime vurgulu, kanca, kredi)
  editor.py       ffmpeg dikey kurgu
  highlights.py   VOD ses zirvesi tespiti
  metadata.py     Claude ile başlık/açıklama/hashtag
  uploaders/      youtube.py, tiktok.py
  pipeline.py     akış
  db.py           SQLite (tekrar yüklemeyi önler, günlük limit)
  cli.py
```

Testler: `pytest`
