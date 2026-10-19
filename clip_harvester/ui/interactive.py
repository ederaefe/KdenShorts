"""Interactive user prompts, clip curation table, and timecode modification loop."""

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
    """Interactively prompts the user for a source media file path."""
    console.print("[bold cyan]>[/bold cyan] [bold bright_white]Drag & drop or enter path to video/audio file:[/bold bright_white]")
    while True:
        raw = Prompt.ask("  [dim]Path[/dim]")
        if not raw:
            continue
        p = clean_input_path(raw)
        if p.exists() and p.is_file():
            return p.resolve()
        error(f"File not found: '{p}'. Please enter a valid path.")


def prompt_for_profile() -> str:
    """Interactively prompts the user to select an extraction profile."""
    console.print("\n[bold cyan]>[/bold cyan] [bold bright_white]Select content profile:[/bold bright_white]")
    console.print("  [cyan]1[/cyan] [white]Sermon[/white]    [dim](theological insights, conviction, standalone revelations)[/dim]")
    console.print("  [cyan]2[/cyan] [white]Podcast[/white]   [dim](contrarian takes, energetic hooks, sharp punchlines)[/dim]")
    console.print("  [cyan]3[/cyan] [white]General[/white]   [dim](keynote highlights, universal wisdom, high-impact quotes)[/dim]")

    choice = Prompt.ask("  [dim]Select [1-3][/dim]", choices=["1", "2", "3"], default="1")
    mapping = {"1": "sermon", "2": "podcast", "3": "general"}
    return mapping[choice]


def render_clips_table(clips: List[ValidatedClip], active_indices: Set[int]) -> Table:
    """Builds a formatted, minimalist table of candidate clips."""
    table = Table(
        box=box.SIMPLE_HEAD,
        show_edge=False,
        pad_edge=False,
        expand=True,
        header_style="bold cyan",
    )

    table.add_column("SEL", justify="center", width=5, style="bold")
    table.add_column("#", justify="center", width=4, style="dim white")
    table.add_column("TITLE & HOOK", ratio=4)
    table.add_column("TIMECODE", justify="center", width=22)
    table.add_column("DUR", justify="right", width=8)
    table.add_column("TYPE", justify="center", width=16, style="dim white")
    table.add_column("CONF", justify="center", width=8)

    for i, clip in enumerate(clips, 1):
        is_active = (i - 1) in active_indices
        status_badge = "[green][X][/green]" if is_active else "[dim][ ][/dim]"
        title_style = "bold bright_white" if is_active else "dim white"
        hook_style = "dim cyan" if is_active else "dim grey50"

        title_hook = Text.assemble(
            (clip.title, title_style),
            ("\n", "default"),
            (f'"{clip.hook_sentence}"', hook_style),
        )

        timecode_str = f"{clip.start_timecode} -> {clip.end_timecode}"
        dur_str = f"{clip.duration_seconds:.1f}s"

        conf_color = "green" if clip.confidence == "high" else ("yellow" if clip.confidence == "medium" else "dim")
        conf_badge = f"[{conf_color}]{clip.confidence.upper()}[/{conf_color}]"

        table.add_row(
            status_badge,
            str(i),
            title_hook,
            timecode_str,
            dur_str,
            clip.hook_type,
            conf_badge,
        )

    return table


def edit_clip_timecode(clip: ValidatedClip) -> ValidatedClip:
    """Interactively modifies the start and end timestamps of a clip."""
    console.print(f"\n[cyan]Editing Clip: {clip.title}[/cyan]")
    console.print(f"Current range: [bold]{clip.start_timecode}[/bold] -> [bold]{clip.end_timecode}[/bold] ({clip.duration_seconds:.1f}s)")

    new_start_raw = Prompt.ask("  [dim]New start timecode (HH:MM:SS, or press Enter to keep)[/dim]", default=clip.start_timecode)
    new_end_raw = Prompt.ask("  [dim]New end timecode (HH:MM:SS, or press Enter to keep)[/dim]", default=clip.end_timecode)

    try:
        start_sec = timecode_to_seconds(new_start_raw)
        end_sec = timecode_to_seconds(new_end_raw)

        if start_sec >= end_sec:
            error("Start time must be earlier than end time. Changes discarded.")
            return clip

        dur = end_sec - start_sec
        success(f"Updated timecode: {new_start_raw} -> {new_end_raw} ({dur:.1f}s)")
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
        console.print()

        selected_count = len(active_indices)
        console.print(f" [dim]Selected {selected_count} of {len(current_clips)} clip(s)[/dim]")
        console.print("[dim]─" * 60 + "[/dim]")
        console.print(
            " [bold cyan][A][/bold cyan] Approve & build Kdenlive project  "
            " [bold cyan][T][/bold cyan] Toggle clips  "
            " [bold cyan][E][/bold cyan] Edit timecode  "
            " [bold cyan][Q][/bold cyan] Abort"
        )

        action = Prompt.ask(
            " [bold cyan]>[/bold cyan] Action",
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
            raw_input = Prompt.ask(" [dim]Toggle[/dim]").strip().lower()
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
            clip_num = IntPrompt.ask(" Enter clip number to edit", default=1)
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
    """Renders a sleek summary panel upon successful project export."""
    body = Text()
    body.append("PROJECT READY FOR KDENLIVE\n\n", style="bold green")
    body.append(f"Output File: ", style="bold white")
    body.append(f"{project_path}\n", style="cyan")
    body.append(f"Clips Placed: ", style="bold white")
    body.append(f"{len(clips)} pre-cut sequence(s)\n", style="bright_white")
    body.append(f"Aspect Ratio: ", style="bold white")
    body.append("1080x1920 (9:16 Vertical)\n\n", style="bright_white")
    body.append("Next Steps in Kdenlive:\n", style="bold cyan")
    body.append("  1. Double-click the .kdenlive file to launch.\n", style="dim white")
    body.append("  2. Reposition / pan & crop the speaker's face for vertical framing.\n", style="dim white")
    body.append("  3. Apply your color grading, captions, or watermarks.\n", style="dim white")
    body.append("  4. Render directly to MP4!\n", style="dim white")

    panel = Panel(
        body,
        box=box.ROUNDED,
        border_style="green",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()
