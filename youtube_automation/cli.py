"""
YouTube Long-Form Automation Pipeline Orchestrator.
Main entry point for end-to-end 13-minute video production, thumbnail creation, channel branding, and YouTube publishing.
"""

import os
import argparse
from typing import Dict, Any

from youtube_automation.script_generator import generate_13min_script
from youtube_automation.voice_synth import synthesize_scene_narration
from youtube_automation.video_generator import generate_scene_video
from youtube_automation.assembler import assemble_full_video
from youtube_automation.thumbnail_generator import generate_professional_thumbnail
from youtube_automation.channel_branding import generate_channel_avatar, generate_channel_banner, CHANNEL_BRANDING
from youtube_automation.uploader import upload_to_youtube


def run_pipeline(output_dir: str = "cikti/youtube_videos", custom_title: str = None) -> Dict[str, Any]:
    """
    Runs full long-form video production pipeline:
    1. Generates 13-minute structured script with LTX-2.5 prompts and narration.
    2. Generates channel branding assets (Profile Avatar & Banner Art).
    3. Synthesizes high quality voiceover audio using edge-tts.
    4. Generates LTX-2.5 AI visual scenes (or procedural motion graphics fallback when limits are hit).
    5. Assembles full 16:9 1080p widescreen video with voice, visuals, and captions.
    6. Generates high-CTR custom thumbnail (1280x720).
    7. Uploads to YouTube via YouTube Data API v3 (or queues locally if OAuth is pending).
    """
    print("=====================================================")
    print(" 🚀 STARTING 13-MINUTE YOUTUBE VIDEO AUTOMATION")
    print("=====================================================")

    # 1. Script Generation
    print("[1/6] Generating ~13-minute high retention script...")
    script = generate_13min_script(title=custom_title)
    title = script["title"]
    print(f" -> Title: {title}")
    print(f" -> Total scenes: {script['total_scenes']}")

    work_dir = os.path.join(output_dir, "temp_render")
    os.makedirs(work_dir, exist_ok=True)

    # 2. Channel Branding Assets Generation
    print("\n[2/6] Generating professional channel branding assets...")
    avatar_path = generate_channel_avatar(os.path.join(output_dir, "branding", "channel_avatar.png"))
    banner_path = generate_channel_banner(os.path.join(output_dir, "branding", "channel_banner.png"))
    print(f" -> Channel Avatar: {avatar_path}")
    print(f" -> Channel Banner: {banner_path}")

    scene_clips_info = []

    # 3 & 4. Voice Synthesis & Visual Generation
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

    # 5. Assembly & Thumbnail Generation
    print("\n[5/6] Assembling full 16:9 widescreen long-form video & creating high-CTR thumbnail...")
    final_video_filename = "youtube_13min_video.mp4"
    final_video_path = os.path.join(output_dir, final_video_filename)
    assemble_full_video(scene_clips_info, final_video_path)

    thumbnail_path = os.path.join(output_dir, "thumbnail.jpg")
    first_scene_visual = scene_clips_info[0]["visual_path"] if scene_clips_info else None
    generate_professional_thumbnail(script["title"], thumbnail_path, bg_image_path=None)
    print(f" -> Final Video Rendered: {final_video_path}")
    print(f" -> Custom Thumbnail: {thumbnail_path}")

    # 6. YouTube Upload
    print("\n[6/6] Triggering YouTube Uploader with Custom Thumbnail...")
    upload_result = upload_to_youtube(
        video_path=final_video_path,
        thumbnail_path=thumbnail_path,
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
        "thumbnail_path": thumbnail_path,
        "branding": {
            "avatar": avatar_path,
            "banner": banner_path,
            "info": CHANNEL_BRANDING
        },
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
