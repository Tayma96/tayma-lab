"""
YouTube Data API v3 Client for automated uploading of long-form videos with custom thumbnails & SEO metadata.
"""

import os
import json
from typing import Dict, Any


def upload_to_youtube(video_path: str, metadata: Dict[str, Any], thumbnail_path: str = None, client_secrets_file: str = "client_secret.json") -> Dict[str, Any]:
    """
    Uploads long-form video to YouTube channel using YouTube Data API v3.
    Also attaches custom high-CTR thumbnail if thumbnail_path is provided.
    If client_secrets_file is missing, saves upload request into local queue for deferred upload.
    """
    if not os.path.exists(client_secrets_file):
        queue_dir = "youtube_automation/upload_queue"
        os.makedirs(queue_dir, exist_ok=True)
        queue_file = os.path.join(queue_dir, f"queued_upload_{int(os.path.getmtime(video_path))}.json")

        queue_data = {
            "video_path": os.path.abspath(video_path),
            "thumbnail_path": os.path.abspath(thumbnail_path) if thumbnail_path else None,
            "title": metadata.get("title", "Untitled Video"),
            "description": metadata.get("description", ""),
            "tags": metadata.get("tags", []),
            "privacyStatus": "public",
            "status": "QUEUED_PENDING_YOUTUBE_OAUTH"
        }

        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False)

        return {
            "status": "QUEUED",
            "message": f"OAuth client secrets file '{client_secrets_file}' not found. Saved video metadata to queue file.",
            "queue_file": queue_file
        }

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google_auth_oauthlib.flow import InstalledAppFlow

        SCOPES = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.force-ssl"
        ]
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
        creds = flow.run_local_server(port=0)

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": metadata.get("title")[:100],
                "description": metadata.get("description"),
                "tags": metadata.get("tags", []),
                "categoryId": "27"  # Education / Science & Tech category
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()

        video_id = response.get("id")

        # Set custom thumbnail if provided
        if thumbnail_path and os.path.exists(thumbnail_path) and video_id:
            try:
                thumb_media = MediaFileUpload(thumbnail_path)
                youtube.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
            except Exception as thumb_err:
                print(f"[Thumbnail Upload Warning] Could not attach thumbnail: {thumb_err}")

        return {
            "status": "SUCCESS",
            "video_id": video_id,
            "youtube_url": f"https://www.youtube.com/watch?v={video_id}"
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e)
        }
