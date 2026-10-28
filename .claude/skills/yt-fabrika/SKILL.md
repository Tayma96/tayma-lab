---
name: yt-fabrika
description: >-
  Run the channel's production line end to end for ONE long-form video and
  its Shorts: pick a proven topic, research, script, AI voiceover, Remotion
  visuals, packaging, SEO, chapters, Shorts cut from the long video, and a
  pre-publish policy check. Use for "yeni video yap", "sıradaki video",
  "fabrikayı çalıştır", "make the next video", "produce this week's
  videos", or any request to make a full video for the channel.
---

# yt-fabrika

One long video at a time, done properly. The previous automation shipped 700 templated Shorts and
earned nothing; this one exists to not repeat that. Read `kanal/kanal.yaml` first; every
channel-level choice (niche, language, voice, cadence) comes from there, never from memory.
`docs/STRATEJI.md` explains why.

Work in `uretim/<YYYY-MM-DD>-<slug>/`. Keep `durum.md` in that folder: a checklist of the stages
below, ticked as each one is approved, so a later session can pick up where this one stopped.

## The stages

Each stage ends with a short summary and **waits for the user's yes** before the next one starts.
Never chain stages silently.

1. **Topic.** Run `/yt-viral` against the niche. Pick topics that beat their own channel's median
   by 3x or more, then check the channel has not already covered the same question (look in
   `uretim/`). Offer three, with the multiple and the one-line promise of each. One question per
   video; two questions is two videos.
2. **Research.** Collect the facts the script will state, each with a source URL, into
   `kaynaklar.md`. Prefer primary sources (central banks, statistics offices, official filings).
   Any number without a source is cut, not guessed. Note the date of each figure.
3. **Script.** `/yt-script`, in the channel's language, 8-14 minutes at 150 wpm. Every
   `[ON SCREEN: ...]` beat names a chart, table, map or text card that Remotion can draw from the
   numbers in `kaynaklar.md`. End with the education-only line from `kanal.yaml`.
4. **Packaging before production.** `/yt-package` for title and thumbnail. If no title scores
   well, the topic is weak: go back to stage 1 rather than producing a video nobody clicks.
5. **Voice.** `/yt-seslendirme` with the channel `voice_id` and settings from `kanal.yaml`.
6. **Visuals.** Load `remotion-best-practices` and build the video as data-driven compositions in
   `video/` (one composition per beat, shared channel style). Show the Studio preview; render only
   after the user approves the preview.
7. **Chapters and SEO.** `/yt-chapters` from the voiceover transcript (`speech-to-text` if needed),
   then `/yt-seo`. Sources from `kaynaklar.md` go in the description.
8. **Shorts.** `/yt-shorts` on the finished long video: 2-3 cuts, each ending by pointing to the
   long video. Vertical Remotion compositions reuse the long video's charts.
9. **Policy check.** Fill in the checklist below in `durum.md`. Any "no" blocks upload.
10. **Hand-off.** List every file to upload, the title, description, tags, chapters, thumbnail and
    the schedule time. Upload as **private** (or scheduled) only; making a video public is always
    the user's action.

## Pre-publish policy checklist

- [ ] This video answers a question no earlier video on the channel answered.
- [ ] Every number on screen or in the narration has a source in `kaynaklar.md`.
- [ ] No financial advice: no "buy X", no price predictions; education-only line present.
- [ ] The voice imitates no real person. Altered/synthetic content disclosure will be ticked.
- [ ] `made_for_kids` is false and the content is not aimed at children.
- [ ] No third-party footage, music or images without a licence we can name.
- [ ] Title and thumbnail promise only what the video delivers.

## Cadence guard

Before starting a new video, count what was uploaded in the last 7 days in `uretim/`. If it already
meets `haftalik_uzun_video`, say so and suggest improving a weak earlier video instead. More volume
is not the lever; the 700 Shorts proved that.

## After 8 videos

Ask for the Studio numbers (CTR, average view duration, retention exports) and run `/yt-audit` and
`/yt-retention`. Adjust `kanal.yaml` from real data, not from these defaults.
