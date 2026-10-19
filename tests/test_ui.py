"""Unit tests for UI rendering, input sanitization, and table construction."""

from pathlib import Path
from clip_harvester.ai.models import ValidatedClip
from clip_harvester.ui.interactive import clean_input_path, render_clips_table
from clip_harvester.ui.theme import render_header, render_step


def test_clean_input_path_single_quotes():
    raw = "'C:/Videos/Sermon File.mp4'"
    cleaned = clean_input_path(raw)
    assert cleaned == Path("C:/Videos/Sermon File.mp4")


def test_clean_input_path_double_quotes():
    raw = '"C:\\Videos\\Podcast Ep 01.mp4"'
    cleaned = clean_input_path(raw)
    assert cleaned == Path("C:/Videos/Podcast Ep 01.mp4") or str(cleaned).endswith("Podcast Ep 01.mp4")


def test_clean_input_path_powershell_ampersand():
    raw = "& 'C:/Footage/Sunday.mp4'"
    cleaned = clean_input_path(raw)
    assert cleaned == Path("C:/Footage/Sunday.mp4")


def test_render_clips_table_structure():
    clips = [
        ValidatedClip(
            clip_id="clip_1",
            title="The Mystery of Faith",
            hook_sentence="Faith does not make sense until you take the first step.",
            start_seconds=30.0,
            end_seconds=75.0,
            duration_seconds=45.0,
            start_timecode="00:00:30",
            end_timecode="00:01:15",
            reasoning="Strong theological thesis",
            confidence="high",
            hook_type="theological_revelation",
            chunk_index=0,
        )
    ]
    table = render_clips_table(clips, active_indices={0})
    assert table is not None
    assert len(table.columns) == 7
    assert table.row_count == 1


def test_theme_headers_do_not_crash():
    # Verify banner and step renders do not raise exceptions
    render_header("1.0.0")
    render_step(1, 5, "Unit Test Stage", "details")
