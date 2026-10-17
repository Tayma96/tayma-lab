"""
YouTube Automation Package Initialization.
"""

from youtube_automation.script_generator import generate_13min_script
from youtube_automation.voice_synth import synthesize_scene_narration
from youtube_automation.video_generator import generate_scene_video
from youtube_automation.assembler import assemble_full_video
from youtube_automation.audio_mixer import generate_ambient_soundtrack, mix_voice_and_soundtrack
from youtube_automation.thumbnail_generator import generate_professional_thumbnail
from youtube_automation.channel_branding import generate_channel_avatar, generate_channel_banner, CHANNEL_BRANDING
from youtube_automation.uploader import upload_to_youtube
from youtube_automation.cli import run_pipeline

__all__ = [
    "generate_13min_script",
    "synthesize_scene_narration",
    "generate_scene_video",
    "assemble_full_video",
    "generate_ambient_soundtrack",
    "mix_voice_and_soundtrack",
    "generate_professional_thumbnail",
    "generate_channel_avatar",
    "generate_channel_banner",
    "CHANNEL_BRANDING",
    "upload_to_youtube",
    "run_pipeline",
]
