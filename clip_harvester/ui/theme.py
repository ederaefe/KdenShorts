"""Vibrant, colorful theme definitions, stylized banners, and layout primitives for the CLI UI."""

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# Vibrant, intentional, high-contrast neon developer palette
CUSTOM_THEME = Theme(
    {
        "primary": "bold bright_cyan",
        "secondary": "bold bright_magenta",
        "accent": "bold bright_yellow",
        "success": "bold bright_green",
        "warning": "bold bright_yellow",
        "danger": "bold bright_red",
        "muted": "dim white",
        "dim_cyan": "cyan dim",
        "badge_cyan": "bold black on bright_cyan",
        "badge_magenta": "bold black on bright_magenta",
        "badge_yellow": "bold black on bright_yellow",
        "badge_green": "bold black on bright_green",
        "badge_red": "bold black on bright_red",
        "badge_blue": "bold black on deep_sky_blue1",
    }
)

console = Console(theme=CUSTOM_THEME)


def render_header(version: str) -> None:
    """Renders a colorful, high-energy cyber banner for KdenShorts."""
    header_content = Text.from_markup(
        f"[bold bright_cyan]  KDENSHORTS[/bold bright_cyan]  "
        f"[dim]|[/dim]  [bold bright_white]AI-Assisted YouTube Shorts & Kdenlive Engine[/bold bright_white]\n\n"
        f"  [bold black on bright_cyan] CANVAS [/] [bold bright_white]1080x1920 (9:16 Vertical)[/]   "
        f"[bold black on bright_magenta] AI MODEL [/] [bold bright_white]Gemini 2.5 Flash[/]   "
        f"[bold black on bright_yellow] OUTPUT [/] [bold bright_white]Kdenlive Timeline[/]"
    )

    panel = Panel(
        header_content,
        box=box.ROUNDED,
        border_style="bright_cyan",
        title="[bold black on bright_cyan] KDENSHORTS [/] [bold black on bright_magenta] CLIP HARVESTER [/]",
        title_align="left",
        subtitle=f"[bold bright_yellow]v{version}[/] [dim]|[/dim] [bold bright_white]GPU-Free Cloud AI[/]",
        subtitle_align="right",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def render_step(step_idx: int, total_steps: int, label: str, detail: str = "") -> None:
    """Renders a colorful, structured progress divider for each workflow stage."""
    badge = f" STEP {step_idx:02d}/{total_steps:02d} "
    header_text = Text.assemble(
        (badge, "bold black on bright_cyan"),
        (" ", "default"),
        (f" {label.upper()}", "bold bright_white"),
    )
    if detail:
        header_text.append("  ")
        header_text.append(f" {detail} ", style="bold black on bright_magenta")

    console.print()
    console.print(header_text)
    console.print("[dim cyan]" + "━" * 68 + "[/dim cyan]")


def info(msg: str) -> None:
    """Prints a styled informational notice with a cyan badge."""
    console.print(f" [bold bright_cyan]>>>[/bold bright_cyan] [bright_white]{msg}[/bright_white]")


def success(msg: str) -> None:
    """Prints a styled success notice with an emerald badge."""
    console.print(f" [bold black on bright_green] OK [/bold black on bright_green] [bold bright_green]{msg}[/bold bright_green]")


def warning(msg: str) -> None:
    """Prints a styled warning notice with a golden badge."""
    console.print(f" [bold black on bright_yellow] WARN [/bold black on bright_yellow] [bold bright_yellow]{msg}[/bold bright_yellow]")


def error(msg: str) -> None:
    """Prints a styled error notice with a crimson badge."""
    console.print(f" [bold black on bright_red] ERR [/bold black on bright_red] [bold bright_red]{msg}[/bold bright_red]")
