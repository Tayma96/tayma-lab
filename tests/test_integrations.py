import subprocess
import sys
import types

import pytest

from gta6clips import facecam, highlights
from gta6clips.config import DEFAULTS, _merge
from gta6clips.uploaders import tiktok_browser


def test_stable_face_picks_static_small_face():
    cam = (0.80, 0.05, 0.06, 0.10)      # sağ üst köşede sabit yüz kamerası
    frames = []
    for i in range(10):
        moving = (0.1 + i * 0.07, 0.5, 0.05, 0.09)  # oyundaki hareket eden karakter
        frames.append([cam, moving] if i % 4 else [moving])
    face = facecam.stable_face(frames)
    assert face is not None and abs(face[0] - 0.80) < 1e-6


def test_stable_face_rejects_big_or_rare():
    assert facecam.stable_face([[(0.3, 0.3, 0.4, 0.4)]] * 6) is None        # tam ekran kamera / oyun yüzü
    assert facecam.stable_face([[(0.8, 0.05, 0.06, 0.1)]] + [[]] * 5) is None  # sadece 1/6 karede
    assert facecam.stable_face([]) is None


def test_face_to_cam_stays_in_frame():
    cam = facecam.face_to_cam((0.92, 0.02, 0.06, 0.10))
    assert 0 <= cam["x"] and cam["x"] + cam["w"] <= 1.0001
    assert 0 <= cam["y"] and cam["y"] + cam["h"] <= 1.0001
    assert cam["w"] == pytest.approx(0.192, abs=1e-3)


def test_facecam_cache_on_video_without_face(tmp_path):
    src = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=10",
                    "-t", "2", str(src)], check=True)
    cache = facecam.FacecamCache(tmp_path / "f.json")
    assert cache.get("someone", src) is None
    assert not (tmp_path / "f.json").exists()


def test_tiktok_browser_uses_library(monkeypatch, tmp_path):
    calls = {}

    class FakeUploader:
        def __init__(self, **kw):
            calls["init"] = kw

        def upload_video(self, filename, description="", visibility="everyone", **kw):
            calls["upload"] = (filename, description, visibility)
            return True

        def close(self):
            calls["closed"] = True

    pkg = types.ModuleType("tiktok_uploader")
    mod = types.ModuleType("tiktok_uploader.upload")
    mod.TikTokUploader = FakeUploader
    monkeypatch.setitem(sys.modules, "tiktok_uploader", pkg)
    monkeypatch.setitem(sys.modules, "tiktok_uploader.upload", mod)
    monkeypatch.setenv("TIKTOK_SESSIONID", "abc")
    tiktok_browser.close()

    cfg = _merge(DEFAULTS, {})
    meta = {"title": "Insane chase", "hashtags": ["GTA6", "Kai"]}
    rid = tiktok_browser.upload(tmp_path / "x.mp4", meta, cfg)
    assert rid == "browser:x"
    assert calls["init"]["sessionid"] == "abc" and calls["init"]["headless"] is True
    assert calls["upload"][1] == "Insane chase\n#GTA6 #Kai" and calls["upload"][2] == "everyone"
    tiktok_browser.close()
    assert calls["closed"]


def test_tiktok_browser_missing_session(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "tiktok_uploader", types.ModuleType("tiktok_uploader"))
    m = types.ModuleType("tiktok_uploader.upload")
    m.TikTokUploader = object
    monkeypatch.setitem(sys.modules, "tiktok_uploader.upload", m)
    monkeypatch.delenv("TIKTOK_SESSIONID", raising=False)
    monkeypatch.setenv("TIKTOK_COOKIES_FILE", str(tmp_path / "none.txt"))
    tiktok_browser.close()
    with pytest.raises(RuntimeError, match="oturumu yok"):
        tiktok_browser.upload(tmp_path / "x.mp4", {"title": "t", "hashtags": []}, _merge(DEFAULTS, {}))


def test_rank_with_ai_without_provider_keeps_order():
    c = [{"index": 0, "start": 1, "end": 31, "transcript": "a"}, {"index": 1, "start": 50, "end": 80, "transcript": ""}]
    assert highlights.rank_with_ai(c, _merge(DEFAULTS, {"ai": {"provider": "none"}})) == c
