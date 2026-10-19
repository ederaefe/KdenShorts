"""Clip validation, timestamp sanitization, pre-roll padding, and ranking."""

import re
from typing import List, Tuple

from clip_harvester.ai.models import ChunkAnalysisResult, ValidatedClip
from clip_harvester.config import CONFIG
from clip_harvester.kdenlive.timecode import seconds_to_timecode, timecode_to_seconds
from clip_harvester.media.audio import AudioChunk


def clean_title(title: str) -> str:
    """Sanitizes clip title for use in markers and file metadata."""
    cleaned = re.sub(r'["\<\>\:\/\\\|\?\*]', "", title).strip()
    return cleaned if cleaned else "Highlight Clip"


def validate_and_filter_clips(
    chunk_pairs: List[Tuple[AudioChunk, ChunkAnalysisResult]],
    min_duration: int = CONFIG.default_min_duration,
    max_duration: int = CONFIG.default_max_duration,
    max_clips: int = CONFIG.default_max_clips,
    head_padding: float = CONFIG.head_padding_seconds,
) -> List[ValidatedClip]:
    """Validates raw Gemini clip recommendations and extracts the top candidates.

    Applies:
    1. Timestamp parse validation and ordering check (start < end).
    2. Chunk boundary sanity check (start and end within segment range + grace period).
    3. Strict duration range compliance.
    4. Head-padding (1.5s pre-roll) to protect the initial syllable from truncation.
    5. Deduplication and non-overlapping timeline verification.
    6. Ranking prioritizing high confidence and complete thought structure.
    """
    candidates: List[ValidatedClip] = []
    seen_ranges: List[Tuple[float, float]] = []

    for chunk, analysis in chunk_pairs:
        chunk_min_bound = max(0.0, chunk.offset_seconds - 5.0)
        chunk_max_bound = chunk.offset_seconds + chunk.duration_seconds + 15.0

        for clip_rec in analysis.clips:
            try:
                raw_start = timecode_to_seconds(clip_rec.start_time)
                raw_end = timecode_to_seconds(clip_rec.end_time)
            except ValueError:
                continue

            # Basic ordering validation
            if raw_start >= raw_end:
                continue

            raw_duration = raw_end - raw_start

            # Duration boundaries (allow minor leeway before hard reject)
            if raw_duration < (min_duration - 5) or raw_duration > (max_duration + 15):
                continue

            # Sanity check: must be near this chunk's time window
            if raw_start < chunk_min_bound or raw_end > chunk_max_bound:
                continue

            # Apply pre-roll head padding, bounded at 0
            padded_start = max(0.0, raw_start - head_padding)
            padded_duration = raw_end - padded_start

            # Check overlap with existing approved candidates (avoid duplicate clips)
            is_overlapping = False
            for prev_start, prev_end in seen_ranges:
                overlap_start = max(padded_start, prev_start)
                overlap_end = min(raw_end, prev_end)
                if (overlap_end - overlap_start) > 10.0:  # More than 10s overlap
                    is_overlapping = True
                    break

            if is_overlapping:
                continue

            clip_id = f"clip_{chunk.chunk_index + 1}_{clip_rec.clip_number}"
            title = clean_title(clip_rec.title)

            validated = ValidatedClip(
                clip_id=clip_id,
                title=title,
                hook_sentence=clip_rec.hook_sentence.strip(),
                start_seconds=padded_start,
                end_seconds=raw_end,
                duration_seconds=round(padded_duration, 2),
                start_timecode=seconds_to_timecode(padded_start),
                end_timecode=seconds_to_timecode(raw_end),
                reasoning=clip_rec.reasoning.strip(),
                confidence=clip_rec.confidence,
                hook_type=clip_rec.hook_type,
                chunk_index=chunk.chunk_index,
            )

            candidates.append(validated)
            seen_ranges.append((padded_start, raw_end))

    # Rank candidates: "high" > "medium" > "low"
    confidence_rank = {"high": 3, "medium": 2, "low": 1}
    candidates.sort(key=lambda c: (confidence_rank.get(c.confidence, 0), -abs(c.duration_seconds - 50)), reverse=True)

    # Return top N requested clips
    selected = candidates[:max_clips]

    # Re-sort selected clips chronologically for pleasant timeline editing
    selected.sort(key=lambda c: c.start_seconds)
    return selected
