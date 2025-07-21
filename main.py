#!/usr/bin/env python3
"""
Viral Clip Generator System

An intelligent video processing tool that combines video clips with background audio
to create compilation videos using fair rotation algorithms.
"""

import argparse
import json
import random
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ffmpeg

# Configuration constants
DEFAULT_NUM_CLIPS = 7
DEFAULT_USAGE_FILE = "clip_usage.json"
SUPPORTED_VIDEO_EXTENSIONS = ('.mp4',)
SUPPORTED_AUDIO_EXTENSIONS = ('.mp3',)
AUDIO_VOLUME = 0.8
FADE_DURATION_SECONDS = 2.0
FADE_DURATION_PERCENTAGE = 0.1


class UsageTracker:
    """Handles clip usage tracking and rotation logic."""
    
    def __init__(self, usage_file: str = DEFAULT_USAGE_FILE):
        self.usage_file = Path(usage_file)
        self.usage_data = self._load_usage_data()
    
    def _load_usage_data(self) -> Dict[str, Dict[str, float]]:
        """Load clip usage tracking data from JSON file."""
        if not self.usage_file.exists():
            return {}
        
        try:
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    
    def save_usage_data(self) -> None:
        """Save clip usage tracking data to JSON file."""
        try:
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(self.usage_data, f, indent=2)
        except OSError as e:
            raise RuntimeError(f"Could not save clip usage data: {e}")
    
    def update_usage(self, clips: List[str]) -> None:
        """Update usage statistics for the given clips."""
        current_time = datetime.now().timestamp()
        
        for clip in clips:
            if clip not in self.usage_data:
                self.usage_data[clip] = {"last_used": 0, "usage_count": 0}
            
            self.usage_data[clip]["last_used"] = current_time
            self.usage_data[clip]["usage_count"] += 1
    
    def select_clips_with_rotation(self, available_clips: List[str], num_clips: int) -> List[str]:
        """Select clips prioritizing least recently used ones."""
        def sort_key(clip: str) -> Tuple[float, int]:
            clip_data = self.usage_data.get(clip, {"last_used": 0, "usage_count": 0})
            return (clip_data["last_used"], clip_data["usage_count"])
        
        sorted_clips = sorted(available_clips, key=sort_key)
        
        if len(sorted_clips) >= num_clips:
            return sorted_clips[:num_clips]
        else:
            # If we need more clips than available, repeat some randomly
            remaining_needed = num_clips - len(sorted_clips)
            repeated_clips = random.choices(sorted_clips, k=remaining_needed)
            return sorted_clips + repeated_clips


class MediaValidator:
    """Validates media files and directories."""
    
    @staticmethod
    def validate_directory(path: Path, name: str) -> None:
        """Validate that a directory exists."""
        if not path.exists():
            raise FileNotFoundError(f"{name} folder '{path}' does not exist")
        if not path.is_dir():
            raise NotADirectoryError(f"{name} path '{path}' is not a directory")
    
    @staticmethod
    def get_media_files(directory: Path, extensions: Tuple[str, ...]) -> List[str]:
        """Get all media files with specified extensions from directory."""
        files = [
            f.name for f in directory.iterdir()
            if f.is_file() and f.suffix.lower() in extensions
        ]
        
        if not files:
            ext_str = ', '.join(extensions)
            raise ValueError(f"No files with extensions {ext_str} found in {directory}")
        
        return files
    
    @staticmethod
    def validate_specific_files(files: List[str], available_files: List[str], directory: Path) -> None:
        """Validate that all specified files exist in the available files."""
        for file in files:
            if file not in available_files:
                raise FileNotFoundError(f"Specified file '{file}' not found in {directory}")


class VideoProcessor:
    """Handles video processing operations using FFmpeg."""
    
    def __init__(self, video_folder: Path, audio_folder: Path):
        self.video_folder = video_folder
        self.audio_folder = audio_folder
    
    def process_clips(
        self,
        selected_videos: List[str],
        selected_audio: str,
        output_file: Path
    ) -> None:
        """Process and combine video clips with audio."""
        video_paths = [self.video_folder / video for video in selected_videos]
        audio_path = self.audio_folder / selected_audio
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as concat_file:
            temp_concat_path = Path(concat_file.name)
            
            # Write concat file
            for video_path in video_paths:
                abs_path = video_path.resolve()
                concat_file.write(f"file '{abs_path}'\n")
        
        temp_video_path = Path(tempfile.mktemp(suffix='.mp4'))
        
        try:
            self._concatenate_videos(temp_concat_path, temp_video_path)
            video_duration = self._get_video_duration(temp_video_path)
            self._add_audio(temp_video_path, audio_path, output_file, video_duration)
            
            print(f"Successfully created: {output_file}")
            
        finally:
            # Clean up temporary files
            temp_concat_path.unlink(missing_ok=True)
            temp_video_path.unlink(missing_ok=True)
    
    def _concatenate_videos(self, concat_file: Path, output_file: Path) -> None:
        """Concatenate video clips using FFmpeg."""
        print("Concatenating video clips...")
        (
            ffmpeg
            .input(str(concat_file), format='concat', safe=0)
            .output(str(output_file), c='copy')
            .overwrite_output()
            .run(quiet=True)
        )
    
    def _get_video_duration(self, video_file: Path) -> float:
        """Get the duration of a video file."""
        probe = ffmpeg.probe(str(video_file))
        duration = float(probe['streams'][0]['duration'])
        print(f"Total video duration: {duration:.2f} seconds")
        return duration
    
    def _add_audio(
        self,
        video_file: Path,
        audio_file: Path,
        output_file: Path,
        video_duration: float
    ) -> None:
        """Add background audio to video with fade-out effect."""
        print("Adding background music...")
        
        video_input = ffmpeg.input(str(video_file))
        audio_input = ffmpeg.input(str(audio_file))
        
        # Calculate fade duration
        fade_duration = min(FADE_DURATION_SECONDS, video_duration * FADE_DURATION_PERCENTAGE)
        
        # Apply audio effects
        audio_with_volume = ffmpeg.filter(audio_input, 'volume', str(AUDIO_VOLUME))
        audio_with_fade = ffmpeg.filter(
            audio_with_volume,
            'afade',
            t='out',
            st=video_duration - fade_duration,
            d=fade_duration
        )
        
        # Combine video and audio
        (
            ffmpeg
            .output(
                video_input['v'],
                audio_with_fade,
                str(output_file),
                t=video_duration,
                vcodec='libx264',
                acodec='aac'
            )
            .overwrite_output()
            .run(quiet=True)
        )


class ViralClipGenerator:
    """Main class for generating viral clips."""
    
    def __init__(self, video_folder: str = "clips", audio_folder: str = "audio"):
        self.video_folder = Path(video_folder)
        self.audio_folder = Path(audio_folder)
        self.usage_tracker = UsageTracker()
        self.validator = MediaValidator()
        self.processor = VideoProcessor(self.video_folder, self.audio_folder)
    
    def generate(
        self,
        output_file: str,
        num_clips: int = DEFAULT_NUM_CLIPS,
        specific_clips: Optional[List[str]] = None,
        specific_audio: Optional[str] = None
    ) -> None:
        """Generate viral clips with specified parameters."""
        # Validate directories
        self.validator.validate_directory(self.video_folder, "Video")
        self.validator.validate_directory(self.audio_folder, "Audio")
        
        # Get available files
        video_files = self.validator.get_media_files(
            self.video_folder, SUPPORTED_VIDEO_EXTENSIONS
        )
        audio_files = self.validator.get_media_files(
            self.audio_folder, SUPPORTED_AUDIO_EXTENSIONS
        )
        
        # Select videos
        if specific_clips:
            self.validator.validate_specific_files(specific_clips, video_files, self.video_folder)
            selected_videos = specific_clips
        else:
            selected_videos = self.usage_tracker.select_clips_with_rotation(video_files, num_clips)
        
        # Select audio
        if specific_audio:
            self.validator.validate_specific_files([specific_audio], audio_files, self.audio_folder)
            selected_audio = specific_audio
        else:
            selected_audio = random.choice(audio_files)
        
        print(f"Selected videos: {selected_videos}")
        print(f"Selected audio: {selected_audio}")
        
        # Update usage tracking
        self.usage_tracker.update_usage(selected_videos)
        self.usage_tracker.save_usage_data()
        
        # Process videos
        self.processor.process_clips(selected_videos, selected_audio, Path(output_file))


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate viral clips by combining video clips with background audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Random selection (default)
  python main.py --clips clip1.mp4 clip2.mp4 --audio music.mp3
  python main.py --clips clip1.mp4 clip2.mp4  # Random audio
  python main.py --audio music.mp3        # Random clips with specific audio
  python main.py --num-clips 10           # Select 10 random clips
        """
    )
    
    parser.add_argument(
        '--clips',
        nargs='+',
        help='Specific video clips to use (filenames from clips/ folder)'
    )
    parser.add_argument(
        '--audio',
        help='Specific audio file to use (filename from audio/ folder)'
    )
    parser.add_argument(
        '--num-clips',
        type=int,
        default=DEFAULT_NUM_CLIPS,
        help=f'Number of random clips to select when not specifying --clips (default: {DEFAULT_NUM_CLIPS})'
    )
    parser.add_argument(
        '--output',
        help='Output filename (default: timestamped filename in output/ folder)'
    )
    
    return parser


def main() -> None:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Generate output filename if not specified
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
        output_file = f"output/viral-clip-{timestamp}.mp4"
    
    try:
        generator = ViralClipGenerator()
        generator.generate(
            output_file=output_file,
            num_clips=args.num_clips,
            specific_clips=args.clips,
            specific_audio=args.audio
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())