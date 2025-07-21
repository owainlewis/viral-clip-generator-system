# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based video processing tool called "felt-adventures" that intelligently combines video clips with background audio to create compilation videos. The project uses FFmpeg (via ffmpeg-python) for video processing and includes a sophisticated clip rotation system to ensure fair usage across all available clips.

## Architecture

The project follows a single-file architecture with JSON-based state management:

- **main.py**: Core video processing logic and clip selection algorithms
- **clip_usage.json**: Tracks usage statistics and rotation data for all video clips
- **clips/**: Directory containing source MP4 video files 
- **audio/**: Directory containing MP3 background music files
- **output/**: Directory for generated timestamped videos

### Key Components

- **combine_random_clips()** (main.py:53): Main orchestration function for video generation
- **select_clips_with_rotation()** (main.py:26): Intelligent clip selection prioritizing least-used clips
- **load_clip_usage()** (main.py:8) / **save_clip_usage()** (main.py:18): Persistent usage tracking system
- **Video Processing Pipeline**:
  1. Load usage statistics from JSON file
  2. Select clips using rotation algorithm (prioritizes least recently used)
  3. FFmpeg concatenation with temporary file list
  4. Audio mixing with fade-out effects and volume control
  5. Update and save usage statistics

## Common Commands

### Running the Application
```bash
python main.py
```

### Dependencies
The project requires Python 3.13+ with ffmpeg-python. Install dependencies using uv (recommended) or pip:
```bash
uv add ffmpeg-python
# or
pip install ffmpeg-python
```

### Project Structure Requirements
- Video clips must be placed in `clips/` directory (MP4 format only)
- Background audio must be placed in `audio/` directory (MP3 format only)  
- Output videos are generated in `output/` directory with timestamps
- `clip_usage.json` is automatically created and managed for rotation tracking

## Configuration

Key configuration variables in main.py (main:162-169):
- `VIDEO_FOLDER`: Source directory for video clips (default: "clips")
- `AUDIO_FOLDER`: Source directory for audio files (default: "audio") 
- `OUTPUT_FILE`: Timestamped filename pattern (default: "output/felt-adventures-{timestamp}.mp4")
- `NUM_CLIPS`: Number of clips to select (default: 7)

## Clip Rotation Algorithm

The system uses intelligent clip selection via `select_clips_with_rotation()` (main.py:26):
- Prioritizes clips with oldest `last_used` timestamps
- Secondary sort by `usage_count` (ascending)
- Automatically handles cases where `num_clips` exceeds available clips
- Updates usage statistics after each selection
- Persists state in `clip_usage.json` for cross-session tracking

## Audio Processing Features

Advanced audio processing in the pipeline (main.py:133-136):
- Volume reduction to 80% to balance with video audio
- Automatic fade-out effect (2 seconds or 10% of video duration)
- Audio trimmed to match exact video duration
- Uses AAC codec for output compatibility

## Development Notes

- Temporary files (`temp_concat_list.txt`, `temp_concatenated.mp4`) are automatically cleaned up
- FFmpeg operations run with `quiet=True` to minimize console output
- Uses absolute paths for FFmpeg concatenation to avoid path resolution issues
- Output directory is created automatically if it doesn't exist
- All file operations include proper error handling and validation