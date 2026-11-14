---
name: tiktok-upload
description: TikTok'a video yükleme - tiktok-uploader (wkaisertexas, tarayıcı otomasyonu, herkese açık) veya resmi Content Posting API. TikTok yükleme, çerez/sessionid alma, TikTok yükleme hatası, gizli kalan TikTok paylaşımları, TikTok zamanlama isteklerinde kullan.
---

# TikTok Yükleme

İki yöntem var, `config.yaml` → `upload.tiktok.method` ile seçilir:

| | `browser` (önerilen, şu an) | `api` |
|---|---|---|
| Kütüphane | [wkaisertexas/tiktok-uploader](https://github.com/wkaisertexas/tiktok-uploader) (MIT, PyPI `tiktok-uploader`) | TikTok Content Posting API v2 |
| Kod | `src/gta6clips/uploaders/tiktok_browser.py` | `src/gta6clips/uploaders/tiktok.py` |
| Herkese açık | Evet | Uygulama denetimi onaylanana kadar sadece SELF_ONLY |
| Kimlik | Tarayıcı çerezi (`sessionid`) | OAuth (`gta6clips auth tiktok`) |
| Risk | Resmi değil; TikTok otomasyonu fark ederse doğrulama isteyebilir | Yok |

## browser kurulumu
```bash
pip install -e '.[tiktok-browser]'
playwright install chromium   # Docker imajında zaten var
```
Oturum: TikTok'a normal tarayıcıda giriş yap → "Get cookies.txt LOCALLY" eklentisiyle tiktok.com çerezlerini
`secrets/tiktok_cookies.txt` olarak kaydet. Alternatif: geliştirici araçları → Application → Cookies →
`sessionid` değerini `.env`'de `TIKTOK_SESSIONID=` olarak yaz. Çerezler gizlidir, asla commit'leme.

Doğrudan kütüphane kullanımı (tek seferlik yükleme):
```python
from tiktok_uploader.upload import TikTokUploader
with TikTokUploader(cookies="secrets/tiktok_cookies.txt", browser="chromium", headless=True) as up:
    ok = up.upload_video("data/out/<id>.mp4", description="Başlık #GTA6", visibility="everyone")
```
`upload_video` başarıda `True` döner. Zamanlama için `schedule=datetime` (UTC, 20 dk - 10 gün ileri, 5 dk katları).

## Sorun giderme
- `Authentication failed ... sessionid cookie is missing`: çerez süresi dolmuş → yeniden dışa aktar.
- Headless'ta takılma / captcha: `upload.tiktok.headless: false` yap; sunucuda `xvfb-run gta6clips upload` ile çalıştır.
- Arayüz değişikliği yüzünden seçici hataları: `pip install -U tiktok-uploader` (kütüphane aktif bakımda).
- Hesabı korumak için `max_per_day` 10 civarında ve `min_gap_minutes` ≥ 30 kalsın.

## api yöntemi
Uygulamayı developers.tiktok.com'da oluştur, Content Posting API + `video.publish` scope, redirect
`http://localhost:8765/callback`. Denetim başvurusunu hemen yap; onaylanınca kod hesabın izin verdiği
en açık gizliliği otomatik seçer (`choose_privacy`).
