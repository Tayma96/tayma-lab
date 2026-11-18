"""Ücretsiz/bilgisayarsız çalışma: sezgisel analiz, GitHub Models, secrets, şifreli durum."""
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pytest
import requests

from gta6clips import analyze, llm, pipeline
from gta6clips.config import DEFAULTS, _merge, bootstrap_secrets
from gta6clips.db import DB
from gta6clips.metadata import ClipMeta

ROOT = Path(__file__).resolve().parent.parent


def cfg(**over):
    return _merge(DEFAULTS, over)


@pytest.fixture(autouse=True)
def reset_pause():
    llm._PAUSED_UNTIL.clear()
    yield
    llm._PAUSED_UNTIL.clear()


# --- sezgisel puan ---
def test_heuristic_rejects_static_screen():
    score, reason = analyze.heuristic_score({"motion": 0.002, "spike_db": 20, "wps": 3}, {"score": 1e5})
    assert score == 2 and "motion" in reason


def test_heuristic_rewards_strong_signals():
    strong = analyze.heuristic_score({"motion": 0.1, "spike_db": 18, "wps": 2.5},
                                     {"source": "live", "score": 40000})[0]
    weak = analyze.heuristic_score({"motion": 0.02, "spike_db": 3, "wps": 0.2}, {"score": 5})[0]
    assert strong == 10 and weak <= 5 < strong


def test_heuristic_trim_keeps_peak_late():
    loud = np.full(60, 40.0)
    loud[45] = 80.0
    s, e = analyze.heuristic_trim(loud, 60.0, target=30)
    assert e - s == pytest.approx(30) and s <= 45 < e and 45 - s >= 15
    assert analyze.heuristic_trim(loud[:30], 30.0) == (0.0, 30.0)  # kısa klip kırpılmaz


def test_heuristic_meta_uses_good_title_or_template():
    m = analyze.heuristic_meta("Kai", "he really jumped off the bridge", "c1")
    assert m["title"].startswith("he really jumped off the bridge") and "twitch.tv/kai" in m["description"]
    junk = analyze.heuristic_meta("Kai", "DAY 1 GTA 6 !discord !merch | drops on", "c2")
    assert "!discord" not in junk["title"] and "Kai" in junk["title"]
    assert junk["hook"] in analyze.HOOKS


def test_analyze_free_mode_on_real_video(tmp_path):
    src = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30",
                    "-f", "lavfi", "-i", "sine", "-t", "12", "-shortest", str(src)], check=True)
    a = analyze.analyze(src, 12, [], "Kai", "crazy chase", 10, cfg(ai={"provider": "none"}), clip_id="x",
                        signals={"score": 5000, "source": "top"})
    assert a["engine"] == "heuristic" and 1 <= a["score"] <= 10 and a["best_end"] == 12


# --- GitHub Models ---
class Resp:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body or {}, headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def test_github_models_success(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    seen = {}

    def post(url, **kw):
        seen.update(kw)
        content = json.dumps({"title": "x", "hook": "y", "description": "d", "hashtags": ["GTA6"]})
        return Resp(200, {"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr(llm.requests, "post", post)
    out = llm.structured(cfg(), "sys", "hi", ClipMeta, images=[b"a", b"b", b"c", b"d", b"e"])
    assert out.title == "x"
    parts = seen["json"]["messages"][1]["content"]
    assert sum(p["type"] == "image_url" for p in parts) == 4      # max_images
    assert seen["headers"]["Authorization"] == "Bearer t"


def test_github_models_rate_limit_pauses(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    calls = []
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: calls.append(1) or Resp(429, headers={"retry-after": "600"}))
    assert llm.structured(cfg(), "s", "t", ClipMeta) is None
    assert llm.structured(cfg(), "s", "t", ClipMeta) is None
    assert len(calls) == 1                                         # ikinci çağrı API'ye gitmez


def test_github_models_without_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_MODELS_TOKEN", raising=False)
    assert llm.structured(cfg(), "s", "t", ClipMeta) is None


def test_provider_none_never_calls(monkeypatch):
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: pytest.fail("çağrılmamalı"))
    assert llm.structured(cfg(ai={"provider": "none"}), "s", "t", ClipMeta) is None


# --- bilgisayarsız kurulum ---
def test_bootstrap_youtube_token(monkeypatch, tmp_path):
    f = tmp_path / "yt.json"
    monkeypatch.setenv("YOUTUBE_TOKEN_FILE", str(f))
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "cid")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "sec")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "rt")
    bootstrap_secrets()
    data = json.loads(f.read_text())
    assert data["refresh_token"] == "rt" and data["type"] == "authorized_user"
    refreshed = {**data, "token": "erisim", "expiry": "2099-01-01T00:00:00Z"}
    f.write_text(json.dumps(refreshed))
    bootstrap_secrets()                                            # aynı secret: yenilenmiş dosyayı ezmez
    assert json.loads(f.read_text()) == refreshed
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "rt2")             # secret güncellendi: yenisi yazılır
    bootstrap_secrets()
    assert json.loads(f.read_text())["refresh_token"] == "rt2"
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "sec2")            # yeni client secret de yansır
    bootstrap_secrets()
    assert json.loads(f.read_text())["client_secret"] == "sec2"


