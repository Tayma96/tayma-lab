"""
YouTube Professional Channel Branding Asset Generator & Channel Configurator.
Generates Channel Avatar (800x800), Banner Art (2560x1440), and Channel Description & Branding Metadata.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont


CHANNEL_BRANDING = {
    "channel_name": "DEEP HORIZONS | Scientific Mysteries & Future Tech",
    "handle": "@DeepHorizonsOfficial",
    "description": "Deep Horizons explores the world's most captivating ancient mysteries, breakthrough science, space discoveries, and future artificial intelligence.\n\nSubscribe for weekly 4K high-retention cinematic documentaries.\n\nBusiness & Inquiries: contact@deephorizons.ai",
    "keywords": ["Deep Horizons", "Documentary", "Unsolved Mysteries", "Ancient History", "Future Tech", "Space Mysteries", "Science"],
}


def generate_channel_avatar(output_path: str) -> str:
    """
    Generates a 800x800 high-resolution glowing logo/avatar for the YouTube channel profile picture.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    size = 800
    img = Image.new("RGBA", (size, size), (10, 15, 30, 255))
    draw = ImageDraw.Draw(img)

    # Glowing radial rings
    for r in range(350, 50, -10):
        alpha_color = (int(20 + r / 3), int(100 + r / 2), int(220 - r / 4), 255)
        draw.ellipse([size // 2 - r, size // 2 - r, size // 2 + r, size // 2 + r], outline=alpha_color, width=3)

    # Monogram "DH" in center
    try:
        font = ImageFont.truetype("DejaVuSans-ExtraBold.ttf", 220)
    except Exception:
        font = ImageFont.load_default()

    # Draw shadow
    draw.text((size // 2 + 6, size // 2 + 6), "DH", font=font, fill=(0, 0, 0, 255), anchor="mm")
    # Draw glowing text
    draw.text((size // 2, size // 2), "DH", font=font, fill=(255, 215, 0, 255), anchor="mm")

    img.convert("RGB").save(output_path, quality=95)
    return output_path


def generate_channel_banner(output_path: str) -> str:
    """
    Generates 2560x1440 YouTube Banner Header Art optimized for TV, Desktop, and Mobile safe areas.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    w, h = 2560, 1440
    img = Image.new("RGBA", (w, h), (12, 18, 32, 255))
    draw = ImageDraw.Draw(img)

    # Draw space/cosmic particle overlay
    np.random.seed(42)
    for _ in range(300):
        px, py = int(np.random.randint(0, w)), int(np.random.randint(0, h))
        r = int(np.random.randint(1, 4))
        draw.ellipse([px, py, px + r, py + r], fill=(255, 255, 255, int(np.random.randint(100, 255))))

    # Safe banner area (Mobile & Desktop safe region: 1546x423 in center)
    safe_top = (h - 423) // 2
    safe_bottom = safe_top + 423

    # Gold accent lines
    draw.line([(0, safe_top), (w, safe_top)], fill=(255, 215, 0, 255), width=4)
    draw.line([(0, safe_bottom), (w, safe_bottom)], fill=(255, 215, 0, 255), width=4)

    try:
        font_title = ImageFont.truetype("DejaVuSans-ExtraBold.ttf", 90)
        font_sub = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Main Channel Title
    draw.text((w // 2, h // 2 - 30), "DEEP HORIZONS", font=font_title, fill=(255, 255, 255, 255), anchor="mm")
    draw.text((w // 2, h // 2 + 55), "ANCIENT MYSTERIES • FUTURE TECH • SCIENCE DOCUMENTARIES", font=font_sub, fill=(255, 215, 0, 255), anchor="mm")

    img.convert("RGB").save(output_path, quality=95)
    return output_path
