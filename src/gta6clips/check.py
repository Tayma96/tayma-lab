"""Bağlantı kontrolü: secret'ların ve girişlerin çalışıp çalışmadığını hiçbir şey yüklemeden test eder.

Salt okunur: Twitch kullanıcı token'ını yenilemez (yenilemek token'ı değiştirir ve bu iş durumu
kaydetmez), sadece geçerliliğine bakar. Sonuçları Türkçe bir tablo olarak döner.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from .config import env


def _twitch_app(cfg: dict) -> tuple[bool, str]:
    from .twitch import Twitch

    try:
        tw = Twitch(env("TWITCH_CLIENT_ID"), env("TWITCH_CLIENT_SECRET"))
        gid = tw.game_id(cfg["game_name"])
        streams = tw.top_streams(gid, None, limit=100)
        viewers = sum(s.get("viewer_count", 0) for s in streams)
        return True, (f"'{cfg['game_name']}' kategorisi bulundu (id {gid}); şu an {len(streams)} canlı "
                      f"yayın, toplam {viewers} izleyici")
    except Exception as e:  # noqa: BLE001 - kullanıcıya okunur hata
        return False, f"Hata: {str(e)[:200]}"


def _twitch_user() -> tuple[bool, str]:
    f = Path(env("TWITCH_USER_TOKEN_FILE", "secrets/twitch_user_token.json"))
    if not f.exists():
        return False, "Giriş yok: Actions > 'Twitch girişi' iş akışını çalıştır"
    try:
        tok = json.loads(f.read_text())
    except ValueError:
        return False, "Token dosyası bozuk: 'Twitch girişi' iş akışını tekrar çalıştır"
    if not tok.get("refresh_token"):
        return False, "Refresh token yok: 'Twitch girişi' iş akışını tekrar çalıştır"
    r = requests.get("https://id.twitch.tv/oauth2/validate", timeout=30,
                     headers={"Authorization": f"OAuth {tok.get('access_token', '')}"})
    if r.status_code == 200:
        d = r.json()
        scopes = d.get("scopes", [])
        if "clips:edit" not in scopes:
            return False, f"@{d.get('login')} bağlı ama klip izni (clips:edit) yok: girişi tekrar yap"
        return True, f"@{d.get('login')} hesabı bağlı, klip oluşturma izni var"
    age_h = (time.time() - tok.get("obtained_at", time.time())) / 3600
    return True, (f"Erişim token'ının süresi dolmuş ({age_h:.0f} saat önce alındı); bu normal, ana iş "
                  "ilk kullanımda otomatik yeniler")


def _youtube() -> tuple[bool, str]:
    if not env("YOUTUBE_REFRESH_TOKEN"):
        missing = [n for n in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
                   if not env(n)]
        return False, f"Eksik secret: {', '.join(missing)}"
    try:
        from googleapiclient.discovery import build

        from .uploaders.youtube import _credentials

        yt = build("youtube", "v3", credentials=_credentials(), cache_discovery=False)
        items = yt.channels().list(part="snippet,statistics", mine=True).execute().get("items", [])
        if not items:
            return False, "Giriş çalışıyor ama bu Google hesabında YouTube kanalı yok"
        ch = items[0]
        subs = ch.get("statistics", {}).get("subscriberCount", "?")
        return True, f"Kanal: '{ch['snippet']['title']}' ({subs} abone), yükleme izni var"
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "invalid_grant" in msg:
            return False, ("Refresh token geçersiz ya da süresi dolmuş (invalid_grant): OAuth Playground'dan "
                           "yenisini al, YOUTUBE_REFRESH_TOKEN'ı güncelle")
        if "invalid_client" in msg or "unauthorized_client" in msg:
            return False, ("Client ID / secret uyuşmuyor: refresh token'ı aldığın client'ın ID ve secret'ı "
                           "GitHub'dakilerle aynı olmalı")
        if "insufficient" in msg.lower() or "403" in msg:
            return False, ("İzin eksik: Playground'da iki scope'u da (youtube.upload, youtube.readonly) "
                           "yazıp izin ekranında iki kutuyu da işaretle")
        return False, f"Hata: {msg[:200]}"


def _tiktok(cfg: dict) -> tuple[bool, str]:
    if cfg["upload"]["tiktok"].get("method") != "browser":
        return False, "method: api (bu kontrol sadece browser yöntemini test eder)"
    sid = env("TIKTOK_SESSIONID")
    if not sid:
        return False, "Eksik secret: TIKTOK_SESSIONID"
    return True, f"TIKTOK_SESSIONID var ({len(sid)} karakter); geçerliliği ilk yüklemede anlaşılır"


def _ai(cfg: dict) -> tuple[bool, str]:
    provider = cfg.get("ai", {}).get("provider")
    if provider == "github":
        ok = bool(env("GITHUB_TOKEN") or env("GH_MODELS_TOKEN"))
        return ok, "GitHub Models hazır" if ok else "GITHUB_TOKEN yok (sadece GitHub Actions'ta otomatik gelir)"
    return True, f"Sağlayıcı: {provider}"


def run_checks(cfg: dict) -> list[tuple[str, bool, str]]:
    return [
        ("Twitch API", *_twitch_app(cfg)),
        ("Twitch girişi (canlı avcı)", *_twitch_user()),
        ("YouTube", *_youtube()),
        ("TikTok", *_tiktok(cfg)),
        ("Yapay zeka", *_ai(cfg)),
    ]


def render(results: list[tuple[str, bool, str]]) -> str:
    lines = ["## Bağlantı kontrolü", "", "| | Bağlantı | Sonuç |", "|---|---|---|"]
    for name, ok, msg in results:
        lines.append(f"| {'✅' if ok else '❌'} | {name} | {msg.replace('|', '/')} |")
    return "\n".join(lines)
