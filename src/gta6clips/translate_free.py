"""Ücretsiz, çevrimdışı İngilizce -> Türkçe çeviri (Argos Translate modeli, CTranslate2 ile).

GitHub Models çalışmadığında TikTok altyazılarını Türkçeye çevirmek için. Argos'un hazır Python paketi
PyTorch'a bağımlı olduğu için çok ağır; burada sadece modeli indirip doğrudan CTranslate2 (faster-whisper
ile zaten kurulu) + sentencepiece ile çalıştırıyoruz. Model (~100 MB) ilk kullanımda indirilir ve
GitHub Actions önbelleğinde saklanır.
"""
from __future__ import annotations

import logging
import threading
import time
import zipfile
from pathlib import Path

import requests

from .config import env

log = logging.getLogger(__name__)
MODEL_URL = "https://argos-net.com/v1/translate-en_tr-1_5.argosmodel"
_LOCK = threading.Lock()
_MODEL: tuple | None = None
_FAILED_UNTIL = 0.0


def model_dir() -> Path:
    return Path(env("ARGOS_DIR", "~/.cache/argos-en-tr")).expanduser()


def _find_root(base: Path) -> Path | None:
    for sp in base.rglob("sentencepiece.model"):
        if (sp.parent / "model").is_dir():
            return sp.parent
    return None


def _ensure() -> Path:
    base = model_dir()
    root = _find_root(base) if base.exists() else None
    if root:
        return root
    base.mkdir(parents=True, exist_ok=True)
    tmp = base / "model.zip"
    log.info("Türkçe çeviri modeli indiriliyor (ilk sefer): %s", MODEL_URL)
    with requests.get(MODEL_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    with zipfile.ZipFile(tmp) as z:
        z.extractall(base)
    tmp.unlink(missing_ok=True)
    root = _find_root(base)
    if not root:
        raise RuntimeError("Çeviri modeli beklenen biçimde değil (model/ + sentencepiece.model yok)")
    return root


def _load():
    global _MODEL
    if _MODEL is None:
        import ctranslate2
        import sentencepiece

        root = _ensure()
        translator = ctranslate2.Translator(str(root / "model"), device="cpu", compute_type="int8",
                                            inter_threads=1, intra_threads=2)
        sp = sentencepiece.SentencePieceProcessor(model_file=str(root / "sentencepiece.model"))
        _MODEL = (translator, sp)
    return _MODEL


def translate(texts: list[str]) -> list[str] | None:
    """Her metni ayrı çevirir (aynı sıra, aynı sayı). Kullanılamazsa None."""
    global _FAILED_UNTIL
    if time.time() < _FAILED_UNTIL:
        return None
    if not texts:
        return []
    try:
        with _LOCK:
            translator, sp = _load()
            tokens = [sp.encode(t, out_type=str) for t in texts]
            results = translator.translate_batch(tokens, beam_size=2, max_decoding_length=64)
        return [sp.decode(r.hypotheses[0]).replace("▁", " ").strip() for r in results]
    except Exception:  # noqa: BLE001 - çeviri yoksa altyazısız devam
        log.exception("Ücretsiz çeviri kullanılamıyor; Türkçe altyazı atlanacak")
        _FAILED_UNTIL = time.time() + 1800  # 30 dk sonra tekrar dene
        return None
