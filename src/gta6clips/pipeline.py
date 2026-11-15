"""Uçtan uca akış:
  kaynaklar (Twitch popüler klipler + canlı sohbet patlamaları + VOD)
  -> indir -> döküm -> Claude analizi (kalite kapısı + kırpma + metin)
  -> kurgu -> öncelik sırasıyla yükle -> izlenmeleri çek -> yayıncı ağırlıklarını güncelle
"""
from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

from . import analyze, captions, download, editor, highlights, transcribe
from .config import env
from .db import DB
from .facecam import FacecamCache
from .twitch import Twitch, rank_clips

log = logging.getLogger(__name__)
_FACECAMS: FacecamCache | None = None


def data_dir(cfg: dict) -> Path:
    return Path(cfg["paths"]["data_dir"])


def open_db(cfg: dict) -> DB:
    return DB(data_dir(cfg) / "clips.db")


def resolve_facecam(cfg: dict, broadcaster: str, src: Path) -> dict | None:
    """Önce config.yaml'daki elle girilmiş konum, yoksa otomatik tespit (render.auto_facecam)."""
    global _FACECAMS
    manual = cfg["facecams"].get(broadcaster.lower())
    if manual or not cfg["render"].get("auto_facecam"):
        return manual
    if _FACECAMS is None:
        _FACECAMS = FacecamCache(data_dir(cfg) / "facecams.json")
    return _FACECAMS.get(broadcaster, src)


# ---------------------------------------------------------------- keşif
def discover(cfg: dict, db: DB) -> int:
    tw = Twitch(env("TWITCH_CLIENT_ID"), env("TWITCH_CLIENT_SECRET"))
    d = cfg["discovery"]
    gid = tw.game_id(cfg["game_name"])
    streams = tw.top_streams(gid, d.get("language"))
    top_streamers = [s["user_login"] for s in streams]
    if top_streamers:
        log.info("Şu an en çok izlenen GTA 6 yayıncıları: %s", ", ".join(top_streamers[:10]))
    ranked = rank_clips(tw.top_clips(gid, d["lookback_hours"]), top_streamers, cfg, db.streamer_performance())
    added = sum(db.add_clip(c) for c in ranked[: d["max_clips_per_run"] * 3])
    log.info("Keşif: %d uygun klip, %d yeni eklendi", len(ranked), added)
    return added


# ---------------------------------------------------------------- üretim
def shift_words(words: list[transcribe.Word], start: float, end: float) -> list[transcribe.Word]:
    return [transcribe.Word(w.start - start, w.end - start, w.text) for w in words if start <= w.start < end]


def produce(cfg: dict, *, clip_id: str, broadcaster: str, title: str, views: int, src: Path,
            hook_hint: str = "", signals: dict | None = None) -> tuple[Path | None, dict]:
    """Analiz eder; kalite kapısından geçerse kırpıp dikey video üretir.
    Dönüş: (video yolu veya reddedildiyse None, analiz sözlüğü)"""
    dd = data_dir(cfg)
    r, q = cfg["render"], cfg["quality"]
    total = editor.probe_duration(src)
    words: list[transcribe.Word] = []
    if r["captions"]:
        words = transcribe.transcribe(src, r["whisper_model"], cfg["discovery"].get("language"))
    a = analyze.analyze(src, total, words, broadcaster, title or hook_hint, views, cfg, clip_id=clip_id,
                        signals=signals or {"views": views})
    if not a["is_gta6"] or a["score"] < q["min_score"]:
        log.info("Elendi [%s] puan=%s gta6=%s: %s", broadcaster, a["score"], a["is_gta6"], a["reason"])
        return None, a

    start, end = a["best_start"], a["best_end"]
    trimmed = start > 0.3 or end < total - 0.3
    words = shift_words(words, start, end) if trimmed else words
    length = end - start
    meta = a["meta"]
    facecam = resolve_facecam(cfg, broadcaster, src)
    ass = dd / "tmp" / f"{clip_id}.ass"
    ass.write_text(captions.build_ass(
        words, length,
        hook=meta["hook"] if r["hook"] else None,
        credit=f"twitch.tv/{broadcaster.lower()}" if r["credit"] else None,
        caption_y=editor.caption_y(facecam),
        brand=r.get("brand") or None), encoding="utf-8")
    out = dd / "out" / f"{clip_id}.mp4"
    editor.render(src, out, ass_path=ass, zoom=r["zoom"], facecam=facecam,
                  start=start if trimmed else None, duration=length if trimmed else None,
                  progress=r.get("progress_bar", True))
    log.info("Kurgulandı [%s] (%s) puan=%s %s (%.0fs%s): %s", broadcaster, a.get("engine"), a["score"], a["category"], length,
             f", kırpıldı {start:.0f}-{end:.0f}" if trimmed else "", meta["title"])
    return out, a


