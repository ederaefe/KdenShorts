"""Interactive user prompts, colorful clip curation table, and timecode modification loop."""

from pathlib import Path
from typing import List, Optional, Set

from rich import box
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from clip_harvester.ai.models import ValidatedClip
from clip_harvester.config import CONFIG, resolve_model_name
from clip_harvester.kdenlive.timecode import seconds_to_timecode, timecode_to_seconds
from clip_harvester.ui.theme import console, error, info, success, warning


def clean_input_path(raw_path: str) -> Path:
    """Cleans up drag-and-dropped file paths by stripping quotes and whitespace."""
    cleaned = raw_path.strip()
    if cleaned.startswith("&"):
        cleaned = cleaned[1:].strip()
    while len(cleaned) >= 2 and cleaned[0] in "'\"" and cleaned[-1] in "'\"":
        cleaned = cleaned[1:-1].strip()
    return Path(cleaned)


def prompt_for_media_file() -> Path:
    """Interactively prompts the user for a source media file path with colorful styling."""
    console.print()
    console.print(
        " [bold black on bright_cyan] INPUT [/bold black on bright_cyan] "
        "[bold bright_white]Drag & drop or enter path to video/audio recording:[/bold bright_white]"
    )
    while True:
        raw = Prompt.ask(" [bold bright_cyan] >>> [/bold bright_cyan][dim]Path[/dim]")
        if not raw:
            continue
        p = clean_input_path(raw)
        if p.exists() and p.is_file():
            return p.resolve()
        error(f"File not found: '{p}'. Please enter a valid path.")


def prompt_for_profile() -> str:
    """Interactively prompts the user to select an extraction profile with colorful options."""
    console.print()
    console.print(
        " [bold black on bright_magenta] PROFILE [/bold black on bright_magenta] "
        "[bold bright_white]Select content evaluation criteria:[/bold bright_white]"
    )
    console.print("   [bold black on bright_cyan] 1 [/] [bold bright_white]SERMON [/]  [dim]|[/] [bright_yellow]Theological depth, conviction, scripture revelations[/]")
    console.print("   [bold black on bright_cyan] 2 [/] [bold bright_white]PODCAST[/]  [dim]|[/] [bright_magenta]Contrarian debates, energetic banter, comedic punchlines[/]")
    console.print("   [bold black on bright_cyan] 3 [/] [bold bright_white]GENERAL[/]  [dim]|[/] [bright_cyan]Keynote wisdom, universal quotes, actionable ideas[/]")

    choice = Prompt.ask(" [bold bright_cyan] >>> [/bold bright_cyan][dim]Select [1-3][/dim]", choices=["1", "2", "3"], default="1")
    mapping = {"1": "sermon", "2": "podcast", "3": "general"}
    return mapping[choice]


