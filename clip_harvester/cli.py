"""Sleek, interactive command-line interface and orchestrator for Clip Harvester."""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from clip_harvester import __version__
from clip_harvester.ai.client import (
    analyze_audio_chunk,
    check_api_key_present,
    create_gemini_client,
)
from clip_harvester.ai.models import ChunkAnalysisResult, ValidatedClip
from clip_harvester.ai.prompts import build_chunk_prompt
from clip_harvester.ai.validator import validate_and_filter_clips
from clip_harvester.config import CONFIG, resolve_model_name
from rich.prompt import Confirm
from clip_harvester.kdenlive.launcher import open_in_kdenlive
from clip_harvester.kdenlive.timecode import seconds_to_timecode
from clip_harvester.kdenlive.xml_builder import write_kdenlive_project
from clip_harvester.media.audio import AudioChunk, extract_and_chunk_audio
from clip_harvester.media.downloader import (
    DependencyDownloader,
    check_ffmpeg_available,
    ensure_bin_in_path,
)
from clip_harvester.media.probe import (
    probe_media_file,
    verify_ffmpeg_installed,
    verify_ffprobe_installed,
)
from clip_harvester.ui.interactive import (
    curate_clips_interactively,
    prompt_for_media_file,
    prompt_for_profile,
    render_summary_panel,
)
from clip_harvester.ui.onboarding import run_concurrent_onboarding
from clip_harvester.ui.theme import (
    console,
    error,
    info,
    render_header,
    render_step,
    success,
    warning,
)


def perform_preflight_checks(strict: bool = False) -> Tuple[bool, bool, bool]:
    """Verifies system binaries and credentials, returning availability flags.

    Args:
        strict: When True, prints an error panel and terminates if any dependency is missing.

    Returns:
        Tuple of (has_ffmpeg, has_ffprobe, has_api_key).
    """
    ensure_bin_in_path()
    has_ffmpeg, has_ffprobe = check_ffmpeg_available()
    has_key = check_api_key_present()

    if strict and (not has_ffmpeg or not has_ffprobe or not has_key):
        missing = []
        if not has_ffmpeg:
            missing.append("ffmpeg is not installed or not discoverable in Windows PATH.")
        if not has_ffprobe:
            missing.append("ffprobe is not installed or not discoverable in Windows PATH.")
        if not has_key:
            missing.append("GEMINI_API_KEY environment variable is not set. Run: $env:GEMINI_API_KEY='key'")

        console.print()
        error("Pre-flight environment checks failed:")
        for item in missing:
            console.print(f"   [dim red]•[/dim red] {item}")
        console.print("\n [dim]Please address the prerequisites above and re-run.[/dim]\n")
        sys.exit(1)

    return has_ffmpeg, has_ffprobe, has_key


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="kdenshorts",
        description="KdenShorts: AI-assisted tool for extracting YouTube Shorts into Kdenlive.",
    )

    parser.add_argument(
        "media_path",
        type=Path,
        nargs="?",
        default=None,
        help="Path to source video/audio file (optional; interactive prompt triggers if omitted).",
    )
    parser.add_argument(
        "--profile",
        "-p",
        type=str,
        default="sermon",
        choices=["sermon", "podcast", "general"],
        help="Clip selection criteria profile (default: sermon).",
    )
    parser.add_argument(
        "--max-clips",
        "-n",
        type=int,
        default=CONFIG.default_max_clips,
        help=f"Maximum number of clips to extract (default: {CONFIG.default_max_clips}).",
    )
    parser.add_argument(
        "--min-duration",
        type=int,
        default=CONFIG.default_min_duration,
        help=f"Minimum clip duration in seconds (default: {CONFIG.default_min_duration}).",
    )
    parser.add_argument(
        "--max-duration",
        type=int,
        default=CONFIG.default_max_duration,
        help=f"Maximum clip duration in seconds (default: {CONFIG.default_max_duration}).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Custom output path for the .kdenlive project.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=CONFIG.default_model,
        help=f"Gemini model identifier or alias ('flash', 'flash-latest', 'pro'. Default: {CONFIG.default_model}).",
    )
    parser.add_argument(
        "--chunk-duration",
        type=int,
        default=CONFIG.chunk_duration_seconds,
        help=f"Audio chunk length in seconds (default: {CONFIG.chunk_duration_seconds}s / 20 min).",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Auto-approve all detected clips without interactive review.",
    )
    parser.add_argument(
        "--open",
        "-O",
        dest="open_kdenlive",
        action="store_true",
        help="Automatically launch Kdenlive with the compiled project once complete.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Retain temporary audio chunks after completion.",
    )

    return parser.parse_args()