def render_pending(cfg: dict, db: DB, limit: int | None = None) -> int:
    limit = limit or cfg["discovery"]["max_clips_per_run"]
    done = 0
    for row in db.clips_with_status("new", limit):
        try:
            src = download.download_clip(row["url"], data_dir(cfg) / "raw", row["id"])
            out, a = produce(cfg, clip_id=row["id"], broadcaster=row["broadcaster"], title=row["title"] or "",
                             views=row["views"], src=src,
                             signals={"views": row["views"], "score": row["score"], "source": row["source"]})
            analysis = {k: v for k, v in a.items() if k != "meta"}
            if out is None:
                db.mark_rejected(row["id"], a["score"], a["reason"], analysis)
            else:
                db.mark_rendered(row["id"], str(out), a["meta"], a["score"], analysis)
                done += 1
        except Exception as e:  # tek klip hatası tüm akışı durdurmasın
            log.exception("Klip işlenemedi: %s", row["id"])
            db.mark_failed(row["id"], str(e))
    return done


def vod_candidates(cfg: dict, audio: Path, key: str, top_k: int, length: int) -> list[dict]:
    """Ses zirvelerinden top_k'nın 3 katı aday çıkarır, her adayın sesini yazıya döker ve
    Claude'a viral potansiyele göre sıralatır. İlk top_k aday döner."""
    dd = data_dir(cfg)
    windows = highlights.pick_windows(highlights.loudness_per_second(audio), length=length, top_k=top_k * 3)
    cands = []
    for i, (start, end, score) in enumerate(windows):
        text = ""
        if cfg["render"]["captions"]:
            piece = highlights.cut_audio(audio, start, end, dd / "tmp" / f"{key}_{start}.wav")
            text = transcribe.plain_text(transcribe.transcribe(piece, cfg["render"]["whisper_model"],
                                                               cfg["discovery"].get("language")))
        cands.append({"index": i, "start": start, "end": end, "loud_score": score, "transcript": text})
    ranked = highlights.rank_with_ai(cands, cfg)
    for c in ranked[:top_k]:
        log.info("Aday %ss-%ss viral=%s %s", c["start"], c["end"], c.get("viral_score", "-"), c.get("reason", ""))
    return ranked[:top_k]


def process_vod(cfg: dict, db: DB, url: str, broadcaster: str, top_k: int = 5, length: int = 40) -> int:
    """Uzun bir yayından (VOD) ses zirveleri + Claude viral puanına göre kesitler çıkarır."""
    dd = data_dir(cfg)
    key = "vod_" + "".join(ch for ch in url if ch.isalnum())[-24:]
    audio = download.download_audio(url, dd / "raw", key)
    picks = vod_candidates(cfg, audio, key, top_k, length)
    done = 0
    for c in picks:
        start, end = c["start"], c["end"]
        clip_id = f"{key}_{start}"
        if not db.add_clip({"id": clip_id, "broadcaster": broadcaster, "title": c.get("hook", ""), "url": url,
                            "score": c.get("viral_score", c["loud_score"]), "duration": end - start,
                            "source": "vod"}):
            continue
        try:
            src = download.download_section(url, dd / "raw", clip_id, start, end)
            out, a = produce(cfg, clip_id=clip_id, broadcaster=broadcaster, title="", views=0, src=src,
                             hook_hint=c.get("hook", ""))
            analysis = {k: v for k, v in a.items() if k != "meta"}
            if out is None:
                db.mark_rejected(clip_id, a["score"], a["reason"], analysis)
            else:
                db.mark_rendered(clip_id, str(out), a["meta"], a["score"], analysis)
                done += 1
        except Exception as e:
            log.exception("VOD kesiti işlenemedi: %s", clip_id)
            db.mark_failed(clip_id, str(e))
    return done


# ---------------------------------------------------------------- yayın
_NOT_READY_LOGGED: set[str] = set()


def platform_ready(cfg: dict, platform: str) -> bool:
    """Giriş bilgisi eklenmemiş platformu atla (kurulum bitene kadar hata yağmuru olmasın)."""
    if platform == "youtube":
        ok = Path(env("YOUTUBE_TOKEN_FILE", "secrets/youtube_token.json")).exists()
        hint = "YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN secret'larını ekle"
    elif cfg["upload"]["tiktok"].get("method") == "browser":
        ok = bool(env("TIKTOK_SESSIONID")) or Path(env("TIKTOK_COOKIES_FILE", "secrets/tiktok_cookies.txt")).exists()
        hint = "TIKTOK_SESSIONID secret'ını ekle"
    else:
        ok = Path(env("TIKTOK_TOKEN_FILE", "secrets/tiktok_token.json")).exists()
        hint = "gta6clips auth tiktok"
    if not ok and platform not in _NOT_READY_LOGGED:
        log.warning("%s yüklemesi atlanıyor: giriş bilgisi yok (%s)", platform, hint)
        _NOT_READY_LOGGED.add(platform)
    return ok


