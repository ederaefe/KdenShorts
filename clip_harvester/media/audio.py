"""Audio extraction and chunking pipeline using FFmpeg."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

from clip_harvester.config import CONFIG
from clip_harvester.kdenlive.timecode import seconds_to_timecode
from clip_harvester.media.probe import probe_media_file, verify_ffmpeg_installed


@dataclass(frozen=True)
class AudioChunk:
    """Represents a sliced audio segment with offset coordinates."""

    chunk_index: int
    file_path: Path
    offset_seconds: float
    offset_timecode: str
    duration_seconds: float


def get_audio_file_duration(file_path: Path) -> float:
    """Gets the duration in seconds of an audio file using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(file_path.resolve()),
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data.get("format", {}).get("duration", 0.0))


def extract_and_chunk_audio(
    source_media: Path,
    output_dir: Path,
    chunk_seconds: int = CONFIG.chunk_duration_seconds,
) -> List[AudioChunk]:
    """Extracts the audio track from the source media and splits it into fixed-duration chunks.

    Args:
        source_media: Path to the input video or audio file.
        output_dir: Directory where chunk files will be saved.
        chunk_seconds: Target chunk duration in seconds (default: 1200s / 20 mins).

    Returns:
        List of AudioChunk objects containing metadata and file locations.

    Raises:
        FileNotFoundError: If ffmpeg is missing or source file does not exist.
        RuntimeError: If ffmpeg execution fails.
    """
    if not source_media.exists():
        raise FileNotFoundError(f"Source media not found: {source_media}")

    if not verify_ffmpeg_installed():
        from clip_harvester.bootstrap import detect_os_info

        os_info = detect_os_info()
        raise FileNotFoundError(
            f"ffmpeg is not found on system PATH. Install for {os_info.display_name}: {os_info.ffmpeg_install_cmd}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Output pattern for chunk files
    chunk_pattern = output_dir / "chunk_%03d.mp3"

    # 2. Single-pass FFmpeg extraction and segmentation:
    # -vn: Drop video
    # -ac 1: Downmix to mono
    # -ar 16000: 16kHz speech optimal sample rate
    # -b:a 128k: 128kbps MP3
    # -f segment: Segment muxer
    # -segment_time {chunk_seconds}: Target segment duration
    # -reset_timestamps 1: Reset timestamp inside each chunk
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_media.resolve()),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(CONFIG.audio_sample_rate),
        "-c:a",
        "libmp3lame",
        "-b:a",
        CONFIG.audio_bitrate,
        "-f",
        "segment",
        "-segment_time",
        str(chunk_seconds),
        "-reset_timestamps",
        "1",
        str(chunk_pattern),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio chunking failed: {result.stderr.strip()}")

    # 3. Discover and validate generated chunks
    generated_files = sorted(output_dir.glob("chunk_*.mp3"))

    if not generated_files:
        raise RuntimeError(f"No audio chunks generated from: {source_media}")

    chunks: List[AudioChunk] = []
    cumulative_offset = 0.0

    for idx, chunk_file in enumerate(generated_files):
        try:
            chunk_dur = get_audio_file_duration(chunk_file)
        except Exception:
            chunk_dur = float(chunk_seconds)

        chunk_obj = AudioChunk(
            chunk_index=idx,
            file_path=chunk_file,
            offset_seconds=cumulative_offset,
            offset_timecode=seconds_to_timecode(cumulative_offset),
            duration_seconds=chunk_dur,
        )
        chunks.append(chunk_obj)
        cumulative_offset += chunk_dur

    return chunks
