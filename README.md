# Felt Adventures - Video Clip Generator

A Python tool that automatically creates compilation videos by combining multiple video clips with background music.

## What it does

This tool randomly selects video clips from your collection and joins them together with a single background audio track to create compilation videos. Perfect for creating highlight reels, montages, or compilation content.

## Setup

1. **Create and activate virtual environment:**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   uv pip install ffmpeg-python
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

- Randomly selects video clips from the `clips/` folder
- Joins them together in sequence
- Adds background music from the `audio/` folder
- Outputs a timestamped video file in the `output/` folder
- Uses a rotation system to ensure all clips get used fairly over time

That's it! Each run creates a unique compilation with different clips and music.