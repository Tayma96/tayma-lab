# tayma-lab — YouTube kanal fabrikası

Yüksek RPM'li (şirket hikayeleri, İngilizce, ABD/İngiltere/Kanada/Avustralya) bir YouTube kanalı için
yarı otomatik üretim hattı. Uzun video ana ürün; Shorts yalnızca uzun videonun fragmanı. Her video
yayından önce insan onayından geçer.

- Neden bu niş, bu kitle, bu ülkeler: [docs/ARASTIRMA.md](docs/ARASTIRMA.md)
- Kanal planı ve gelir hesabı: [docs/STRATEJI.md](docs/STRATEJI.md)
- Kanal ayarları: [kanal/kanal.yaml](kanal/kanal.yaml)

## Kullanım

Claude Code'da bu repoyu açıp:

```
/yt-fabrika
```

Hat şu skilleri sırayla çalıştırır (hepsi `.claude/skills/` altında):

| Aşama | Skill |
|---|---|
| Konu | `yt-viral` |
| Senaryo | `yt-script` |
| Başlık + küçük resim | `yt-package` |
| Seslendirme (Eleven v4) | `yt-seslendirme`, `text-to-speech`, `music`, `sound-effects` |
| Görsel (animasyonlu grafik) | `remotion-best-practices` |
| Bölümler + açıklama | `yt-chapters`, `speech-to-text`, `yt-seo` |
| Shorts | `yt-shorts` |
| Analiz | `yt-retention`, `yt-audit`, `yt-plan`, `yt-comment` |

## Gerekenler

- `ELEVENLABS_API_KEY` (seslendirme) — `onboarding` skill'i kurar.
- Node.js (Remotion), Python 3.
- Bir YouTube kanalı. Yükleme şimdilik elle; YouTube API ile özel/planlı yükleme bir sonraki adım.

Dışarıdan alınan skillerin kaynak ve lisansları: `.claude/youtube-agent/`, `.claude/elevenlabs/`,
`.claude/remotion/`.
