"""Rich console output helpers."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

pseo_theme = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red bold",
        "heading": "bold magenta",
        "muted": "dim",
    }
)

console = Console(theme=pseo_theme)


def heading(text: str) -> None:
    """Print a section heading."""
    console.print(f"\n[heading]{text}[/heading]")


def success(text: str) -> None:
    """Print a success message."""
    console.print(f"[success]{text}[/success]")


def warning(text: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]{text}[/warning]")


def error(text: str) -> None:
    """Print an error message."""
    console.print(f"[error]{text}[/error]")


def info(text: str) -> None:
    """Print an info message."""
    console.print(f"[info]{text}[/info]")


def banner(title: str, subtitle: str = "") -> None:
    """Print a styled banner."""
    content = f"[bold]{title}[/bold]"
    if subtitle:
        content += f"\n[muted]{subtitle}[/muted]"
    console.print(Panel(content, border_style="cyan", padding=(1, 2)))


def render_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    """Render a Rich table."""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    for col in columns:
        table.add_column(col)
    for row in rows:
        table.add_row(*row)
    console.print(table)
