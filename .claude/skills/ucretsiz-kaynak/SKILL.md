---
name: ucretsiz-kaynak
description: >-
  Find free, commercially usable b-roll, archival footage, photos, music
  and sound effects for a video, and keep a licence log for every asset.
  Use for "b-roll bul", "görüntü bul", "stok video", "müzik bul", "ses
  efekti", "free footage", or the visuals stage of /yt-fabrika.
---

# ucretsiz-kaynak

Real footage is what makes a faceless video look made by a person. A video built only from
generated images or one chart style looks like a template. Budget is zero, so every asset comes
from a source whose licence allows monetised use, and every asset is logged.

## Where to look

| Need | Source | Licence to check |
|---|---|---|
| Modern b-roll (offices, cities, hands, products in use) | Pexels, Pixabay (free API keys) | Their own licence: free commercial use, no attribution required, no selling the raw clip, no implying endorsement |
| Historical footage and photos | Wikimedia Commons, Internet Archive (Prelinger collection), Library of Congress, US National Archives | **Public domain or CC BY / CC BY-SA only.** Read the file's own licence line; "found on Commons" is not a licence |
| Space, science, US government | NASA, NOAA, other US federal works | Usually public domain; NASA logos and people's likeness have extra rules |
| Music | YouTube Audio Library (in Studio), Pixabay Music | Use tracks marked no attribution, or put the required credit in the description |
| Sound effects | Freesound (filter to CC0), Pixabay | CC0 only, to keep the log simple |

Never use: clips from other YouTube videos, films, TV, news broadcasts, company ads, "no copyright"
compilations from YouTube, or anything with a watermark. Company logos only when the video is
discussing that logo, never as decoration.

## How to pick

- **One shot per 4-8 seconds of narration**, matched to what is being SAID at that moment, not to
  the topic in general. "The factory closed in 2009" wants an empty factory, not a stock photo of
  money.
- Prefer footage with people doing real things, natural light and imperfection. Glossy smiling
  stock-office clips are the second biggest template tell after the voice.
- Mix the sources inside a video: real footage, archival stills with a slow push-in, a map, a
  chart. Never more than three charts or three stock clips in a row.
- Same clip never twice in one video, and not in two videos within a month.

## The licence log

Write `uretim/<video>/lisanslar.csv`, one row per asset used:

```csv
file,source,url,author,licence,attribution_required,used_at
```

Assets with `attribution_required=yes` get their credit in the video description automatically at
the SEO stage. An asset without a row is removed before render.

## API keys

Pexels and Pixabay keys are free; ask the user to put them in `.env` as `PEXELS_API_KEY` and
`PIXABAY_API_KEY`, never in chat and never in code. Without keys, list search links for the user to
download from instead.
