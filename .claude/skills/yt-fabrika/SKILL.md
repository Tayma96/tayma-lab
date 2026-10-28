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
   `kaynaklar.md`. Prefer primary sources: annual reports and SEC filings, founders' own interviews and books, reputable press (Reuters, Bloomberg, FT, WSJ).
   Any number without a source is cut, not guessed. Note the date of each figure.
3. **Script.** `/yt-script`, in the channel's language, 8-14 minutes at 150 wpm. Every
   `[ON SCREEN: ...]` beat names what is seen: a real or archival shot, a map, a chart, a document
   or a text card. End with the disclaimer line from `kanal.yaml`.
4. **Packaging before production.** `/yt-package` for title and thumbnail. If no title scores
   well, the topic is weak: go back to stage 1 rather than producing a video nobody clicks.
5. **Voice.** `/yt-seslendirme` with the engine and settings in `kanal.yaml` (zero budget:
   Chatterbox).
6. **Visuals.** Two layers:
   - **Footage**: `ucretsiz-kaynak` finds real and archival shots for every beat and writes
     `lisanslar.csv`.
   - **Graphics**: `remotion-best-practices` renders the charts, maps, timelines and text cards in
     the channel style, as separate clips.
   Show the user a shot list (timecode, line, shot, source) before downloading or rendering.
7. **Edit.** `ffmpeg-skill` assembles voice, footage, graphics, music and sound effects into the
   16:9 master: shot every 4-8 s, slow push-ins on stills, music ducked under the voice, -14 LUFS,
   YouTube export. Show a 720p preview first; the final render only after the user approves it.
8. **Chapters and SEO.** `/yt-chapters` from the voiceover transcript, then `/yt-seo`. Sources from
   `kaynaklar.md` and credits from `lisanslar.csv` go in the description.
9. **Shorts.** `/yt-shorts` on the finished long video: 2-3 cuts reframed to 9:16 with
   `ffmpeg-skill`, each ending by pointing to the long video.
10. **Quality and policy.** Run `insan-isi`; anything under 8/10 goes back to the weakest stage.
    Then fill in the checklist below in `durum.md`. Any "no" blocks upload.
11. **Hand-off.** List every file to upload, the title, description, tags, chapters, thumbnail and
    the schedule time. Upload as **private** (or scheduled) only; making a video public is always
    the user's action.

## Pre-publish policy checklist

- [ ] This video answers a question no earlier video on the channel answered.
- [ ] Every number on screen or in the narration has a source in `kaynaklar.md`.
- [ ] No financial advice: no "buy this stock", no price predictions; disclaimer line present.
- [ ] Claims about real people and companies are sourced facts, not rumour; opinions are labelled
      as opinions. Nothing that could read as defamation.
- [ ] No company logos, product photos or ad footage used as decoration; company names and our own
      charts, timelines and maps instead.
- [ ] The voice imitates no real person. YouTube's AI-use / altered content question will be
      answered truthfully at upload.
- [ ] `made_for_kids` is false and the content is not aimed at children.
- [ ] Every footage, image, music and sound file has a row in `lisanslar.csv`.
- [ ] Title and thumbnail promise only what the video delivers.

## Cadence guard

Before starting a new video, count what was uploaded in the last 7 days in `uretim/`. If it already
meets `haftalik_uzun_video`, say so and suggest improving a weak earlier video instead. More volume
is not the lever; the 700 Shorts proved that.

## After 8 videos

Ask for the Studio numbers (CTR, average view duration, retention exports) and run `/yt-audit` and
`/yt-retention`. Adjust `kanal.yaml` from real data, not from these defaults.
