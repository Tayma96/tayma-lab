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
    assert launch.adjust_run_minutes(c, 15, at(-10)) == 15  # kısa deneme turu uzatılmaz
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


# --- klip zamanlaması ve akıllı kesim ---
from gta6clips.analyze import smart_cut  # noqa: E402
from gta6clips.live import clip_timing  # noqa: E402
from gta6clips.localize import spread, tr_upper  # noqa: E402
from gta6clips.transcribe import Word  # noqa: E402


def test_clip_timing_puts_moment_10s_in():
    delay, moment_at = clip_timing(DEFAULTS["live"])
    assert delay == 13 and moment_at == 10                  # 30 sn klip: 10 sn önce + 20 sn tepki


def test_smart_cut_keeps_pre_roll_and_reaction():
    s, e = smart_cut(6.0, 14.0, 30.0, [], None, moment_at=10.0)
    assert s == 0.0 and e >= 18.0                           # andan 10 sn önce, en az 8 sn sonra


def test_smart_cut_never_starts_or_ends_mid_sentence():
    words = [Word(4.6, 5.0, "oh"), Word(5.1, 5.6, "my"), Word(5.7, 6.2, "god"),
             Word(19.5, 20.0, "this"), Word(20.1, 20.6, "is"), Word(20.7, 21.4, "insane!")]
    s, e = smart_cut(5.3, 20.3, 30.0, words, None)
    assert s <= 4.6                                         # cümlenin başına alındı
    assert e >= 21.4                                        # cümle bitene kadar uzatıldı


def test_smart_cut_extends_while_screaming_and_takes_tail():
    import numpy as np
    loud = np.array([40.0] * 30)
    loud[20:23] = 60.0                                      # 20-23 sn arası bağırış
    s, e = smart_cut(0.0, 20.5, 30.0, [], loud)
    assert e >= 23.0
    s, e = smart_cut(0.0, 29.2, 30.0, [], None)
    assert e == 30.0                                        # sona çok yakınsa tamamı


def test_smart_cut_length_bounds():
    s, e = smart_cut(0.0, 5.0, 60.0, [], None)
    assert e - s >= 12
    s, e = smart_cut(0.0, 59.0, 60.0, [], None)
    assert e - s <= 48


def test_turkish_spread_and_upper():
    groups = [[Word(1.0, 1.4, "oh"), Word(1.5, 2.0, "no")], [Word(3.0, 3.5, "run")]]
    out = spread(groups, ["eyvah ya", "kaç"])
    assert [w.text for w in out] == ["eyvah", "ya", "kaç"]
    assert out[0].start == 1.0 and out[1].end <= 2.0 and out[2].start == 3.0
    assert tr_upper("inanılmaz şimdi") == "İNANILMAZ ŞİMDİ"


def test_upload_language_routing(tmp_path):
    db = DB(tmp_path / "c.db")
    for cid, lang in (("en1", "en"), ("tr1", "tr")):
        db.add_clip({"id": cid, "broadcaster": "a", "url": "u", "language": lang})
        db.mark_rendered(cid, f"/v/{cid}.mp4", {"title": "t", "hashtags": []}, 7,
                         video_tr=f"/v/{cid}_tr.mp4", meta_tr={"title": "tr", "hashtags": []})
    yt = [r["id"] for r in db.pending_uploads("youtube", languages=["en"])]
    tt = [r["id"] for r in db.pending_uploads("tiktok", languages=["en", "tr"])]
    assert yt == ["en1"] and sorted(tt) == ["en1", "tr1"]
    row = db.pending_uploads("tiktok", languages=["tr"])[0]
    assert row["video_tr_path"] == "/v/tr1_tr.mp4"


def test_pick_channels_adds_turkish_streams():
    lc = {"min_viewers": 3000, "top_channels": 2, "local_channels": 1, "local_min_viewers": 300}
    en = [{"user_login": f"en{i}", "viewer_count": 50000 - i, "language": "en"} for i in range(4)]
    tr = [{"user_login": "elraenn", "viewer_count": 8000, "language": "tr"},
          {"user_login": "kucuk", "viewer_count": 100, "language": "tr"}]
    out = pick_channels(en, [], lc, set(), tr)
    assert set(out) == {"en0", "en1", "elraenn"}


def test_transcribe_passes_array_not_path(monkeypatch, tmp_path):
    """faster-whisper'a dosya yolu verilirse yeni PyAV ile çöküyor: ses dizisi verilmeli."""
    import subprocess
    import sys
    import types

    import numpy as np

    from gta6clips import transcribe

    src = tmp_path / "a.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                    str(src)], check=True)
    seen = {}

    class FakeModel:
        def __init__(self, *a, **k):
            pass

        def transcribe(self, audio, **k):
            seen["type"] = type(audio)
            w = types.SimpleNamespace(word=" hey", start=0.1, end=0.4)
            return [types.SimpleNamespace(words=[w])], None

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    monkeypatch.setattr(transcribe, "_MODEL", None)
    words = transcribe.transcribe(src, "tiny", "en")
    assert seen["type"] is np.ndarray and words[0].text == "hey"

    class Broken(FakeModel):
        def transcribe(self, audio, **k):
            raise TypeError("metadata_errors")

    monkeypatch.setattr(transcribe, "_MODEL", Broken())
    assert transcribe.transcribe(src, "tiny", "en") == []      # döküm hatası klibi düşürmez
