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
    if _MODEL is None:
        _MODEL = WhisperModel(model_name, device="auto", compute_type="int8")
    segments, _ = _MODEL.transcribe(str(path), language=language, word_timestamps=True, vad_filter=True)
    words: list[Word] = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append(Word(float(w.start), float(w.end), text))
    return words


def plain_text(words: list[Word]) -> str:
    return " ".join(w.text for w in words)
