"""Minimalist theme, color definitions, and layout primitives for the terminal UI."""

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# Intentional, high-contrast, distraction-free palette
CUSTOM_THEME = Theme(
    {
        "primary": "bold cyan",
        "secondary": "bright_white",
        "muted": "dim white",
        "dim_cyan": "cyan dim",
        "accent": "bold bright_white",
        "success": "bold green",
        "warning": "bold yellow",
        "danger": "bold red",
        "tag": "reverse cyan",
    }
)

console = Console(theme=CUSTOM_THEME)


def render_header(version: str) -> None:
    """Renders a sleek, border-constrained header banner without clutter."""
    title = Text("KDENSHORTS", style="bold bright_white")
    subtitle = Text(f" v{version}  |  AI-Assisted YouTube Shorts & Kdenlive Engine", style="dim_cyan")

    panel = Panel(
        Text.assemble(title, "\n", subtitle),
        box=box.ROUNDED,
        border_style="dim_cyan",
        padding=(0, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def render_step(step_idx: int, total_steps: int, label: str, detail: str = "") -> None:
    """Renders an intentional, structured progress header for a workflow stage."""
    badge = f"[{step_idx:02d}/{total_steps:02d}]"
    header_text = Text.assemble(
        (badge, "bold cyan"),
        (" ", "default"),
        (label.upper(), "bold bright_white"),
    )
    if detail:
        header_text.append(f"  ({detail})", style="dim white")

    console.print()
    console.print(header_text)
    console.print("[dim]─" * 60 + "[/dim]")


def info(msg: str) -> None:
    """Prints a standard info notice."""
    console.print(f" [cyan]•[/cyan] {msg}")


def success(msg: str) -> None:
    """Prints a success notice."""
    console.print(f" [green][OK][/green] [bright_white]{msg}[/bright_white]")


def warning(msg: str) -> None:
    """Prints a warning notice."""
    console.print(f" [yellow][WARN][/yellow] [yellow]{msg}[/yellow]")


def error(msg: str) -> None:
    """Prints an error notice."""
    console.print(f" [red][ERR][/red] [bold red]{msg}[/bold red]")
