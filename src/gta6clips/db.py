"""Hangi klip bulundu, işlendi, nereye yüklendi: hepsi SQLite'ta (tekrar yüklemeyi önler)."""
from __future__ import annotations

import json
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
    status TEXT NOT NULL DEFAULT 'new',   -- new | rendered | failed | skipped
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


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class DB:
    def __init__(self, path: str | Path):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # --- clips ---
    def add_clip(self, clip: dict) -> bool:
        """Yeni klibi ekler; zaten varsa False döner."""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO clips (id, broadcaster, title, url, views, score, duration, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (clip["id"], clip["broadcaster"], clip.get("title"), clip["url"], clip.get("views", 0),
             clip.get("score", 0), clip.get("duration", 0), clip.get("created_at")),
        )
        self.conn.commit()
        return cur.rowcount == 1

    def clips_with_status(self, status: str, limit: int = 100) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM clips WHERE status=? ORDER BY score DESC LIMIT ?", (status, limit)))

    def mark_rendered(self, clip_id: str, video_path: str, meta: dict) -> None:
        self.conn.execute("UPDATE clips SET status='rendered', video_path=?, meta_json=?, error=NULL WHERE id=?",
                          (video_path, json.dumps(meta, ensure_ascii=False), clip_id))
        self.conn.commit()

    def mark_failed(self, clip_id: str, error: str) -> None:
        self.conn.execute("UPDATE clips SET status='failed', error=? WHERE id=?", (error[:2000], clip_id))
        self.conn.commit()

    # --- uploads ---
    def pending_uploads(self, platform: str, limit: int = 50) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT c.* FROM clips c WHERE c.status='rendered' AND NOT EXISTS ("
            " SELECT 1 FROM uploads u WHERE u.clip_id=c.id AND u.platform=? AND u.status='done')"
            " ORDER BY c.score DESC LIMIT ?", (platform, limit)))

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

    def can_upload(self, platform: str, max_per_day: int, min_gap_minutes: int) -> bool:
        now = now_utc()
        if self.uploads_since(platform, now - timedelta(days=1)) >= max_per_day:
            return False
        last = self.last_upload_at(platform)
        return last is None or now - last >= timedelta(minutes=min_gap_minutes)

    def stats(self) -> dict:
        clips = {r[0]: r[1] for r in self.conn.execute("SELECT status, COUNT(*) FROM clips GROUP BY status")}
        ups = {f"{r[0]}:{r[1]}": r[2] for r in self.conn.execute(
            "SELECT platform, status, COUNT(*) FROM uploads GROUP BY platform, status")}
        return {"clips": clips, "uploads": ups}
