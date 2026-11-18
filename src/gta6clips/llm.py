"""Yapay zeka sağlayıcısı seçimi (config.yaml -> ai.provider). Varsayılan tamamen ÜCRETSİZ:

  github : ÜCRETSİZ. GitHub Models; GitHub Actions içinde otomatik gelen GITHUB_TOKEN ile çalışır
           (anahtar, kart, bilgisayar gerekmez). Günlük istek sınırı var; dolunca sezgisele düşer.
  none   : ÜCRETSİZ. Yapay zeka yok; analiz sezgisel sinyallerle yapılır (analyze.heuristic_*).
  ollama : ÜCRETSİZ ama kendi bilgisayarında/sunucunda model çalıştırmak gerekir.
  claude : ÜCRETLİ (Anthropic API). Sadece açıkça seçilirse kullanılır.

structured() başarısız olursa None döner; çağıran taraf ücretsiz sezgisel yönteme düşer.
"""
from __future__ import annotations

import base64
import logging
import time
from typing import TypeVar

import requests
from pydantic import BaseModel, ValidationError

from .config import env

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)
_PAUSED_UNTIL: dict[str, float] = {}   # sağlayıcı -> bu zamana kadar deneme (sınır doldu / ulaşılamıyor)


def provider(cfg: dict) -> str:
    return (cfg.get("ai") or {}).get("provider", "github")


def _pause(name: str, seconds: float, why: str) -> None:
    if _PAUSED_UNTIL.get(name, 0) < time.time():
        log.warning("%s kullanılamıyor (%s); %d dk boyunca ücretsiz sezgisel analiz kullanılacak",
                    name, why, seconds // 60)
    _PAUSED_UNTIL[name] = time.time() + seconds


def structured(cfg: dict, system: str, text: str, schema: type[T], images: list[bytes] | None = None,
               effort: str = "low") -> T | None:
    p = provider(cfg)
    if p == "none" or _PAUSED_UNTIL.get(p, 0) > time.time():
        return None
    if p == "github":
        return _github(cfg, system, text, schema, images or [])
    if p == "ollama":
        return _ollama(cfg, system, text, schema, images or [])
    if p == "claude":
        return _claude(cfg, system, text, schema, images or [], effort)
    return None


def _github(cfg: dict, system: str, text: str, schema: type[T], images: list[bytes]) -> T | None:
    token = env("GITHUB_TOKEN") or env("GH_MODELS_TOKEN")
    if not token:
        _pause("github", 24 * 3600, "GITHUB_TOKEN yok; GitHub Actions dışında çalışıyor olabilir")
        return None
    ai = cfg["ai"]
    content: list[dict] = [{"type": "text", "text": text}]
    for img in images[: ai.get("max_images", 4)]:
        content.append({"type": "image_url", "image_url": {
            "url": "data:image/jpeg;base64," + base64.b64encode(img).decode(), "detail": "low"}})
    url = ai.get("github_url", "https://models.github.ai/inference/chat/completions")
    body = {"model": ai["github_model"],
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": schema.__name__, "schema": schema.model_json_schema()}},
            "temperature": 0.3}
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    try:
        for attempt in range(3):  # anlık bağlantı kopmalarında hemen pes etme
            try:
                r = requests.post(url, timeout=120, headers=headers, json=body)
                break
            except requests.ConnectionError as e:
                log.warning("GitHub Models bağlantı hatası (deneme %d/3): %s", attempt + 1, str(e)[:300])
                if attempt == 2:
                    raise
                time.sleep(3 * (attempt + 1))
        if r.status_code == 429:
            wait = float(r.headers.get("retry-after", 3600))
            _pause("github", max(300.0, wait), "ücretsiz istek sınırı doldu")
            return None
        if r.status_code in (401, 403):
            _pause("github", 6 * 3600, f"yetki yok ({r.status_code}); workflow'da 'models: read' izni gerekli")
            return None
        r.raise_for_status()
        try:
            data = r.json()
        except ValueError:
            log.warning("GitHub Models JSON olmayan yanıt döndü: HTTP %s, %s, gövde: %r", r.status_code,
                        r.headers.get("content-type"), r.text[:300])
            return None
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
        if not content:
            log.warning("GitHub Models boş içerik döndü: %s", str(data)[:300])
            return None
        return schema.model_validate_json(content)
    except requests.ConnectionError as e:
        _pause("github", 300, f"bağlantı kurulamadı: {str(e)[:200]}")
        return None
    except (requests.RequestException, ValidationError, KeyError, IndexError, ValueError) as e:
        log.warning("GitHub Models yanıtı kullanılamadı (%s), bu klip sezgisel analiz edilecek", e)
        return None


def _ollama(cfg: dict, system: str, text: str, schema: type[T], images: list[bytes]) -> T | None:
    ai = cfg["ai"]
    msg: dict = {"role": "user", "content": text}
    if images:
        msg["images"] = [base64.b64encode(i).decode() for i in images]
    try:
        r = requests.post(f"{ai['ollama_url'].rstrip('/')}/api/chat", timeout=300, json={
            "model": ai["ollama_model"], "messages": [{"role": "system", "content": system}, msg],
            "format": schema.model_json_schema(), "stream": False, "options": {"temperature": 0.3}})
        r.raise_for_status()
        return schema.model_validate_json(r.json()["message"]["content"])
    except requests.ConnectionError:
        _pause("ollama", 1800, f"{ai['ollama_url']} adresine ulaşılamadı")
    except (requests.RequestException, ValidationError, KeyError, ValueError) as e:
        log.warning("Ollama yanıtı kullanılamadı (%s)", e)
    return None


def _claude(cfg: dict, system: str, text: str, schema: type[T], images: list[bytes], effort: str) -> T | None:
    if not env("ANTHROPIC_API_KEY") and not env("ANTHROPIC_AUTH_TOKEN"):
        _pause("claude", 24 * 3600, "ANTHROPIC_API_KEY yok")
        return None
    import anthropic

    content: list[dict] = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                        "data": base64.b64encode(i).decode()}} for i in images]
    content.append({"type": "text", "text": text})
    try:
        resp = anthropic.Anthropic().beta.messages.parse(
            model=cfg["metadata"]["model"], max_tokens=8000, output_config={"effort": effort},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            system=system, messages=[{"role": "user", "content": content}], output_format=schema)
    except anthropic.APIError as e:
        log.warning("Claude hatası: %s", e)
        return None
    return None if resp.stop_reason == "refusal" else resp.parsed_output
