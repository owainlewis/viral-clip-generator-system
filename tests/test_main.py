import json
import shutil
import subprocess
from pathlib import Path

import pytest

import main


def test_usage_tracker_rejects_corrupt_json(tmp_path: Path) -> None:
    usage_file = tmp_path / "usage.json"
    usage_file.write_text("not json", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Could not read clip usage data"):
        main.UsageTracker(usage_file)


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"clip.mp4": {"last_used": -1, "usage_count": 1}},
        {"clip.mp4": {"last_used": 1, "usage_count": -1}},
        {"clip.mp4": {"last_used": 1}},
    ],
)
def test_usage_tracker_rejects_invalid_schema(tmp_path: Path, data: object) -> None:
    usage_file = tmp_path / "usage.json"
    usage_file.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(RuntimeError, match="usage"):
        main.UsageTracker(usage_file)


def test_usage_tracker_saves_and_loads_usage(tmp_path: Path) -> None:
    usage_file = tmp_path / "state" / "usage.json"
    tracker = main.UsageTracker(usage_file, clock=lambda: 123.5)

    tracker.update_usage(["first.mp4", "first.mp4", "second.mp4"])
    tracker.save_usage_data()

    assert main.UsageTracker(usage_file).usage_data == {
        "first.mp4": {"last_used": 123.5, "usage_count": 2},
        "second.mp4": {"last_used": 123.5, "usage_count": 1},
    }
    assert not list(usage_file.parent.glob("*.tmp"))


def test_rotation_prioritizes_unseen_then_oldest_clips(tmp_path: Path) -> None:
    usage_file = tmp_path / "usage.json"
    usage_file.write_text(
        json.dumps(
            {
                "newer.mp4": {"last_used": 20, "usage_count": 1},
                "older.mp4": {"last_used": 10, "usage_count": 4},
            }
        ),
        encoding="utf-8",
    )
    tracker = main.UsageTracker(usage_file)

    selected = tracker.select_clips_with_rotation(
        ["newer.mp4", "unseen.mp4", "older.mp4"], 3
    )

    assert selected == ["unseen.mp4", "older.mp4", "newer.mp4"]


@pytest.mark.parametrize("num_clips", [0, -1])
def test_rotation_rejects_non_positive_clip_counts(
    tmp_path: Path, num_clips: int
) -> None:
    tracker = main.UsageTracker(tmp_path / "usage.json")

    with pytest.raises(ValueError, match="at least 1"):
        tracker.select_clips_with_rotation(["clip.mp4"], num_clips)


def test_media_files_are_filtered_and_sorted(tmp_path: Path) -> None:
    for name in ["z.MP4", "A.mp4", "notes.txt"]:
        (tmp_path / name).touch()

    assert main.MediaValidator.get_media_files(tmp_path, (".mp4",)) == [
        "A.mp4",
        "z.MP4",
    ]


def test_media_files_reject_line_breaks(tmp_path: Path) -> None:
    (tmp_path / "line\nbreak.mp4").touch()

    with pytest.raises(ValueError, match="cannot contain line breaks"):
        main.MediaValidator.get_media_files(tmp_path, (".mp4",))


def test_failed_processing_does_not_record_usage(tmp_path: Path) -> None:
    clips = tmp_path / "clips"
    audio = tmp_path / "audio"
    clips.mkdir()
    audio.mkdir()
    (clips / "clip.mp4").touch()
    (audio / "music.mp3").touch()
    usage_file = tmp_path / "usage.json"
    generator = main.ViralClipGenerator(clips, audio, usage_file)

    class FailingProcessor:
        def process_clips(self, *_args: object) -> None:
            raise RuntimeError("FFmpeg failed")

    generator.processor = FailingProcessor()  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="FFmpeg failed"):
        generator.generate(tmp_path / "output.mp4", num_clips=1)

    assert generator.usage_tracker.usage_data == {}
    assert not usage_file.exists()


