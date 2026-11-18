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

    def take(self, now: float) -> bool:
        while self.times and self.times[0] < now - 3600:
            self.times.popleft()
        if len(self.times) >= self.per_hour:
            return False
        self.times.append(now)
        return True


def live_score(strength: float, viewers: int) -> float:
    """Patlamanın gücü x yayının büyüklüğü (logaritmik)."""
    return round(strength * math.log10(max(viewers, 10)) * 1000, 1)


def pick_channels(category_streams: list[dict], watched_streams: list[dict], lc: dict,
                  blocked: set[str]) -> dict[str, dict]:
    """Kategorideki en büyük yayınlar + (lansmanda) izleme listesindeki canlı yayıncılar."""
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
    pending: list[tuple] = []  # (oluşturma zamanı, klip id, yayıncı, puan, kaynak)
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
                category = tw.top_streams(gid, cfg["discovery"].get("language"))
                watched = []
                if is_launch and launch.watch_channels(cfg):
                    watched = [w for w in tw.streams_by_login(launch.watch_channels(cfg))
                               if w["viewer_count"] >= 500]
                streams = pick_channels(category, watched, lc, blocked)
                chat.set_channels(set(streams))
                for ch in streams:
                    det = detectors.setdefault(ch, ChatSpikeDetector(
                        ratio=lc["spike_ratio"], min_weight=lc["min_weight"], cooldown=lc["cooldown_seconds"]))
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
            if strength is None or not budget.take(time.time()):
                continue
            try:
                clip_id = user.create_clip(s["user_id"])
            except Exception:
                log.exception("Klip oluşturma hatası: %s", channel)
                continue
            if clip_id:
                score = live_score(strength, s["viewer_count"])
                log.info("🔥 %s sohbeti patladı (x%.1f, %d izleyici) -> klip %s", channel, strength,
                         s["viewer_count"], clip_id)
                pending.append((time.time(), clip_id, s["user_name"], score,
                                "launch" if launch.active(cfg) else "live"))

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
                                 "created_at": c.get("created_at"), "score": p[3], "source": p[4]})
                    pending.remove(p)
                elif time.time() - p[0] > 120:
                    log.info("Klip %s hazır olmadı, atlandı", p[1])
                    pending.remove(p)
