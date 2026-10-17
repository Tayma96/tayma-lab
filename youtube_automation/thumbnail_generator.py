"""
Professional High-CTR YouTube Thumbnail Generator (1280x720).
Generates eye-catching, high-contrast thumbnails with bold typography, glowing borders, and dramatic visual overlays.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter


def generate_professional_thumbnail(title: str, output_filepath: str, bg_image_path: str = None) -> str:
    """
    Renders a 1280x720 high-CTR YouTube custom thumbnail with:
    - Cinematic background
    - Vignette & dark gradient overlay for text readability
    - Big bold yellow/white text with heavy drop shadows
    - Glowing badge / border highlights
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
    width, height = 1280, 720

    # 1. Background image or dynamic gradient
    if bg_image_path and os.path.exists(bg_image_path):
        bg = Image.open(bg_image_path).convert("RGB")
        bg = bg.resize((width, height), Image.Resampling.LANCZOS)
        # Increase contrast and saturation for thumbnail pop
        bg = ImageEnhance.Contrast(bg).enhance(1.25)
        bg = ImageEnhance.Color(bg).enhance(1.3)
    else:
        # Create atmospheric dark cinematic gradient background
        bg_array = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                r = int(15 + 40 * (y / height))
                g = int(20 + 30 * (x / width))
                b = int(50 + 60 * (1 - y / height))
                bg_array[y, x] = [r, g, b]
        bg = Image.fromarray(bg_array)

    # 2. Add dark vignette overlay on left half for crisp text contrast
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Left dark side gradient
    for x in range(int(width * 0.75)):
        alpha = int(220 * (1.0 - (x / (width * 0.75))))
        draw_overlay.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))

    bg = Image.alpha_composite(bg.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(bg)

    # 3. Add glowing badge / border
    draw.rectangle([15, 15, width - 15, height - 15], outline=(255, 215, 0, 200), width=6)

    # 4. Render Big Bold Typography
    try:
        font_main = ImageFont.truetype("DejaVuSans-ExtraBold.ttf", 64)
        font_sub = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
    except Exception:
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Clean title for thumbnail (short & punchy 3-5 words)
    words = title.upper().split()
    short_title = " ".join(words[:4]) if len(words) > 4 else " ".join(words)

    # Wrap title into max 2-3 lines
    lines = []
    curr_line = []
    for w in words[:6]:
        curr_line.append(w)
        if len(" ".join(curr_line)) > 14:
            lines.append(" ".join(curr_line[:-1]))
            curr_line = [w]
    if curr_line:
        lines.append(" ".join(curr_line))

    start_y = 180
    for line in lines[:3]:
        # Heavy black shadow for 3D effect
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                draw.text((60 + dx, start_y + dy), line, font=font_main, fill=(0, 0, 0, 255))

        # Yellow / Gold text fill for high visibility
        draw.text((60, start_y), line, font=font_main, fill=(255, 223, 0, 255))
        start_y += 85

    # 5. Add "4K DOCUMENTARY" high-value badge
    draw.rectangle([60, height - 110, 360, height - 50], fill=(220, 20, 60, 230), outline=(255, 255, 255, 255), width=2)
    draw.text((80, height - 98), "4K DOCUMENTARY", font=font_sub, fill=(255, 255, 255, 255))

    # Convert back to RGB and save
    final_thumbnail = bg.convert("RGB")
    final_thumbnail.save(output_filepath, quality=95)
    return output_filepath
