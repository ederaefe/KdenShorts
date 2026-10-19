"""Pydantic data models for structured Gemini audio outputs and internal clip representation."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ClipRecommendation(BaseModel):
    """A single standalone video clip recommendation."""

    clip_number: int = Field(description="Sequential index of the clip within this chunk")
    title: str = Field(description="Punchy, engaging, curiosity-inducing title (max 8 words)")
    hook_sentence: str = Field(description="Exact verbatim opening sentence of this clip")
    start_time: str = Field(description="Absolute start time in HH:MM:SS format (including global chunk offset)")
    end_time: str = Field(description="Absolute end time in HH:MM:SS format (including global chunk offset)")
    duration_seconds: int = Field(description="Approximate clip duration in seconds (30 to 80 seconds)")
    reasoning: str = Field(description="One sentence explaining why this works as a standalone viral short")
    hook_type: Literal[
        "bold_claim",
        "curiosity_gap",
        "emotional_vulnerability",
        "theological_revelation",
        "personal_story",
        "counter_intuitive",
        "challenging_question",
    ] = Field(description="Classification of the hook style")
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence score that this clip is standalone and engaging"
    )


class ChunkAnalysisResult(BaseModel):
    """Structured response from Gemini containing transcription and extracted clips."""

    chunk_summary: str = Field(description="Brief 2-sentence summary of the topics discussed in this 20-minute section")
    transcript: str = Field(
        description="Continuous verbatim transcript where every sentence begins with its absolute [HH:MM:SS] timestamp"
    )
    clips: List[ClipRecommendation] = Field(
        default_factory=list,
        description="List of 0 to 4 best standalone clips meeting the duration and complete-thought criteria",
    )


class ValidatedClip(BaseModel):
    """Internal validated clip ready for timeline placement in Kdenlive."""

    clip_id: str
    title: str
    hook_sentence: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    start_timecode: str
    end_timecode: str
    reasoning: str
    confidence: str
    hook_type: str
    chunk_index: int
