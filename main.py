#!/usr/bin/env python3
"""Build a compilation video from local clips and background audio."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import ffmpeg

DEFAULT_NUM_CLIPS = 7
DEFAULT_USAGE_FILE = "clip_usage.json"
SUPPORTED_VIDEO_EXTENSIONS = (".mp4",)
SUPPORTED_AUDIO_EXTENSIONS = (".mp3",)
AUDIO_VOLUME = 0.8
FADE_DURATION_SECONDS = 2.0
FADE_DURATION_PERCENTAGE = 0.1


class UsageRecord(TypedDict):
    """Persisted usage data for one clip."""

    last_used: float
    usage_count: int


class UsageTracker:
    """Persist clip usage and select the least recently used clips first."""

    def __init__(
        self,
        usage_file: str | Path = DEFAULT_USAGE_FILE,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.usage_file = Path(usage_file)
        self._clock = clock
        self.usage_data = self._load_usage_data()

    def _load_usage_data(self) -> dict[str, UsageRecord]:
        if not self.usage_file.exists():
            return {}

        try:
            raw_data = json.loads(self.usage_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(
                f"Could not read clip usage data from '{self.usage_file}': {exc}"
            ) from exc

        if not isinstance(raw_data, dict):
            raise RuntimeError(
                f"Clip usage data in '{self.usage_file}' must be an object"
            )

        usage_data: dict[str, UsageRecord] = {}
        for clip, record in raw_data.items():
            if not isinstance(clip, str) or not isinstance(record, dict):
                raise RuntimeError(f"Invalid clip usage entry in '{self.usage_file}'")

            last_used = record.get("last_used")
            usage_count = record.get("usage_count")
            valid_last_used = (
                isinstance(last_used, (int, float))
                and not isinstance(last_used, bool)
                and math.isfinite(last_used)
                and last_used >= 0
            )
            valid_usage_count = (
                isinstance(usage_count, int)
                and not isinstance(usage_count, bool)
                and usage_count >= 0
            )
            if not valid_last_used or not valid_usage_count:
                raise RuntimeError(
                    f"Invalid usage values for clip '{clip}' in '{self.usage_file}'"
                )

            usage_data[clip] = {
                "last_used": float(last_used),
                "usage_count": usage_count,
            }

        return usage_data

    def save_usage_data(self) -> None:
        """Atomically save usage data so interruption cannot corrupt the file."""
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.usage_file.parent,
                prefix=f".{self.usage_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(self.usage_data, temporary_file, indent=2, sort_keys=True)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_path, self.usage_file)
        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise RuntimeError(f"Could not save clip usage data: {exc}") from exc

    def update_usage(self, clips: Sequence[str]) -> None:
        current_time = self._clock()

        for clip in clips:
            record = self.usage_data.setdefault(
                clip, {"last_used": 0.0, "usage_count": 0}
            )
            record["last_used"] = current_time
            record["usage_count"] += 1

    def select_clips_with_rotation(
        self, available_clips: Sequence[str], num_clips: int
    ) -> list[str]:
        if num_clips < 1:
            raise ValueError("Number of clips must be at least 1")
        if not available_clips:
            raise ValueError("No video clips are available")

        def sort_key(clip: str) -> tuple[float, int, str]:
            record = self.usage_data.get(clip, {"last_used": 0.0, "usage_count": 0})
            return (record["last_used"], record["usage_count"], clip.casefold())

        sorted_clips = sorted(available_clips, key=sort_key)
        if len(sorted_clips) >= num_clips:
            return sorted_clips[:num_clips]

        remaining = num_clips - len(sorted_clips)
        return sorted_clips + random.choices(sorted_clips, k=remaining)


class MediaValidator:
    """Validate input directories and list supported media files."""

    @staticmethod
    def validate_directory(path: Path, name: str) -> None:
        if not path.exists():
            raise FileNotFoundError(f"{name} folder '{path}' does not exist")
        if not path.is_dir():
            raise NotADirectoryError(f"{name} path '{path}' is not a directory")

    @staticmethod
    def get_media_files(directory: Path, extensions: tuple[str, ...]) -> list[str]:
        files: list[str] = []
        for path in directory.iterdir():
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            if "\r" in path.name or "\n" in path.name:
                raise ValueError(
                    f"Media filename cannot contain line breaks: {path.name!r}"
                )
            files.append(path.name)

        files.sort(key=str.casefold)
        if not files:
            extension_list = ", ".join(extensions)
            raise ValueError(
                f"No files with extensions {extension_list} found in {directory}"
            )
        return files

    @staticmethod
    def validate_specific_files(
        files: Sequence[str], available_files: Sequence[str], directory: Path
    ) -> None:
        available = set(available_files)
        missing = [file for file in files if file not in available]
        if missing:
            raise FileNotFoundError(
                f"Specified file '{missing[0]}' not found in {directory}"
            )


class VideoProcessor:
    """Combine clips and replace their audio with a background track."""

    def __init__(self, video_folder: Path, audio_folder: Path) -> None:
        self.video_folder = video_folder
        self.audio_folder = audio_folder

    def process_clips(
        self,
        selected_videos: Sequence[str],
        selected_audio: str,
        output_file: Path,
    ) -> None:
        video_paths = [self.video_folder / video for video in selected_videos]
        audio_path = self.audio_folder / selected_audio
        if output_file.suffix.lower() != ".mp4":
            raise ValueError("Output file must use the .mp4 extension")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(
            prefix=".viral-clip-", dir=output_file.parent
        ) as temporary_directory:
            temporary_path = Path(temporary_directory)
            concat_path = temporary_path / "clips.txt"
            concatenated_video_path = temporary_path / "concatenated.mp4"
            temporary_output_path = temporary_path / f"result{output_file.suffix}"
            concat_path.write_text(
                "".join(
                    f"file '{self._escape_concat_path(path.resolve())}'\n"
                    for path in video_paths
                ),
                encoding="utf-8",
            )

            self._concatenate_videos(concat_path, concatenated_video_path)
            video_duration = self._get_video_duration(concatenated_video_path)
            self._add_audio(
                concatenated_video_path,
                audio_path,
                temporary_output_path,
                video_duration,
            )
            os.replace(temporary_output_path, output_file)

        print(f"Successfully created: {output_file}")

    @staticmethod
    def _escape_concat_path(path: Path) -> str:
        """Escape a path for FFmpeg's single-quoted concat file syntax."""
        return str(path).replace("'", "'\\''")

    def _concatenate_videos(self, concat_file: Path, output_file: Path) -> None:
        print("Concatenating video clips...")
        (
            ffmpeg.input(str(concat_file), format="concat", safe=0)
            .output(str(output_file), c="copy")
            .overwrite_output()
            .run(quiet=True)
        )

    def _get_video_duration(self, video_file: Path) -> float:
        probe = ffmpeg.probe(str(video_file))
        candidates = [probe.get("format", {}).get("duration")]
        candidates.extend(
            stream.get("duration")
            for stream in probe.get("streams", [])
            if stream.get("codec_type") == "video"
        )

        for candidate in candidates:
            if candidate is None:
                continue
            try:
                duration = float(candidate)
            except (TypeError, ValueError):
                continue
            if math.isfinite(duration) and duration > 0:
                print(f"Total video duration: {duration:.2f} seconds")
                return duration

        raise RuntimeError(f"Could not determine video duration for '{video_file}'")

    def _add_audio(
        self,
        video_file: Path,
        audio_file: Path,
        output_file: Path,
        video_duration: float,
    ) -> None:
        print("Adding background music...")
        video_input = ffmpeg.input(str(video_file))
        audio_input = ffmpeg.input(str(audio_file), stream_loop=-1)
        fade_duration = min(
            FADE_DURATION_SECONDS, video_duration * FADE_DURATION_PERCENTAGE
        )
        audio_with_volume = ffmpeg.filter(audio_input, "volume", AUDIO_VOLUME)
        audio_with_fade = ffmpeg.filter(
            audio_with_volume,
            "afade",
            t="out",
            st=video_duration - fade_duration,
            d=fade_duration,
        )

        (
            ffmpeg.output(
                video_input["v"],
                audio_with_fade,
                str(output_file),
                t=video_duration,
                vcodec="libx264",
                acodec="aac",
                pix_fmt="yuv420p",
                movflags="+faststart",
            )
            .overwrite_output()
            .run(quiet=True)
        )


class ViralClipGenerator:
    """Select media, produce an output video, and record successful usage."""

    def __init__(
        self,
        video_folder: str | Path = "clips",
        audio_folder: str | Path = "audio",
        usage_file: str | Path = DEFAULT_USAGE_FILE,
    ) -> None:
        self.video_folder = Path(video_folder)
        self.audio_folder = Path(audio_folder)
        self.usage_tracker = UsageTracker(usage_file)
        self.validator = MediaValidator()
        self.processor = VideoProcessor(self.video_folder, self.audio_folder)

    def generate(
        self,
        output_file: str | Path,
        num_clips: int = DEFAULT_NUM_CLIPS,
        specific_clips: Sequence[str] | None = None,
        specific_audio: str | None = None,
    ) -> Path:
        self.validator.validate_directory(self.video_folder, "Video")
        self.validator.validate_directory(self.audio_folder, "Audio")

        video_files = self.validator.get_media_files(
            self.video_folder, SUPPORTED_VIDEO_EXTENSIONS
        )
        audio_files = self.validator.get_media_files(
            self.audio_folder, SUPPORTED_AUDIO_EXTENSIONS
        )

        if specific_clips:
            self.validator.validate_specific_files(
                specific_clips, video_files, self.video_folder
            )
            selected_videos = list(specific_clips)
        else:
            selected_videos = self.usage_tracker.select_clips_with_rotation(
                video_files, num_clips
            )

        if specific_audio:
            self.validator.validate_specific_files(
                [specific_audio], audio_files, self.audio_folder
            )
            selected_audio = specific_audio
        else:
            selected_audio = random.choice(audio_files)

        print(f"Selected videos: {selected_videos}")
        print(f"Selected audio: {selected_audio}")

        output_path = Path(output_file)
        self.processor.process_clips(selected_videos, selected_audio, output_path)
        self.usage_tracker.update_usage(selected_videos)
        self.usage_tracker.save_usage_data()
        return output_path


