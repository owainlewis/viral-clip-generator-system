import os
import random
import ffmpeg
import json
from pathlib import Path
from datetime import datetime

def load_clip_usage(usage_file="clip_usage.json"):
    """Load clip usage tracking data from JSON file."""
    if os.path.exists(usage_file):
        try:
            with open(usage_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_clip_usage(usage_data, usage_file="clip_usage.json"):
    """Save clip usage tracking data to JSON file."""
    try:
        with open(usage_file, 'w') as f:
            json.dump(usage_data, f, indent=2)
    except IOError:
        print("Warning: Could not save clip usage data")

def select_clips_with_rotation(video_files, num_clips, usage_data):
    """Select clips prioritizing least recently used ones."""
    current_time = datetime.now().timestamp()
    
    # Sort clips by last used time (oldest first), then by usage count
    def sort_key(clip):
        clip_data = usage_data.get(clip, {"last_used": 0, "usage_count": 0})
        return (clip_data["last_used"], clip_data["usage_count"])
    
    sorted_clips = sorted(video_files, key=sort_key)
    
    # If we have enough clips, take from the least used
    if len(sorted_clips) >= num_clips:
        selected = sorted_clips[:num_clips]
    else:
        # If we need more clips than available, take all and repeat some
        selected = sorted_clips + random.sample(sorted_clips, num_clips - len(sorted_clips))
    
    # Update usage data for selected clips
    for clip in selected:
        if clip not in usage_data:
            usage_data[clip] = {"last_used": 0, "usage_count": 0}
        usage_data[clip]["last_used"] = current_time
        usage_data[clip]["usage_count"] += 1
    
    return selected, usage_data

def combine_random_clips(video_folder, audio_folder, output_file="output.mp4", num_clips=5):
    """
    Intelligently select video clips using rotation algorithm and combine with audio.
    
    Args:
        video_folder: Path to folder containing MP4 video clips
        audio_folder: Path to folder containing MP3 audio files
        output_file: Name of the output video file
        num_clips: Number of video clips to select (default: 5)
    """
    
    # Check if directories exist
    if not os.path.exists(video_folder):
        raise ValueError(f"Video folder '{video_folder}' does not exist")
    if not os.path.exists(audio_folder):
        raise ValueError(f"Audio folder '{audio_folder}' does not exist")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Get all video and audio files
    video_files = [f for f in os.listdir(video_folder) if f.lower().endswith('.mp4')]
    audio_files = [f for f in os.listdir(audio_folder) if f.lower().endswith('.mp3')]
    
    if len(video_files) == 0:
        raise ValueError("No video files found in the clips folder")
    
    if len(audio_files) == 0:
        raise ValueError("No audio files found")
    
    # Load clip usage data and select clips with rotation
    usage_data = load_clip_usage()
    selected_videos, updated_usage = select_clips_with_rotation(video_files, num_clips, usage_data)
    selected_audio = random.choice(audio_files)
    
    print(f"Selected videos: {selected_videos}")
    print(f"Selected audio: {selected_audio}")
    
    # Save updated usage data
    save_clip_usage(updated_usage)
    
    # Create full paths
    video_paths = [os.path.join(video_folder, video) for video in selected_videos]
    audio_path = os.path.join(audio_folder, selected_audio)
    
    # Step 1: Concatenate video clips
    print("Concatenating video clips...")
    
    # Create temporary file list for ffmpeg concat
    concat_file = "temp_concat_list.txt"
    with open(concat_file, 'w') as f:
        for video_path in video_paths:
            # Use absolute path and escape single quotes
            abs_path = os.path.abspath(video_path)
            f.write(f"file '{abs_path}'\n")
    
    try:
        # Concatenate videos first
        temp_video = "temp_concatenated.mp4"
        (
            ffmpeg
            .input(concat_file, format='concat', safe=0)
            .output(temp_video, c='copy')
            .overwrite_output()
            .run(quiet=True)
        )
        
        # Get duration of concatenated video
        probe = ffmpeg.probe(temp_video)
        video_duration = float(probe['streams'][0]['duration'])
        print(f"Total video duration: {video_duration:.2f} seconds")
        
        # Step 2: Combine with audio (trim audio to video length)
        print("Adding background music...")
        
        video_input = ffmpeg.input(temp_video)
        audio_input = ffmpeg.input(audio_path)
        
        # Add background music with fade-out (last 2 seconds) and reduce volume to 80%
        fade_duration = min(2.0, video_duration * 0.1)  # fade for 2 seconds or 10% of video, whichever is shorter
        audio_with_volume = ffmpeg.filter(audio_input, 'volume', '0.8')
        audio_with_fade = ffmpeg.filter(audio_with_volume, 'afade', t='out', st=video_duration-fade_duration, d=fade_duration)
        
        (
            ffmpeg
            .output(
                video_input['v'],  # video stream
                audio_with_fade,   # background audio with fade-out
                output_file,
                t=video_duration,  # trim to video duration
                vcodec='libx264',  # video codec
                acodec='aac'       # audio codec
            )
            .overwrite_output()
            .run(quiet=True)
        )
        
        print(f"Successfully created: {output_file}")
        
    finally:
        # Clean up temporary files
        if os.path.exists(concat_file):
            os.remove(concat_file)
        if os.path.exists(temp_video):
            os.remove(temp_video)

def main():
    # Configuration - update these paths
    VIDEO_FOLDER = "clips"  
    AUDIO_FOLDER = "audio" 
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    OUTPUT_FILE = f"output/viral-clip-{timestamp}.mp4"
    NUM_CLIPS = 7
    
    try:
        combine_random_clips(VIDEO_FOLDER, AUDIO_FOLDER, OUTPUT_FILE, NUM_CLIPS)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
