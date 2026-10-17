"""
Voice Synthesizer using edge-tts (Microsoft Edge Voice - 100% Free, Unlimited, High-Quality).
"""

import asyncio
import os
import edge_tts
from typing import Dict, Any


DEFAULT_VOICE = "en-US-ChristopherNeural"  # Deep cinematic male documentary narrator voice


async def synthesize_speech_async(text: str, output_filepath: str, voice: str = DEFAULT_VOICE) -> str:
    """
    Synthesizes speech to an MP3 audio file using edge-tts.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_filepath)
    return output_filepath


def synthesize_scene_narration(scene_data: Dict[str, Any], output_dir: str, voice: str = DEFAULT_VOICE) -> str:
    """
    Synchronous wrapper for generating narration audio for a given scene.
    """
    scene_num = scene_data.get("scene_number", 1)
    filename = f"scene_{scene_num:02d}_narration.mp3"
    filepath = os.path.join(output_dir, filename)

    text = scene_data["narration_text"]
    asyncio.run(synthesize_speech_async(text, filepath, voice=voice))
    return filepath
