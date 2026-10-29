"""Directed narration with Gemini TTS: the whole passage in ONE take, so the read flows like a person's.

Usage:
  GEMINI_API_KEY=... python3 ses_gemini.py metin.txt cikti.wav [--voice Charon] [--model gemini-3.1-flash-tts-preview]

metin.txt holds the director's note on the first line(s) and the script below a line with ---.
Audio tags such as [pause], [whispers], [serious] go inline in the script.
Standard library only.
"""
import argparse, base64, json, os, sys, urllib.request, wave

p = argparse.ArgumentParser()
p.add_argument("metin")
p.add_argument("cikti")
p.add_argument("--voice", default="Charon")
p.add_argument("--model", default="gemini-3.1-flash-tts-preview")
a = p.parse_args()

key = os.environ.get("GEMINI_API_KEY")
if not key:
    sys.exit("GEMINI_API_KEY is not set (put it in the environment or .env, never in code or chat).")

note, _, script = open(a.metin, encoding="utf-8").read().partition("\n---\n")
prompt = f"{note.strip()}\n\n{script.strip()}" if script else note.strip()

body = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "responseModalities": ["AUDIO"],
        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": a.voice}}},
    },
}
req = urllib.request.Request(
    f"https://generativelanguage.googleapis.com/v1beta/models/{a.model}:generateContent",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json", "x-goog-api-key": key},
)
try:
    resp = json.load(urllib.request.urlopen(req, timeout=300))
except urllib.error.HTTPError as e:
    sys.exit(f"HTTP {e.code}: {e.read().decode()[:500]}")

part = resp["candidates"][0]["content"]["parts"][0]["inlineData"]
pcm = base64.b64decode(part["data"])
rate = int(part.get("mimeType", "rate=24000").split("rate=")[-1].split(";")[0] or 24000)
with wave.open(a.cikti, "wb") as w:  # Gemini returns 16-bit mono PCM
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)
print(f"{a.cikti}: {len(pcm) / 2 / rate:.1f}s, voice={a.voice}")
