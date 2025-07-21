# Viral Clip Generator System

An AI-powered video processing tool that intelligently combines video clips with background audio to create unlimited compilation videos. Build a high-quality media library and generate viral content automatically.

## What it does

This system creates unlimited video content by:
- Intelligently selecting from your media library of high-quality clips
- Using AI-driven rotation algorithms to ensure fair usage across all clips
- Combining clips with background music to create engaging compilations
- Building a sustainable content generation pipeline for viral videos

Perfect for content creators, marketers, and anyone looking to generate unlimited video content from their media library.

## Setup

1. **Create and activate virtual environment:**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Create required folders and add your content:**
   - Create a `clips/` folder and add your video files (MP4 format)
   - Create an `audio/` folder and add background music files (MP3 format)
   - The tool will create an `output/` folder automatically

3. **Run the generator:**
   ```bash
   python main.py
   ```

## How it works

- **Smart Selection**: Uses rotation algorithms to prioritize least-used clips from your media library
- **Intelligent Combination**: Seamlessly joins selected clips in sequence
- **Audio Integration**: Adds background music with automatic volume balancing and fade effects
- **Automated Output**: Generates timestamped videos in the `output/` folder
- **Fair Usage Tracking**: Maintains statistics to ensure all clips get equal representation over time
- **Unlimited Generation**: Each run creates unique compilations, providing endless content possibilities

Build your media library once, generate unlimited viral content forever!