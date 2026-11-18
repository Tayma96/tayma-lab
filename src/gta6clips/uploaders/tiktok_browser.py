"""TikTok'a tarayıcı otomasyonuyla yükleme: wkaisertexas/tiktok-uploader (MIT, PyPI: tiktok-uploader).

Content Posting API denetimini beklemeden herkese açık paylaşır. TikTok hesabının oturum çerezini
kullanır (cookies.txt veya sadece `sessionid`). Bu yöntem TikTok'un resmi API'si değildir; TikTok
otomasyonu fark ederse hesabı doğrulamaya sokabilir, bu yüzden günlük limiti makul tut.

Her yükleme AYRI bir Python sürecinde yapılır: tiktok-uploader Playwright'ın senkron API'sini kullanır
ve aynı süreçte başka bir kütüphanenin açık bıraktığı asyncio döngüsü varsa "Playwright Sync API inside
the asyncio loop" hatasıyla hiç açılmaz. Ayrı süreç bunu tamamen önler, tarayıcıyı da her seferinde kapatır.
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path

from ..config import env

log = logging.getLogger(__name__)


def caption(meta: dict) -> str:
    tags = " ".join(f"#{t}" for t in meta["hashtags"][:8])
    return f"{meta['title']}\n{tags}"[:2200]


def _session() -> tuple[str, str]:
    cookies = env("TIKTOK_COOKIES_FILE", "secrets/tiktok_cookies.txt")
    sessionid = env("TIKTOK_SESSIONID") or ""
    if not sessionid and not Path(cookies).exists():
        raise RuntimeError("TikTok oturumu yok: TIKTOK_SESSIONID ya da secrets/tiktok_cookies.txt gerekli")
    return ("" if sessionid else cookies), sessionid


def upload(video: Path, meta: dict, cfg: dict, timeout: float = 600) -> str:
    _session()  # erken ve anlaşılır hata
    tcfg = cfg["upload"]["tiktok"]
    job = {"video": str(Path(video).resolve()), "description": caption(meta),
           "visibility": tcfg.get("visibility", "everyone"), "browser": tcfg.get("browser", "chromium"),
           "headless": bool(tcfg.get("headless", True))}
    res = subprocess.run([sys.executable, "-m", "gta6clips.uploaders.tiktok_browser"], input=json.dumps(job),
                         capture_output=True, text=True, timeout=timeout)
    tail = (res.stdout + res.stderr).strip()[-1500:]
    if res.returncode != 0 or "TIKTOK_OK" not in res.stdout:
        raise RuntimeError(f"TikTok yüklemesi başarısız (çerez süresi dolmuş ya da doğrulama istenmiş olabilir): "
                           f"{tail}")
    log.info("TikTok (tarayıcı) paylaşıldı: %s", Path(video).name)
    return f"browser:{Path(video).stem}"


def close() -> None:  # geriye dönük uyumluluk: tarayıcı artık her yüklemede kendi sürecinde kapanıyor
    return None


def _child() -> int:
    """Ayrı süreç: stdin'den işi okur, yükler, başarıda TIKTOK_OK yazar."""
    job = json.loads(sys.stdin.read())
    try:
        from tiktok_uploader.upload import TikTokUploader
    except ImportError:
        print("tiktok-uploader kurulu değil: pip install '.[tiktok-browser]' && playwright install chromium")
        return 2
    cookies, sessionid = _session()
    client = TikTokUploader(cookies=cookies, sessionid=sessionid, browser=job["browser"], headless=job["headless"])
    try:
        ok = client.upload_video(job["video"], description=job["description"], visibility=job["visibility"])
    finally:
        try:
            client.close()
        except Exception:  # noqa: BLE001
            pass
    if not ok:
        print("tiktok-uploader yüklemeyi tamamlayamadı")
        return 1
    print("TIKTOK_OK")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(_child())
