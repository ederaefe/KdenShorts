"""Interactive onboarding wizard with concurrent dependency downloading and live healthchecks."""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from rich import box
from rich.panel import Panel
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn
from rich.prompt import Confirm, Prompt
from rich.text import Text

from clip_harvester.ai.client import check_api_key_present, create_gemini_client
from clip_harvester.media.downloader import DependencyDownloader
from clip_harvester.ui.interactive import clean_input_path, prompt_for_media_file, prompt_for_profile
from clip_harvester.ui.theme import console, error, info, render_step, success, warning


def validate_gemini_api_key(api_key: str) -> Tuple[bool, str]:
    """Tests a Gemini API key against Google AI Studio with a lightweight ping."""
    try:
        client = create_gemini_client(api_key=api_key)
        # Fast 1-token test check to verify key validity and quota
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say 'OK'",
        )
        if response and response.text:
            return True, "API Key authenticated successfully."
        return True, "API Key authenticated."
    except Exception as e:
        return False, str(e)


def save_api_key_permanently(api_key: str) -> bool:
    """Persists the API key permanently in the user environment across OS platforms."""
    os.environ["GEMINI_API_KEY"] = api_key
    if os.name == "nt":
        try:
            cmd = [
                "powershell",
                "-Command",
                f"[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', '{api_key}', 'User')",
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False
    else:
        # macOS and Linux: append to active shell profile (~/.zshrc, ~/.bashrc, or ~/.profile)
        home = Path.home()
        candidates = [home / ".zshrc", home / ".bashrc", home / ".profile"]
        export_line = f'\nexport GEMINI_API_KEY="{api_key}"\n'

        for rc_file in candidates:
            if rc_file.exists():
                try:
                    with open(rc_file, "a", encoding="utf-8") as f:
                        f.write(export_line)
                    return True
                except Exception:
                    pass

        # Fallback to ~/.profile
        try:
            with open(home / ".profile", "a", encoding="utf-8") as f:
                f.write(export_line)
            return True
        except Exception:
            return False


def render_kdenlive_tips_panel() -> None:
    """Renders a colorful, educational guide on 9:16 vertical editing while downloads proceed."""
    tips = Text.from_markup(
        "[bold bright_cyan]MASTERING 9:16 VERTICAL EDITING IN KDENLIVE[/bold bright_cyan]\n\n"
        "  [bold bright_yellow]1. Vertical Canvas:[/]  [bright_white]KdenShorts automatically formats resolution to [/][bold bright_cyan]1080x1920 (9:16)[/].\n"
        "  [bold bright_yellow]2. Face Centering:[/]   [bright_white]Apply the [/][bold bright_magenta]'Transform'[/][bright_white] effect to Track V1 to dial in horizontal X-offset.[/]\n"
        "  [bold bright_yellow]3. Motion Tracking:[/]  [bright_white]Use Kdenlive's [/][bold deep_sky_blue1]'Motion Tracker'[/][bright_white] effect to follow pacing speakers.[/]\n"
        "  [bold bright_yellow]4. Dynamic Subtitles:[/] [bright_white]Run [/][bold bright_green]'Project -> Subtitles -> Speech Recognition'[/][bright_white] for animated captions.[/]"
    )

    panel = Panel(
        tips,
        box=box.ROUNDED,
        border_style="bright_blue",
        title="[bold black on bright_cyan] WORKFLOW TIPS [/]",
        title_align="left",
        padding=(1, 2),
    )
    console.print(panel)


def wait_for_downloader_with_progress(downloader: DependencyDownloader) -> bool:
    """Renders a live rich progress bar until the background downloader finishes."""
    if downloader.is_finished():
        _, _, _, err = downloader.get_snapshot()
        return err is None

    console.print("\n [bold cyan][WAIT][/bold cyan] Finalizing portable FFmpeg download...")
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("[cyan]Downloading FFmpeg static binaries...", total=100)

        while not downloader.is_finished():
            _, pct, status_text, _ = downloader.get_snapshot()
            progress.update(task_id, completed=pct, description=f"[cyan]{status_text}")
            time.sleep(0.2)

        progress.update(task_id, completed=100, description="[green]FFmpeg binaries ready.")

    completed, _, _, err = downloader.get_snapshot()
    if err:
        error(f"Background download failed: {err}")
        return False
    return True


def run_concurrent_onboarding(
    downloader: Optional[DependencyDownloader],
    media_path: Optional[Path] = None,
    profile_name: Optional[str] = None,
) -> Tuple[Path, str]:
    """Runs interactive user onboarding while background downloads proceed concurrently."""
    render_step(0, 5, "Interactive Setup & Dependency Sync")

    if downloader:
        info("Portable FFmpeg download initiated in background. Let's configure your project:")

    # 1. API Key Setup & Live Verification
    if not check_api_key_present():
        warning("GEMINI_API_KEY is not set.")
        console.print(" [dim]Get your free API key at: https://aistudio.google.com/[/dim]")
        while True:
            key_input = Prompt.ask(" [bold cyan]>[/bold cyan] Enter your Gemini API Key").strip()
            if not key_input:
                continue

            with console.status("[dim cyan]Testing API key with Google AI Studio...[/dim cyan]", spinner="dots"):
                is_valid, msg = validate_gemini_api_key(key_input)

            if is_valid:
                from clip_harvester.bootstrap import detect_os_info

                os_info = detect_os_info()
                success("Gemini API Key validated successfully!")
                if Confirm.ask(f" Save API key permanently for {os_info.display_name}?", default=True):
                    if save_api_key_permanently(key_input):
                        success(f"Saved permanently to {os_info.display_name} environment.")
                    else:
                        os.environ["GEMINI_API_KEY"] = key_input
                else:
                    os.environ["GEMINI_API_KEY"] = key_input
                break
            else:
                error(f"Validation failed: {msg}. Please check the key and try again.")
    else:
        success("Gemini API Key detected in environment.")

    # 2. Media Source Selection
    if not media_path or not media_path.exists():
        if media_path and not media_path.exists():
            warning(f"Specified media file does not exist: {media_path}")
        console.print()
        selected_media = prompt_for_media_file()
    else:
        selected_media = media_path.resolve()

    # 3. Profile Selection
    if not profile_name or profile_name not in ["sermon", "podcast", "general"]:
        selected_profile = prompt_for_profile()
    else:
        selected_profile = profile_name

    # 4. Display educational tips
    console.print()
    render_kdenlive_tips_panel()

    # 5. Barrier Synchronization: Wait for background download to finish
    if downloader:
        ok = wait_for_downloader_with_progress(downloader)
        if not ok:
            from clip_harvester.bootstrap import detect_os_info

            os_info = detect_os_info()
            error(f"Cannot proceed without FFmpeg. Please install manually for {os_info.display_name}: {os_info.ffmpeg_install_cmd}")
            raise RuntimeError("FFmpeg dependency unavailable.")
        success("All system dependencies verified.")

    return selected_media, selected_profile
