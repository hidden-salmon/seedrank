"""Path helpers for workspace and package directories."""

from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent.parent


def find_workspace(start: Path | None = None) -> Path:
    """Find the workspace root by looking for seedrank.config.yaml.

    Walks up from `start` (default: cwd) until it finds seedrank.config.yaml.

    Raises:
        FileNotFoundError: If no config file is found.
    """
    current = start or Path.cwd()
    current = current.resolve()

    for parent in [current, *current.parents]:
        if (parent / "seedrank.config.yaml").exists():
            return parent
    raise FileNotFoundError(
        "No seedrank.config.yaml found in current directory or any parent.\n"
        "Run 'seedrank init' to create a workspace, or cd into an existing one."
    )


def workspace_dirs(root: Path) -> dict[str, Path]:
    """Return standard workspace directory paths."""
    return {
        "data": root / "data",
        "competitors": root / "data" / "competitors",
        "pipeline": root / "pipeline",
        "sessions": root / "sessions",
        "decisions": root / "decisions",
        "research": root / "research",
        "briefs": root / "briefs",
        "content": root / "content",
        "claude": root / ".claude",
    }


def ensure_workspace_dirs(root: Path) -> None:
    """Create all standard workspace directories."""
    for dir_path in workspace_dirs(root).values():
        dir_path.mkdir(parents=True, exist_ok=True)
