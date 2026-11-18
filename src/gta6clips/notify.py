"""Telegram bildirimi: hazır videoyu başlık/açıklama/hashtag ile telefona gönderir.

Neden: Google denetiminden geçmemiş API projelerinden YouTube'a yüklenen videolar gizli (kilitli) kalır.
Lansman anı gibi kritik kliplerde video saniyeler içinde telefona gelir; oradan YouTube Shorts, Instagram
Reels, X vb. uygulamalara paylaş düğmesiyle elle yüklenir.

Kurulum: Telegram'da @BotFather > /newbot > token'ı TELEGRAM_BOT_TOKEN secret'ı yap > kendi botuna /start yaz.
TELEGRAM_CHAT_ID verilmezse bota en son yazan kişi bulunur ve data/telegram.json'a kaydedilir.
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

import requests

from .config import env

log = logging.getLogger(__name__)
API = "https://api.telegram.org/bot{token}/{method}"
MAX_BYTES = 48 * 1024 * 1024  # bot API sınırı 50 MB
_STATE = Path("data/telegram.json")


def _token() -> str | None:
    return env("TELEGRAM_BOT_TOKEN")


def enabled(cfg: dict) -> bool:
    return bool((cfg.get("notify") or {}).get("telegram", True)) and bool(_token())


def chat_id(save: bool = True) -> str | None:
    """Secret'taki chat id; yoksa kayıtlı olan; o da yoksa bota son yazan özel sohbet."""
    cid = env("TELEGRAM_CHAT_ID")
    if cid:
        return cid
    if _STATE.exists():
        try:
            cid = json.loads(_STATE.read_text()).get("chat_id")
            if cid:
                return str(cid)
        except ValueError:
            pass
    token = _token()
    if not token:
        return None
    try:
        r = requests.get(API.format(token=token, method="getUpdates"), timeout=30)
        r.raise_for_status()
        for upd in reversed(r.json().get("result", [])):
            chat = (upd.get("message") or upd.get("my_chat_member") or {}).get("chat") or {}
            if chat.get("type") == "private" and chat.get("id"):
                cid = str(chat["id"])
                if save:
                    _STATE.parent.mkdir(parents=True, exist_ok=True)
                    _STATE.write_text(json.dumps({"chat_id": cid}))
                return cid
    except Exception:  # noqa: BLE001
        log.exception("Telegram sohbeti bulunamadı")
    return None


def caption(meta: dict, broadcaster: str, quality: float | None, launch_clip: bool) -> str:
    tags = " ".join(meta.get("hashtags") or [])
    head = "🚨 LANSMAN ANI" if launch_clip else f"⭐ Kalite {quality}"
    text = (f"{head} | twitch.tv/{broadcaster.lower()}\n\n"
            f"{meta.get('title', '')}\n\n{meta.get('description', '')}\n\n{tags}")
    return text[:1020]  # Telegram açıklama sınırı 1024


def _shrink(video: Path) -> Path:
    small = video.with_name(video.stem + "_tg.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vf", "scale=720:-2",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", "-b:a", "96k",
                    str(small)], check=True)
    return small


def send_video(cfg: dict, video: Path, text: str) -> bool:
    if not enabled(cfg):
        return False
    cid = chat_id()
    if not cid:
        log.warning("Telegram: sohbet yok. Kendi botuna Telegram'dan /start yaz.")
        return False
    path = video if video.stat().st_size <= MAX_BYTES else _shrink(video)
    try:
        with path.open("rb") as f:
            r = requests.post(API.format(token=_token(), method="sendVideo"), timeout=180,
                              data={"chat_id": cid, "caption": text, "supports_streaming": "true"},
                              files={"video": (video.name, f, "video/mp4")})
        if r.status_code != 200:
            log.warning("Telegram gönderimi başarısız (%s): %s", r.status_code, r.text[:200])
            return False
        log.info("📲 Telegram'a gönderildi: %s", video.name)
        return True
    except Exception:  # noqa: BLE001 - bildirim hatası akışı durdurmasın
        log.exception("Telegram gönderim hatası")
        return False


def send_text(cfg: dict, text: str) -> bool:
    if not enabled(cfg):
        return False
    cid = chat_id()
    if not cid:
        return False
    try:
        r = requests.post(API.format(token=_token(), method="sendMessage"), timeout=30,
                          data={"chat_id": cid, "text": text[:4000]})
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        log.exception("Telegram mesaj hatası")
        return False
