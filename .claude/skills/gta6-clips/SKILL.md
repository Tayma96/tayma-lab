---
name: gta6-clips
description: GTA 6 klip otomasyonunu (gta6clips CLI) çalıştırma, ayarlama ve sorun giderme. Klip bul, kurgula, yükle, VOD'dan kesit çıkar, durum raporu, telif uyarısı gelen yayıncıyı engelleme, yüz kamerası düzeltme, başarısız yüklemeleri inceleme gibi her istekte kullan.
---

# GTA 6 Klip Otomasyonu

Bu repodaki `gta6clips` paketi Twitch'teki popüler GTA 6 anlarını dikey Shorts/TikTok videosuna çevirip yükler.
Kod `src/gta6clips/`, ayarlar `config.yaml` (örnek: `config.example.yaml`), anahtarlar `.env`, durum `data/clips.db`.

## Komutlar

| İstek | Komut |
|---|---|
| Yeni klip bul | `gta6clips discover` |
| Bulunanları kurgula | `gta6clips render [--limit N]` |
| Yükle | `gta6clips upload` |
| Hepsi, sürekli | `gta6clips run --loop --interval 30` |
| Sadece üret, yükleme | `gta6clips run --no-upload` |
| Uzun yayından kesit | `gta6clips vod <twitch-vod-url> --broadcaster <ad> --top 5 --length 30` |
| Özet | `gta6clips status` |
| Yetki | `gta6clips auth youtube` / `gta6clips auth tiktok` (sadece TikTok api yöntemi) |

Komutları repo kökünden çalıştır. `-v` ayrıntılı log verir.

## Sık görevler

**Telif uyarısı / yayıncı şikayeti geldi:**
1. `config.yaml` → `blocklist`'e yayıncının Twitch kullanıcı adını küçük harfle ekle.
2. O yayıncının yüklenmiş videolarını bul:
   `sqlite3 data/clips.db "SELECT u.platform,u.remote_id,c.title FROM uploads u JOIN clips c ON c.id=u.clip_id WHERE lower(c.broadcaster)='<ad>' AND u.status='done'"`
3. YouTube videolarını silmek için `youtube` skill'ini (yutu MCP, `video-delete`) kullan. Silmeden önce listeyi kullanıcıya göster ve onay al. TikTok'takiler elle silinir.

**Yüz kamerası yanlış bulundu:** `data/facecams.json` içindeki yayıncı kaydını sil (tekrar tespit edilir) ya da
`config.yaml` → `facecams.<ad>: {x, y, w, h}` ile elle gir (0-1 oranları, kaynak 16:9 kareye göre). Elle girilen önceliklidir.
Kontrol için: `ffmpeg -ss 5 -i data/out/<id>.mp4 -frames:v 1 /tmp/kare.png` ile kareye bak.

**Başarısız klipler / yüklemeler:**
`sqlite3 data/clips.db "SELECT id,error FROM clips WHERE status='failed'"` ve
`sqlite3 data/clips.db "SELECT clip_id,platform,detail FROM uploads WHERE status='failed'"`.
Bir klibi yeniden denemek için: `UPDATE clips SET status='new' WHERE id='<id>'`.
Bir yüklemeyi yeniden denemek için ilgili `uploads` satırını sil.

**Daha fazla / daha az video:** `discovery.min_views`, `discovery.max_clips_per_run`, `upload.*.max_per_day`, `upload.min_gap_minutes`.

## Bilinen kısıtlar
- YouTube: denetimden geçmemiş API projesinde yüklemeler gizli kalır, varsayılan kota ~6 yükleme/gün.
- TikTok `method: api`: denetim onaylanana kadar SELF_ONLY. `method: browser` (tiktok-uploader) herkese açık paylaşır; çerez süresi dolarsa yeniden al (bkz. `tiktok-upload` skill'i).
- Başlık/kanca yazımında `viral-shorts` skill'indeki ilkeleri uygula.

## Test
`pytest` (ffmpeg gerekir). Kod değiştirdikten sonra çalıştır.
