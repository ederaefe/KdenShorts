"""Unit tests for clip validation, boundary checks, and ranking."""

from pathlib import Path
from clip_harvester.ai.models import ChunkAnalysisResult, ClipRecommendation
from clip_harvester.ai.validator import validate_and_filter_clips
from clip_harvester.media.audio import AudioChunk


def make_dummy_chunk(chunk_index: int, offset_sec: float, duration_sec: float) -> AudioChunk:
    return AudioChunk(
        chunk_index=chunk_index,
        file_path=Path(f"chunk_{chunk_index}.mp3"),
        offset_seconds=offset_sec,
        offset_timecode="00:00:00",
        duration_seconds=duration_sec,
    )


def test_validator_accepts_valid_clip():
    chunk = make_dummy_chunk(0, 0.0, 1200.0)
    clip_rec = ClipRecommendation(
        clip_number=1,
        title="Why Prayer Changes You",
        hook_sentence="Most people pray to change God, but prayer changes you.",
        start_time="00:02:00",
        end_time="00:02:45",
        duration_seconds=45,
        reasoning="Powerful reframing on prayer",
        hook_type="counter_intuitive",
        confidence="high",
    )
    analysis = ChunkAnalysisResult(
        chunk_summary="Sermon intro and prayer discussion",
        transcript="[00:02:00] Most people pray to change God...",
        clips=[clip_rec],
    )

    validated = validate_and_filter_clips([(chunk, analysis)], head_padding=1.5)

    assert len(validated) == 1
    clip = validated[0]
    assert clip.title == "Why Prayer Changes You"
    # Pre-roll padding of 1.5s applied to 120s -> 118.5s
    assert clip.start_seconds == 118.5
    assert clip.end_seconds == 165.0
    assert clip.duration_seconds == 46.5
    assert clip.confidence == "high"


def test_validator_filters_reversed_timestamps():
    chunk = make_dummy_chunk(0, 0.0, 1200.0)
    clip_rec = ClipRecommendation(
        clip_number=1,
        title="Reversed Timestamps Clip",
        hook_sentence="Invalid timing",
        start_time="00:05:00",
        end_time="00:04:00",  # end before start
        duration_seconds=60,
        reasoning="Invalid clip",
        hook_type="bold_claim",
        confidence="high",
    )
    analysis = ChunkAnalysisResult(
        chunk_summary="Summary",
        transcript="Transcript",
        clips=[clip_rec],
    )

    validated = validate_and_filter_clips([(chunk, analysis)])
    assert len(validated) == 0


def test_validator_filters_out_of_chunk_bounds():
    # Chunk 0 covers 00:00:00 to 00:20:00 (0 to 1200s)
    chunk = make_dummy_chunk(0, 0.0, 1200.0)
    clip_rec = ClipRecommendation(
        clip_number=1,
        title="Hallucinated Timestamp Clip",
        hook_sentence="This clip belongs to 1 hour later",
        start_time="01:15:00",  # 4500 seconds, far beyond 1200s
        end_time="01:15:45",
        duration_seconds=45,
        reasoning="Far out of range",
        hook_type="bold_claim",
        confidence="high",
    )
    analysis = ChunkAnalysisResult(
        chunk_summary="Summary",
        transcript="Transcript",
        clips=[clip_rec],
    )

    validated = validate_and_filter_clips([(chunk, analysis)])
    assert len(validated) == 0


def test_validator_deduplicates_overlapping_clips():
    chunk = make_dummy_chunk(0, 0.0, 1200.0)
    clip1 = ClipRecommendation(
        clip_number=1,
        title="First Version",
        hook_sentence="Sentence 1",
        start_time="00:01:00",
        end_time="00:01:45",
        duration_seconds=45,
        reasoning="First pick",
        hook_type="bold_claim",
        confidence="high",
    )
    clip2 = ClipRecommendation(
        clip_number=2,
        title="Duplicate Version",
        hook_sentence="Sentence 1",
        start_time="00:01:05",  # Overlaps significantly with clip1
        end_time="00:01:40",
        duration_seconds=35,
        reasoning="Second pick",
        hook_type="bold_claim",
        confidence="low",
    )
    analysis = ChunkAnalysisResult(
        chunk_summary="Summary",
        transcript="Transcript",
        clips=[clip1, clip2],
    )

    validated = validate_and_filter_clips([(chunk, analysis)])
    assert len(validated) == 1
    assert validated[0].title == "First Version"
