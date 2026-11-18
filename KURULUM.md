# Telefondan, ücretsiz kurulum (bilgisayar gerekmez)

Sistem GitHub'ın ücretsiz sunucularında (GitHub Actions) kendi kendine çalışır. Bu repo herkese açık
olduğu için kullanım süresi sınırsız ve ücretsiz. Kart, sunucu, bilgisayar gerekmez.

Toplam süre: ~30-40 dakika. Hepsini telefonun tarayıcısından yapabilirsin. Bazı sayfalarda tarayıcı
menüsünden **"Masaüstü sitesi"** seçeneğini açman gerekecek (GitHub ayarları ve Google Cloud).

> Gizli bilgileri (şifre, token) **hiçbir zaman** bir dosyaya ya da sohbete yazma; sadece 1. adımdaki
> GitHub "Secrets" bölümüne ekle. Orada şifreli saklanır, repo herkese açık olsa da kimse göremez.

---

## 1. GitHub Secrets nereye eklenir

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
Aşağıdaki her bilgi için: *Name* kutusuna adı (tam olarak yazıldığı gibi), *Secret* kutusuna değeri yaz → **Add secret**.

İlk secret:

| Name | Değer |
|---|---|
| `STATE_KEY` | Uzun, rastgele bir şifre uydur (en az 30 karakter, örn. harf+rakam karışık). Sistemin hafızasını şifreler. Bir yere not et ama kimseyle paylaşma. |

---

## 2. Twitch (klipleri bulmak ve canlı yayından klip almak için)

1. **dev.twitch.tv/console/apps** adresine Twitch hesabınla gir. (Twitch, geliştirici sayfası için hesapta
   iki adımlı doğrulamanın açık olmasını ister; açık değilse Twitch ayarlarından aç.)
2. **Register Your Application**:
   - Name: `gta6clips-` + rastgele birkaç harf (benzersiz olmalı)
   - OAuth Redirect URLs: `http://localhost:8767/callback`
   - Category: **Application Integration**
   - Client Type: **Confidential**
   - **Create**
3. Uygulamanın yanındaki **Manage** → **Client ID**'yi kopyala → **New Secret** → çıkan secret'ı kopyala.
4. GitHub Secrets'a ekle:

| Name | Değer |
|---|---|
| `TWITCH_CLIENT_ID` | Client ID |
| `TWITCH_CLIENT_SECRET` | Secret |

5. **Twitch girişi (canlı avcı için, bir kez):** Repo → **Actions** → soldan **Twitch girişi** →
   **Run workflow** → yeşil düğme. Çalışmaya başlayan işe dokun → **auth** → *"Kodu logda gör"* adımını aç.
   Orada bir adres (twitch.tv/activate) ve 8 harfli bir kod göreceksin. Telefondan o adresi aç, kodu yaz,
   **Authorize** de. 15 dakika içinde yapmalısın. İş yeşil tik alınca tamam.

> Not: "GTA 6 klipleri" işi o sırada çalışıyorsa önce onu iptal et (işe gir → **Cancel workflow**),
> sonra Twitch girişini çalıştır. İkisi aynı anda çalışmaz.

---

## 3. YouTube (Shorts yüklemek için)

### 3a. Google Cloud projesi (masaüstü sitesi modunda)
1. **console.cloud.google.com** → kanalının bağlı olduğu Google hesabıyla gir.
2. Üstte proje seçici → **New Project** → ad `gta6clips` → **Create**.
3. Arama kutusuna "YouTube Data API v3" yaz → aç → **Enable**.
4. Menü → **APIs & Services** → **OAuth consent screen** (ya da "Google Auth Platform"):
   - **Get started**, uygulama adı `gta6clips`, e-posta olarak kendi adresin, **External**, kaydet.
   - **Audience** bölümünde **Test users** → kendi Google hesabını ekle.
   - Sonra yine **Audience** → **Publish app** → onayla. (Bunu yapmazsan giriş 7 günde bir sona erer.)
5. **Credentials** (ya da **Clients**) → **Create credentials / Create client** → **OAuth client ID**:
   - Application type: **Web application**
   - Authorized redirect URIs → **Add URI**: `https://developers.google.com/oauthplayground`
   - **Create** → çıkan **Client ID** ve **Client secret**'ı kopyala.

### 3b. Yenileme anahtarını (refresh token) al
1. **developers.google.com/oauthplayground** adresini aç.
2. Sağ üstteki **dişli simgesi** → **Use your own OAuth credentials** kutusunu işaretle →
   Client ID ve Client secret'ı yapıştır.
3. Soldaki **Step 1** listesinin altındaki kutuya şunu yapıştır (iki adres, arada boşluk):
   ```
   https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly
   ```
   → **Authorize APIs**.
4. Kanalının hesabını seç. "Google bu uygulamayı doğrulamadı" uyarısı çıkarsa: **Gelişmiş** →
   **gta6clips'e git** → izinleri onayla. (Kendi uygulaman olduğu için güvenli.)
