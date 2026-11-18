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
        if not (env("GITHUB_TOKEN") or env("GH_MODELS_TOKEN")):
            return False, "GITHUB_TOKEN yok (sadece GitHub Actions'ta otomatik gelir)"
        from pydantic import BaseModel

        from . import llm

        class Ping(BaseModel):
            answer: str

        res = llm.structured(cfg, "Reply in JSON.", "Say OK in the answer field.", Ping)
        if res is None:
            _diagnose_github_models(cfg)
            return False, "GitHub Models yanıt vermedi (ayrıntı logda): başlıklar şablondan, çeviri kapalı kalır"
        return True, f"GitHub Models çalışıyor ({cfg['ai'].get('github_model')})"
    return True, f"Sağlayıcı: {provider}"


def _telegram(cfg: dict) -> tuple[bool, str]:
    from . import notify

    if not env("TELEGRAM_BOT_TOKEN"):
        return False, "Eksik secret: TELEGRAM_BOT_TOKEN (lansman videoları telefonuna gelsin diye)"
    try:
        me = requests.get(f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/getMe", timeout=30)
        if me.status_code != 200:
            return False, "Bot token'ı geçersiz: @BotFather'dan aldığın token'ı kontrol et"
        bot = me.json()["result"].get("username")
        cid = notify.chat_id(save=False)
        if not cid:
            return False, f"@{bot} bulundu ama sohbet yok: Telegram'da @{bot} aç ve Başlat (/start) de"
        ok = notify.send_text(cfg, "✅ GTA 6 klip botu bağlandı. Lansman anları buraya video olarak gelecek.")
        return ok, f"@{bot} bağlı, test mesajı gönderildi" if ok else f"@{bot}: mesaj gönderilemedi"
    except Exception as e:  # noqa: BLE001
        return False, f"Hata: {str(e)[:200]}"


def _free_translate(cfg: dict) -> tuple[bool, str]:
    from . import translate_free

    out = translate_free.translate(["oh my god", "this is insane", "run, the cops are coming"])
    if not out:
        return False, "Ücretsiz çeviri modeli çalışmadı (ayrıntı logda): TikTok'ta İngilizce klipler altyazısız"
    return True, "Örnek: " + " / ".join(out)


def _launch(cfg: dict) -> tuple[bool, str]:
    from . import launch

    return True, launch.describe(cfg)


def _diagnose_github_models(cfg: dict) -> None:
    """Yapay zeka çalışmazsa nedenini loga yazar: model listesi ve birkaç istek biçimi."""
    import logging

    log = logging.getLogger("gta6clips.check")
    token = env("GITHUB_TOKEN") or env("GH_MODELS_TOKEN")
    auth = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get("https://models.github.ai/catalog/models", headers=auth, timeout=30)
        ids = [m.get("id") for m in r.json()] if r.headers.get("content-type", "").startswith("application/json") else []
        log.warning("Katalog: HTTP %s %s, %d model, örnek: %s | ham: %r", r.status_code,
                    r.headers.get("content-type"), len(ids), [i for i in ids if "mini" in (i or "")][:8],
                    r.text[:200] if not ids else "")
    except Exception as e:  # noqa: BLE001
        log.warning("Katalog alınamadı: %s", e)
    for model in (cfg["ai"].get("github_model"), "openai/gpt-4.1-mini", "openai/gpt-4o-mini"):
        for headers in ({**auth, "Content-Type": "application/json"},
                        {**auth, "Accept": "application/vnd.github+json"}):
            try:
                r = requests.post("https://models.github.ai/inference/chat/completions", headers=headers,
                                  timeout=60, json={"model": model,
                                                    "messages": [{"role": "user", "content": "Say hi"}]})
                log.warning("Deneme model=%s accept=%s -> HTTP %s %s %r", model, headers.get("Accept", "-"),
                            r.status_code, r.headers.get("content-type"), r.text[:160])
            except Exception as e:  # noqa: BLE001
                log.warning("Deneme model=%s hata: %s", model, e)


def run_checks(cfg: dict) -> list[tuple[str, bool, str]]:
    return [
        ("Twitch API", *_twitch_app(cfg)),
        ("Twitch girişi (canlı avcı)", *_twitch_user()),
        ("YouTube", *_youtube()),
        ("TikTok", *_tiktok(cfg)),
        ("Yapay zeka", *_ai(cfg)),
        ("Türkçe çeviri (ücretsiz)", *_free_translate(cfg)),
        ("Telegram", *_telegram(cfg)),
        ("Lansman modu", *_launch(cfg)),
    ]


def render(results: list[tuple[str, bool, str]]) -> str:
    lines = ["## Bağlantı kontrolü", "", "| | Bağlantı | Sonuç |", "|---|---|---|"]
    for name, ok, msg in results:
        lines.append(f"| {'✅' if ok else '❌'} | {name} | {msg.replace('|', '/')} |")
    return "\n".join(lines)
