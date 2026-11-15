import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from gta6clips import analyze, captions, editor, pipeline
from gta6clips.chat import ChatSpikeDetector, message_weight, parse_privmsg
from gta6clips.config import DEFAULTS, _merge
from gta6clips.db import DB, upload_priority
from gta6clips.live import ClipBudget, live_score
from gta6clips.transcribe import Word
from gta6clips.twitch import clip_velocity, rank_clips

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def iso(hours_ago):
    return (NOW - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")


# --- sohbet patlaması ---
def test_message_weight():
    assert message_weight("hello") == 1.0
    assert message_weight("KEKW KEKW") > 1.9
    assert message_weight("CLIP IT ?????") == 3.0  # bonus 2 ile sınırlı


def test_spike_detector_triggers_on_burst_and_respects_cooldown():
    d = ChatSpikeDetector(window=6, baseline=180, ratio=3, min_weight=15, cooldown=120, warmup=60)
    t = 0.0
    fired = []
    while t < 120:                      # sakin sohbet: saniyede ~1 mesaj
        if d.add(t, "nice drive"):
            fired.append(t)
        t += 1
    assert fired == []
    for i in range(30):                 # 3 saniyede 30 KEKW
        if (s := d.add(t + i * 0.1, "KEKW OMEGALUL")):
            fired.append((t + i * 0.1, s))
    assert len(fired) == 1 and fired[0][1] > 3
    t2 = t + 10
    for i in range(30):                 # 10 sn sonra ikinci patlama: cooldown nedeniyle yok
        assert d.add(t2 + i * 0.1, "KEKW") is None


def test_spike_detector_needs_warmup():
    d = ChatSpikeDetector(warmup=60)
    assert all(d.add(i * 0.05, "KEKW KEKW") is None for i in range(100))


def test_parse_privmsg():
    line = ":bob!bob@bob.tmi.twitch.tv PRIVMSG #KaiCenat :no way KEKW"
    assert parse_privmsg(line) == ("kaicenat", "no way KEKW")
    assert parse_privmsg(":tmi.twitch.tv 001 justinfan1 :Welcome") is None


def test_chat_survives_connection_failure(monkeypatch):
    from gta6clips import chat as chat_mod

    def boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(chat_mod.socket, "create_connection", boom)
    monkeypatch.setattr(chat_mod.time, "sleep", lambda s: None)
    c = chat_mod.TwitchChat()
    c.set_channels({"a"})
    assert c.poll() == [] and c.sock is None and c.channels == {"a"}


def test_clip_budget_and_live_score():
    b = ClipBudget(2)
    assert b.take(0) and b.take(1) and not b.take(2) and b.take(3601)
    assert live_score(5, 100000) > live_score(5, 2000) > live_score(2, 2000)


# --- sıralama ---
def test_velocity_prefers_fresh_fast_clips():
    assert clip_velocity(5000, iso(1), NOW) > clip_velocity(20000, iso(20), NOW)


def test_rank_uses_velocity_and_performance():
    cfg = _merge(DEFAULTS, {})
    clips = [{"id": "old", "broadcaster_name": "a", "url": "u1", "view_count": 20000, "duration": 20,
              "language": "en", "created_at": iso(20)},
             {"id": "new", "broadcaster_name": "b", "url": "u2", "view_count": 5000, "duration": 20,
              "language": "en", "created_at": iso(1)}]
    assert [c["id"] for c in rank_clips(clips, [], cfg, now=NOW)] == ["new", "old"]
    assert [c["id"] for c in rank_clips(clips, [], cfg, {"b": 0.5, "a": 2.0}, now=NOW)] == ["old", "new"]


def test_upload_priority_quality_then_freshness():
    good_old = {"quality": 9, "views": 1000, "created_at": iso(30)}
    ok_new = {"quality": 6, "views": 1000, "created_at": iso(1)}
    great_new = {"quality": 9, "views": 1000, "created_at": iso(1)}
    p = [upload_priority(r, NOW) for r in (good_old, ok_new, great_new)]
    assert p[2] > p[1] > p[0]
    assert upload_priority({**great_new, "source": "live"}, NOW) > p[2]


# --- veritabanı ---
def test_db_migrates_old_schema_and_filters_stale(tmp_path):
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.executescript("CREATE TABLE clips (id TEXT PRIMARY KEY, broadcaster TEXT NOT NULL, title TEXT,"
                      " url TEXT NOT NULL, views INTEGER DEFAULT 0, score REAL DEFAULT 0, duration REAL DEFAULT 0,"
                      " created_at TEXT, status TEXT NOT NULL DEFAULT 'new', video_path TEXT, meta_json TEXT,"
                      " error TEXT);")
    con.commit()
    con.close()
    db = DB(path)
    cols = {r[1] for r in db.conn.execute("PRAGMA table_info(clips)")}
    assert {"source", "quality", "analysis_json", "added_at"} <= cols
    stale = (datetime.now(timezone.utc) - timedelta(hours=50)).isoformat()
    db.add_clip({"id": "a", "broadcaster": "x", "url": "u", "created_at": stale})
    db.add_clip({"id": "b", "broadcaster": "x", "url": "u"})
    for cid in ("a", "b"):
        db.mark_rendered(cid, "v.mp4", {"title": "t"}, quality=7)
    assert [r["id"] for r in db.pending_uploads("youtube", max_age_hours=36)] == ["b"]
    db.mark_rejected("a", 3, "boring")
    assert db.conn.execute("SELECT status FROM clips WHERE id='a'").fetchone()[0] == "rejected"


def test_streamer_performance(tmp_path):
    db = DB(tmp_path / "p.db")
    for i, (b, v) in enumerate([("a", 1000)] * 3 + [("b", 9000)] * 3):
        db.add_clip({"id": str(i), "broadcaster": b, "url": "u"})
        db.record_upload(str(i), "youtube", "done", f"y{i}")
        db.set_views("youtube", f"y{i}", v)
    perf = db.streamer_performance()
    assert perf["b"] > 1 > perf["a"] >= 0.5


def test_peak_hours_gate(tmp_path):
    db = DB(tmp_path / "h.db")
    hour = datetime.now(timezone.utc).hour
    assert db.can_upload("youtube", 5, 0, [hour])
    assert not db.can_upload("youtube", 5, 0, [(hour + 1) % 24])


# --- analiz ---
def test_clamp_trim():
    assert analyze.clamp_trim(3, 25, 30) == (3, 25)
    assert analyze.clamp_trim(-5, 99, 30) == (0, 30)
    s, e = analyze.clamp_trim(10, 12, 30)       # çok kısa -> 8 sn'ye genişlet
    assert e - s == pytest.approx(8)
    s, e = analyze.clamp_trim(27, 29, 30)
    assert e == 30 and s == 22


def test_timed_transcript():
    words = [Word(0, 0.5, "no"), Word(0.6, 1, "way"), Word(3.2, 3.6, "run"), Word(3.7, 4, "now")]
    assert analyze.timed_transcript(words, every=3) == "[0.0] no way run\n[3.7] now"
    assert analyze.timed_transcript([]) == "(no speech detected)"


def _make_src(path, seconds=6):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30",
                    "-f", "lavfi", "-i", "sine", "-t", str(seconds), "-shortest", str(path)], check=True)


