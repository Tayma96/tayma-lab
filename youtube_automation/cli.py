"""
YouTube Long-Form Automation Pipeline Orchestrator.
Main entry point for end-to-end 13-minute video production and YouTube publishing.
"""

import os
import argparse
from typing import Dict, Any

from youtube_automation.script_generator import generate_13min_script
from youtube_automation.voice_synth import synthesize_scene_narration
from youtube_automation.video_generator import generate_scene_video
from youtube_automation.assembler import assemble_full_video
from youtube_automation.uploader import upload_to_youtube


def run_pipeline(output_dir: str = "cikti/youtube_videos", custom_title: str = None) -> Dict[str, Any]:
    """
    Runs full long-form video production pipeline:
    1. Generates 13-minute structured script with LTX-2.5 prompts and narration.
    2. Synthesizes high quality voiceover audio using edge-tts.
    3. Generates LTX-2.5 AI visual scenes (or procedural motion graphics fallback when limits are hit).
    4. Assembles full 16:9 1080p widescreen video with voice, visuals, and captions.
    5. Uploads to YouTube via YouTube Data API v3 (or queues locally if OAuth is pending).
    """
    print("=====================================================")
    print(" 🚀 STARTING 13-MINUTE YOUTUBE VIDEO AUTOMATION")
    print("=====================================================")

    # 1. Script Generation
    print("[1/5] Generating ~13-minute high retention script...")
    script = generate_13min_script(title=custom_title)
    title = script["title"]
    print(f" -> Title: {title}")
    print(f" -> Total scenes: {script['total_scenes']}")

    work_dir = os.path.join(output_dir, "temp_render")
    os.makedirs(work_dir, exist_ok=True)

    scene_clips_info = []

    # 2 & 3. Voice Synthesis & Visual Generation
    for idx, scene in enumerate(script["scenes"]):
        scene_num = scene["scene_number"]
        print(f"\n[Processing Scene {scene_num}/{script['total_scenes']}]")

        # Audio
        print(f" -> Generating voice narration...")
        audio_path = synthesize_scene_narration(scene, work_dir)

        # Video (LTX-2.5 + Fallback)
        print(f" -> Generating video visual (LTX-2.5 / Fallback)...")
        visual_path = generate_scene_video(
            prompt=scene["visual_prompt"],
            target_duration_sec=scene["target_duration_sec"],
            output_dir=work_dir,
            scene_num=scene_num
        )

        scene_clips_info.append({
            "scene_data": scene,
            "audio_path": audio_path,
            "visual_path": visual_path
        })

    # 4. Assembly
    print("\n[4/5] Assembling full 16:9 widescreen long-form video...")
    final_video_filename = "youtube_13min_video.mp4"
    final_video_path = os.path.join(output_dir, final_video_filename)
    assemble_full_video(scene_clips_info, final_video_path)
    print(f" -> Final Video Rendered: {final_video_path}")

    # 5. YouTube Upload
    print("\n[5/5] Triggering YouTube Uploader...")
    upload_result = upload_to_youtube(
        video_path=final_video_path,
        metadata={
            "title": script["title"],
            "description": script["description"],
            "tags": script["tags"]
        }
    )
    print(f" -> Upload Result: {upload_result['status']}")

    return {
        "title": script["title"],
        "video_path": final_video_path,
        "upload_result": upload_result
    }


def main():
    parser = argparse.ArgumentParser(description="YouTube 13-Minute Long-Form Automation System")
    parser.add_argument("--out", type=str, default="cikti/youtube_videos", help="Directory to save generated video")
    parser.add_argument("--title", type=str, default=None, help="Optional video title topic")
    args = parser.parse_args()

    run_pipeline(output_dir=args.out, custom_title=args.title)


if __name__ == "__main__":
    main()
