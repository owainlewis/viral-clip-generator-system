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
   source .venv/bin/activate
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

## Usage

The tool supports both random selection (default) and specific clip/audio selection:

### Random Selection (Original Behavior)
```bash
python main.py                    # Randomly selects 7 clips and random audio
python main.py --num-clips 10     # Randomly selects 10 clips and random audio
```

### Specific Selection
```bash
# Use specific clips with random audio
python main.py --clips clip1.mp4 clip2.mp4 clip3.mp4

# Use random clips with specific audio
python main.py --audio background-music.mp3

# Full control over clips and audio
python main.py --clips clip1.mp4 clip2.mp4 --audio music.mp3

# Custom output filename
python main.py --output my-compilation.mp4
```

### CLI Options
- `--clips` - Specify exact video clips to use (filenames from clips/ folder)
- `--audio` - Specify exact audio file to use (filename from audio/ folder)  
- `--num-clips` - Number of random clips to select when not using --clips (default: 7)
- `--output` - Custom output filename (default: timestamped filename in output/ folder)

### Examples
```bash
python main.py --help                                    # Show help
python main.py                                          # Default: 7 random clips + random audio
python main.py --clips funny1.mp4 funny2.mp4            # Specific clips, random audio
python main.py --audio upbeat-song.mp3 --num-clips 5    # 5 random clips, specific audio
python main.py --clips a.mp4 b.mp4 --audio song.mp3 --output compilation.mp4
```

## How it works

- **Smart Selection**: Uses rotation algorithms to prioritize least-used clips from your media library
- **Intelligent Combination**: Seamlessly joins selected clips in sequence
- **Audio Integration**: Adds background music with automatic volume balancing and fade effects
- **Automated Output**: Generates timestamped videos in the `output/` folder
- **Fair Usage Tracking**: Maintains statistics to ensure all clips get equal representation over time
- **Unlimited Generation**: Each run creates unique compilations, providing endless content possibilities

Build your media library once, generate unlimited viral content forever!

## Example Output

![Example Output](example.gif)