def positive_int(value: str) -> int:
    """Parse a positive integer for argparse."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Combine video clips with background audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python main.py
  python main.py --clips clip1.mp4 clip2.mp4 --audio music.mp3
  python main.py --audio music.mp3 --num-clips 10
""",
    )
    parser.add_argument(
        "--clips",
        nargs="+",
        help="Specific video clips to use (filenames from clips/)",
    )
    parser.add_argument(
        "--audio", help="Specific audio file to use (filename from audio/)"
    )
    parser.add_argument(
        "--num-clips",
        type=positive_int,
        default=DEFAULT_NUM_CLIPS,
        help=(
            "Number of clips to select when --clips is omitted "
            f"(default: {DEFAULT_NUM_CLIPS})"
        ),
    )
    parser.add_argument(
        "--output",
        help="Output filename (default: timestamped MP4 in output/)",
    )
    return parser


def describe_error(error: Exception) -> str:
    """Return useful FFmpeg stderr instead of its generic exception message."""
    if isinstance(error, ffmpeg.Error) and error.stderr:
        stderr = error.stderr.decode(errors="replace")
        detail_lines = [line.strip() for line in stderr.splitlines() if line.strip()]
        if detail_lines:
            return f"FFmpeg failed: {detail_lines[-1]}"
    return str(error)


def main() -> int:
    args = create_parser().parse_args()
    timestamp = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    output_file = args.output or f"output/viral-clip-{timestamp}.mp4"

    try:
        ViralClipGenerator().generate(
            output_file=output_file,
            num_clips=args.num_clips,
            specific_clips=args.clips,
            specific_audio=args.audio,
        )
    except (OSError, ValueError, RuntimeError, ffmpeg.Error) as exc:
        print(f"Error: {describe_error(exc)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
