# Viral Clip Generator

A small command-line tool that joins local MP4 clips and replaces their audio with
an MP3 background track.

It keeps a local `clip_usage.json` file and selects the least recently used clips
first. Usage is recorded only after a video is created successfully.

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- FFmpeg and FFprobe available on `PATH`

The input MP4 files must have compatible codecs, resolutions, frame rates, and
stream layouts. FFmpeg concatenates the source clips without re-encoding before it
creates the final H.264/AAC output.

## Setup

```bash
uv sync
```

Add source files to these directories:

- `clips/` for MP4 video clips
- `audio/` for MP3 background tracks

The directories already contain placeholder files so Git preserves them. Generated
videos are written to `output/` by default.

## Usage

```bash
# Use seven clips and a random audio track
uv run python main.py

# Select a different number of clips
uv run python main.py --num-clips 10

# Select exact clips and audio
uv run python main.py \
  --clips clip1.mp4 clip2.mp4 \
  --audio music.mp3 \
  --output output/compilation.mp4
```

Run `uv run python main.py --help` for all options.

When the requested clip count exceeds the available clips, the tool repeats clips.
A short audio track is looped to cover the full output, then faded out at the end.

## Development

```bash
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run pytest --cov=main --cov-report=term-missing --cov-fail-under=85
```

## Example

[View the example video](example.mp4)
