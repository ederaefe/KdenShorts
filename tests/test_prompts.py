"""Unit tests for prompt construction and profile loaders."""

from clip_harvester.ai.prompts import build_chunk_prompt, load_profile_criteria


def test_load_profile_criteria_sermon():
    criteria = load_profile_criteria("sermon")
    assert "SERMON" in criteria
    assert "theological" in criteria.lower()


def test_load_profile_criteria_podcast():
    criteria = load_profile_criteria("podcast")
    assert "PODCAST" in criteria
    assert "punchline" in criteria.lower()


def test_load_profile_criteria_fallback():
    criteria = load_profile_criteria("unknown_profile_xyz")
    assert len(criteria) > 0


def test_build_chunk_prompt_offset_injection():
    # 20-minute offset = 1200 seconds = 00:20:00
    prompt = build_chunk_prompt(
        offset_seconds=1200.0,
        chunk_index=1,
        total_chunks=3,
        profile_name="sermon",
        min_duration=30,
        max_duration=60,
    )

    assert "00:20:00" in prompt
    assert "1200 seconds" in prompt
    assert "Segment 2 of 3" in prompt
    assert "Strictly between 30 and 60 seconds" in prompt
