"""Twitch Helix API: GTA 6 kategorisindeki en çok izlenen klipleri ve canlı yayınları bulur."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import requests

HELIX = "https://api.twitch.tv/helix"


class Twitch:
    def __init__(self, client_id: str, client_secret: str):
        if not client_id or not client_secret:
            raise RuntimeError("TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET eksik (.env)")
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._token_exp = 0.0

    def _auth(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        r = requests.post("https://id.twitch.tv/oauth2/token", params={
            "client_id": self.client_id, "client_secret": self.client_secret,
            "grant_type": "client_credentials"}, timeout=30)
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._token_exp = time.time() + data.get("expires_in", 3600)
        return self._token

    def _get(self, path: str, params: dict) -> dict:
        for attempt in range(4):
            r = requests.get(f"{HELIX}{path}", params=params, timeout=30, headers={
                "Client-Id": self.client_id, "Authorization": f"Bearer {self._auth()}"})
            if r.status_code == 429:
                reset = float(r.headers.get("Ratelimit-Reset", time.time() + 2))
                time.sleep(max(1.0, reset - time.time()))
                continue
            if r.status_code == 401 and attempt == 0:
                self._token = None
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"Twitch API {path} tekrar denemelerden sonra başarısız")

    def game_id(self, name: str) -> str:
        data = self._get("/games", {"name": name}).get("data", [])
        if not data:
            raise RuntimeError(f"Twitch'te '{name}' kategorisi bulunamadı")
        return data[0]["id"]

    def top_streams(self, game_id: str, language: str | None, limit: int = 100) -> list[dict]:
        params = {"game_id": game_id, "first": min(limit, 100)}
        if language:
            params["language"] = language
        return self._get("/streams", params).get("data", [])

    def top_clips(self, game_id: str, lookback_hours: int, pages: int = 3) -> list[dict]:
        started = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        params = {"game_id": game_id, "first": 100, "started_at": started}
        out: list[dict] = []
        for _ in range(pages):
            resp = self._get("/clips", params)
            out.extend(resp.get("data", []))
            cursor = resp.get("pagination", {}).get("cursor")
            if not cursor:
                break
            params["after"] = cursor
        return out


def rank_clips(clips: list[dict], top_streamers: list[str], cfg: dict) -> list[dict]:
    """Klipleri filtreler ve puanlar. Saf fonksiyon (test edilebilir)."""
    d = cfg["discovery"]
    blocked = set(cfg.get("blocklist") or [])
    boost_rank = {name.lower(): i for i, name in enumerate(top_streamers[: d["top_streamers_boost"]])}
    seen_vods: set[tuple] = set()
    ranked = []
    for c in clips:
        login = (c.get("broadcaster_name") or "").lower()
        if login in blocked or c.get("broadcaster_id") and str(c["broadcaster_id"]) in blocked:
            continue
        if d.get("language") and c.get("language") and not c["language"].startswith(d["language"]):
            continue
        if c.get("view_count", 0) < d["min_views"] or c.get("duration", 0) < d["min_duration"]:
            continue
        # Aynı anın birden fazla klibi olabilir: aynı VOD'da ±30 sn içindekileri tekrar sayma
        if c.get("video_id") and c.get("vod_offset") is not None:
            key = (c["video_id"], int(c["vod_offset"]) // 30)
            if key in seen_vods:
                continue
            seen_vods.add(key)
        score = float(c["view_count"])
        if login in boost_rank:
            score *= 1.5 + (len(boost_rank) - boost_rank[login]) / max(len(boost_rank), 1)
        ranked.append({
            "id": c["id"],
            "broadcaster": c.get("broadcaster_name") or login,
            "title": c.get("title", ""),
            "url": c["url"],
            "views": c["view_count"],
            "duration": c.get("duration", 0),
            "created_at": c.get("created_at"),
            "score": round(score, 1),
        })
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked
