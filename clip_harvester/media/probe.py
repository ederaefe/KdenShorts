"""Video and audio metadata inspection using ffprobe."""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class MediaMetadata:
    """Extracted metadata for a media file."""

    file_path: Path
    duration_seconds: float
    fps: float
    fps_num: int
    fps_den: int
    width: int
    height: int
    has_video: bool
    has_audio: bool


def verify_ffprobe_installed() -> bool:
    """Verifies that ffprobe executable is discoverable in PATH or managed cache."""
    from clip_harvester.media.downloader import ensure_bin_in_path
    ensure_bin_in_path()
    return shutil.which("ffprobe") is not None


def verify_ffmpeg_installed() -> bool:
    """Verifies that ffmpeg executable is discoverable in PATH or managed cache."""
    from clip_harvester.media.downloader import ensure_bin_in_path
    ensure_bin_in_path()
    return shutil.which("ffmpeg") is not None


def parse_fps_fraction(fps_str: str) -> tuple[float, int, int]:
    """Parses rational frame rate string like '30000/1001' or '30/1' into (float_fps, num, den)."""
    if not fps_str or fps_str == "0/0":
        return 30.0, 30, 1

    try:
        if "/" in fps_str:
            num_str, den_str = fps_str.split("/", 1)
            num = int(num_str)
            den = int(den_str)
            if den == 0:
                return 30.0, 30, 1
            return round(num / den, 3), num, den
        else:
            val = float(fps_str)
            return round(val, 3), int(round(val * 1000)), 1000
    except (ValueError, ZeroDivisionError):
        return 30.0, 30, 1


def probe_media_file(media_path: Path) -> MediaMetadata:
    """Inspects a media file using ffprobe and returns structured MediaMetadata.

    Raises:
        FileNotFoundError: If the media file or ffprobe does not exist.
        ValueError: If media streams cannot be read.
        subprocess.CalledProcessError: If ffprobe returns an error.
    """
    if not media_path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    if not verify_ffprobe_installed():
        raise FileNotFoundError("ffprobe is not found on system PATH. Please ensure FFmpeg is installed.")

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,width,height,r_frame_rate,avg_frame_rate",
        "-of",
        "json",
        str(media_path.resolve()),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    format_info = data.get("format", {})

    duration_seconds = float(format_info.get("duration", 0.0))

    has_video = False
    has_audio = False
    width = 1920
    height = 1080
    fps = 30.0
    fps_num = 30
    fps_den = 1

    for s in streams:
        c_type = s.get("codec_type")
        if c_type == "video" and not has_video:
            has_video = True
            width = int(s.get("width") or 1920)
            height = int(s.get("height") or 1080)
            fps_str = s.get("r_frame_rate") or s.get("avg_frame_rate") or "30/1"
            fps, fps_num, fps_den = parse_fps_fraction(fps_str)
        elif c_type == "audio":
            has_audio = True

    if not has_audio and not has_video:
        raise ValueError(f"No audio or video streams detected in: {media_path}")

    return MediaMetadata(
        file_path=media_path.resolve(),
        duration_seconds=duration_seconds,
        fps=fps,
        fps_num=fps_num,
        fps_den=fps_den,
        width=width,
        height=height,
        has_video=has_video,
        has_audio=has_audio,
    )
