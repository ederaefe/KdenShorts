"""Timecode parsing, mathematical operations, and frame conversion utilities."""

import math
from typing import Union


def timecode_to_seconds(ts_str: str) -> float:
    """Converts timecode formats (HH:MM:SS, MM:SS, SS.sss) into total seconds.

    Supports:
        '01:23:45' -> 5025.0
        '23:45'    -> 1425.0
        '00:05.5'  -> 5.5
        '120'      -> 120.0
    """
    cleaned = ts_str.strip().replace("[", "").replace("]", "")
    parts = cleaned.split(":")

    try:
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])
            return h * 3600.0 + m * 60.0 + s
        elif len(parts) == 2:
            m = float(parts[0])
            s = float(parts[1])
            return m * 60.0 + s
        elif len(parts) == 1:
            return float(parts[0])
        else:
            raise ValueError(f"Unrecognized timecode structure: {ts_str}")
    except ValueError as e:
        raise ValueError(f"Invalid numeric value in timecode '{ts_str}': {e}") from e


def seconds_to_timecode(seconds: float, include_millis: bool = False) -> str:
    """Converts total seconds into standard HH:MM:SS format."""
    sec = max(0.0, seconds)
    h = int(sec // 3600)
    remainder = sec % 3600
    m = int(remainder // 60)
    s = remainder % 60

    if include_millis:
        return f"{h:02d}:{m:02d}:{s:06.3f}"
    return f"{h:02d}:{m:02d}:{int(s):02d}"


def seconds_to_frames(seconds: float, fps: float) -> int:
    """Converts seconds into integer frame count based on project FPS."""
    return int(round(max(0.0, seconds) * fps))


def frames_to_seconds(frames: int, fps: float) -> float:
    """Converts integer frame count into floating point seconds."""
    if fps <= 0:
        return 0.0
    return frames / fps


def frames_to_timecode(frames: int, fps: float) -> str:
    """Converts integer frame count into HH:MM:SS format."""
    sec = frames_to_seconds(frames, fps)
    return seconds_to_timecode(sec)
