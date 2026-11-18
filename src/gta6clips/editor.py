"""ffmpeg ile 16:9 klibi 1080x1920 dikey videoya çevirir: bulanık arka plan / yüz kamerası düzeni,
altyazı, açılış kancası, kredi ve ses normalizasyonu."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe_duration(path: Path) -> float:
    res = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    return float(json.loads(res.stdout)["format"]["duration"])


LAYOUTS = ("fit", "landscape", "blur", "stack")


def canvas(layout: str | None) -> tuple[int, int]:
    return (1920, 1080) if layout == "landscape" else (1080, 1920)


def filter_graph(zoom: float = 1.0, facecam: dict | None = None, subs: str | None = None,
                 progress_duration: float | None = None, layout: str | None = None) -> str:
    """Saf fonksiyon: ffmpeg filter_complex metnini üretir. Çıkış etiketi [v].
    progress_duration verilirse altta soldan sağa dolan sarı ilerleme çubuğu eklenir
    (izleyiciye 'az kaldı' hissi verir, izlenme süresini artırır)."""
    z = max(1.0, float(zoom))
    layout = layout or ("stack" if facecam else "blur")
    W, H = canvas(layout)
    if layout == "landscape":
        # TikTok: yatay yüklenir, "tam ekran / yan çevir" düğmesi çıkar; yayının tamamı, kırpma yok
        graph = ("[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
                 "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[v0]")
    elif layout == "fit":
        # Twitch'in "Dolu" düzeni: dikey çerçevede yayının tamamı ortada, üst/alt siyah
        graph = ("[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                 "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[v0]")
    elif layout == "stack" and facecam:
        x, y, w, h = (float(facecam[k]) for k in ("x", "y", "w", "h"))
        graph = (
            f"[0:v]crop=iw*{w}:ih*{h}:iw*{x}:ih*{y},scale=1080:640:force_original_aspect_ratio=increase,"
            f"crop=1080:640,setsar=1[cam];"
            f"[0:v]crop=ih*0.84375/{z}:ih/{z},scale=1080:1280,setsar=1[game];"
            f"[cam][game]vstack=inputs=2[v0]"
        )
    else:
        graph = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            "boxblur=25:2,eq=brightness=-0.10,setsar=1[bg];"
            f"[0:v]crop=iw/{z}:ih/{z},scale=1080:-2,setsar=1[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[v0]"
        )
    if subs:
        graph += f";[v0]subtitles={subs}[v1]"
    else:
        graph += ";[v0]null[v1]"
    if progress_duration:
        d = max(0.1, float(progress_duration))
        graph += (f";color=c=0xFFD400:s={W}x12:r=30[bar];"
                  f"[v1][bar]overlay=x='-w+w*t/{d:.3f}':y=H-h:shortest=1[v]")
    else:
        graph += ";[v1]null[v]"
    return graph


def caption_y(facecam: dict | None, layout: str | None = None) -> int:
    if layout == "landscape":
        return 940
    if layout == "fit":
        return 1430  # yayın görüntüsü 656-1264 arası; altyazı hemen altında
    # Bulanık düzende oyun görüntüsü ~656-1264 arası; altyazı hemen altına.
    # Yüz kamerası düzeninde iki panelin birleştiği yerin biraz altına.
    return 820 if facecam else 1420


def render(src: Path, out: Path, *, ass_path: Path | None, zoom: float, facecam: dict | None,
           start: float | None = None, duration: float | None = None, progress: bool = False,
           layout: str | None = None) -> Path:
    # subtitles filtresi yol kaçışında sorun çıkarmasın diye ffmpeg'i .ass'in klasöründe çalıştırıyoruz
    cwd = ass_path.parent if ass_path else None
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if start is not None:
        cmd += ["-ss", f"{start:.2f}"]
    cmd += ["-i", str(src.resolve())]
    if duration is not None:
        cmd += ["-t", f"{duration:.2f}"]
    length = duration or (probe_duration(src) - (start or 0))
    # Kısa ses yumuşatma: kesim noktasında "tık" ya da yarım hece sesi duyulmasın
    fades = f"afade=t=in:st=0:d=0.12,afade=t=out:st={max(0.0, length - 0.3):.2f}:d=0.3,"
    cmd += [
        "-filter_complex", filter_graph(zoom, facecam, ass_path.name if ass_path else None,
                                        length if progress else None, layout),
        "-map", "[v]", "-map", "0:a?",
        "-af", fades + "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        str(out.resolve()),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg başarısız: {res.stderr.strip()[-1500:]}")
    return out
