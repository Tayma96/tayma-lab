"""faster-whisper ile kelime zamanlı döküm. Kurulu değilse altyazısız devam edilir."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)
_MODEL = None


@dataclass
class Word:
    start: float
    end: float
    text: str


def transcribe(path: Path, model_name: str = "small", language: str | None = "en") -> list[Word]:
    global _MODEL
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log.warning("faster-whisper kurulu değil, altyazı atlanıyor (pip install '.[captions]')")
        return []
    try:
        if _MODEL is None:
            _MODEL = WhisperModel(model_name, device="auto", compute_type="int8")
        # Sesi ffmpeg ile kendimiz çözüyoruz: faster-whisper'ın PyAV ile çözmesi yeni PyAV sürümlerinde
        # "unexpected keyword argument 'metadata_errors'" hatası veriyor (sürüm uyuşmazlığı).
        audio = load_audio(path)
        if audio.size == 0:
            return []
        segments, _ = _MODEL.transcribe(audio, language=language, word_timestamps=True, vad_filter=True)
        words: list[Word] = []
        for seg in segments:
            for w in seg.words or []:
                text = w.word.strip()
                if text:
                    words.append(Word(float(w.start), float(w.end), text))
        return words
    except Exception:  # noqa: BLE001 - döküm hatası klibi düşürmesin, altyazısız devam
        log.exception("Döküm başarısız, altyazısız devam: %s", path)
        return []


def load_audio(path: Path, sr: int = 16000):
    """ffmpeg ile 16 kHz mono float32 dizi (Whisper'ın beklediği biçim)."""
    import subprocess

    import numpy as np

    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1",
                          "-ar", str(sr), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def plain_text(words: list[Word]) -> str:
    return " ".join(w.text for w in words)