def run_pipeline() -> int:
    """Executes the interactive Clip Harvester workflow."""
    args = parse_arguments()
    render_header(__version__)

    has_ffmpeg, has_ffprobe, has_key = perform_preflight_checks(strict=False)
    needs_downloader = not (has_ffmpeg and has_ffprobe)

    downloader: Optional[DependencyDownloader] = None
    if needs_downloader:
        info("FFmpeg/FFprobe binaries not detected. Launching portable background downloader...")
        downloader = DependencyDownloader()
        downloader.start()

    # Determine if onboarding wizard is required
    needs_onboarding = (
        downloader is not None
        or not has_key
        or args.media_path is None
        or not args.media_path.exists()
    )

    if needs_onboarding:
        try:
            source_media, profile_choice = run_concurrent_onboarding(
                downloader=downloader,
                media_path=args.media_path,
                profile_name=args.profile,
            )
        except RuntimeError as e:
            error(f"Onboarding failed: {e}")
            return 1
    else:
        source_media = args.media_path.resolve()
        profile_choice = args.profile

    if not source_media.exists():
        error(f"Source file does not exist: {source_media}")
        return 1

    # 2. Output path calculation
    if args.output:
        output_kdenlive = args.output.resolve()
    else:
        output_kdenlive = source_media.parent / f"{source_media.stem}_shorts.kdenlive"

    # 3. Stage 1: Inspect Metadata
    render_step(1, 5, "Inspect Source Media", source_media.name)
    with console.status("[dim cyan]Probing video streams and frame rate with ffprobe...[/dim cyan]", spinner="dots"):
        try:
            metadata = probe_media_file(source_media)
        except Exception as e:
            error(f"Failed to inspect media: {e}")
            return 1

    info(f"Duration:   [bold bright_white]{seconds_to_timecode(metadata.duration_seconds)}[/bold bright_white] ({metadata.duration_seconds:.1f}s)")
    info(f"Resolution: [bold bright_white]{metadata.width}x{metadata.height}[/bold bright_white] | Canvas: [cyan]9:16 Vertical[/cyan]")
    info(f"Frame Rate: [bold bright_white]{metadata.fps} FPS[/bold bright_white] ({metadata.fps_num}/{metadata.fps_den})")

    # 4. Stage 2: Extract & Chunk Audio
    render_step(2, 5, "Audio Segmentation", f"{args.chunk_duration // 60}m chunks")
    temp_dir = Path(tempfile.mkdtemp(prefix="clip_harvester_"))
    try:
        with console.status("[dim cyan]Downsampling to 16kHz mono and slicing audio with ffmpeg...[/dim cyan]", spinner="dots"):
            chunks = extract_and_chunk_audio(
                source_media=source_media,
                output_dir=temp_dir,
                chunk_seconds=args.chunk_duration,
            )
        success(f"Generated {len(chunks)} audio chunk(s) for analysis.")
    except Exception as e:
        error(f"Audio extraction failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return 1

    # 5. Stage 3: Gemini Analysis
    model_name = resolve_model_name(args.model)
    render_step(3, 5, "AI Audio Understanding", f"{model_name} • {profile_choice}")
    client = create_gemini_client()
    chunk_results: List[Tuple[AudioChunk, ChunkAnalysisResult]] = []

    for i, chunk in enumerate(chunks):
        c_start = chunk.offset_timecode
        c_end = seconds_to_timecode(chunk.offset_seconds + chunk.duration_seconds)
        status_label = f"Processing segment {i + 1}/{len(chunks)} [{c_start} -> {c_end}]"

        prompt = build_chunk_prompt(
            offset_seconds=chunk.offset_seconds,
            chunk_index=i,
            total_chunks=len(chunks),
            profile_name=profile_choice,
            min_duration=args.min_duration,
            max_duration=args.max_duration,
        )

        with console.status(f"[dim cyan]{status_label}...[/dim cyan]", spinner="dots"):
            try:
                analysis = analyze_audio_chunk(
                    client=client,
                    audio_path=chunk.file_path,
                    prompt=prompt,
                    model_name=model_name,
                )
                chunk_results.append((chunk, analysis))
                info(f"Segment {i + 1:02d}: Extracted {len(analysis.clips)} candidate(s) [{c_start} -> {c_end}]")
            except Exception as e:
                warning(f"Segment {i + 1:02d} failed: {e}")

    # 6. Stage 4: Filter & Review Clips
    render_step(4, 5, "Clip Review & Curation")
    candidate_clips: List[ValidatedClip] = validate_and_filter_clips(
        chunk_pairs=chunk_results,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        max_clips=args.max_clips,
        head_padding=CONFIG.head_padding_seconds,
    )

    if not candidate_clips:
        warning("No clips matched the duration and complete-thought thresholds.")
        info("Try running with broader bounds (--min-duration 20 --max-duration 90) or another profile.")
        if not args.keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return 0

    # Interactive curation or auto-approval
    if args.yes:
        info(f"Auto-approving {len(candidate_clips)} clip(s) (--yes specified).")
        approved_clips = candidate_clips
    else:
        info("Opening interactive curation panel:")
        approved_clips = curate_clips_interactively(candidate_clips)

    if not approved_clips:
        warning("Operation cancelled. No clips were selected for export.")
        if not args.keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return 0

    success(f"Confirmed {len(approved_clips)} clip(s) for final compilation.")

    # 7. Stage 5: Synthesize Kdenlive Project
    render_step(5, 5, "Kdenlive Project Synthesis", output_kdenlive.name)
    try:
        with console.status("[dim cyan]Generating MLT XML timeline structure...[/dim cyan]", spinner="dots"):
            write_kdenlive_project(
                output_path=output_kdenlive,
                source_metadata=metadata,
                clips=approved_clips,
                project_title=f"{source_media.stem} Shorts",
            )
        success(f"Compiled: {output_kdenlive}")
    except Exception as e:
        error(f"Failed to generate Kdenlive project: {e}")
        return 1
    finally:
        if not args.keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            info(f"Temporary chunks preserved at: {temp_dir}")

    # Final Summary
    render_summary_panel(output_kdenlive, approved_clips)

    # Optional automatic launch into Kdenlive GUI
    should_launch = args.open_kdenlive
    if not should_launch and not args.yes:
        should_launch = Confirm.ask(
            " [bold cyan]?[/bold cyan] [bold bright_white]Open this project in Kdenlive now?[/bold bright_white]",
            default=True,
        )

    if should_launch:
        info("Launching Kdenlive...")
        if open_in_kdenlive(output_kdenlive):
            success(f"Kdenlive launched with {output_kdenlive.name} loaded!")
        else:
            warning("Could not launch Kdenlive automatically. Please double-click the project file to open.")
            info("To install Kdenlive on Windows, run: winget install KDE.Kdenlive")

    return 0


def main() -> None:
    """CLI entry point wrapper."""
    sys.exit(run_pipeline())


if __name__ == "__main__":
    main()