def upload_pending(cfg: dict, db: DB) -> int:
    from .uploaders import tiktok, tiktok_browser, youtube

    up = cfg["upload"]
    tiktok_fn = tiktok_browser.upload if up["tiktok"].get("method") == "browser" else tiktok.upload
    uploaders = {"youtube": youtube.upload, "tiktok": tiktok_fn}
    count = 0
    for platform, fn in uploaders.items():
        pcfg = up[platform]
        if not pcfg.get("enabled") or not platform_ready(cfg, platform):
            continue
        for row in db.pending_uploads(platform, max_age_hours=up.get("max_age_hours")):
            if not db.can_upload(platform, pcfg["max_per_day"], up["min_gap_minutes"], up.get("peak_hours_utc")):
                break
            try:
                remote = fn(Path(row["video_path"]), json.loads(row["meta_json"]), cfg)
                db.record_upload(row["id"], platform, "done", remote)
                log.info("Yüklendi %s [kalite %s] %s", platform, row.get("quality"), row["id"])
                count += 1
            except Exception as e:
                log.exception("%s yükleme hatası: %s", platform, row["id"])
                db.record_upload(row["id"], platform, "failed", detail=str(e)[:1000])
                break  # yetki/kota sorunlarında aynı turda tekrar tekrar deneme
    tiktok_browser.close()
    return count


def refresh_stats(cfg: dict, db: DB) -> int:
    """YouTube izlenmelerini çeker; yayıncı çarpanları bir sonraki keşifte kullanılır."""
    from .uploaders import youtube

    ids = db.youtube_ids_to_check()
    if not ids:
        return 0
    views = youtube.fetch_views(ids)
    for vid, n in views.items():
        db.set_views("youtube", vid, n)
    log.info("İstatistik: %d videonun izlenmesi güncellendi; yayıncı çarpanları: %s",
             len(views), db.streamer_performance())
    return len(views)


# ---------------------------------------------------------------- sürekli çalışma
def _loop(name: str, every_s: float, fn, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            fn()
        except Exception:
            log.exception("%s turu başarısız, sonraki turda tekrar denenecek", name)
        stop.wait(every_s)


def recover_missing_videos(db: DB) -> int:
    """Bulut sunucusu (GitHub Actions) her çalıştırmada temiz başlar: kurgulanmış ama henüz yüklenmemiş
    videoların dosyası kaybolduysa klibi yeniden kurgu kuyruğuna al."""
    n = 0
    for row in db.clips_with_status("rendered", 10000):
        if not row["video_path"] or not Path(row["video_path"]).exists():
            db.conn.execute("UPDATE clips SET status='new' WHERE id=?", (row["id"],))
            n += 1
    db.conn.commit()
    if n:
        log.info("%d klibin videosu yoktu, yeniden kurgulanacak", n)
    return n


def run_forever(cfg: dict, upload: bool = True, live: bool = True, max_minutes: float | None = None) -> None:
    """Her iş kendi iş parçacığında, kendi veritabanı bağlantısıyla:
    canlı avcı (sürekli) | keşif (15 dk) | kurgu (1 dk) | yükleme (5 dk) | istatistik (3 saat)"""
    from .live import run_live

    stop = threading.Event()
    s = cfg["schedule"]
    recover_missing_videos(open_db(cfg))
    deadline = time.time() + max_minutes * 60 if max_minutes else None
    jobs = [
        ("keşif", s["discover_minutes"] * 60, lambda db: discover(cfg, db)),
        ("kurgu", 60, lambda db: render_pending(cfg, db, 5)),
    ]
    if upload:
        jobs.append(("yükleme", 300, lambda db: upload_pending(cfg, db)))
        if cfg["upload"]["youtube"].get("enabled"):
            jobs.append(("istatistik", s["stats_hours"] * 3600, lambda db: refresh_stats(cfg, db)))
    threads = []
    for name, every, fn in jobs:
        def target(name=name, every=every, fn=fn):
            db = open_db(cfg)
            _loop(name, every, lambda: fn(db), stop)
        threads.append(threading.Thread(target=target, name=name, daemon=True))
    if live and cfg["live"].get("enabled"):
        threads.append(threading.Thread(target=lambda: run_live(cfg, open_db(cfg), stop), name="canlı", daemon=True))
    for t in threads:
        t.start()
    log.info("Çalışıyor: %s (durdurmak için Ctrl+C)", ", ".join(t.name for t in threads))
    try:
        while any(t.is_alive() for t in threads):
            if deadline and time.time() >= deadline:
                log.info("Süre doldu (%s dk), durum kaydedilmek üzere duruluyor", max_minutes)
                stop.set()
                for t in threads:
                    t.join(timeout=120)  # yarım kalan kurgu/yükleme bitsin
                return
            time.sleep(5)
    except KeyboardInterrupt:
        log.info("Durduruluyor...")
        stop.set()
