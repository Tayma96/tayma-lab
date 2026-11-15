"""Twitch Helix API: GTA 6 kategorisindeki en çok izlenen klipleri ve canlı yayınları bulur."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

log = logging.getLogger(__name__)
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


class TwitchUser:
    """Kullanıcı yetkili Twitch istemcisi: canlı yayından klip oluşturmak için (clips:edit).
    Klip, çağrıldığı andan önceki ~30 saniyeyi kapsar ve senin hesabın adına oluşturulur."""

    SCOPES = "clips:edit"

    def __init__(self, client_id: str, client_secret: str, token_file: str | Path):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_file = Path(token_file)

    @classmethod
    def from_env(cls) -> "TwitchUser":
        from .config import env
        return cls(env("TWITCH_CLIENT_ID"), env("TWITCH_CLIENT_SECRET"),
                   env("TWITCH_USER_TOKEN_FILE", "secrets/twitch_user_token.json"))

    def available(self) -> bool:
        return self.token_file.exists()

    def authorize(self) -> None:
        from .config import env
        from .oauth_local import capture_code

        redirect = env("TWITCH_REDIRECT_URI", "http://localhost:8767/callback")
        code = capture_code("https://id.twitch.tv/oauth2/authorize", {
            "client_id": self.client_id, "response_type": "code", "scope": self.SCOPES}, redirect)
        self._save(self._token({"code": code, "grant_type": "authorization_code", "redirect_uri": redirect}))
        print("Twitch kullanıcı yetkisi kaydedildi (canlı klip oluşturma açık).")

    def authorize_device(self, timeout: float = 900) -> None:
        """Bilgisayarsız giriş (Device Code Flow): telefondan twitch.tv/activate adresinde kodu gir.
        GitHub Actions'taki 'Twitch girişi' iş akışı bunu çalıştırır."""
        r = requests.post("https://id.twitch.tv/oauth2/device", timeout=30,
                          data={"client_id": self.client_id, "scopes": self.SCOPES})
        r.raise_for_status()
        d = r.json()
        print("=" * 60)
        print(f"Telefonundan şu adresi aç: {d['verification_uri']}")
        print(f"Kod: {d['user_code']}   ({d['expires_in'] // 60} dakika geçerli)")
        print("=" * 60, flush=True)
        end = time.time() + min(timeout, d["expires_in"])
        while time.time() < end:
            time.sleep(d.get("interval", 5))
            t = requests.post("https://id.twitch.tv/oauth2/token", timeout=30, data={
                "client_id": self.client_id, "client_secret": self.client_secret, "scopes": self.SCOPES,
                "device_code": d["device_code"], "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
            if t.status_code == 200:
                self._save(t.json())
                print("Twitch girişi tamam, canlı avcı klip oluşturabilir.")
                return
            if "authorization_pending" not in t.text and "slow_down" not in t.text:
                raise RuntimeError(f"Twitch girişi başarısız: {t.text[:300]}")
        raise RuntimeError("Süre doldu, kod girilmedi. İş akışını tekrar çalıştır.")

    def _token(self, data: dict) -> dict:
        r = requests.post("https://id.twitch.tv/oauth2/token", timeout=30, data={
            "client_id": self.client_id, "client_secret": self.client_secret, **data})
        r.raise_for_status()
        return r.json()

    def _save(self, tok: dict) -> None:
        tok["obtained_at"] = time.time()
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps(tok, indent=2))

    def _access(self, force_refresh: bool = False) -> str:
        if not self.token_file.exists():
            raise RuntimeError("Twitch kullanıcı yetkisi yok: `gta6clips auth twitch`")
        tok = json.loads(self.token_file.read_text())
        if force_refresh or time.time() > tok["obtained_at"] + tok.get("expires_in", 0) - 300:
            tok = self._token({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})
            self._save(tok)
        return tok["access_token"]

    def _req(self, method: str, path: str, params: dict) -> requests.Response:
        for attempt in range(2):
            r = requests.request(method, f"{HELIX}{path}", params=params, timeout=30, headers={
                "Client-Id": self.client_id, "Authorization": f"Bearer {self._access(force_refresh=attempt > 0)}"})
            if r.status_code != 401:
                return r
        return r

    def create_clip(self, broadcaster_id: str) -> str | None:
        """Canlı yayında klip oluşturur, klip id'si döner. Yayıncı klibi kapattıysa None."""
        r = self._req("POST", "/clips", {"broadcaster_id": broadcaster_id, "has_delay": "true"})
        if r.status_code in (403, 404):
            log.info("Klip oluşturulamadı (%s): %s", broadcaster_id, r.text[:200])
            return None
        r.raise_for_status()
        data = r.json().get("data", [])
        return data[0]["id"] if data else None

    def get_clips(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []
        r = self._req("GET", "/clips", {"id": ids})
        r.raise_for_status()
        return r.json().get("data", [])


def clip_velocity(view_count: int, created_at: str | None, now: datetime | None = None) -> float:
    """Saat başına izlenme (en az 1 saatlik yaşla). Yeni ama hızla izlenen klip, eski popülerden değerli."""
    now = now or datetime.now(timezone.utc)
    if not created_at:
        return float(view_count)
    born = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    hours = max(1.0, (now - born).total_seconds() / 3600)
    return view_count / hours ** 0.8


def rank_clips(clips: list[dict], top_streamers: list[str], cfg: dict,
               performance: dict[str, float] | None = None, now: datetime | None = None) -> list[dict]:
    """Klipleri filtreler ve puanlar. Saf fonksiyon (test edilebilir).
    Puan = izlenme hızı x canlı izleyici sıralaması bonusu x geçmiş performans çarpanı."""
    d = cfg["discovery"]
    blocked = set(cfg.get("blocklist") or [])
    performance = performance or {}
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
        score = clip_velocity(c["view_count"], c.get("created_at"), now)
        if login in boost_rank:
            score *= 1.5 + (len(boost_rank) - boost_rank[login]) / max(len(boost_rank), 1)
        score *= performance.get(login, 1.0)
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
