"""
Unit tests for the YouTube Long-Form Automation module.
Tests script generator, high-CPM strategy engine, voice synthesizer, video generation & fallback, video assembler, and uploader.
"""

import os
import pytest
import shutil
from youtube_automation.script_generator import generate_13min_script
from youtube_automation.strategy import get_optimized_monetization_strategy
from youtube_automation.voice_synth import synthesize_scene_narration
from youtube_automation.video_generator import create_procedural_fallback_clip, generate_scene_video
from youtube_automation.assembler import assemble_scene_clip, assemble_full_video
from youtube_automation.uploader import upload_to_youtube
from youtube_automation.cli import run_pipeline


def test_strategy_engine():
    strat = get_optimized_monetization_strategy()
    assert strat["target_length_minutes"] == 13.0
    assert "target_audience" in strat
    assert "top_high_cpm_niches" in strat
    assert "AI_FUTURE_TECH" in strat["top_high_cpm_niches"]


def test_script_generator():
    script = generate_13min_script(title="Test Ancient Mystery Video")
    assert script["title"] == "Test Ancient Mystery Video"
    assert script["total_scenes"] == 15
    assert len(script["scenes"]) == 15
    assert script["target_total_duration_sec"] == 780
    assert "narration_text" in script["scenes"][0]
    assert "visual_prompt" in script["scenes"][0]


def test_voice_synth(tmp_path):
    scene = {
        "scene_number": 1,
        "narration_text": "This is a test narration for the YouTube video automation pipeline."
    }
    output_dir = str(tmp_path / "audio")
    audio_file = synthesize_scene_narration(scene, output_dir)
    assert os.path.exists(audio_file)
    assert os.path.getsize(audio_file) > 0


def test_video_fallback_generator(tmp_path):
    output_file = str(tmp_path / "test_fallback.mp4")
    res = create_procedural_fallback_clip("Cinematic space scene", duration_sec=2.0, output_filepath=output_file)
    assert os.path.exists(res)
    assert os.path.getsize(res) > 0


def test_generate_scene_video(tmp_path):
    output_dir = str(tmp_path / "video")
    # Will use procedural fallback if LTX-2.5 Space is offline/unreachable
    video_file = generate_scene_video("Cinematic ancient ruins", target_duration_sec=2.0, output_dir=output_dir, scene_num=1)
    assert os.path.exists(video_file)
    assert os.path.getsize(video_file) > 0


def test_video_assembler(tmp_path):
    work_dir = str(tmp_path / "work")
    scene = {
        "scene_number": 1,
        "narration_text": "Short narration test.",
        "visual_prompt": "Cinematic ruins",
        "target_duration_sec": 2.0
    }

    audio_path = synthesize_scene_narration(scene, work_dir)
    visual_path = generate_scene_video("Cinematic ruins", target_duration_sec=2.0, output_dir=work_dir, scene_num=1)

    out_video = str(tmp_path / "final.mp4")
    scene_clips_info = [{
        "scene_data": scene,
        "audio_path": audio_path,
        "visual_path": visual_path
    }]

    final_res = assemble_full_video(scene_clips_info, out_video)
    assert os.path.exists(final_res)
    assert os.path.getsize(final_res) > 0


def test_youtube_uploader_queue(tmp_path):
    video_file = str(tmp_path / "dummy_video.mp4")
    with open(video_file, "w") as f:
        f.write("dummy video content")

    metadata = {
        "title": "Test YouTube Video Title",
        "description": "Test description for YouTube video.",
        "tags": ["test", "automation"]
    }

    # Should save to queue since client_secret.json is not present in local test environment
    result = upload_to_youtube(video_file, metadata, client_secrets_file=str(tmp_path / "non_existent.json"))
    assert result["status"] == "QUEUED"
    assert "queue_file" in result
    assert os.path.exists(result["queue_file"])
