"""Uçtan uca akış: keşfet -> indir -> döküm -> meta veri -> kurgu -> yükle."""
from __future__ import annotations

import logging
from pathlib import Path

from . import captions, download, editor, highlights, metadata, transcribe
from .config import env
from .db import DB
from .facecam import FacecamCache
from .twitch import Twitch, rank_clips

log = logging.getLogger(__name__)
_FACECAMS: FacecamCache | None = None


def resolve_facecam(cfg: dict, broadcaster: str, src: Path) -> dict | None:
    """Önce config.yaml'daki elle girilmiş konum, yoksa otomatik tespit (render.auto_facecam)."""
    global _FACECAMS
    manual = cfg["facecams"].get(broadcaster.lower())
    if manual or not cfg["render"].get("auto_facecam"):
        return manual
    if _FACECAMS is None:
        _FACECAMS = FacecamCache(data_dir(cfg) / "facecams.json")
    return _FACECAMS.get(broadcaster, src)


def data_dir(cfg: dict) -> Path:
    return Path(cfg["paths"]["data_dir"])


def open_db(cfg: dict) -> DB:
    return DB(data_dir(cfg) / "clips.db")


def discover(cfg: dict, db: DB) -> int:
    tw = Twitch(env("TWITCH_CLIENT_ID"), env("TWITCH_CLIENT_SECRET"))
    d = cfg["discovery"]
    gid = tw.game_id(cfg["game_name"])
    streams = tw.top_streams(gid, d.get("language"))
    top_streamers = [s["user_login"] for s in streams]
    if top_streamers:
        log.info("Şu an en çok izlenen GTA 6 yayıncıları: %s", ", ".join(top_streamers[:10]))
    ranked = rank_clips(tw.top_clips(gid, d["lookback_hours"]), top_streamers, cfg)
    added = sum(db.add_clip(c) for c in ranked[: d["max_clips_per_run"] * 3])
    log.info("Keşif: %d uygun klip, %d yeni eklendi", len(ranked), added)
    return added


def produce(cfg: dict, *, clip_id: str, broadcaster: str, title: str, views: int, src: Path,
            hook_hint: str = "") -> tuple[Path, dict]:
    """Tek bir kaynak videodan dikey klip + meta veri üretir."""
    dd = data_dir(cfg)
    r = cfg["render"]
    words: list[transcribe.Word] = []
    if r["captions"]:
        words = transcribe.transcribe(src, r["whisper_model"], cfg["discovery"].get("language"))
    meta = metadata.generate(broadcaster, title or hook_hint, transcribe.plain_text(words), views, cfg)
    facecam = resolve_facecam(cfg, broadcaster, src)
    total = editor.probe_duration(src)
    ass = dd / "tmp" / f"{clip_id}.ass"
    ass.write_text(captions.build_ass(
        words, total,
        hook=meta["hook"] if r["hook"] else None,
        credit=f"twitch.tv/{broadcaster.lower()}" if r["credit"] else None,
        caption_y=editor.caption_y(facecam)), encoding="utf-8")
    out = dd / "out" / f"{clip_id}.mp4"
    editor.render(src, out, ass_path=ass, zoom=r["zoom"], facecam=facecam)
    return out, meta


def render_pending(cfg: dict, db: DB, limit: int | None = None) -> int:
    limit = limit or cfg["discovery"]["max_clips_per_run"]
    done = 0
    for row in db.clips_with_status("new", limit):
        try:
            src = download.download_clip(row["url"], data_dir(cfg) / "raw", row["id"])
            out, meta = produce(cfg, clip_id=row["id"], broadcaster=row["broadcaster"], title=row["title"] or "",
                                views=row["views"], src=src)
            db.mark_rendered(row["id"], str(out), meta)
            log.info("Kurgulandı: %s  [%s] %s", out, row["broadcaster"], meta["title"])
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
    ranked = highlights.rank_with_claude(cands, cfg)
    for c in ranked[:top_k]:
        log.info("Aday %ss-%ss viral=%s %s", c["start"], c["end"], c.get("viral_score", "-"), c.get("reason", ""))
    return ranked[:top_k]


def process_vod(cfg: dict, db: DB, url: str, broadcaster: str, top_k: int = 5, length: int = 30) -> int:
    """Uzun bir yayından (VOD) ses zirveleri + Claude viral puanına göre kesitler çıkarır."""
    dd = data_dir(cfg)
    key = "vod_" + "".join(ch for ch in url if ch.isalnum())[-24:]
    audio = download.download_audio(url, dd / "raw", key)
    picks = vod_candidates(cfg, audio, key, top_k, length)
    log.info("VOD'da %d öne çıkan an seçildi", len(picks))
    done = 0
    for c in picks:
        start, end = c["start"], c["end"]
        clip_id = f"{key}_{start}"
        if not db.add_clip({"id": clip_id, "broadcaster": broadcaster, "title": c.get("hook", ""), "url": url,
                            "score": c.get("viral_score", c["loud_score"]), "duration": end - start}):
            continue
        try:
            src = download.download_section(url, dd / "raw", clip_id, start, end)
            out, meta = produce(cfg, clip_id=clip_id, broadcaster=broadcaster, title="", views=0, src=src,
                                hook_hint=c.get("hook", ""))
            db.mark_rendered(clip_id, str(out), meta)
            done += 1
        except Exception as e:
            log.exception("VOD kesiti işlenemedi: %s", clip_id)
            db.mark_failed(clip_id, str(e))
    return done


def upload_pending(cfg: dict, db: DB) -> int:
    import json

    from .uploaders import tiktok, tiktok_browser, youtube

    up = cfg["upload"]
    tiktok_fn = tiktok_browser.upload if up["tiktok"].get("method") == "browser" else tiktok.upload
    uploaders = {"youtube": youtube.upload, "tiktok": tiktok_fn}
    count = 0
    for platform, fn in uploaders.items():
        pcfg = up[platform]
        if not pcfg.get("enabled"):
            continue
        for row in db.pending_uploads(platform):
            if not db.can_upload(platform, pcfg["max_per_day"], up["min_gap_minutes"]):
                log.info("%s: günlük limit / bekleme süresi doldu, sonraki tura kaldı", platform)
                break
            try:
                remote = fn(Path(row["video_path"]), json.loads(row["meta_json"]), cfg)
                db.record_upload(row["id"], platform, "done", remote)
                count += 1
            except Exception as e:
                log.exception("%s yükleme hatası: %s", platform, row["id"])
                db.record_upload(row["id"], platform, "failed", detail=str(e)[:1000])
                break  # yetki/kota sorunlarında aynı turda tekrar tekrar deneme
    tiktok_browser.close()
    return count
