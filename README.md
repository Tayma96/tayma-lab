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
| TikTok çerezi | Tarayıcıda giriş → "Get cookies.txt LOCALLY" → `secrets/tiktok_cookies.txt` (ya da `TIKTOK_SESSIONID`) | `method: browser` için |
| `TIKTOK_CLIENT_KEY/SECRET` | developers.tiktok.com → Content Posting API, `video.publish` | Sadece `method: api` için |

```bash
pip install -e '.[captions,tiktok-browser]' && playwright install chromium
gta6clips auth youtube    # tarayıcıda izin ver
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

## Kullanılan açık kaynak projeler ve Claude skill'leri

| Proje | Ne için | Nasıl |
|---|---|---|
| [wkaisertexas/tiktok-uploader](https://github.com/wkaisertexas/tiktok-uploader) (MIT) | TikTok'a denetim beklemeden herkese açık yükleme | `upload.tiktok.method: browser`, `pip install -e '.[tiktok-browser]' && playwright install chromium` |
| [eat-pray-ai/yutu](https://github.com/eat-pray-ai/yutu) (Apache-2.0) | YouTube kanal yönetimi: SEO, yorum, oynatma listesi, silme | `.claude/skills/youtube` (resmi skill'leri) + `.mcp.json` (yutu MCP sunucusu) |
| [Anil-matcha/AI-Youtube-Shorts-Generator](https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator) (MIT) | Yüz takibi ve viral an ölçütleri | Fikir olarak uyarlandı: `facecam.py` (yüz kamerası tespiti), `highlights.VIRALITY_SYSTEM` (Claude ile VOD puanlama) |

Claude Code bu repoda şu skill'leri kullanır (`.claude/skills/`):
- **gta6-clips**: otomasyonu çalıştırma, ayarlama, sorun giderme, şikayet gelen yayıncıyı engelleyip videolarını bulma
- **tiktok-upload**: iki TikTok yöntemi, çerez alma, hata çözümü
- **youtube**: yutu'nun resmi skill'i (MCP üzerinden YouTube işlemleri + SEO rehberi)
- **viral-shorts**: an seçimi, kanca, başlık, hashtag ilkeleri

yutu kurulumu: `npm i -g @eat-pray-ai/yutu`, sonra `yutu auth --credential secrets/youtube_client_secret.json --cacheToken secrets/yutu_token.json`.

## ⚠️ Platform kısıtları
- **YouTube:** Denetimden geçmemiş API projelerinden yüklenen videoları Google gizli (private) olarak
  kilitliyor. Google Cloud Console'dan *YouTube API Services Audit* başvurusu yap. Varsayılan kota
  günde yaklaşık 6 yüklemeye yetiyor (`max_per_day: 6`).
- **TikTok:** Varsayılan `method: browser` herkese açık paylaşır. Bu resmi API değil; TikTok
  otomasyonu fark ederse hesabı doğrulamaya sokabilir, günlük limiti makul tut. `method: api`
  denetim onaylanana kadar sadece gizli paylaşır.
- **Telif:** Şikayet gelirse yayıncıyı `blocklist`'e ekle. Videolarını bulup silme adımları `gta6-clips` skill'inde.

## Yapı
```
src/gta6clips/
  twitch.py       Helix API + klip puanlama/filtreleme
  download.py     yt-dlp
  transcribe.py   faster-whisper (kelime zamanları)
  captions.py     ASS altyazı (kelime vurgulu, kanca, kredi)
  editor.py       ffmpeg dikey kurgu
  facecam.py      OpenCV ile yüz kamerası tespiti
  highlights.py   VOD ses zirvesi + Claude viral puanlama
  metadata.py     Claude ile başlık/açıklama/hashtag
  uploaders/      youtube.py, tiktok.py (API), tiktok_browser.py (tiktok-uploader)
  pipeline.py     akış
  db.py           SQLite (tekrar yüklemeyi önler, günlük limit)
  cli.py
```

Testler: `pytest`
