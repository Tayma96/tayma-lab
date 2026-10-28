---
name: yt-seslendirme
description: >-
  Turn a YouTube script into a realistic, emotional voiceover at zero cost
  with the open-source Chatterbox models (MIT, commercial use allowed),
  with ElevenLabs Eleven v4 as the paid upgrade. Picks the voice, directs
  the read line by line, generates it in parts and cleans the audio. Use
  for "seslendir", "voiceover", "AI ses", "bu senaryoyu oku", "duygulu
  ses", "kendi sesimi klonla", or right after /yt-script.
---

# yt-seslendirme

The voice is the first thing that gives a faceless video away. A flat, perfectly even read with no
breath is what people call "AI voice". The job here is a DIRECTED read, not a conversion.

## Engine (read `ses` in `kanal/kanal.yaml`)

| Engine | Cost | Runs on | Use when |
|---|---|---|---|
| `chatterbox` original (500M) | free, MIT | free Colab GPU or local GPU | default narration; `exaggeration` + `cfg_weight` give the emotional range |
| `chatterbox` Nano (110M) | free, MIT | **CPU**, ~3x realtime on 8 cores | no GPU at all; supports `[laugh]`, `[chuckle]`, `[cough]` tags |
| `elevenlabs` `eleven_v4` | paid (Starter plan) | API | once the channel earns. The **free ElevenLabs plan is non-commercial** and cannot be used on a monetised channel |

```bash
pip install chatterbox-tts
```

```python
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS                 # original
from chatterbox.tts_turbo import ChatterboxTurboTTS      # Turbo / Nano

model = ChatterboxTTS.from_pretrained(device="cuda")      # or "cpu" / "mps"
wav = model.generate(line, audio_prompt_path="voice/ref.wav",
                     exaggeration=0.6, cfg_weight=0.35)
ta.save("01_hook.wav", wav, model.sr)

nano = ChatterboxTurboTTS.from_pretrained(device="cpu", nano=True)  # Nano needs a reference clip
```

Check the README of https://github.com/resemble-ai/chatterbox if an import fails; the API moves.
Chatterbox embeds an inaudible watermark in every file. Never try to strip it.

## 1. The voice

One narrator for the whole channel, chosen once and stored in `voice/` with its settings in
`kanal.yaml`. Options, in order:

1. **The model's own default voice** (original Chatterbox, no reference clip). Zero risk.
2. **The user's own voice**: 10-20 s of clean speech recorded by the user, used as the reference.
3. **A designed voice** from a paid tool later.

Never use a recording of another real person as the reference clip (a celebrity, another creator,
an audiobook narrator, a film), even if the recording itself is public domain. Refuse and offer
option 1 or 2.

## 2. Direct the script

Split the script into lines of one or two sentences. For each line decide, and write next to it:

- **Energy**: `exaggeration` 0.4 (calm fact) to 0.8 (reveal, twist). Lower `cfg_weight` (~0.3) when
  exaggeration goes up, so the pace stays deliberate.
- **Pause**: punctuation does the work. A full stop and a new line before a reveal; an ellipsis for
  a held beat; a dash for a turn.
- **Tag** (Nano/Turbo, or v4): at most one per 30 seconds. A `[chuckle]` on a line that is
  actually funny sounds human; a tag every line sounds like a demo.

Rules that make it sound read by a person:

- Vary sentence length in the SCRIPT. Three long sentences in a row produce the robot cadence no
  setting can fix.
- Write numbers as spoken ("about two point four billion", not "$2.4B").
- Strip every `[ON SCREEN: ...]` note before generating.
- Contractions ("it's", "didn't") unless the line needs weight.

Show the directed script to the user before generating.

## 3. Generate

- **Hook first, three takes** (different settings), the user picks. If the hook sounds synthetic
  the rest will too: fix the writing, not the settings.
- Then line by line, files numbered in order (`001.wav`, `002.wav`...). Regenerate any line that
  mispronounces a name or stumbles; never ship a stumble.
- Join with `ffmpeg-skill`, leaving 150-400 ms of room tone between lines (longer before a reveal),
  not silence and not a hard butt joint.

## 4. Finish the audio

With `ffmpeg-skill`: light denoise, normalise to -14 LUFS for YouTube, music bed 15-20 dB under the
voice with ducking. Listen to the whole file once at 1x before handing it on.

## Honesty

Answer YouTube's AI-use question in Studio truthfully for every upload; `kanal.yaml`
`yapay_zeka_etiketi` records the channel's standing answer. Quality is what keeps a video out of
the shadows, not hiding how it was made.

## The gate

Every run ends with the files in order, total runtime and the question: **ship it, or change it?**
