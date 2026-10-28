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
| Seslendirme (Chatterbox, ücretsiz) | `yt-seslendirme` |
| Görüntü, müzik, efekt (ücretsiz, lisans kayıtlı) | `ucretsiz-kaynak` |
| Grafik, harita, zaman çizelgesi | `remotion-best-practices` |
| Kurgu ve YouTube çıktısı | `ffmpeg-skill` |
| Bölümler + açıklama | `yt-chapters`, `speech-to-text`, `yt-seo` |
| Shorts | `yt-shorts` |
| "İnsan işi" kalite kontrolü | `insan-isi` |
| Analiz | `yt-retention`, `yt-audit`, `yt-plan`, `yt-comment` |

## Gerekenler

- Bütçe: 0 $. Ücretsiz `PEXELS_API_KEY` ve `PIXABAY_API_KEY` (`.env` içine).
- Python 3.10+, FFmpeg, Node.js (Remotion), `pip install chatterbox-tts`.
- İleride ücretli yükseltme: ElevenLabs (`text-to-speech` vb. skiller hazır).
- Bir YouTube kanalı. Yükleme şimdilik elle; YouTube API ile özel/planlı yükleme bir sonraki adım.

Dışarıdan alınan skillerin kaynak ve lisansları: `.claude/youtube-agent/`, `.claude/elevenlabs/`,
`.claude/remotion/`, `.claude/ffmpeg-skill/`.
