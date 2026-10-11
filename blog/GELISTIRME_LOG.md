# Satıcı Rehberi — Geliştirme Günlüğü

Günlük iyileştirme kaydı. Her çalışmada buraya kısa bir tarihli madde eklenir; rotasyon için son maddelere bakılır.

## Rotasyon
SEO → içerik → tasarım/erişilebilirlik → hız → (tekrar)

---

## 2026-10-11 — SEO: kategori şeması + iç linkler + Twitter görseli
- Kategori sayfalarına `CollectionPage` + `ItemList` JSON-LD eklendi (yazı listesi arama motorlarına yapılandırılmış veri olarak sunuluyor).
- Ana sayfa / kategori kartlarındaki kategori adı artık ilgili kategori sayfasına iç link veriyor (`PostCard`).
- `Base` layout’a eksik `twitter:image` ve `og:image:alt` meta etiketleri eklendi.
- Kategori linklerinin `.meta` stili okunabilirlik için hafifçe ayarlandı (aynı SEO iyileştirmesinin parçası).
