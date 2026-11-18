from datetime import datetime, timedelta, timezone

from gta6clips import launch, notify
from gta6clips.config import DEFAULTS, _merge
from gta6clips.db import DB, upload_priority
from gta6clips.live import pick_channels

ET = datetime(2026, 11, 19, 5, 0, tzinfo=timezone.utc)  # ABD doğu gece yarısı


def cfg(**over):
    return _merge(DEFAULTS, over)


def at(minutes):
    return ET + timedelta(minutes=minutes)


def test_windows_and_campaign():
    c = cfg()
    assert launch.active(c, at(0)) and launch.active(c, at(-20)) and launch.active(c, at(90))
    assert not launch.active(c, at(-21)) and not launch.active(c, at(91))
    assert launch.in_campaign(c, at(-120))           # 00:00 ile 08:00 pencereleri arası: keşif durur
    assert not launch.in_campaign(c, datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc))
    assert not launch.active(cfg(launch={"enabled": False}), at(0))


def test_reserve_only_before_launch():
    c = cfg()
    day_before = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    assert launch.reserve_for(c, "youtube", day_before) == 3
    assert launch.reserve_for(c, "tiktok", day_before) == 5
    assert launch.reserve_for(c, "youtube", datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)) == 0
    assert launch.reserve_for(c, "youtube", datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)) == 0


def test_live_settings_switch_in_window():
    c = cfg()
    assert launch.live_settings(c, at(-180))["spike_ratio"] == DEFAULTS["live"]["spike_ratio"]
    lc = launch.live_settings(c, at(5))
    assert lc["spike_ratio"] == 2.0 and lc["refresh_minutes"] == 2 and lc["max_clips_per_hour"] == 40


def test_run_never_ends_inside_a_window():
    c = cfg()
    now = at(-200)                                   # 330 dk'lık tur 05:00 penceresinin ortasında bitecekti
    m = launch.adjust_run_minutes(c, 330, now)
    end = now + timedelta(minutes=m)
    assert all(not (a - timedelta(minutes=25) < end < b) for a, b in launch.windows(c))
    assert 200 <= m <= 340                           # pencere bitene kadar uzatıldı
    far = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    assert launch.adjust_run_minutes(c, 330, far) == 330  # 17:30'da bitiyor: dokunma
    # uzatma sığmıyorsa pencereden önce bitir
    m2 = launch.adjust_run_minutes(c, 330, at(-340))
    end2 = at(-340) + timedelta(minutes=m2)
    assert end2 <= ET - timedelta(minutes=20 + 25) and m2 >= 30


def test_pick_channels_watchlist_first_and_blocklist():
    lc = {"min_viewers": 3000, "top_channels": 2}
    category = [{"user_login": f"big{i}", "viewer_count": 100000 - i} for i in range(5)]
    watched = [{"user_login": "KaiCenat", "viewer_count": 900000}, {"user_login": "banned", "viewer_count": 5}]
    out = pick_channels(category, watched, lc, {"banned"})
    assert list(out)[0] == "kaicenat" and "banned" not in out
    assert set(out) == {"kaicenat", "big0", "big1"}


def test_launch_clip_first_in_render_and_upload(tmp_path):
    db = DB(tmp_path / "c.db")
    now = datetime.now(timezone.utc).isoformat()
    db.add_clip({"id": "pop", "broadcaster": "a", "url": "u", "views": 900000, "score": 99,
                 "created_at": now, "source": "top"})
    db.add_clip({"id": "live", "broadcaster": "b", "url": "u", "views": 10, "score": 5, "created_at": now,
                 "source": "live"})
    db.add_clip({"id": "moment", "broadcaster": "c", "url": "u", "views": 1, "score": 1, "created_at": now,
                 "source": "launch"})
    assert [r["id"] for r in db.clips_with_status("new", 3)] == ["moment", "live", "pop"]
    rows = [{"quality": 9, "views": 900000, "source": "top", "created_at": now},
            {"quality": 3, "views": 1, "source": "launch", "created_at": now}]
    assert upload_priority(rows[1]) > upload_priority(rows[0])


def test_urgent_upload_skips_gap_but_not_daily_limit(tmp_path):
    db = DB(tmp_path / "c.db")
    db.add_clip({"id": "x", "broadcaster": "a", "url": "u"})
    db.record_upload("x", "youtube", "done", "vid")
    assert not db.can_upload("youtube", 6, 45, None)              # 45 dk bekleme
    assert db.can_upload("youtube", 6, 45, None, urgent=True)     # lansman anı beklemez
    assert not db.can_upload("youtube", 1, 45, None, urgent=True)  # günlük hak yine de geçerli


def test_telegram_caption_and_chat_discovery(monkeypatch, tmp_path):
    text = notify.caption({"title": "T" * 50, "description": "D" * 2000, "hashtags": ["#gta6", "#shorts"]},
                          "KaiCenat", 9, True)
    assert text.startswith("🚨 LANSMAN ANI | twitch.tv/kaicenat") and len(text) <= 1024
    monkeypatch.setattr(notify, "_STATE", tmp_path / "telegram.json")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    class R:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"result": [{"message": {"chat": {"id": 42, "type": "private"}}}]}

    monkeypatch.setattr(notify.requests, "get", lambda *a, **k: R())
    assert notify.chat_id() == "42"
    monkeypatch.setattr(notify.requests, "get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ağ")))
    assert notify.chat_id() == "42"                                # kaydedilenden okur, ağa çıkmaz
    assert not notify.enabled(cfg(notify={"telegram": False}))
