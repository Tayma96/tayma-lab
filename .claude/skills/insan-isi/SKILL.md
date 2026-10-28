---
name: insan-isi
description: >-
  Quality review that makes a faceless video read as the work of a
  professional human team: finds the template tells in the script, voice,
  visuals, edit and packaging and fixes them before upload. Use for
  "profesyonel görünsün", "yapay zeka gibi durmasın", "kalite kontrol",
  "is this good enough", or as the last stage of /yt-fabrika.
---

# insan-isi

YouTube buries videos that look mass-produced. Viewers leave videos that feel generic. Both are
caused by the same tells, listed here. This review finds them and fixes them; it does not hide how
the video was made, and it never removes a watermark or skips a disclosure.

Score each section 0-2 (0 = the tell is there, 2 = clearly not). Anything below 8/10 total goes
back for fixes, starting with the lowest section.

## 1. Script

- [ ] Opens on a specific thing (a date, a sum, a name, a scene), not "In today's video" or
      "Have you ever wondered".
- [ ] Has a point of view: at least one place where the narrator judges, doubts or is surprised.
- [ ] Contains details only research could produce: a quote, a forgotten number, a minor character.
- [ ] Banned words absent: delve, tapestry, testament, in the realm of, it's worth noting,
      game-changer, unlock, navigate the landscape, in conclusion.
- [ ] Sentence lengths vary; no paragraph is three long sentences in a row.

## 2. Voice

- [ ] Listened end to end at 1x: no stumble, no mispronounced name, no line that sounds pasted in.
- [ ] Energy changes with the story; the hook and the reveal are audibly different from the setup.
- [ ] Pauses before reveals; breathing room between lines rather than butt joints.

## 3. Visuals

- [ ] Picture changes every 4-8 s and each shot matches the line it sits under.
- [ ] At least three kinds of visual (real footage, archival, map, chart, document, text card).
- [ ] No more than three of the same kind in a row; no shot reused.
- [ ] No generated image that pretends to be a real photo of a real person or event.
- [ ] Every asset is in `lisanslar.csv`.

## 4. Edit and sound

- [ ] Music changes with the act structure (at least two cues in a 10-minute video), ducked under
      the voice, ends on a button rather than a fade into nothing.
- [ ] Sound design on transitions and reveals, sparingly.
- [ ] Loudness -14 LUFS, no clipping (`ffmpeg-skill` check).
- [ ] Captions, if burned in, are clean and timed, not the default bouncing-word template.

## 5. Packaging and channel

- [ ] Thumbnail is designed for THIS video (`/yt-package`), not a template with swapped text.
- [ ] Title and description are written for this video; sources and credits are in the description.
- [ ] Not near-identical to an earlier upload in structure, title shape or thumbnail.

## Hand-back

The score per section, every failed box with the timecode or line, and the fix for each. Then:
**ship it, or change it?**
