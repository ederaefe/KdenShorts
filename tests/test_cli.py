"""Unit tests for command-line interface arguments and preflight checks."""

from pathlib import Path
from unittest.mock import patch

from clip_harvester.cli import parse_arguments, perform_preflight_checks


def test_perform_preflight_checks_non_strict() -> None:
    """Verifies that perform_preflight_checks(strict=False) returns 3 booleans without exiting."""
    has_ffmpeg, has_ffprobe, has_key = perform_preflight_checks(strict=False)
    assert isinstance(has_ffmpeg, bool)
    assert isinstance(has_ffprobe, bool)
    assert isinstance(has_key, bool)


def test_parse_arguments_defaults() -> None:
    """Verifies default values for CLI flags when no options are provided."""
    with patch("sys.argv", ["kdenshorts"]):
        args = parse_arguments()
        assert args.media_path is None
        assert args.profile == "sermon"
        assert args.max_clips == 5
        assert args.min_duration == 30
        assert args.max_duration == 80
        assert args.open_kdenlive is False
        assert args.yes is False


def test_parse_arguments_custom_values() -> None:
    """Verifies custom arguments and flags are correctly parsed."""
    test_args = [
        "kdenshorts",
        "sample.mp4",
        "--profile",
        "podcast",
        "--max-clips",
        "8",
        "--open",
        "-y",
    ]
    with patch("sys.argv", test_args):
        args = parse_arguments()
        assert args.media_path == Path("sample.mp4")
        assert args.profile == "podcast"
        assert args.max_clips == 8
        assert args.open_kdenlive is True
        assert args.yes is True
