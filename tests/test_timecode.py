"""Unit tests for timecode parsing and frame conversion arithmetic."""

import pytest
from clip_harvester.kdenlive.timecode import (
    frames_to_seconds,
    frames_to_timecode,
    seconds_to_frames,
    seconds_to_timecode,
    timecode_to_seconds,
)


def test_timecode_to_seconds_hh_mm_ss():
    assert timecode_to_seconds("00:00:00") == 0.0
    assert timecode_to_seconds("00:01:30") == 90.0
    assert timecode_to_seconds("01:00:00") == 3600.0
    assert timecode_to_seconds("01:23:45") == 5025.0


def test_timecode_to_seconds_mm_ss():
    assert timecode_to_seconds("05:30") == 330.0
    assert timecode_to_seconds("00:15") == 15.0


def test_timecode_to_seconds_with_brackets_and_spaces():
    assert timecode_to_seconds("[00:02:15]") == 135.0
    assert timecode_to_seconds("  01:10:05  ") == 4205.0


def test_timecode_to_seconds_fractional():
    assert timecode_to_seconds("00:00:12.500") == 12.5
    assert timecode_to_seconds("12.5") == 12.5


def test_timecode_invalid_format():
    with pytest.raises(ValueError):
        timecode_to_seconds("invalid:time:code:extra")

    with pytest.raises(ValueError):
        timecode_to_seconds("abc:def")


def test_seconds_to_timecode():
    assert seconds_to_timecode(0.0) == "00:00:00"
    assert seconds_to_timecode(90.0) == "00:01:30"
    assert seconds_to_timecode(3665.0) == "01:01:05"


def test_seconds_to_timecode_with_millis():
    assert seconds_to_timecode(90.5, include_millis=True) == "00:01:30.500"


def test_seconds_to_frames():
    fps = 30.0
    assert seconds_to_frames(0.0, fps) == 0
    assert seconds_to_frames(1.0, fps) == 30
    assert seconds_to_frames(1.5, fps) == 45
    assert seconds_to_frames(10.0, 29.97) == 300


def test_frames_to_seconds():
    fps = 30.0
    assert frames_to_seconds(0, fps) == 0.0
    assert frames_to_seconds(30, fps) == 1.0
    assert frames_to_seconds(45, fps) == 1.5


def test_frames_to_timecode():
    assert frames_to_timecode(900, 30.0) == "00:00:30"
    assert frames_to_timecode(54000, 30.0) == "00:30:00"
