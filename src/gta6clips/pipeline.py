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

from . import analyze, captions, download, editor, highlights, launch, notify, transcribe
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
    if launch.in_campaign(cfg):
        log.info("Keşif lansman süresince duraklatıldı (kurgu ve yapay zeka hakkı lansman kliplerine)")
        return 0
    tw = Twitch(env("TWITCH_CLIENT_ID"), env("TWITCH_CLIENT_SECRET"))
    d = cfg["discovery"]
    gid = tw.game_id(cfg["game_name"])
    langs = d.get("languages") or [d.get("language") or "en"]
    streams = tw.top_streams(gid, langs)
    top_streamers = [s["user_login"] for s in streams]
    if top_streamers:
        log.info("Şu an en çok izlenen GTA 6 yayıncıları: %s", ", ".join(top_streamers[:10]))
    ranked = rank_clips(tw.top_clips(gid, d["lookback_hours"]), top_streamers, cfg, db.streamer_performance())
    # Her dile kendi kotası: Türkçe klipler İngilizcelerin izlenmeleri altında ezilmesin
    per_lang = max(1, d["max_clips_per_run"] * 3 // len(langs))
    chosen = [c for lang in langs for c in [r for r in ranked if r.get("language", "en") == lang][:per_lang]]
    added = sum(db.add_clip(c) for c in chosen)
    log.info("Keşif: %d uygun klip, %d yeni eklendi", len(ranked), added)
    return added


# ---------------------------------------------------------------- üretim
def shift_words(words: list[transcribe.Word], start: float, end: float) -> list[transcribe.Word]:
    return [transcribe.Word(w.start - start, w.end - start, w.text) for w in words if start <= w.start < end]


def _render_version(cfg: dict, *, src: Path, out: Path, words: list[transcribe.Word], meta: dict,
                    broadcaster: str, facecam: dict | None, start: float, end: float, total: float,
                    upper=str.upper, layout: str = "fit") -> Path:
    dd, r = data_dir(cfg), cfg["render"]
    trimmed = start > 0.05 or end < total - 0.05
    length = end - start
    words = shift_words(words, start, end) if trimmed else words
    ass = dd / "tmp" / f"{out.stem}.ass"
    ass.write_text(captions.build_ass(
        words, length,
        hook=meta["hook"] if r["hook"] else None,
        credit=f"twitch.tv/{broadcaster.lower()}" if r["credit"] else None,
        caption_y=editor.caption_y(facecam if layout == "stack" else None, layout),
        brand=r.get("brand") or None, upper=upper, size=editor.canvas(layout)), encoding="utf-8")
    editor.render(src, out, ass_path=ass, zoom=r["zoom"], facecam=facecam if layout == "stack" else None,
                  start=start if trimmed else None, duration=length if trimmed else None,
                  progress=r.get("progress_bar", True), layout=layout)
    return out


def produce(cfg: dict, *, clip_id: str, broadcaster: str, title: str, views: int, src: Path,
            hook_hint: str = "", signals: dict | None = None, launch_clip: bool = False,
            language: str = "en", moment_at: float | None = None) -> tuple[Path | None, dict]:
    """Analiz eder; kalite kapısından geçerse doğal noktalardan kırpıp dikey video üretir.
    İngilizce yayın: global sürüm (İngilizce altyazı, YouTube) + Türkçe sürüm (TikTok).
    Türkçe yayın: sadece Türkçe sürüm (TikTok).
    Dönüş: (ana video yolu veya reddedildiyse None, analiz sözlüğü; Türkçe sürüm a["tr"] içinde)"""
    from . import localize
    from .highlights import loudness_per_second

    dd = data_dir(cfg)
    r, q, up = cfg["render"], cfg["quality"], cfg["upload"]
    language = (language or "en")[:2]
    total = editor.probe_duration(src)
    words: list[transcribe.Word] = []
    if r["captions"]:
        words = transcribe.transcribe(src, r["whisper_model"], language)
    clip_title = title or hook_hint
    if moment_at is not None:
        clip_title += f" [chat exploded at ~{moment_at:.0f}s into this clip: that is the key moment]"
    if launch_clip:
        clip_title = (f"{clip_title} [LAUNCH MOMENT: {broadcaster} is opening/starting GTA 6 for the very first "
                      "time on launch night; the title screen, loading or first seconds ARE the content]")
    a = analyze.analyze(src, total, words, broadcaster, clip_title, views, cfg, clip_id=clip_id,
                        signals=signals or {"views": views})
    bypass = launch_clip and cfg.get("launch", {}).get("bypass_quality", True)
    if bypass and (not a["is_gta6"] or a["score"] < q["min_score"]):
        log.info("Lansman klibi kalite kapısını atladı [%s] puan=%s gta6=%s", broadcaster, a["score"], a["is_gta6"])
    elif not a["is_gta6"] or a["score"] < q["min_score"]:
        log.info("Elendi [%s] puan=%s gta6=%s: %s", broadcaster, a["score"], a["is_gta6"], a["reason"])
        return None, a

    c = cfg.get("cut") or {}
    try:
        loud = loudness_per_second(src)
    except Exception:  # noqa: BLE001 - ses okunamazsa kesim yine çalışır
        loud = None
    start, end = analyze.smart_cut(
        a["best_start"], a["best_end"], total, words, loud, moment_at=moment_at,
        pre_roll=cfg["live"].get("pre_roll_seconds", 10), min_after=c.get("min_after_moment", 8),
        min_len=c.get("min_length", 12), max_len=c.get("max_length", 45), max_shift=c.get("max_shift", 3.0))
    a["best_start"], a["best_end"] = start, end
    layout_main = r.get("layout", "fit")                        # YouTube Shorts: dikey, yayının tamamı
    layout_tt = up["tiktok"].get("layout", "landscape")        # TikTok: yatay (tam ekran düğmesi)
    facecam = resolve_facecam(cfg, broadcaster, src) if "stack" in (layout_main, layout_tt) else None
    common = dict(src=src, broadcaster=broadcaster, facecam=facecam, start=start, end=end, total=total)

    tiktok_tr = (up["tiktok"].get("enabled") and up["tiktok"].get("subtitles") == "tr"
                 and language in (up["tiktok"].get("languages") or ["en", "tr"]))
    out: Path | None = None
    if language != "tr":
        out = _render_version(cfg, out=dd / "out" / f"{clip_id}.mp4", words=words, meta=a["meta"],
                              layout=layout_main, **common)
    if tiktok_tr or language == "tr":
        tr_words, tr_meta = localize.to_turkish(cfg, words, a["meta"], broadcaster, language, clip_id)
        tr_out = _render_version(cfg, out=dd / "out" / f"{clip_id}_tr.mp4", words=tr_words, meta=tr_meta,
                                 upper=localize.tr_upper, layout=layout_tt, **common)
        a["tr"] = {"video": str(tr_out), "meta": tr_meta}
        if out is None:  # Türkçe yayın: ana video da Türkçe sürüm
            out, a["meta"] = tr_out, tr_meta
    log.info("Kurgulandı [%s/%s] (%s) puan=%s %s (%.0f-%.0f sn, %.0f sn)%s: %s", broadcaster, language,
             a.get("engine"), a["score"], a["category"], start, end, end - start,
             " + TR sürüm" if a.get("tr") else "", a["meta"]["title"])
    return out, a


def render_pending(cfg: dict, db: DB, limit: int | None = None) -> int:
    """Her klipten önce kuyruğu yeniden sorgular: yeni gelen bir lansman klibi en fazla bir kurgu bekler."""
    limit = limit or cfg["discovery"]["max_clips_per_run"]
    done = 0
    for _ in range(limit):
        rows = db.clips_with_status("new", 1)
        if not rows:
            break
        row = rows[0]
        launch_clip = row["source"] == "launch"
        try:
            src = download.download_clip(row["url"], data_dir(cfg) / "raw", row["id"])
            out, a = produce(cfg, clip_id=row["id"], broadcaster=row["broadcaster"], title=row["title"] or "",
                             views=row["views"], src=src,
                             signals={"views": row["views"], "score": row["score"], "source": row["source"]},
                             launch_clip=launch_clip, language=row["language"] or "en",
                             moment_at=row["moment_at"])
            analysis = {k: v for k, v in a.items() if k not in ("meta", "tr")}
            tr = a.get("tr") or {}
            if out is None:
                db.mark_rejected(row["id"], a["score"], a["reason"], analysis)
            else:
                db.mark_rendered(row["id"], str(out), a["meta"], a["score"], analysis,
                                 video_tr=tr.get("video"), meta_tr=tr.get("meta"))
                done += 1
                if launch_clip or (a["score"] or 0) >= cfg.get("notify", {}).get("min_quality", 8):
                    notify.send_video(cfg, out, notify.caption(a["meta"], row["broadcaster"], a["score"],
                                                               launch_clip))
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


_UPLOAD_BACKOFF: dict[str, float] = {}


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
        if time.time() < _UPLOAD_BACKOFF.get(platform, 0):
            continue  # son hatadan sonra kısa mola (kota/yetki sorununda her 30 sn'de denemesin)
        reserve = launch.reserve_for(cfg, platform)
        for row in db.pending_uploads(platform, max_age_hours=up.get("max_age_hours"),
                                      languages=pcfg.get("languages")):
            urgent = row.get("source") == "launch"
            limit = pcfg["max_per_day"] if urgent else max(0, pcfg["max_per_day"] - reserve)
            if not db.can_upload(platform, limit, up["min_gap_minutes"], up.get("peak_hours_utc"), urgent=urgent):
                if urgent:
                    break  # günlük hak bitti
                continue  # sıradan klip bekler; listede lansman klibi varsa o yine geçebilir
            try:
                video, meta = row["video_path"], row["meta_json"]
                if platform == "tiktok" and row.get("video_tr_path") and Path(row["video_tr_path"]).exists():
                    video, meta = row["video_tr_path"], row["meta_tr_json"] or meta  # Türkçe sürüm
                remote = fn(Path(video), json.loads(meta), cfg)
                db.record_upload(row["id"], platform, "done", remote)
                log.info("Yüklendi %s [kalite %s] %s", platform, row.get("quality"), row["id"])
                count += 1
            except Exception as e:
                log.exception("%s yükleme hatası: %s", platform, row["id"])
                db.record_upload(row["id"], platform, "failed", detail=str(e)[:1000])
                _UPLOAD_BACKOFF[platform] = time.time() + (120 if row.get("source") == "launch" else 600)
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
        tr = row["video_tr_path"]
        if not row["video_path"] or not Path(row["video_path"]).exists() or (tr and not Path(tr).exists()):
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
        ("kurgu", 15, lambda db: render_pending(cfg, db, 5)),
    ]
    if upload:
        jobs.append(("yükleme", 30, lambda db: upload_pending(cfg, db)))
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
    log.info("%s", launch.describe(cfg))
    if notify.enabled(cfg):  # bota yazılan /start 24 saat sonra kaybolur: sohbeti şimdiden bul ve kaydet
        log.info("Telegram: %s", "sohbet hazır" if notify.chat_id() else "sohbet yok, bota /start yaz")
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