5. **Step 2** → **Exchange authorization code for tokens** → çıkan **Refresh token**'ı kopyala.
6. GitHub Secrets'a ekle:

| Name | Değer |
|---|---|
| `YOUTUBE_CLIENT_ID` | 3a'daki Client ID |
| `YOUTUBE_CLIENT_SECRET` | 3a'daki Client secret |
| `YOUTUBE_REFRESH_TOKEN` | 3b'deki Refresh token |

---

## 4. TikTok (herkese açık paylaşım için)

Sistem TikTok'a tarayıcı otomasyonuyla yükler; bunun için hesabının `sessionid` çerezi gerekir.

**Android:**
1. Play Store'dan **Firefox**'u kur.
2. Firefox menüsü → **Eklentiler** → **Cookie-Editor**'ü ekle.
3. Firefox'ta **tiktok.com**'u aç, menüden **Masaüstü sitesi**'ni işaretle, TikTok hesabınla giriş yap.
4. Menü → Eklentiler → **Cookie-Editor** → listede **sessionid**'i bul → değerini kopyala.

**iPhone:** Telefonda çerez okumak zor. En kolayı bir kez herhangi bir bilgisayarda (arkadaş, internet
kafe) Chrome ile tiktok.com'a girip **F12** → **Application** → **Cookies** → `sessionid` değerini almak.
Sonra o bilgisayarda TikTok'tan çıkış yapmadan sadece tarayıcıyı kapat (çıkış yaparsan çerez geçersiz olur).

GitHub Secrets'a ekle:

| Name | Değer |
|---|---|
| `TIKTOK_SESSIONID` | sessionid değeri |

Bu çerez birkaç ay geçerli kalır. TikTok yüklemeleri hata vermeye başlarsa yeniden al ve secret'ı güncelle.

---

## 5. Kanal adını yaz (isteğe bağlı)

Repo'da **config.yaml** dosyasını aç → kalem simgesi → `brand: ""` satırını kendi kanal adınla değiştir
(örn. `brand: "@gta6moments"`) → **Commit changes**. Diğer ayarların açıklamaları da aynı dosyada.

---

## 6. Bağlantıları kontrol et

Actions → **Bağlantı kontrolü** → **Run workflow**. Bir dakikada biter; işe dokununca özet sayfasında
Twitch, YouTube ve TikTok için ✅/❌ tablosu çıkar (YouTube'da kanal adını da gösterir). Hiçbir şey yüklemez.
❌ olan satırda ne yapman gerektiği yazar.

> **YouTube test modundaysa** (uygulamayı "Publish app" ile yayına alamadıysan): giriş 7 günde bir sona
> erer. Kontrol "invalid_grant" derse OAuth Playground'dan yeni refresh token al ve GitHub'da
> `YOUTUBE_REFRESH_TOKEN` secret'ını güncelle (kalem simgesi → Update secret). Sistem yenisini kendisi algılar.

---

## 7. Başlat

**Önce kontrol turu (önerilir):** Actions → **GTA 6 klipleri** → **Run workflow** →
"Yükleme yapılsın mı" kutusunun **işaretini kaldır**, "Kaç dakika" = `40` → **Run workflow**.
İş bitince sayfanın altındaki **Artifacts** bölümünden `onizleme-videolari` dosyasını indirip videolara bak.
Özet de aynı sayfada.

**Sonra otomatik mod:** Hiçbir şey yapmana gerek yok. Sistem her 30 dakikada bir kontrol eder ve çalışan
bir iş yoksa yenisini başlatır; her iş ~5.5 saat sürer, biter bitmez sıradaki başlar. Yani 7/24 çalışır.
Durdurmak için: Actions → **GTA 6 klipleri** → sağ üstteki **⋯** → **Disable workflow**.

---

## Bilmen gerekenler
- **Yapay zeka ücretsiz:** GitHub Models (GitHub'ın ücretsiz yapay zekası) klipleri puanlar ve başlık yazar.
  Günlük ücretsiz sınırı dolarsa sistem durmaz; o gün kalan klipleri ücretsiz sinyallerle (izlenme hızı,
  sohbet patlaması, ses, ekran hareketi, konuşma) puanlar ve hazır şablon başlık kullanır.
- **TikTok:** GitHub sunucusundan yapılan girişleri TikTok bazen doğrulamaya (captcha) takabilir. Olursa
  TikTok yüklemesi o tur atlanır; YouTube etkilenmez.
- **GitHub kuralları:** GitHub Actions asıl olarak yazılım projeleri için tasarlandı. Bu tür sürekli
  çalışan bir otomasyonu GitHub uygun görmezse repodaki Actions'ı kapatabilir. Olursa söyle, alternatif kurarız.
- **60 gün kuralı:** Herkese açık repolarda 60 gün boyunca hiçbir değişiklik yapılmazsa GitHub
  zamanlanmış işleri kapatır. Arada bir config.yaml'da küçük bir değişiklik yapmak yeterli.
