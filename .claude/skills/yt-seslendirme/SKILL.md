---
name: yt-seslendirme
description: >-
  Turn a YouTube script into a realistic, emotional AI voiceover with
  ElevenLabs Eleven v4 - pick or design the voice ("voice DNA"), mark the
  script with emotion audio tags, generate it in parts, and add music and
  sound effects. Use for "seslendir", "voiceover", "AI ses", "bu senaryoyu
  oku", "kendi sesimi klonla", "karakter sesi", "duygulu ses", or right
  after /yt-script when the user will not record their own voice.
---

# yt-seslendirme

A script from `/yt-script` into finished narration. The API calls themselves live in the
`text-to-speech`, `sound-effects`, `music`, `voice-changer` and `voice-isolator` skills: read the
one you need before writing code. This skill decides WHAT to send them.

Needs `ELEVENLABS_API_KEY`. If it is missing, use the `onboarding` skill. Never ask for the key in
chat.

## 1. The voice ("voice DNA")

Ask which of these the user wants, once, before generating anything:

- **A library voice.** Fastest. List voices with the `text-to-speech` skill and play two or three
  short samples of the hook line, not of "Hello world".
- **A designed voice.** A new voice from a description (age, accent, energy, texture, e.g. "30s,
  warm Istanbul Turkish, slightly husky, calm documentary narrator"). Done in the ElevenLabs
  dashboard under Voices; bring back the `voice_id`.
- **A clone of the user's own voice.** Instant clone from a minute of clean audio, or a
  Professional clone for the most faithful result. Clean the sample with `voice-isolator` first.

**Consent rule:** only clone a voice the user owns or has written permission to use. Never clone
a celebrity, a politician, another creator, or anyone who has not agreed. If asked, refuse that
voice and offer a designed voice in a similar style instead.

Write the chosen `voice_id`, model and settings into `~/.claude/youtube/voice.md` under a
`## AI voice` heading so every later run uses the same voice.

## 2. Mark the script for emotion

Default model: `eleven_v4` with `language_code="tr"` for Turkish. v4 ignores `style` and `speed`
and does not read SSML. Emotion comes from three things only:

- **Audio tags** in square brackets before the line they colour: `[excited]`, `[whispers]`,
  `[sighs]`, `[laughs]`, `[sarcastic]`, `[curious]`, `[serious]`.
- **Punctuation.** Ellipses for a pause, a dash for a break, CAPITALS for one stressed word.
- **Stability.** Around 0.35-0.5 for an emotional read, 0.6+ for steady narration.

Rules for tagging:

- At most one tag per sentence, and not on every sentence. A script where everything is
  `[excited]` sounds like nothing is.
- The hook gets the most deliberate tag. The body is mostly untagged.
- Strip every `[ON SCREEN: ...]` note from `/yt-script` output before sending - the model will read
  it out loud.
- Write numbers the way they should be said if `apply_text_normalization` gets them wrong.

Show the user the tagged script and get a yes before spending characters.

## 3. Generate

- **Hook first, alone.** Generate the first 15 seconds in two takes (different `seed`) and let the
  user pick. If the hook sounds wrong, the rest will too.
- **Then beat by beat**, one request per beat, using `previous_text` / `next_text` so the joins do
  not pop. Name files `01_hook.mp3`, `02_turn.mp3`... so the order survives.
- Report the character count from the `x-character-count` header after each run, so the user sees
  the cost.

## 4. Music and effects (optional)

- Background bed: the `music` skill, instrumental, the length of the video, and say "no vocals".
  Keep it 15-20 dB under the voice.
- Transitions, whooshes, risers: the `sound-effects` skill, short and few.
- If the user records a rough take themselves but wants a different voice, use `voice-changer`
  instead of TTS: their timing and emotion survive.

## The gate

Nothing here publishes. Every run ends with the files listed in order, their total runtime, the
characters used, and the question: **ship it, or change it?**
