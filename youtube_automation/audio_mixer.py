"""
Audio Sound FX & Ambient Background Music Mixer.
Synthesizes procedural tension soundscapes and mixes ambient soundtrack with voiceover for cinema-quality depth.
"""

import os
import wave
import struct
import math
import moviepy as mp


def generate_ambient_soundtrack(duration_sec: float, output_filepath: str) -> str:
    """
    Generates a dark cinematic ambient background music track with low-frequency atmospheric tones.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
    sample_rate = 44100
    num_samples = int(sample_rate * duration_sec)

    wav_file = wave.open(output_filepath, 'w')
    wav_file.setnchannels(1)  # Mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(sample_rate)

    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        # Low frequency binaural/drone tones for mystery & depth (55Hz, 110Hz)
        tone1 = 0.15 * math.sin(2 * math.pi * 55 * t)
        tone2 = 0.08 * math.sin(2 * math.pi * 110 * t + 0.3)
        swell = 0.5 + 0.5 * math.sin(2 * math.pi * 0.05 * t)

        val = int((tone1 + tone2) * swell * 0.2 * 32767)
        val = max(-32768, min(32767, val))
        frames.extend(struct.pack('<h', val))

    wav_file.writeframes(frames)
    wav_file.close()
    return output_filepath


def mix_voice_and_soundtrack(voice_audio_path: str, bg_music_path: str, output_filepath: str) -> str:
    """
    Mixes main voice narration with subtle ducked background music.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)

    voice_clip = mp.AudioFileClip(voice_audio_path)
    music_clip = mp.AudioFileClip(bg_music_path)

    if music_clip.duration < voice_clip.duration:
        num_loops = int(math.ceil(voice_clip.duration / music_clip.duration))
        music_clip = mp.concatenate_audioclips([music_clip] * num_loops)

    # Apply volume ducking on background music (0.12x volume)
    music_clip = music_clip.subclipped(0, voice_clip.duration)
    music_clip = music_clip.with_volume_scaled(0.12)

    final_audio = mp.CompositeAudioClip([voice_clip, music_clip])
    final_audio.write_audiofile(output_filepath, fps=44100, logger=None)

    voice_clip.close()
    music_clip.close()
    final_audio.close()

    return output_filepath
