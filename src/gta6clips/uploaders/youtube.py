"""YouTube Data API v3 ile Shorts yükleme.

Not: Google'ın denetiminden (audit) geçmemiş API projelerinden yüklenen videolar Google tarafından
gizli (private) olarak kilitlenir. Herkese açık yükleme için Google Cloud Console'dan
"YouTube API Services - Audit and Quota Extension" formu doldurulmalı.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..config import env

log = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]  # izlenme istatistikleri için


def _credentials(interactive: bool = False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_file = Path(env("YOUTUBE_TOKEN_FILE", "secrets/youtube_token.json"))
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES) if token_file.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not interactive:
            raise RuntimeError("YouTube yetkisi yok: önce `gta6clips auth youtube` çalıştır")
        secrets = env("YOUTUBE_CLIENT_SECRETS", "secrets/youtube_client_secret.json")
        flow = InstalledAppFlow.from_client_secrets_file(secrets, SCOPES)
        creds = flow.run_local_server(port=8766, open_browser=False,
                                      authorization_prompt_message="Bu adresi tarayıcıda aç: {url}")
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json())
    return creds


def authorize() -> None:
    _credentials(interactive=True)
    print("YouTube yetkilendirmesi kaydedildi.")


def upload(video: Path, meta: dict, cfg: dict) -> str:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    yt_cfg = cfg["upload"]["youtube"]
    youtube = build("youtube", "v3", credentials=_credentials(), cache_discovery=False)
    tags = meta["hashtags"]
    description = meta["description"] + "\n\n" + " ".join(f"#{t}" for t in tags[:8]) + " #Shorts"
    body = {
        "snippet": {
            "title": meta["title"][:100],
            "description": description[:4900],
            "tags": tags,
            "categoryId": yt_cfg["category_id"],
            "defaultLanguage": "en",
        },
        "status": {"privacyStatus": yt_cfg["privacy"], "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log.debug("YouTube yükleme %%%d", int(status.progress() * 100))
    video_id = response["id"]
    log.info("YouTube: https://youtube.com/shorts/%s", video_id)
    return video_id


def fetch_views(video_ids: list[str]) -> dict[str, int]:
    """Yüklenen videoların izlenme sayıları (50'şerli gruplar, grup başına 1 kota birimi)."""
    from googleapiclient.discovery import build

    youtube = build("youtube", "v3", credentials=_credentials(), cache_discovery=False)
    out: dict[str, int] = {}
    for i in range(0, len(video_ids), 50):
        resp = youtube.videos().list(part="statistics", id=",".join(video_ids[i:i + 50])).execute()
        for item in resp.get("items", []):
            out[item["id"]] = int(item.get("statistics", {}).get("viewCount", 0))
    return out
