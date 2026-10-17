# YouTube 13-Minute Long-Form Video Automation System

Automated high-retention 13-minute long-form video production and publishing pipeline for YouTube monetization, featuring LTX-2.5 AI visual scene generation with zero-downtime procedural fallbacks.

## Features

- **~13-Minute Script Generator (`youtube_automation/script_generator.py`)**: Creates structured, high-curiosity documentary scripts divided into 15 chapter scenes.
- **High-CPM Strategy Engine (`youtube_automation/strategy.py`)**: Optimizes video length for mid-roll ads, SEO tags, and Tier-1 audience targeting.
- **Unlimited Free Voiceover (`youtube_automation/voice_synth.py`)**: Uses `edge-tts` (Microsoft Edge Voice) for high-quality male/female documentary narrations.
- **LTX-2.5 Visual Generation & Procedural Fallback (`youtube_automation/video_generator.py`)**: Connects to `RioShiina/LTX-2.5` HuggingFace Space API. Seamlessly transitions to procedural motion graphic generation if AI quotas or rate limits are reached.
- **Widescreen 16:9 Assembly (`youtube_automation/assembler.py`)**: Combines 1080p visuals, voice track, and styled subtitles into a final video file using MoviePy.
- **High-CTR Custom Thumbnail Generator (`youtube_automation/thumbnail_generator.py`)**: Renders 1280x720 high-contrast thumbnails with bold typography and drop shadows.
- **Channel Branding Helper (`youtube_automation/channel_branding.py`)**: Generates 800x800 profile avatar and 2560x1440 YouTube banner art.
- **YouTube Data API v3 Uploader (`youtube_automation/uploader.py`)**: Automatically uploads generated long-form videos and attaches custom thumbnails to your YouTube channel.

## Quick Start

```bash
pip install -r requirements.txt
python -m youtube_automation.cli --out cikti/youtube_videolari/
```

## Running Tests

```bash
python -m pytest
```
