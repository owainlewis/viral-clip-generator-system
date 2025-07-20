# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based video processing tool called "felt-adventures" that randomly combines video clips with background audio to create compilation videos. The project uses FFmpeg (via python-ffmpeg) to handle video concatenation and audio mixing.

## Architecture

The project follows a simple single-file architecture:

- **main.py**: Contains the core video processing logic with `combine_random_clips()` function
- **clips/**: Directory containing source MP4 video files 
- **audio/**: Directory containing MP3 background music files
- **output/**: Directory for generated videos
- **images/**: Additional assets directory

### Key Components

- **combine_random_clips()** (main.py:6): Main function that randomly selects video clips, concatenates them, and adds background audio
- **Video Processing Pipeline**:
  1. Random selection of video clips from clips/ directory
  2. FFmpeg concatenation using temporary file list
  3. Audio mixing with background music
  4. Duration trimming to match video length

## Common Commands

### Running the Application
```bash
python main.py
```

### Dependencies
The project requires Python 3.13+ and uses ffmpeg-python. Install dependencies:
```bash
pip install ffmpeg-python
```

### Project Structure
- Video clips should be placed in `clips/` directory (MP4 format)
- Background audio should be placed in `audio/` directory (MP3 format)
- Output videos are generated in the project root by default

## Configuration

Key configuration variables in main.py:
- `VIDEO_FOLDER`: Source directory for video clips (default: "clips")
- `AUDIO_FOLDER`: Source directory for audio files (default: "audio") 
- `OUTPUT_FILE`: Name of generated video (default: "final_combined_video.mp4")
- `NUM_CLIPS`: Number of random clips to select (default: 5)

## Development Notes

- The application creates temporary files (`temp_concat_list.txt`, `temp_concatenated.mp4`) during processing which are automatically cleaned up
- FFmpeg operations run with `quiet=True` to minimize console output
- Error handling includes validation for minimum clip requirements and audio file availability
- Uses absolute paths for FFmpeg concatenation to avoid path resolution issues