def test_successful_processing_records_usage(tmp_path: Path) -> None:
    clips = tmp_path / "clips"
    audio = tmp_path / "audio"
    clips.mkdir()
    audio.mkdir()
    (clips / "clip.mp4").touch()
    (audio / "music.mp3").touch()
    usage_file = tmp_path / "usage.json"
    generator = main.ViralClipGenerator(clips, audio, usage_file)
    calls: list[tuple[list[str], str, Path]] = []

    class RecordingProcessor:
        def process_clips(
            self, videos: list[str], selected_audio: str, output_file: Path
        ) -> None:
            calls.append((videos, selected_audio, output_file))

    generator.processor = RecordingProcessor()  # type: ignore[assignment]

    result = generator.generate(tmp_path / "output.mp4", num_clips=1)

    assert result == tmp_path / "output.mp4"
    assert calls == [(["clip.mp4"], "music.mp3", tmp_path / "output.mp4")]
    assert main.UsageTracker(usage_file).usage_data["clip.mp4"]["usage_count"] == 1


def test_duration_uses_container_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    processor = main.VideoProcessor(Path("clips"), Path("audio"))
    monkeypatch.setattr(
        main.ffmpeg,
        "probe",
        lambda _path: {
            "format": {"duration": "3.25"},
            "streams": [{"codec_type": "video"}],
        },
    )

    assert processor._get_video_duration(Path("video.mp4")) == 3.25


def test_duration_fails_when_metadata_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processor = main.VideoProcessor(Path("clips"), Path("audio"))
    monkeypatch.setattr(main.ffmpeg, "probe", lambda _path: {"streams": []})

    with pytest.raises(RuntimeError, match="Could not determine video duration"):
        processor._get_video_duration(Path("video.mp4"))


def test_concat_path_escapes_single_quotes() -> None:
    assert main.VideoProcessor._escape_concat_path(Path("it's.mp4")) == ("it'\\''s.mp4")


def test_parser_rejects_zero_clips() -> None:
    with pytest.raises(SystemExit):
        main.create_parser().parse_args(["--num-clips", "0"])


def test_ffmpeg_error_includes_stderr_detail() -> None:
    error = main.ffmpeg.Error("ffmpeg", b"", b"first line\nuseful failure\n")

    assert main.describe_error(error) == "FFmpeg failed: useful failure"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg is not installed")
def test_generator_creates_video_with_looped_audio(tmp_path: Path) -> None:
    clips = tmp_path / "clips"
    audio = tmp_path / "audio"
    clips.mkdir()
    audio.mkdir()
    clip_names = ["first.mp4", "second's clip.mp4"]

    for index, clip_name in enumerate(clip_names):
        subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=c={'red' if index == 0 else 'blue'}:s=160x90:d=0.4",
                "-r",
                "25",
                "-pix_fmt",
                "yuv420p",
                str(clips / clip_name),
            ],
            check=True,
        )
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=0.2",
            str(audio / "music.mp3"),
        ],
        check=True,
    )

    output_file = tmp_path / "result.mp4"
    usage_file = tmp_path / "usage.json"
    main.ViralClipGenerator(clips, audio, usage_file).generate(
        output_file,
        specific_clips=clip_names,
        specific_audio="music.mp3",
    )

    probe = main.ffmpeg.probe(str(output_file))
    streams = probe["streams"]
    assert output_file.stat().st_size > 0
    assert {stream["codec_type"] for stream in streams} == {"audio", "video"}
    assert float(probe["format"]["duration"]) >= 0.7
    assert main.UsageTracker(usage_file).usage_data.keys() == set(clip_names)


def test_processor_does_not_leave_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clips = tmp_path / "clips"
    audio = tmp_path / "audio"
    clips.mkdir()
    audio.mkdir()
    (clips / "clip.mp4").touch()
    (audio / "music.mp3").touch()
    processor = main.VideoProcessor(clips, audio)
    monkeypatch.setattr(processor, "_concatenate_videos", lambda *_args: None)
    monkeypatch.setattr(processor, "_get_video_duration", lambda *_args: 1.0)

    def fail_with_partial_output(
        _video: Path, _audio: Path, output: Path, _duration: float
    ) -> None:
        output.write_bytes(b"partial")
        raise RuntimeError("encoding failed")

    monkeypatch.setattr(processor, "_add_audio", fail_with_partial_output)
    output_file = tmp_path / "output" / "result.mp4"

    with pytest.raises(RuntimeError, match="encoding failed"):
        processor.process_clips(["clip.mp4"], "music.mp3", output_file)

    assert not output_file.exists()
    assert not list(output_file.parent.iterdir())


def test_processor_requires_mp4_output(tmp_path: Path) -> None:
    processor = main.VideoProcessor(tmp_path, tmp_path)

    with pytest.raises(ValueError, match=r"\.mp4"):
        processor.process_clips(["clip.mp4"], "music.mp3", tmp_path / "result.mov")
