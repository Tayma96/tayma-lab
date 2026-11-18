"""Canlı yayın avcısı: en çok izlenen GTA 6 yayınlarının sohbetini dinler, patlama anında Twitch klibi
oluşturur ve kurgu kuyruğuna ekler. Herkes klip açmayı beklerken biz o anı saniyeler içinde yakalarız."""
from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque

from . import launch
from .chat import ChatSpikeDetector, TwitchChat
from .config import env
from .db import DB
from .twitch import Twitch, TwitchUser

log = logging.getLogger(__name__)


class ClipBudget:
    """Saatlik klip oluşturma sınırı (Twitch'i ve kurgu kuyruğunu boğmamak için)."""

    def __init__(self, per_hour: int):
        self.per_hour = per_hour
        self.times: deque[float] = deque()

    def available(self, now: float) -> bool:
        while self.times and self.times[0] < now - 3600:
            self.times.popleft()
        return len(self.times) < self.per_hour

    def take(self, now: float) -> bool:
        if not self.available(now):
            return False
        self.times.append(now)
        return True


def live_score(strength: float, viewers: int) -> float:
    """Patlamanın gücü x yayının büyüklüğü (logaritmik)."""
    return round(strength * math.log10(max(viewers, 10)) * 1000, 1)


def clip_timing(lc: dict) -> tuple[float, float]:
    """(patlamadan sonra kaç sn beklenip klip isteneceği, anın klip içindeki saniyesi).
    Twitch klibi isteğin yapıldığı andan önceki `twitch_clip_seconds` saniyeyi alır; an, patlamanın
    `chat_lag_seconds` gerisindedir. Klip andan `pre_roll_seconds` önce başlasın diye istek geciktirilir."""
    length = float(lc.get("twitch_clip_seconds", 30))
    pre = float(lc.get("pre_roll_seconds", 10))
    lag = float(lc.get("chat_lag_seconds", 7))
    delay = max(0.0, length - pre - lag)
    moment_at = max(0.0, length - delay - lag)
    return delay, moment_at


def pick_channels(category_streams: list[dict], watched_streams: list[dict], lc: dict,
                  blocked: set[str], local_streams: list[dict] | None = None) -> dict[str, dict]:
    """(Lansmanda) izleme listesindeki canlı yayıncılar + kategorideki en büyük global yayınlar +
    en büyük yerel (Türkçe) yayınlar."""
    out: dict[str, dict] = {}
    for s in watched_streams:                          # tanınmış yayıncılar önce, kategori fark etmez
        login = s["user_login"].lower()
        if login not in blocked:
            out[login] = s
    top = [s for s in category_streams
           if s["viewer_count"] >= lc["min_viewers"] and s["user_login"].lower() not in blocked]
    limit = lc["top_channels"] + len(out)
    for s in top:
        if len(out) >= limit:
            break
        out.setdefault(s["user_login"].lower(), s)
    local = [s for s in local_streams or []
             if s["viewer_count"] >= lc.get("local_min_viewers", 300) and s["user_login"].lower() not in blocked]
    limit = len(out) + lc.get("local_channels", 0)
    for s in local:
        if len(out) >= limit:
            break
        out.setdefault(s["user_login"].lower(), s)
    return out


