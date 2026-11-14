"""yt-dlp ile klip / VOD indirme."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _ytdlp(args: list[str]) -> None:
    cmd = [sys.executable, "-m", "yt_dlp", "--no-progress", "--no-warnings", *args]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"yt-dlp başarısız: {res.stderr.strip()[-800:]}")


def download_clip(url: str, out_dir: Path, name: str) -> Path:
    out = out_dir / f"{name}.mp4"
    if out.exists() and out.stat().st_size > 0:
        return out
    _ytdlp(["-f", "best[ext=mp4]/best", "--merge-output-format", "mp4", "-o", str(out), url])
    return out


def download_audio(url: str, out_dir: Path, name: str) -> Path:
    """Uzun VOD analizi için sadece sesi indirir (videodan çok daha küçük)."""
    out = out_dir / f"{name}.m4a"
    if not out.exists():
        _ytdlp(["-f", "bestaudio/best", "-x", "--audio-format", "m4a", "-o", str(out), url])
    return out


def download_section(url: str, out_dir: Path, name: str, start: float, end: float) -> Path:
    out = out_dir / f"{name}.mp4"
    if not out.exists():
        _ytdlp(["-f", "best[height<=1080]/best", "--download-sections", f"*{start:.1f}-{end:.1f}",
                "--force-keyframes-at-cuts", "--merge-output-format", "mp4", "-o", str(out), url])
    return out
