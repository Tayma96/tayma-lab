---
name: gta6-clips
description: GTA 6 klip otomasyonunu (gta6clips CLI) çalıştırma, ayarlama ve sorun giderme. Canlı avcı, klip bul, kalite eşiği, kurgula, yükle, yayın saatleri, VOD'dan kesit, izlenme istatistikleri, durum raporu, yayıncı engelleme, yüz kamerası düzeltme, başarısız/elenen klipleri inceleme gibi her istekte kullan.
---

# GTA 6 Klip Otomasyonu

Kod `src/gta6clips/`, ayarlar `config.yaml` (örnek: `config.example.yaml`), anahtarlar `.env`, durum `data/clips.db`.

## Akış
```
Kaynaklar ─┬─ live.py      canlı sohbet patlaması -> Twitch klibi oluştur (en hızlı)
           ├─ twitch.py    popüler klipler, izlenme HIZINA + yayıncı performansına göre
           └─ highlights   VOD ses zirveleri + Claude viral puanı
   -> analyze.py  Claude: kareler + döküm -> puan 1-10, GTA 6 mı, en iyi bölüm, başlık/kanca
   -> kalite kapısı (quality.min_score) -> kırp + kurgula (editor.py)
   -> upload_priority: kalite > popülerlik, 12 saat yarı ömürlü tazelik, canlı bonusu
   -> yükle (peak_hours_utc, max_per_day, min_gap) -> izlenmeleri çek -> yayıncı çarpanları
```

## Komutlar
| İstek | Komut |
|---|---|
| Her şey, sürekli (önerilen) | `gta6clips run --loop` |
| Sadece üret, yükleme yok | `gta6clips run --loop --no-upload` |
| Sadece canlı avcı | `gta6clips live` |
| Tek tur | `gta6clips discover`, `render`, `upload` |
| Uzun yayından kesit | `gta6clips vod <url> --broadcaster <ad> --top 5` |
| İzlenmeler + yayıncı performansı | `gta6clips stats` |
| Özet | `gta6clips status` |
| Yetki | `gta6clips auth twitch` (canlı avcı) / `auth youtube` / `auth tiktok` |

## Ayar rehberi
- **Hacim az:** `quality.min_score` 5'e, `discovery.min_views` düşür, `live.spike_ratio` 2.5'e indir.
- **Kalite düşük:** `min_score` 7'ye çıkar. Elenenleri incele:
  `sqlite3 data/clips.db "SELECT broadcaster, quality, error FROM clips WHERE status='rejected' ORDER BY rowid DESC LIMIT 20"`
- **Canlı avcı çok/az klip açıyor:** `live.spike_ratio`, `live.min_weight`, `live.cooldown_seconds`, `live.max_clips_per_hour`.
- **Yayın saatleri:** `upload.peak_hours_utc` (ABD akşamı: 22-04 UTC). `max_age_hours` bayat içeriği eler.
- **Hangi yayıncı iyi gidiyor:** `gta6clips stats` → `streamer_multipliers` (0.5-2.0, keşif sıralamasını etkiler).

## Sık görevler
**Yayıncıyı çıkar:** `config.yaml` → `blocklist`. Yüklenmiş videolarını bul:
`sqlite3 data/clips.db "SELECT u.platform,u.remote_id,c.title FROM uploads u JOIN clips c ON c.id=u.clip_id WHERE lower(c.broadcaster)='<ad>' AND u.status='done'"`
YouTube'dakileri `youtube` skill'i (yutu MCP, `video-delete`) ile sil; önce listeyi göster ve onay al.

**Yüz kamerası yanlış:** `data/facecams.json`'dan yayıncıyı sil (yeniden tespit) ya da `config.yaml` → `facecams.<ad>` ile elle gir.

**Yeniden dene:** klip `UPDATE clips SET status='new' WHERE id='<id>'`; yükleme için ilgili `uploads` satırını sil.

## Test
`pytest` (ffmpeg gerekir). Kod değiştirdikten sonra çalıştır. Başlık/kanca ilkeleri: `viral-shorts` skill'i.
