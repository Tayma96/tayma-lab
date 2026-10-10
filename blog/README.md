# Satıcı Rehberi — otomatik içerik blogu

Trendyol / Hepsiburada / pazaryeri satıcıları için Türkçe rehber sitesi.
**Canlı adres:** https://tayma96.github.io/tayma-lab/

- Statik site: [Astro 5](https://astro.build) (`blog/` klasörü), GitHub Pages'e GitHub Actions ile yayınlanır.
- Günlük içerik: `blog/scripts/generate_post.py` her gün **1 yazı** üretir (LLM API anahtarı varsa).
- Para kazanma: reklam ve ortaklık (affiliate) bileşenleri **yer tutucu** olarak hazır; kimlikler boşken hiçbir şey göstermez.

> Bu klasör dışındaki dosyalar (repo kökündeki README, `hakedis/`, `docs/` vb.) bu blogla ilgili değildir.

---

## 1. Nasıl çalışır?

```
blog/
├── site.config.json          # site adı, temel URL, reklam/affiliate kimlikleri (boş = kapalı)
├── topics.yaml               # günlük yazı konu kuyruğu (~30 konu)
├── scripts/generate_post.py  # LLM ile yazı üretir + kalite kontrol + commit/push
├── src/content/posts/*.md    # yazılar (Markdown + frontmatter)
├── src/components/           # AdSlot, AffiliateLink, AffiliateBox, Disclaimer, CookieNotice
├── src/pages/                # ana sayfa, yazı, kategori, rss.xml, sitemap.xml, robots.txt, yasal sayfalar
└── public/                   # favicon, og-default.png
.github/workflows/
├── blog-deploy.yml           # blog/** değişince derle → GitHub Pages'e yayınla (actions/deploy-pages)
└── blog-daily-post.yml       # her gün 06:17 UTC (09:17 TSİ): yazı üret → push → deploy
```

**SEO:** her sayfada `<title>`, meta description, canonical URL, OpenGraph/Twitter etiketleri; yazılarda JSON-LD `Article` + `BreadcrumbList`; `sitemap.xml`, `rss.xml`, `robots.txt`; içindekiler, “İlgili rehberler” bölümüyle iç bağlantılar, kategori sayfaları.

**Günlük yazı akışı (`generate_post.py`):**
1. `topics.yaml` içinden `src/content/posts/<slug>.md` dosyası **olmayan** ilk konuyu seçer.
2. `OPENAI_API_KEY` (öncelikli) veya `ANTHROPIC_API_KEY` ile yazı ister. İstem; rakam/oran/tarih uydurmamayı, kaynaksız sayı vermemeyi, belirsizliği açıkça söylemeyi ve URL uydurmamayı şart koşar.
3. Kalite kontrolleri: asgari kelime (varsayılan 800), yinelenen/çok benzer başlık yok, zorunlu uyarı cümlesi (*“bilgilendirme amaçlıdır, güncel kuralları platformdan doğrulayın”*), en az 3 ara başlık, H1 yok, yer tutucu yok; kaynak URL'leri kontrol edilir (uydurma alan adı / 404 elenir). Başarısızsa bir kez geri bildirimle yeniden dener, yine olmazsa **hiçbir şey yayınlamadan** hata verir.
4. Yazıyı `aiGenerated: true` ile kaydeder (sayfada “Yapay zekâ desteğiyle hazırlandı” etiketi görünür), commit eder, `git pull --rebase` ile main'e push eder ve deploy iş akışını çağırır.
5. **Anahtar yoksa** iş `::notice::` basıp başarıyla (yeşil) biter; hiçbir şey commit edilmez.

Hacim bilinçli olarak düşüktür (günde 1). Ölçekli/otomatik içerik spam'i Google politikalarına aykırıdır; kaliteyi korumak için aşağıdaki **insan onayı modunu** öneririz.

## 2. API anahtarını ekleme

GitHub → **Tayma96/tayma-lab → Settings → Secrets and variables → Actions → New repository secret**

| Secret | Açıklama |
|---|---|
| `OPENAI_API_KEY` | OpenAI anahtarı (öncelikli kullanılır) |
| `ANTHROPIC_API_KEY` | Alternatif: Anthropic anahtarı |

veya terminalden: `gh secret set OPENAI_API_KEY -R Tayma96/tayma-lab`

İsteğe bağlı **Variables** (aynı ekranda “Variables” sekmesi):

| Variable | Varsayılan | Açıklama |
|---|---|---|
| `LLM_PROVIDER` | `openai` | İki anahtar da varsa hangisi kullanılsın (`openai`/`anthropic`) |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Model adı (hesabınızda erişilebilir bir model yazın) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-5` | Model adı |
| `MIN_WORDS` | `800` | Asgari kelime sayısı |
| `REQUIRE_REVIEW` | (boş) | `true` yapılırsa yazılar `draft: true` kaydedilir ve **yayına girmez**; bir insan okuyup `draft: false` yapınca yayınlanır. Önerilir. |

Elle çalıştırma: Actions → “Blog — Günlük Yazı (LLM)” → **Run workflow** (isteğe bağlı belirli bir `topic` slug'ı).

Yerelde deneme:
```bash
cd blog && pip install -r scripts/requirements.txt
OPENAI_API_KEY=... python scripts/generate_post.py          # sadece dosyayı yazar
python scripts/generate_post.py --commit-push               # + commit/push
npm ci && npm run dev                                       # http://localhost:4321/tayma-lab/
```

## 3. Reklam ve affiliate kimliklerini doldurma

Hepsi `blog/site.config.json` içinde. **Boş bırakılan her alan hiçbir HTML/JS üretmez.**

- **AdSense:** onay aldıktan sonra `ads.adsenseClientId` (`ca-pub-…`) ve `ads.slots.postTop` / `postBottom` / `sidebar` alanlarına reklam birimi kimliklerini yazın. `client` doluysa AdSense betiği tüm sayfalara eklenir; birim kimliği dolu olan yerlerde reklam alanı görünür (`AdSlot.astro`).
  - AdSense genelde kökte `ads.txt` ister. GitHub Pages proje sitesinde (`/tayma-lab/`) kök alan adına dosya koyamazsınız → **özel alan adı** bağlamanız gerekir (bkz. insan adımları).
- **Affiliate:** `affiliate.programs.<anahtar>` altında `label`, `url` (içinde `{id}` yer tutucusu) ve `id` alanları var. Örnek programlar (`ornekMuhasebe`, `ornekKargo`) yalnızca şablondur; gerçek programa göre adı/URL'yi değiştirin. `id` dolu olanlar yazı sonundaki “İşinizi kolaylaştırabilecek araçlar” kutusunda görünür (`showOnPosts`). Linkler `rel="sponsored nofollow"` taşır ve “ortaklık linki” etiketi alır.
- Değişikliği commit/push edin → site otomatik yeniden yayınlanır.

## 4. İnsan tarafından yapılması gerekenler (kontrol listesi)

Bu adımlar kimlik, banka bilgisi veya hukuki sorumluluk gerektirdiği için **otomatikleştirilmemiştir**:

- [ ] **LLM API anahtarı** ekleyin (yukarıda) ve kullanım/bütçe limiti tanımlayın.
- [ ] İlk haftalarda `REQUIRE_REVIEW=true` ile yazıları okuyup onaylayın; rakam ve kaynakları kontrol edin.
- [ ] **Hukuki inceleme:** `gizlilik-ve-cerezler` ve `ortaklik-aciklamasi` sayfaları şablondur (sayfada kırmızı “TASLAK” uyarısı var). Veri sorumlusu adı/adresi, iletişim e-postası (`site.config.json → contactEmail`), tarih ve yurt dışı aktarım bölümü bir avukat tarafından tamamlanmalı; sonra `Page.astro` çağrılarındaki `needsReview` kaldırılmalı.
- [ ] Reklam/analitik etkinleştirilmeden önce KVKK Çerez Rehberi'ne uygun **onay (rıza) mekanizması** eklenmeli (şu anki bildirim yalnızca bilgilendirme).
- [ ] **Özel alan adı** (önerilir): AdSense `ads.txt`, kökte `robots.txt` ve marka için. Alındıktan sonra Settings → Pages → Custom domain; `site.config.json` içinde `siteUrl` ve `basePath: "/"` güncellenmeli.
- [ ] **Google Search Console** doğrulaması ve `sitemap.xml` gönderimi.
- [ ] **AdSense başvurusu** (kimlik, adres, vergi ve banka bilgisi ister; genelde yeterli özgün içerik ve yasal sayfalar beklenir).
- [ ] **Affiliate programı başvuruları** (ör. muhasebe/e-Arşiv yazılımları, kargo entegratörleri, Hepsiburada/Trendyol ortaklık programları varsa) — kimlik/vergi/IBAN gerektirir.
- [ ] Reklam/ortaklık gelirinin **vergisel durumu** için mali müşavire danışın.
- [ ] `topics.yaml` kuyruğunu düzenli olarak yenileyin (konu bitince iş “Konu kalmadı” uyarısıyla atlanır).

## 5. Notlar

- GitHub, 60 gün boyunca hiç commit olmayan repolarda zamanlanmış (cron) iş akışlarını durdurabilir; günlük yazılar repo'yu aktif tutar.
- `GITHUB_TOKEN` ile yapılan push başka iş akışlarını tetiklemediği için günlük iş akışı deploy'u doğrudan (`workflow_call`) çağırır.
- Ana içerik ilk 3 yazı elle, kaynaklar araştırılarak yazılmıştır (`aiGenerated: false`).