def test_platform_ready(monkeypatch, tmp_path):
    monkeypatch.setenv("YOUTUBE_TOKEN_FILE", str(tmp_path / "none.json"))
    monkeypatch.delenv("TIKTOK_SESSIONID", raising=False)
    monkeypatch.setenv("TIKTOK_COOKIES_FILE", str(tmp_path / "none.txt"))
    c = cfg()
    assert not pipeline.platform_ready(c, "youtube") and not pipeline.platform_ready(c, "tiktok")
    monkeypatch.setenv("TIKTOK_SESSIONID", "s")
    assert pipeline.platform_ready(c, "tiktok")


def test_recover_missing_videos(tmp_path):
    db = DB(tmp_path / "r.db")
    db.add_clip({"id": "a", "broadcaster": "x", "url": "u"})
    db.mark_rendered("a", str(tmp_path / "gone.mp4"), {"title": "t"})
    assert pipeline.recover_missing_videos(db) == 1
    assert db.conn.execute("SELECT status FROM clips").fetchone()[0] == "new"


def test_state_roundtrip_encrypted(tmp_path):
    env = {**os.environ, "STATE_KEY": "test-key-123"}
    (tmp_path / "data").mkdir()
    (tmp_path / "secrets").mkdir()
    DB(tmp_path / "data" / "clips.db").add_clip({"id": "a", "broadcaster": "x", "url": "u"})
    (tmp_path / "secrets" / "twitch_user_token.json").write_text('{"refresh_token": "SECRET123"}')
    subprocess.run(["bash", str(ROOT / "scripts/state.sh"), "pack"], cwd=tmp_path, env=env, check=True)
    assert b"SECRET123" not in (tmp_path / "state.enc").read_bytes()
    (tmp_path / "secrets" / "twitch_user_token.json").unlink()
    (tmp_path / "data" / "clips.db").unlink()
    subprocess.run(["bash", str(ROOT / "scripts/state.sh"), "unpack"], cwd=tmp_path, env=env, check=True)
    assert "SECRET123" in (tmp_path / "secrets" / "twitch_user_token.json").read_text()
    assert DB(tmp_path / "data" / "clips.db").conn.execute("SELECT id FROM clips").fetchone()[0] == "a"
    bad = subprocess.run(["bash", str(ROOT / "scripts/state.sh"), "unpack"], cwd=tmp_path,
                         env={**env, "STATE_KEY": "wrong"}, capture_output=True)
    assert bad.returncode != 0


def test_twitch_device_flow(monkeypatch, tmp_path):
    from gta6clips import twitch

    responses = iter([
        Resp(200, {"device_code": "dc", "user_code": "ABCD", "verification_uri": "https://twitch.tv/activate",
                   "expires_in": 600, "interval": 1}),
        Resp(400, {"message": "authorization_pending"}),
        Resp(200, {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}),
    ])

    class R(Resp):
        @property
        def text(self):
            return json.dumps(self._body)

    def post(url, **kw):
        r = next(responses)
        return R(r.status_code, r._body)

    monkeypatch.setattr(twitch.requests, "post", post)
    monkeypatch.setattr(twitch.time, "sleep", lambda s: None)
    u = twitch.TwitchUser("cid", "sec", tmp_path / "tok.json")
    u.authorize_device()
    assert json.loads((tmp_path / "tok.json").read_text())["refresh_token"] == "rt"


def test_workflows_are_valid_yaml():
    import yaml
    for f in (ROOT / ".github/workflows").glob("*.yml"):
        doc = yaml.safe_load(f.read_text())
        assert "jobs" in doc, f
    clips = yaml.safe_load((ROOT / ".github/workflows/clips.yml").read_text())
    assert clips["permissions"]["models"] == "read"


def test_run_forever_stops_at_deadline(monkeypatch, tmp_path):
    import time as _t
    calls = {"d": 0, "r": 0}
    monkeypatch.setattr(pipeline, "discover", lambda c, db: calls.__setitem__("d", calls["d"] + 1))
    monkeypatch.setattr(pipeline, "render_pending", lambda c, db, n=None: calls.__setitem__("r", calls["r"] + 1))
    c = cfg(paths={"data_dir": str(tmp_path)}, live={"enabled": False})
    t0 = _t.time()
    pipeline.run_forever(c, upload=False, live=False, max_minutes=0.05)
    assert _t.time() - t0 < 20 and calls["d"] >= 1 and calls["r"] >= 1


def test_check_reports_missing_secrets(monkeypatch, tmp_path):
    from gta6clips import check

    for n in ("TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET",
              "YOUTUBE_REFRESH_TOKEN", "TIKTOK_SESSIONID", "GITHUB_TOKEN", "GH_MODELS_TOKEN"):
        monkeypatch.delenv(n, raising=False)
    monkeypatch.setenv("TWITCH_USER_TOKEN_FILE", str(tmp_path / "yok.json"))
    results = {name: (ok, msg) for name, ok, msg in check.run_checks(cfg())}
    assert not results["Twitch API"][0]
    assert not results["Twitch girişi (canlı avcı)"][0]
    assert "YOUTUBE_REFRESH_TOKEN" in results["YouTube"][1]
    assert "TIKTOK_SESSIONID" in results["TikTok"][1]
    table = check.render(check.run_checks(cfg()))
    assert table.startswith("## Bağlantı kontrolü") and "❌" in table