def render_clips_table(clips: List[ValidatedClip], active_indices: Set[int]) -> Table:
    """Builds a vibrant, colorful, high-contrast table of candidate clips."""
    table = Table(
        box=box.ROUNDED,
        border_style="bright_blue",
        show_edge=True,
        pad_edge=True,
        expand=True,
        header_style="bold bright_white on dark_blue",
    )

    table.add_column("SEL", justify="center", width=8)
    table.add_column("#", justify="center", width=4, style="bold bright_white")
    table.add_column("TITLE & HOOK SENTENCE", ratio=4)
    table.add_column("TIMECODE", justify="center", width=24)
    table.add_column("DUR", justify="right", width=9)
    table.add_column("TYPE", justify="center", width=18)
    table.add_column("CONF", justify="center", width=10)

    for i, clip in enumerate(clips, 1):
        is_active = (i - 1) in active_indices

        if is_active:
            status_badge = "[bold black on bright_green] INCL [/]"
            title_style = "bold bright_cyan"
            hook_style = "italic bright_yellow"
            tc_style = "bold bright_white"
            dur_style = "bold bright_magenta"
            type_badge = f"[bold black on deep_sky_blue1] {clip.hook_type.upper().replace('_', ' ')[:14]} [/]"
            conf_color = "bright_green" if clip.confidence == "high" else ("bright_yellow" if clip.confidence == "medium" else "dim")
            conf_badge = f"[bold black on {conf_color}] {clip.confidence.upper()} [/]"
        else:
            status_badge = "[dim] SKIP [/]"
            title_style = "dim white"
            hook_style = "dim grey50"
            tc_style = "dim"
            dur_style = "dim"
            type_badge = f"[dim]{clip.hook_type}[/dim]"
            conf_badge = f"[dim]{clip.confidence}[/dim]"

        title_hook = Text.assemble(
            (clip.title, title_style),
            ("\n", "default"),
            (f'"{clip.hook_sentence}"', hook_style),
        )

        timecode_str = f"[{tc_style}]{clip.start_timecode}[/] [dim cyan]->[/] [{tc_style}]{clip.end_timecode}[/]"
        dur_str = f"[{dur_style}]{clip.duration_seconds:.1f}s[/]"

        table.add_row(
            status_badge,
            str(i),
            title_hook,
            timecode_str,
            dur_str,
            type_badge,
            conf_badge,
        )

    return table


def edit_clip_timecode(clip: ValidatedClip) -> ValidatedClip:
    """Interactively modifies the start and end timestamps of a clip with colorful feedback."""
    console.print(f"\n [bold black on bright_yellow] EDIT [/bold black on bright_yellow] [bold bright_cyan]Clip: {clip.title}[/bold bright_cyan]")
    console.print(
        f" Current range: [bold bright_white]{clip.start_timecode}[/] [dim cyan]->[/] "
        f"[bold bright_white]{clip.end_timecode}[/] ([bold bright_magenta]{clip.duration_seconds:.1f}s[/])"
    )

    new_start_raw = Prompt.ask(" [bold bright_cyan] >>> [/bold bright_cyan][dim]New start timecode (HH:MM:SS, Enter to keep)[/dim]", default=clip.start_timecode)
    new_end_raw = Prompt.ask(" [bold bright_cyan] >>> [/bold bright_cyan][dim]New end timecode (HH:MM:SS, Enter to keep)[/dim]", default=clip.end_timecode)

    try:
        start_sec = timecode_to_seconds(new_start_raw)
        end_sec = timecode_to_seconds(new_end_raw)

        if start_sec >= end_sec:
            error("Start time must be earlier than end time. Changes discarded.")
            return clip

        dur = end_sec - start_sec
        success(f"Updated timecode: [bold bright_white]{new_start_raw}[/] -> [bold bright_white]{new_end_raw}[/] ([bold bright_magenta]{dur:.1f}s[/])")
        return ValidatedClip(
            clip_id=clip.clip_id,
            title=clip.title,
            hook_sentence=clip.hook_sentence,
            start_seconds=start_sec,
            end_seconds=end_sec,
            duration_seconds=round(dur, 2),
            start_timecode=seconds_to_timecode(start_sec),
            end_timecode=seconds_to_timecode(end_sec),
            reasoning=clip.reasoning,
            confidence=clip.confidence,
            hook_type=clip.hook_type,
            chunk_index=clip.chunk_index,
        )
    except ValueError as e:
        error(f"Invalid timecode format: {e}. Changes discarded.")
        return clip


