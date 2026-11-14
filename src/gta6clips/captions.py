"""TikTok tarzı altyazı: 1-3 kelimelik gruplar, konuşulan kelime sarı vurgulu (ASS formatı)."""
from __future__ import annotations

from .transcribe import Word

W, H = 1080, 1920

HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,82,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1
Style: Hook,DejaVu Sans,88,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,3,18,0,5,60,60,0,1
Style: Credit,DejaVu Sans,42,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,2,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

HIGHLIGHT = r"{\c&H00FFFF&}"  # sarı (ASS renkleri BBGGRR)
RESET = r"{\c&HFFFFFF&}"


def ts(sec: float) -> str:
    sec = max(0.0, sec)
    cs = int(round(sec * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def group_words(words: list[Word], max_words: int = 3, max_gap: float = 0.6) -> list[list[Word]]:
    groups: list[list[Word]] = []
    for w in words:
        if groups and len(groups[-1]) < max_words and w.start - groups[-1][-1].end <= max_gap \
                and not groups[-1][-1].text.endswith((".", "!", "?")):
            groups[-1].append(w)
        else:
            groups.append([w])
    return groups


def caption_events(words: list[Word], y: int) -> list[str]:
    lines = []
    for group in group_words(words):
        for i, w in enumerate(group):
            end = group[i + 1].start if i + 1 < len(group) else w.end + 0.15
            parts = []
            for j, g in enumerate(group):
                t = escape(g.text.upper())
                parts.append(f"{HIGHLIGHT}{t}{RESET}" if j == i else t)
            text = rf"{{\pos({W // 2},{y})}}" + " ".join(parts)
            lines.append(f"Dialogue: 0,{ts(w.start)},{ts(end)},Caption,,0,0,0,,{text}")
    return lines


def build_ass(words: list[Word], duration: float, *, hook: str | None, credit: str | None,
              caption_y: int, hook_y: int = 330, credit_y: int = 1790, brand: str | None = None) -> str:
    events = []
    if brand:
        # Kanalın adı/logosu: sağ üstte küçük ve yarı saydam, tüm video boyunca
        events.append(f"Dialogue: 1,{ts(0)},{ts(duration)},Credit,,0,0,0,,"
                      rf"{{\an9\pos({W - 40},70)\alpha&H40&\fs38}}{escape(brand)}")
    if hook:
        # Açılış kancası ilk 3.5 saniye ekranda
        events.append(f"Dialogue: 1,{ts(0)},{ts(min(3.5, duration))},Hook,,0,0,0,,"
                      rf"{{\pos({W // 2},{hook_y})\fad(0,250)}}{escape(hook.upper())}")
    if credit:
        events.append(f"Dialogue: 1,{ts(0)},{ts(duration)},Credit,,0,0,0,,"
                      rf"{{\pos({W // 2},{credit_y})}}{escape(credit)}")
    events.extend(caption_events(words, caption_y))
    return HEADER + "\n".join(events) + "\n"
