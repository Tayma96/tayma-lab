"""TikTok'a tarayıcı otomasyonuyla yükleme: wkaisertexas/tiktok-uploader (MIT, PyPI: tiktok-uploader).

Content Posting API denetimini beklemeden herkese açık paylaşır. TikTok hesabının oturum çerezini
kullanır (cookies.txt veya sadece `sessionid`). Bu yöntem TikTok'un resmi API'si değildir; TikTok
otomasyonu fark ederse hesabı doğrulamaya sokabilir, bu yüzden günlük limiti makul tut.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..config import env

log = logging.getLogger(__name__)
_UPLOADER = None


def _client(cfg: dict):
    global _UPLOADER
    if _UPLOADER is not None:
        return _UPLOADER
    try:
        from tiktok_uploader.upload import TikTokUploader
    except ImportError as e:
        raise RuntimeError("tiktok-uploader kurulu değil: pip install '.[tiktok-browser]' "
                           "&& playwright install chromium") from e
    cookies = env("TIKTOK_COOKIES_FILE", "secrets/tiktok_cookies.txt")
    sessionid = env("TIKTOK_SESSIONID")
    if not sessionid and not Path(cookies).exists():
        raise RuntimeError("TikTok oturumu yok: TIKTOK_SESSIONID ya da secrets/tiktok_cookies.txt gerekli")
    tcfg = cfg["upload"]["tiktok"]
    _UPLOADER = TikTokUploader(
        cookies="" if sessionid else cookies,
        sessionid=sessionid,
        browser=tcfg.get("browser", "chromium"),
        headless=tcfg.get("headless", True),
    )
    return _UPLOADER


def caption(meta: dict) -> str:
    tags = " ".join(f"#{t}" for t in meta["hashtags"][:8])
    return f"{meta['title']}\n{tags}"[:2200]


def upload(video: Path, meta: dict, cfg: dict) -> str:
    client = _client(cfg)
    ok = client.upload_video(str(video), description=caption(meta),
                             visibility=cfg["upload"]["tiktok"].get("visibility", "everyone"))
    if not ok:
        raise RuntimeError("tiktok-uploader yüklemeyi tamamlayamadı (çerez süresi dolmuş olabilir)")
    log.info("TikTok (tarayıcı) paylaşıldı: %s", video.name)
    return f"browser:{video.stem}"


def close() -> None:
    global _UPLOADER
    if _UPLOADER is not None:
        _UPLOADER.close()
        _UPLOADER = None
