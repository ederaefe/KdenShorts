"""Unit tests for Kdenlive MLT XML synthesis."""

import xml.etree.ElementTree as ET
from pathlib import Path
from clip_harvester.ai.models import ValidatedClip
from clip_harvester.kdenlive.xml_builder import build_kdenlive_xml, write_kdenlive_project
from clip_harvester.media.probe import MediaMetadata


def make_dummy_metadata() -> MediaMetadata:
    return MediaMetadata(
        file_path=Path("C:/Videos/Sunday_Sermon.mp4"),
        duration_seconds=3600.0,
        fps=30.0,
        fps_num=30,
        fps_den=1,
        width=1920,
        height=1080,
        has_video=True,
        has_audio=True,
    )


def make_dummy_clips() -> list[ValidatedClip]:
    return [
        ValidatedClip(
            clip_id="clip_1",
            title="The Real Reason You Feel Stuck",
            hook_sentence="Most people don't fail from lack of talent.",
            start_seconds=120.0,
            end_seconds=165.0,
            duration_seconds=45.0,
            start_timecode="00:02:00",
            end_timecode="00:02:45",
            reasoning="Strong universal hook",
            confidence="high",
            hook_type="bold_claim",
            chunk_index=0,
        ),
        ValidatedClip(
            clip_id="clip_2",
            title="Grace Is Not Fair",
            hook_sentence="If God was fair, none of us would stand.",
            start_seconds=600.0,
            end_seconds=650.0,
            duration_seconds=50.0,
            start_timecode="00:10:00",
            end_timecode="00:10:50",
            reasoning="Theological pivot point",
            confidence="high",
            hook_type="theological_revelation",
            chunk_index=0,
        ),
    ]


def test_build_kdenlive_xml_syntax_validity():
    metadata = make_dummy_metadata()
    clips = make_dummy_clips()

    xml_text = build_kdenlive_xml(metadata, clips, project_title="Sunday Service Shorts")

    # 1. Parse with ElementTree to verify syntactic well-formedness
    root = ET.fromstring(xml_text)
    assert root.tag == "mlt"

    # 2. Check 9:16 Profile attributes
    profile = root.find("profile")
    assert profile is not None
    assert profile.attrib["width"] == "1080"
    assert profile.attrib["height"] == "1920"
    assert profile.attrib["display_aspect_num"] == "9"
    assert profile.attrib["display_aspect_den"] == "16"

    # 3. Check Producer points to source
    producer = root.find("producer[@id='producer_raw_source']")
    assert producer is not None
    resource_prop = producer.find("property[@name='resource']")
    assert resource_prop is not None
    assert "Sunday_Sermon.mp4" in resource_prop.text

    # 4. Check Playlist entries and spacers
    playlist = root.find("playlist[@id='playlist_v1']")
    assert playlist is not None
    entries = playlist.findall("entry")
    assert len(entries) == 2

    # Verify blank spacer between clip 1 and clip 2
    blanks = playlist.findall("blank")
    assert len(blanks) == 1
    assert blanks[0].attrib["length"] == "50"

    # 5. Check frame math
    # Clip 1: start=120s -> frame 3600, end=165s -> frame 4950
    assert entries[0].attrib["in"] == "3600"
    assert entries[0].attrib["out"] == "4950"


def test_write_kdenlive_project_to_disk(tmp_path: Path):
    metadata = make_dummy_metadata()
    clips = make_dummy_clips()
    output_file = tmp_path / "test_project.kdenlive"

    result_path = write_kdenlive_project(output_file, metadata, clips)
    assert result_path.exists()
    assert result_path.stat().st_size > 0

    content = result_path.read_text(encoding="utf-8")
    assert "<mlt" in content
    assert "Sunday_Sermon.mp4" in content