def _cfg(tmp_path, **over):
    cfg = _merge(DEFAULTS, {"paths": {"data_dir": str(tmp_path)}, "render": {"captions": False,
                                                                            "auto_facecam": False,
                                                                            "brand": "@gta6moments"}, **over})
    for sub in ("tmp", "out"):
        (tmp_path / sub).mkdir(exist_ok=True)
    return cfg


def test_produce_rejects_low_quality(monkeypatch, tmp_path):
    src = tmp_path / "s.mp4"
    _make_src(src)
    monkeypatch.setattr(analyze, "analyze", lambda *a, **k: {
        "score": 3, "is_gta6": True, "category": "other", "reason": "nothing happens",
        "best_start": 0, "best_end": 6, "meta": {}})
    out, a = pipeline.produce(_cfg(tmp_path), clip_id="c1", broadcaster="kai", title="t", views=0, src=src)
    assert out is None and a["score"] == 3


def test_produce_rejects_not_gta6(monkeypatch, tmp_path):
    src = tmp_path / "s.mp4"
    _make_src(src)
    monkeypatch.setattr(analyze, "analyze", lambda *a, **k: {
        "score": 9, "is_gta6": False, "category": "other", "reason": "this is GTA V",
        "best_start": 0, "best_end": 6, "meta": {}})
    out, _ = pipeline.produce(_cfg(tmp_path), clip_id="c2", broadcaster="kai", title="t", views=0, src=src)
    assert out is None


def test_produce_trims_and_renders(monkeypatch, tmp_path):
    src = tmp_path / "s.mp4"
    _make_src(src, 6)
    meta = {"title": "He did it", "hook": "WATCH THIS", "description": "d", "hashtags": ["GTA6"]}
    monkeypatch.setattr(analyze, "analyze", lambda *a, **k: {
        "score": 8, "is_gta6": True, "category": "chaos", "reason": "boom",
        "best_start": 1.0, "best_end": 4.0, "meta": meta})
    out, a = pipeline.produce(_cfg(tmp_path), clip_id="c3", broadcaster="kai", title="t", views=0, src=src)
    assert out is not None and out.exists()
    assert 2.6 < editor.probe_duration(out) < 3.5
    ass = (tmp_path / "tmp" / "c3.ass").read_text()
    assert "@gta6moments" in ass and "WATCH THIS" in ass


def test_brand_in_ass():
    ass = captions.build_ass([], 5, hook=None, credit=None, caption_y=1400, brand="@chan")
    assert r"\an9" in ass and "@chan" in ass
