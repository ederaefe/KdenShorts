"""MLT XML project generator for Kdenlive vertical (9:16) video timelines."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List
from xml.dom import minidom

from clip_harvester.ai.models import ValidatedClip
from clip_harvester.config import CONFIG
from clip_harvester.kdenlive.timecode import seconds_to_frames
from clip_harvester.media.probe import MediaMetadata


def build_kdenlive_xml(
    source_metadata: MediaMetadata,
    clips: List[ValidatedClip],
    project_title: str = "AI Shorts Project",
    spacer_frames: int = CONFIG.timeline_spacer_frames,
) -> str:
    """Constructs a valid MLT XML string compatible with Kdenlive 24.xx/25.xx/26.xx.

    Configures:
    - 9:16 Vertical video canvas (1080x1920) matching source FPS.
    - Raw media source producer reference.
    - Project bin folder ('Shorts Clips').
    - Sequenced clips placed onto timeline playlist with blank spacers.
    - Formatted XML with indentation.
    """
    fps = source_metadata.fps
    fps_num = source_metadata.fps_num
    fps_den = source_metadata.fps_den
    source_path = str(source_metadata.file_path.resolve()).replace("\\", "/")
    total_source_frames = seconds_to_frames(source_metadata.duration_seconds, fps)

    # 1. Root MLT Element
    root = ET.Element(
        "mlt",
        {
            "LC_NUMERIC": "C",
            "version": "7.22.0",
            "title": project_title,
            "root": str(source_metadata.file_path.parent.resolve()).replace("\\", "/"),
            "xmlns:kdenlive": "http://www.kdenlive.org/project",
        },
    )

    # 2. Profile Element: 9:16 vertical 1080x1920
    ET.SubElement(
        root,
        "profile",
        {
            "id": "vertical_9_16",
            "description": "Vertical HD 1080x1920 9:16",
            "width": str(CONFIG.target_width),
            "height": str(CONFIG.target_height),
            "progressive": "1",
            "sample_aspect_num": "1",
            "sample_aspect_den": "1",
            "display_aspect_num": "9",
            "display_aspect_den": "16",
            "frame_rate_num": str(fps_num),
            "frame_rate_den": str(fps_den),
            "colorspace": "709",
        },
    )

    # 3. Source Video Producer
    producer = ET.SubElement(
        root,
        "producer",
        {
            "id": "producer_raw_source",
            "in": "0",
            "out": str(max(0, total_source_frames - 1)),
        },
    )
    prop_res = ET.SubElement(producer, "property", {"name": "resource"})
    prop_res.text = source_path
    prop_srv = ET.SubElement(producer, "property", {"name": "mlt_service"})
    prop_srv.text = "avformat"
    prop_name = ET.SubElement(producer, "property", {"name": "kdenlive:clipname"})
    prop_name.text = source_metadata.file_path.name

    # 4. Main Bin Playlist (Folder hierarchy and media references)
    main_bin = ET.SubElement(root, "playlist", {"id": "main_bin"})
    folder_prop = ET.SubElement(main_bin, "property", {"name": "kdenlive:folder.-1.1"})
    folder_prop.text = "Shorts Clips"

    # Add master clip into bin
    bin_entry = ET.SubElement(
        main_bin,
        "entry",
        {
            "producer": "producer_raw_source",
            "in": "0",
            "out": str(max(0, total_source_frames - 1)),
        },
    )
    bin_entry_folder = ET.SubElement(bin_entry, "property", {"name": "kdenlive:folder"})
    bin_entry_folder.text = "1"

    # 5. Timeline Playlist (Track V1 containing pre-cut clips)
    playlist_timeline = ET.SubElement(root, "playlist", {"id": "playlist_v1"})
    prop_track_name = ET.SubElement(playlist_timeline, "property", {"name": "kdenlive:track_name"})
    prop_track_name.text = "Video 1"

    total_timeline_frames = 0

    for i, clip in enumerate(clips):
        in_frame = seconds_to_frames(clip.start_seconds, fps)
        out_frame = seconds_to_frames(clip.end_seconds, fps)

        # Ensure out is strictly after in
        if out_frame <= in_frame:
            out_frame = in_frame + int(fps * 30)

        # Cap out_frame to source media length if known
        if total_source_frames > 0:
            out_frame = min(out_frame, total_source_frames - 1)
            in_frame = min(in_frame, out_frame - 1)

        clip_length = out_frame - in_frame + 1

        # Add spacer between clips (except before the first clip)
        if i > 0 and spacer_frames > 0:
            ET.SubElement(playlist_timeline, "blank", {"length": str(spacer_frames)})
            total_timeline_frames += spacer_frames

        entry = ET.SubElement(
            playlist_timeline,
            "entry",
            {
                "producer": "producer_raw_source",
                "in": str(in_frame),
                "out": str(out_frame),
            },
        )
        prop_clip_title = ET.SubElement(entry, "property", {"name": "kdenlive:clipname"})
        prop_clip_title.text = f"Short {i+1}: {clip.title}"

        total_timeline_frames += clip_length

    # 6. Main Tractor (multitrack composition)
    tractor = ET.SubElement(
        root,
        "tractor",
        {
            "id": "maintractor",
            "in": "0",
            "out": str(max(0, total_timeline_frames - 1)),
        },
    )
    multitrack = ET.SubElement(tractor, "multitrack")
    ET.SubElement(multitrack, "track", {"producer": "playlist_v1"})

    # 7. Consumer
    ET.SubElement(root, "consumer", {"target": "maintractor", "mlt_service": "xml"})

    # Convert to formatted indented XML string
    rough_string = ET.tostring(root, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def write_kdenlive_project(
    output_path: Path,
    source_metadata: MediaMetadata,
    clips: List[ValidatedClip],
    project_title: str = "AI Shorts Project",
) -> Path:
    """Builds and saves the .kdenlive project file to disk."""
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    xml_content = build_kdenlive_xml(
        source_metadata=source_metadata,
        clips=clips,
        project_title=project_title,
    )

    output_path.write_text(xml_content, encoding="utf-8")
    return output_path
