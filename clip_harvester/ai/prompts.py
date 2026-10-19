"""Prompt assembly and profile loading for Gemini audio understanding."""

from pathlib import Path
from clip_harvester.config import PROFILES_DIR
from clip_harvester.kdenlive.timecode import seconds_to_timecode


def load_profile_criteria(profile_name: str) -> str:
    """Loads the profile text criteria for clip extraction.

    Falls back to 'general' if the specified profile is not found.
    """
    clean_name = profile_name.lower().replace(".txt", "")
    profile_file = PROFILES_DIR / f"{clean_name}.txt"

    if not profile_file.exists():
        fallback_file = PROFILES_DIR / "general.txt"
        if fallback_file.exists():
            return fallback_file.read_text(encoding="utf-8")
        return "Extract the most compelling, high-retention 30-75 second standalone moments."

    return profile_file.read_text(encoding="utf-8")


def build_chunk_prompt(
    offset_seconds: float,
    chunk_index: int,
    total_chunks: int,
    profile_name: str = "sermon",
    min_duration: int = 30,
    max_duration: int = 80,
) -> str:
    """Constructs the prompt for Gemini with absolute timestamp offset and profile constraints."""
    offset_hh_mm_ss = seconds_to_timecode(offset_seconds)
    profile_criteria = load_profile_criteria(profile_name)

    prompt = f"""You are an elite short-form video editor specializing in YouTube Shorts, TikTok, and Reels.
You are analyzing an audio segment from a long-form recording.

METADATA & TIMING ANCHOR:
- Segment {chunk_index + 1} of {total_chunks}.
- This audio begins at absolute global timestamp: {offset_hh_mm_ss} ({int(offset_seconds)} seconds from start of the master recording).
- ALL TIMESTAMPS in your output MUST be calculated in GLOBAL ABSOLUTE TIME (HH:MM:SS):
  Global Timestamp = {int(offset_seconds)} seconds + time within this audio file.
  Example: If an event happens at 01:30 into this audio file, and the offset is 00:20:00 (1200s), the global timestamp is 00:21:30.

EXECUTION INSTRUCTIONS:

STEP 1 - TRANSCRIBE:
Transcribe the speech in this audio segment sequentially.
Every sentence MUST begin with its calculated global [HH:MM:SS] timestamp.
Do not skip spoken sections. If speech is unintelligible, mark it as [inaudible].

STEP 2 - IDENTIFY TOP STANDALONE CLIPS:
Using the transcript you generated in Step 1, identify 0 to 4 of the most potent standalone clips matching the profile rules below.

{profile_criteria}

MANDATORY CLIP REQUIREMENTS:
1. Target Duration: Strictly between {min_duration} and {max_duration} seconds. Never exceed 90 seconds.
2. Complete Thought Structure: The clip must have a premise (hook) -> insight -> resolution. A viewer watching in a Shorts feed must understand the message with zero outside context.
3. No Throat-Clearing: The first word of the hook must grab attention immediately. Do not start on greetings, pauses, announcements, or setup remarks.
4. Transcript Veracity: The 'start_time' and 'end_time' values you report MUST correspond directly to actual spoken sentences in your Step 1 transcript. Never hallucinate or guess timestamps.
5. If this segment contains no compelling standalone clips, return an empty clips list []. Do NOT force low-quality clips.
"""
    return prompt
