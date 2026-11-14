"""Hangi klip bulundu, analiz edildi, işlendi, nereye yüklendi, kaç izlendi: hepsi SQLite'ta.
Birden çok iş parçacığı (canlı avcı, kurgu, yükleme) aynı dosyayı kullanır: her biri kendi DB() nesnesini açar."""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY,
    broadcaster TEXT NOT NULL,
    title TEXT,
    url TEXT NOT NULL,
    views INTEGER DEFAULT 0,
    score REAL DEFAULT 0,
    duration REAL DEFAULT 0,
    created_at TEXT,
    status TEXT NOT NULL DEFAULT 'new',   -- new | rendered | rejected | failed
    video_path TEXT,
    meta_json TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS uploads (
    clip_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    remote_id TEXT,
    status TEXT NOT NULL,                  -- done | failed
    detail TEXT,
    uploaded_at TEXT NOT NULL,
    PRIMARY KEY (clip_id, platform)
);
"""

# Eski veritabanlarına eklenecek sütunlar (tablo, sütun, tip)
MIGRATIONS = [
    ("clips", "source", "TEXT DEFAULT 'top'"),        # top | live | vod
    ("clips", "quality", "REAL"),                     # Claude kalite puanı 1-10
    ("clips", "analysis_json", "TEXT"),
    ("clips", "added_at", "TEXT"),
    ("uploads", "views", "INTEGER"),
    ("uploads", "views_checked_at", "TEXT"),
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def upload_priority(row: dict, now: datetime | None = None, half_life_hours: float = 12.0) -> float:
    """Saf fonksiyon. Önce kalite (Claude puanı), sonra popülerlik; taze içerik öne çıkar.
    GTA 6 çıkış haftasında içerik çok hızlı bayatlar, bu yüzden 12 saatlik yarı ömür."""
    now = now or now_utc()
    quality = row.get("quality") if row.get("quality") is not None else 5.0
    pop = math.log10((row.get("views") or 0) + 10) + (row.get("score") or 0) / 1e6
    born = parse_ts(row.get("created_at")) or parse_ts(row.get("added_at")) or now
    age_h = max(0.0, (now - born).total_seconds() / 3600)
    fresh = 0.5 ** (age_h / half_life_hours)
    live_bonus = 1.25 if row.get("source") == "live" else 1.0
    return (quality * 10 + pop * 4) * fresh * live_bonus


class DB:
    def __init__(self, path: str | Path):
        self.conn = sqlite3.connect(str(path), timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        for table, col, typ in MIGRATIONS:
            cols = {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")}
            if col not in cols:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
        self.conn.commit()

    # --- clips ---
    def add_clip(self, clip: dict) -> bool:
        """Yeni klibi ekler; zaten varsa False döner."""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO clips (id, broadcaster, title, url, views, score, duration, created_at, source,"
            " added_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (clip["id"], clip["broadcaster"], clip.get("title"), clip["url"], clip.get("views", 0),
             clip.get("score", 0), clip.get("duration", 0), clip.get("created_at"), clip.get("source", "top"),
             now_utc().isoformat()),
        )
        self.conn.commit()
        return cur.rowcount == 1

    def clips_with_status(self, status: str, limit: int = 100) -> list[sqlite3.Row]:
        # Canlı yakalanan klipler en taze içerik: önce onlar
        return list(self.conn.execute(
            "SELECT * FROM clips WHERE status=? ORDER BY (source='live') DESC, score DESC LIMIT ?", (status, limit)))

    def mark_rendered(self, clip_id: str, video_path: str, meta: dict, quality: float | None = None,
                      analysis: dict | None = None) -> None:
        self.conn.execute(
            "UPDATE clips SET status='rendered', video_path=?, meta_json=?, quality=?, analysis_json=?, error=NULL"
            " WHERE id=?",
            (video_path, json.dumps(meta, ensure_ascii=False), quality,
             json.dumps(analysis, ensure_ascii=False) if analysis else None, clip_id))
        self.conn.commit()

    def mark_rejected(self, clip_id: str, quality: float | None, reason: str, analysis: dict | None = None) -> None:
        self.conn.execute("UPDATE clips SET status='rejected', quality=?, error=?, analysis_json=? WHERE id=?",
                          (quality, reason[:500], json.dumps(analysis, ensure_ascii=False) if analysis else None,
                           clip_id))
        self.conn.commit()

    def mark_failed(self, clip_id: str, error: str) -> None:
        self.conn.execute("UPDATE clips SET status='failed', error=? WHERE id=?", (error[:2000], clip_id))
        self.conn.commit()

    # --- uploads ---
    def pending_uploads(self, platform: str, limit: int = 50, max_age_hours: float | None = None) -> list[dict]:
        rows = [dict(r) for r in self.conn.execute(
            "SELECT c.* FROM clips c WHERE c.status='rendered' AND NOT EXISTS ("
            " SELECT 1 FROM uploads u WHERE u.clip_id=c.id AND u.platform=? AND u.status='done')", (platform,))]
        now = now_utc()
        if max_age_hours:
            rows = [r for r in rows
                    if (now - (parse_ts(r.get("created_at")) or parse_ts(r.get("added_at")) or now))
                    <= timedelta(hours=max_age_hours)]
        rows.sort(key=lambda r: upload_priority(r, now), reverse=True)
        return rows[:limit]

    def record_upload(self, clip_id: str, platform: str, status: str, remote_id: str | None = None,
                      detail: str | None = None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO uploads (clip_id, platform, remote_id, status, detail, uploaded_at)"
            " VALUES (?,?,?,?,?,?)",
            (clip_id, platform, remote_id, status, detail, now_utc().isoformat()))
        self.conn.commit()

    def uploads_since(self, platform: str, since: datetime) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM uploads WHERE platform=? AND status='done' AND uploaded_at>=?",
            (platform, since.isoformat())).fetchone()
        return int(row[0])

    def last_upload_at(self, platform: str) -> datetime | None:
        row = self.conn.execute(
            "SELECT MAX(uploaded_at) FROM uploads WHERE platform=? AND status='done'", (platform,)).fetchone()
        return datetime.fromisoformat(row[0]) if row and row[0] else None

    def can_upload(self, platform: str, max_per_day: int, min_gap_minutes: int,
                   peak_hours_utc: list[int] | None = None) -> bool:
        now = now_utc()
        if peak_hours_utc and now.hour not in peak_hours_utc:
            return False
        if self.uploads_since(platform, now - timedelta(days=1)) >= max_per_day:
            return False
        last = self.last_upload_at(platform)
        return last is None or now - last >= timedelta(minutes=min_gap_minutes)

    # --- analitik ---
    def youtube_ids_to_check(self, min_age_hours: float = 2, recheck_hours: float = 6) -> list[str]:
        now = now_utc()
        out = []
        for r in self.conn.execute(
                "SELECT remote_id, uploaded_at, views_checked_at FROM uploads"
                " WHERE platform='youtube' AND status='done' AND remote_id IS NOT NULL"):
            up = parse_ts(r["uploaded_at"])
            chk = parse_ts(r["views_checked_at"])
            if up and now - up >= timedelta(hours=min_age_hours) and (
                    chk is None or now - chk >= timedelta(hours=recheck_hours)):
                out.append(r["remote_id"])
        return out

    def set_views(self, platform: str, remote_id: str, views: int) -> None:
        self.conn.execute("UPDATE uploads SET views=?, views_checked_at=? WHERE platform=? AND remote_id=?",
                          (views, now_utc().isoformat(), platform, remote_id))
        self.conn.commit()

    def streamer_performance(self, min_uploads: int = 3) -> dict[str, float]:
        """Yayıncı başına çarpan: o yayıncının kliplerinin ortalama izlenmesi / genel ortalama (0.5-2.0)."""
        rows = list(self.conn.execute(
            "SELECT lower(c.broadcaster) b, AVG(u.views) v, COUNT(*) n FROM uploads u JOIN clips c ON c.id=u.clip_id"
            " WHERE u.views IS NOT NULL GROUP BY lower(c.broadcaster)"))
        allv = [r["v"] for r in rows if r["v"] is not None]
        if not allv:
            return {}
        mean = sum(allv) / len(allv) or 1
        return {r["b"]: max(0.5, min(2.0, r["v"] / mean)) for r in rows if r["n"] >= min_uploads}

    def stats(self) -> dict:
        clips = {r[0]: r[1] for r in self.conn.execute("SELECT status, COUNT(*) FROM clips GROUP BY status")}
        sources = {r[0]: r[1] for r in self.conn.execute("SELECT source, COUNT(*) FROM clips GROUP BY source")}
        ups = {f"{r[0]}:{r[1]}": r[2] for r in self.conn.execute(
            "SELECT platform, status, COUNT(*) FROM uploads GROUP BY platform, status")}
        top = [dict(r) for r in self.conn.execute(
            "SELECT c.broadcaster, c.title, u.views FROM uploads u JOIN clips c ON c.id=u.clip_id"
            " WHERE u.views IS NOT NULL ORDER BY u.views DESC LIMIT 5")]
        return {"clips": clips, "sources": sources, "uploads": ups, "top_videos": top,
                "streamer_multipliers": self.streamer_performance()}
