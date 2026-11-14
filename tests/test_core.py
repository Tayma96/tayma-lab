import subprocess
from datetime import timedelta

import numpy as np
import pytest

from gta6clips import captions, editor, highlights, metadata
from gta6clips.config import DEFAULTS, _merge
from gta6clips.db import DB, now_utc
from gta6clips.transcribe import Word
from gta6clips.twitch import rank_clips
from gta6clips.uploaders.tiktok import choose_privacy


def cfg(**over):
    return _merge(DEFAULTS, over)


def clip(i, name="streamer", views=1000, dur=20, lang="en", **kw):
    return {"id": str(i), "broadcaster_name": name, "title": f"t{i}", "url": f"https://clips/{i}",
            "view_count": views, "duration": dur, "language": lang, **kw}


def test_rank_filters_and_boosts():
    c = cfg(blocklist=["banned"])
    clips = [clip(1, "small", 5000), clip(2, "big", 3000), clip(3, "banned", 99999),
             clip(4, "x", 10), clip(5, "y", 2000, lang="es"), clip(6, "z", 2000, dur=3)]
    ranked = rank_clips(clips, ["big"], c)
    assert [r["id"] for r in ranked] == ["2", "1"]  # big boosted above small


def test_rank_dedupes_same_moment():
    clips = [clip(1, views=900, video_id="v", vod_offset=100), clip(2, views=800, video_id="v", vod_offset=110),
             clip(3, views=700, video_id="v", vod_offset=400)]
    assert [r["id"] for r in rank_clips(clips, [], cfg())] == ["1", "3"]


def test_db_dedup_and_limits(tmp_path):
    db = DB(tmp_path / "x.db")
    c = {"id": "a", "broadcaster": "b", "url": "u"}
    assert db.add_clip(c) and not db.add_clip(c)
    db.mark_rendered("a", "out.mp4", {"title": "t"})
    assert [r["id"] for r in db.pending_uploads("youtube")] == ["a"]
    assert db.can_upload("youtube", 1, 30)
    db.record_upload("a", "youtube", "done", "vid")
    assert db.pending_uploads("youtube") == []
    assert not db.can_upload("youtube", 1, 0)          # daily cap
    assert not db.can_upload("youtube", 5, 30)         # min gap
    assert db.uploads_since("youtube", now_utc() - timedelta(days=1)) == 1


def test_caption_grouping_and_ass():
    words = [Word(0.0, 0.3, "no"), Word(0.35, 0.6, "way"), Word(0.65, 0.9, "bro!"), Word(2.0, 2.4, "run")]
    groups = captions.group_words(words)
    assert [len(g) for g in groups] == [3, 1]
    ass = captions.build_ass(words, 5.0, hook="He did {what}", credit="twitch.tv/x", caption_y=1400)
    assert "Style: Caption" in ass and "HE DID (WHAT)" in ass and "twitch.tv/x" in ass
    assert ass.count(",Caption,") == 4
    assert captions.HIGHLIGHT + "WAY" in ass
    assert captions.ts(3725.456) == "1:02:05.46"


def test_filter_graph_variants():
    g = editor.filter_graph(1.2, None, "a.ass")
    assert "boxblur" in g and "subtitles=a.ass[v]" in g
    g2 = editor.filter_graph(1.0, {"x": 0, "y": 0, "w": 0.25, "h": 0.3}, None)
    assert "vstack" in g2 and g2.endswith("null[v]")


def test_pick_windows_finds_spikes():
    loud = np.full(600, 40.0)
    loud[100] = loud[400] = 80.0
    loud[405] = 75.0
    w = highlights.pick_windows(loud, length=30, top_k=3, pre_roll=18)
    starts = [s for s, _, _ in w]
    assert 82 in starts and 382 in starts
    for (s1, e1, _), (s2, e2, _) in zip(w, w[1:]):
        assert e1 <= s2


def test_metadata_fallback_and_finalize(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    m = metadata.generate("Kai", "insane police chase", "", 100, cfg())
    assert "twitch.tv/kai" in m["description"] and "GTA6" in m["hashtags"] and len(m["title"]) <= 95
    fin = metadata.finalize(metadata.ClipMeta(title="x", hook="one two three four five six seven",
                                              description="d", hashtags=["#gta6", "GTA6", "fun-time"]), "Kai")
    assert fin["hook"].split() == ["one", "two", "three", "four", "five", "six"]
    assert fin["hashtags"] == ["gta6", "funtime", "Kai"]


def test_choose_privacy():
    assert choose_privacy(["SELF_ONLY"]) == "SELF_ONLY"
    assert choose_privacy(["SELF_ONLY", "PUBLIC_TO_EVERYONE"]) == "PUBLIC_TO_EVERYONE"


@pytest.mark.skipif(subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0, reason="ffmpeg yok")
@pytest.mark.parametrize("facecam", [None, {"x": 0.7, "y": 0.0, "w": 0.3, "h": 0.3}])
def test_render_end_to_end(tmp_path, facecam):
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=30",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", "3", "-shortest", str(src)], check=True)
    ass = tmp_path / "s.ass"
    ass.write_text(captions.build_ass([Word(0.2, 0.8, "hello"), Word(0.9, 1.5, "world")], 3.0,
                                      hook="wait for it", credit="twitch.tv/x", caption_y=1420))
    out = editor.render(src, tmp_path / "out.mp4", ass_path=ass, zoom=1.15, facecam=facecam)
    res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(out)], capture_output=True, text=True)
    assert res.stdout.strip() == "1080,1920"
    assert 2.5 < editor.probe_duration(out) < 3.5
