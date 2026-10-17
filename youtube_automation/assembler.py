"""
Video Assembler for 16:9 Long-Form Widescreen (1920x1080) YouTube Videos.
Combines visual clips, voiceover narrations, cinematic background music, subtitle captions, and transitions.
"""

import os
from typing import List, Dict, Any
import moviepy as mp
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from youtube_automation.audio_mixer import generate_ambient_soundtrack, mix_voice_and_soundtrack


def create_subtitle_clip(text: str, duration_sec: float, width: int = 1920, height: int = 1080) -> mp.ImageClip:
    """
    Renders clean centered cinematic subtitles for high viewer retention.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_size = 38
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > 55:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    lines = lines[:2]
    wrapped_text = "\n".join(lines)

    bar_y = height - 160
    draw.rectangle([100, bar_y, width - 100, height - 60], fill=(0, 0, 0, 160))
    draw.multiline_text((width // 2, height - 110), wrapped_text, font=font, fill=(255, 255, 255, 255), anchor="mm", align="center")

    np_img = np.array(img)
    return mp.ImageClip(np_img).with_duration(duration_sec)


def assemble_scene_clip(visual_path: str, audio_path: str, scene_data: Dict[str, Any], work_dir: str) -> mp.Clip:
    """
    Combines visual video clip and mixed audio narration track for a single scene.
    """
    voice_clip = mp.AudioFileClip(audio_path)
    audio_duration = voice_clip.duration
    voice_clip.close()

    # Create background music soundtrack for scene
    scene_num = scene_data.get("scene_number", 1)
    bg_music_file = os.path.join(work_dir, f"scene_{scene_num:02d}_bg_music.wav")
    mixed_audio_file = os.path.join(work_dir, f"scene_{scene_num:02d}_mixed_audio.wav")

    generate_ambient_soundtrack(audio_duration, bg_music_file)
    mix_voice_and_soundtrack(audio_path, bg_music_file, mixed_audio_file)

    mixed_audio_clip = mp.AudioFileClip(mixed_audio_file)
    video_clip = mp.VideoFileClip(visual_path)

    if video_clip.duration < audio_duration:
        num_loops = int(np.ceil(audio_duration / video_clip.duration))
        video_clip = mp.concatenate_videoclips([video_clip] * num_loops)

    video_clip = video_clip.subclipped(0, audio_duration)
    video_clip = video_clip.with_audio(mixed_audio_clip)

    sub_clip = create_subtitle_clip(scene_data["narration_text"], audio_duration)
    final_scene = mp.CompositeVideoClip([video_clip, sub_clip])

    return final_scene


def assemble_full_video(scene_clips_info: List[Dict[str, Any]], output_filepath: str, work_dir: str = "cikti/temp") -> str:
    """
    Assembles all processed scene clips sequentially into a full 16:9 widescreen video file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
    os.makedirs(work_dir, exist_ok=True)

    rendered_clips = []
    for info in scene_clips_info:
        clip = assemble_scene_clip(info["visual_path"], info["audio_path"], info["scene_data"], work_dir)
        rendered_clips.append(clip)

    final_video = mp.concatenate_videoclips(rendered_clips, method="compose")

    final_video.write_videofile(
        output_filepath,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        logger=None
    )

    for c in rendered_clips:
        c.close()
    final_video.close()

    return output_filepath