def curate_clips_interactively(clips: List[ValidatedClip]) -> List[ValidatedClip]:
    """Displays interactive curation table allowing user to approve, toggle, or edit clips."""
    if not clips:
        return []

    active_indices: Set[int] = set(range(len(clips)))
    current_clips = list(clips)

    while True:
        console.print()
        console.print(render_clips_table(current_clips, active_indices))

        selected_count = len(active_indices)
        status_line = (
            f" [bold bright_magenta]Active Clips:[/] [bold bright_white]{selected_count}[/] of [bold bright_white]{len(current_clips)}[/] selected  "
            f"[dim]|[/dim]  [dim]Canvas: 1080x1920 (9:16)[/dim]"
        )
        console.print(status_line)
        console.print("[dim cyan]" + "━" * 68 + "[/dim cyan]")

        # Colorful keyboard action bar
        console.print(
            " [bold black on bright_green] A [/] Approve & Export   "
            "[bold black on bright_cyan] T [/] Toggle Clips   "
            "[bold black on bright_yellow] E [/] Edit Timecode   "
            "[bold black on bright_red] Q [/] Abort"
        )

        action = Prompt.ask(
            " [bold bright_cyan] >>> [/bold bright_cyan][bold bright_white]Action[/bold bright_white]",
            choices=["A", "a", "T", "t", "E", "e", "Q", "q"],
            default="A",
        ).upper()

        if action == "A":
            if not active_indices:
                warning("No clips are currently selected. Select at least one clip.")
                continue
            approved = [current_clips[i] for i in sorted(active_indices)]
            return approved

        elif action == "T":
            console.print(" Enter clip numbers to toggle (e.g. '1, 3' or 'all'):")
            raw_input = Prompt.ask(" [bold bright_cyan] >>> [/bold bright_cyan][dim]Toggle[/dim]").strip().lower()
            if raw_input == "all":
                if len(active_indices) == len(current_clips):
                    active_indices.clear()
                else:
                    active_indices = set(range(len(current_clips)))
            else:
                for token in raw_input.replace(",", " ").split():
                    try:
                        num = int(token)
                        idx = num - 1
                        if 0 <= idx < len(current_clips):
                            if idx in active_indices:
                                active_indices.remove(idx)
                            else:
                                active_indices.add(idx)
                    except ValueError:
                        pass

        elif action == "E":
            clip_num = IntPrompt.ask(" [bold bright_cyan] >>> [/bold bright_cyan]Enter clip number to edit", default=1)
            idx = clip_num - 1
            if 0 <= idx < len(current_clips):
                updated_clip = edit_clip_timecode(current_clips[idx])
                current_clips[idx] = updated_clip
            else:
                warning(f"Clip number {clip_num} does not exist.")

        elif action == "Q":
            if Confirm.ask(" Discard all clips and exit?"):
                return []


def render_summary_panel(project_path: Path, clips: List[ValidatedClip]) -> None:
    """Renders a colorful, high-contrast summary panel upon successful project export."""
    body = Text.from_markup(
        f"[bold bright_green]PROJECT COMPILED FOR KDENLIVE[/bold bright_green]\n\n"
        f"[bold bright_white]Output Path:[/]  [bold bright_cyan]{project_path}[/]\n"
        f"[bold bright_white]Sequences:[/]    [bold black on bright_magenta] {len(clips)} PRE-CUT CLIPS [/]  "
        f"[bold black on bright_yellow] 1080x1920 (9:16 VERTICAL) [/]  "
        f"[bold black on deep_sky_blue1] MLT XML [/]\n\n"
        f"[bold bright_cyan]Post-Production Workflow in Kdenlive:[/bold bright_cyan]\n"
        f"  [bold bright_yellow]1.[/] [bright_white]Double-click the .kdenlive file to open directly in the editor.[/]\n"
        f"  [bold bright_yellow]2.[/] [bright_white]Use 'Transform' or 'Motion Tracker' on Track V1 to center speaker's face.[/]\n"
        f"  [bold bright_yellow]3.[/] [bright_white]Run 'Project -> Subtitles -> Speech Recognition' for animated captions.[/]\n"
        f"  [bold bright_yellow]4.[/] [bright_white]Batch render individual 9:16 Shorts directly to MP4![/]"
    )

    panel = Panel(
        body,
        box=box.ROUNDED,
        border_style="bright_green",
        title="[bold black on bright_green] EXPORT COMPLETE [/]",
        title_align="left",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()
