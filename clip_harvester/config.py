"""Configuration constants and default settings for Clip Harvester."""

import os
from dataclasses import dataclass
from pathlib import Path


MODEL_ALIASES = {
    "flash": "gemini-2.5-flash",
    "flash-latest": "gemini-2.5-flash",
    "pro": "gemini-2.5-pro",
    "pro-latest": "gemini-2.5-pro",
}


def resolve_model_name(name: str) -> str:
    """Resolves friendly aliases like 'flash' or 'flash-latest' to current active model IDs."""
    normalized = name.strip().lower()
    return MODEL_ALIASES.get(normalized, name.strip())


@dataclass(frozen=True)
class AppConfig:
    """Application-wide configuration parameters."""

    # Default AI settings (can be overridden by GEMINI_MODEL env var)
    default_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    chunk_duration_seconds: int = 1200  # 20 minutes
    audio_sample_rate: int = 16000  # 16kHz mono optimal for Gemini speech recognition
    audio_bitrate: str = "128k"

    # Default clip boundaries
    default_min_duration: int = 30
    default_max_duration: int = 80
    default_max_clips: int = 5
    head_padding_seconds: float = 1.5  # Pre-roll pad to prevent cutting off the first syllable

    # Target Kdenlive profile (9:16 vertical video)
    target_width: int = 1080
    target_height: int = 1920
    timeline_spacer_frames: int = 50  # 50 frames empty spacer between clips on timeline

    # File polling
    poll_interval_seconds: int = 3
    poll_timeout_seconds: int = 300


CONFIG = AppConfig()
PROFILES_DIR = Path(__file__).resolve().parent / "profiles"