def run_live(cfg: dict, db: DB, stop: threading.Event | None = None) -> None:
    lc = cfg["live"]
    stop = stop or threading.Event()
    tw = Twitch(env("TWITCH_CLIENT_ID"), env("TWITCH_CLIENT_SECRET"))
    user = TwitchUser.from_env()
    if not user.available():
        log.warning("Canlı avcı kapalı: Twitch kullanıcı yetkisi yok (`gta6clips auth twitch`)")
        return
    gid = tw.game_id(cfg["game_name"])
    chat = TwitchChat()
    detectors: dict[str, ChatSpikeDetector] = {}
    streams: dict[str, dict] = {}
    pending: list[tuple] = []  # (oluşturma zamanı, klip id, yayıncı, puan, kaynak, anın saniyesi)
    no_clip: set[str] = set()  # klip almaya izin vermeyen kanallar
    scheduled: list[tuple] = []  # (istek zamanı, kanal, yayın, güç, kaynak): an + tepki klibe sığsın diye bekler
    budget = ClipBudget(lc["max_clips_per_hour"])
    blocked = set(cfg.get("blocklist") or [])
    next_refresh = 0.0

    while not stop.is_set():
        now = time.time()
        if now >= next_refresh:
            lc = launch.live_settings(cfg)
            is_launch = launch.active(cfg)
            budget.per_hour = lc["max_clips_per_hour"]
            try:
                langs = cfg["discovery"].get("languages") or [cfg["discovery"].get("language") or "en"]
                category = tw.top_streams(gid, [x for x in langs if x != "tr"] or None)
                local = tw.top_streams(gid, "tr") if "tr" in langs else []
                watched = []
                if is_launch and launch.watch_channels(cfg):
                    watched = [w for w in tw.streams_by_login(launch.watch_channels(cfg))
                               if w["viewer_count"] >= 500]
                streams = pick_channels(category, watched, lc, blocked, local)
                chat.set_channels(set(streams))
                for ch in streams:
                    # Isınma = ortalama penceresi (180 sn): ortalama oturmadan sahte patlama sayılmasın
                    det = detectors.setdefault(ch, ChatSpikeDetector(
                        ratio=lc["spike_ratio"], min_weight=lc["min_weight"], cooldown=lc["cooldown_seconds"],
                        warmup=190))
                    det.ratio, det.min_weight, det.cooldown = lc["spike_ratio"], lc["min_weight"], lc["cooldown_seconds"]
                log.info("%sCanlı izleniyor (%d): %s", "🚀 LANSMAN | " if is_launch else "", len(streams),
                         ", ".join(list(streams)[:12]))
            except Exception:
                log.exception("Canlı yayın listesi alınamadı")
            next_refresh = now + lc["refresh_minutes"] * 60

        for channel, text in chat.poll():
            det = detectors.get(channel)
            s = streams.get(channel)
            if not det or not s:
                continue
            strength = det.add(time.time(), text)
            if strength is None or channel in no_clip or not budget.available(time.time()):
                continue
            if any(x[1] == channel for x in scheduled):
                continue
            delay, _ = clip_timing(lc)
            log.info("🔥 %s sohbeti patladı (x%.1f, %d izleyici) -> %.0f sn sonra klip alınacak", channel,
                     strength, s["viewer_count"], delay)
            scheduled.append((time.time() + delay, channel, s, strength, "launch" if launch.active(cfg) else "live"))

        for item in [x for x in scheduled if time.time() >= x[0]]:
            scheduled.remove(item)
            _, channel, s, strength, source = item
            try:
                clip_id = user.create_clip(s["user_id"])
            except Exception:
                log.exception("Klip oluşturma hatası: %s", channel)
                continue
            if not clip_id:
                # Yayıncı klibi kısıtlamış (takipçi/abone): bu turda bir daha deneme, hakkı boşa harcama
                no_clip.add(channel)
                log.info("%s kanalında klip alınamıyor (kısıtlı), bu tur atlanacak", channel)
                continue
            if budget.take(time.time()):
                score = live_score(strength, s["viewer_count"])
                log.info("🎬 %s klibi alındı: %s", channel, clip_id)
                pending.append((time.time(), clip_id, s["user_name"], score, source, clip_timing(lc)[1],
                                (s.get("language") or "en")[:2]))

        # Twitch klibi işlemesi ~15 sn sürer; hazır olanları kuyruğa al
        ready_after = [p for p in pending if time.time() - p[0] >= 20]
        if ready_after:
            try:
                found = {c["id"]: c for c in user.get_clips([p[1] for p in ready_after])}
            except Exception:
                log.exception("Klip bilgisi alınamadı")
                found = {}
            for p in ready_after:
                c = found.get(p[1])
                if c:
                    db.add_clip({"id": c["id"], "broadcaster": p[2], "title": c.get("title", ""), "url": c["url"],
                                 "views": c.get("view_count", 0), "duration": c.get("duration", 30),
                                 "created_at": c.get("created_at"), "score": p[3], "source": p[4],
                                 "moment_at": p[5], "language": p[6]})
                    pending.remove(p)
                elif time.time() - p[0] > 300:  # yoğunlukta Twitch klibi geç işleyebiliyor
                    log.info("Klip %s hazır olmadı, atlandı", p[1])
                    pending.remove(p)
