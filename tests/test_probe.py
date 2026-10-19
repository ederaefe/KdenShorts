"""Unit tests for probe utilities and FPS parsing."""

import pytest
from pathlib import Path
from clip_harvester.media.probe import parse_fps_fraction, probe_media_file


def test_parse_fps_fraction_standard():
    fps, num, den = parse_fps_fraction("30/1")
    assert fps == 30.0
    assert num == 30
    assert den == 1


def test_parse_fps_fraction_ntsc():
    fps, num, den = parse_fps_fraction("30000/1001")
    assert fps == 29.97
    assert num == 30000
    assert den == 1001


def test_parse_fps_fraction_cinematic():
    fps, num, den = parse_fps_fraction("24/1")
    assert fps == 24.0
    assert num == 24
    assert den == 1


def test_parse_fps_fraction_high_framerate():
    fps, num, den = parse_fps_fraction("60000/1001")
    assert fps == 59.94
    assert num == 60000
    assert den == 1001


def test_parse_fps_fraction_invalid_or_zero():
    fps, num, den = parse_fps_fraction("0/0")
    assert fps == 30.0

    fps, num, den = parse_fps_fraction("")
    assert fps == 30.0

    fps, num, den = parse_fps_fraction("invalid")
    assert fps == 30.0


def test_probe_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        probe_media_file(Path("C:/nonexistent_file_abc123.mp4"))
