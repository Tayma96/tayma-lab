"""TikTok Content Posting API (Direct Post).

Not: TikTok denetiminden geçmemiş uygulamaların paylaşımları sadece "SELF_ONLY" (gizli) olabilir.
Bu modül hesabın izin verdiği gizlilik seçeneklerini sorar; PUBLIC_TO_EVERYONE yoksa gizli paylaşır
ve bunu loglar. Denetim onaylanınca kod değişmeden herkese açık paylaşmaya başlar.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

from ..config import env

log = logging.getLogger(__name__)
API = "https://open.tiktokapis.com/v2"
SCOPES = "user.info.basic,video.publish"


def _token_file() -> Path:
    return Path(env("TIKTOK_TOKEN_FILE", "secrets/tiktok_token.json"))


def _save(tok: dict) -> None:
    tok["obtained_at"] = time.time()
    f = _token_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(tok, indent=2))


def _token_request(data: dict) -> dict:
    r = requests.post(f"{API}/oauth/token/", data={
        "client_key": env("TIKTOK_CLIENT_KEY"), "client_secret": env("TIKTOK_CLIENT_SECRET"), **data},
        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    r.raise_for_status()
    tok = r.json()
    if "access_token" not in tok:
        raise RuntimeError(f"TikTok token hatası: {tok}")
    return tok


def authorize() -> None:
    """Tarayıcıda TikTok girişi yapılır, kod localhost'a döner ve token kaydedilir."""
    from ..oauth_local import capture_code

    redirect = env("TIKTOK_REDIRECT_URI", "http://localhost:8765/callback")
    code = capture_code("https://www.tiktok.com/v2/auth/authorize/", {
        "client_key": env("TIKTOK_CLIENT_KEY"), "scope": SCOPES, "response_type": "code"}, redirect)
    _save(_token_request({"code": code, "grant_type": "authorization_code", "redirect_uri": redirect}))
    print("TikTok yetkilendirmesi kaydedildi.")


def _access_token() -> str:
    f = _token_file()
    if not f.exists():
        raise RuntimeError("TikTok yetkisi yok: önce `gta6clips auth tiktok` çalıştır")
    tok = json.loads(f.read_text())
    if time.time() > tok["obtained_at"] + tok.get("expires_in", 0) - 300:
        tok = _token_request({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})
        _save(tok)
    return tok["access_token"]


def _post(path: str, token: str, body: dict) -> dict:
    r = requests.post(f"{API}{path}", json=body, timeout=60, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    data = r.json() if r.content else {}
    err = data.get("error", {})
    if r.status_code >= 400 or (err.get("code") not in (None, "ok")):
        raise RuntimeError(f"TikTok {path} hatası: {r.status_code} {err or r.text[:300]}")
    return data.get("data", {})


def choose_privacy(options: list[str]) -> str:
    for p in ("PUBLIC_TO_EVERYONE", "FOLLOWER_OF_CREATOR", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"):
        if p in options:
            return p
    return "SELF_ONLY"


def upload(video: Path, meta: dict, cfg: dict) -> str:
    token = _access_token()
    info = _post("/post/publish/creator_info/query/", token, {})
    privacy = choose_privacy(info.get("privacy_level_options", []))
    if privacy != "PUBLIC_TO_EVERYONE":
        log.warning("TikTok: herkese açık paylaşım izni yok (uygulama denetimi bekleniyor), gizlilik=%s", privacy)
    size = video.stat().st_size
    caption = f"{meta['title']} " + " ".join(f"#{t}" for t in meta["hashtags"][:8])
    init = _post("/post/publish/video/init/", token, {
        "post_info": {
            "title": caption[:2200],
            "privacy_level": privacy,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1},
    })
    with video.open("rb") as fh:
        r = requests.put(init["upload_url"], data=fh, timeout=600, headers={
            "Content-Type": "video/mp4", "Content-Length": str(size),
            "Content-Range": f"bytes 0-{size - 1}/{size}"})
    r.raise_for_status()
    publish_id = init["publish_id"]
    for _ in range(60):
        time.sleep(5)
        st = _post("/post/publish/status/fetch/", token, {"publish_id": publish_id})
        status = st.get("status")
        if status == "PUBLISH_COMPLETE":
            log.info("TikTok paylaşıldı: %s (%s)", publish_id, privacy)
            return publish_id
        if status == "FAILED":
            raise RuntimeError(f"TikTok paylaşım başarısız: {st.get('fail_reason')}")
    log.warning("TikTok hâlâ işleniyor, publish_id=%s", publish_id)
    return publish_id
