"""seedrank session — Session start/end management."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer
import yaml

from seedrank.utils.console import console, heading, info, success
from seedrank.utils.paths import find_workspace

session_app = typer.Typer(help="Session management commands.", no_args_is_help=True)


def _load_state(workspace: Path) -> dict:
    """Load pipeline state from state.yaml."""
    state_path = workspace / "pipeline" / "state.yaml"
    if not state_path.exists():
        return {}
    return yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}


def _save_state(workspace: Path, state: dict) -> None:
    """Save pipeline state to state.yaml."""
    state_path = workspace / "pipeline" / "state.yaml"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(yaml.dump(state, default_flow_style=False), encoding="utf-8")


def _get_last_session_log(workspace: Path) -> str | None:
    """Find and read the most recent session log."""
    sessions_dir = workspace / "sessions"
    if not sessions_dir.exists():
        return None
    logs = sorted(sessions_dir.glob("*.md"), reverse=True)
    if not logs:
        return None
    return logs[0].read_text(encoding="utf-8")


@session_app.command(name="start")
def session_start() -> None:
    """Start a new session — loads context from last session."""
    try:
        workspace = find_workspace()
    except FileNotFoundError as e:
        console.print(f"[error]{e}[/error]")
        raise typer.Exit(1)

    heading("Session Start")

    state = _load_state(workspace)
    if state:
        phase = state.get("phase", "unknown")
        next_action = state.get("next_action", "No next action recorded")
        progress = state.get("progress", {})

        info(f"Current phase: {phase}")
        info(f"Next action: {next_action}")

        if progress:
            console.print("\n  [bold]Progress:[/bold]")
            for key, val in progress.items():
                console.print(f"    {key.replace('_', ' ').title()}: {val}")

    last_log = _get_last_session_log(workspace)
    if last_log:
        console.print("\n  [bold]Last session log:[/bold]")
        # Show first 20 lines of last session
        lines = last_log.strip().split("\n")
        for line in lines[:20]:
            console.print(f"    {line}")
        if len(lines) > 20:
            console.print(f"    [muted]... ({len(lines) - 20} more lines)[/muted]")
    else:
        info("No previous session logs found.")

    console.print()
    success(
        "Session started. Use commands to work, then run 'seedrank session end' when done."
    )


@session_app.command(name="end")
def session_end(
    summary: str = typer.Argument(help="Summary of what was accomplished this session."),
) -> None:
    """End the current session — writes session log and updates state."""
    try:
        workspace = find_workspace()
    except FileNotFoundError as e:
        console.print(f"[error]{e}[/error]")
        raise typer.Exit(1)

    heading("Session End")

    now = datetime.now(UTC)
    timestamp = now.strftime("%Y-%m-%d-%H%M")

    # Write session log
    sessions_dir = workspace / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    log_path = sessions_dir / f"{timestamp}.md"

    log_content = f"""# Session {timestamp}

## Summary

{summary}

## Timestamp

{now.isoformat()}
"""
    log_path.write_text(log_content, encoding="utf-8")
    info(f"Session log written: sessions/{timestamp}.md")

    # Update state
    state = _load_state(workspace)
    state["last_session"] = timestamp
    _save_state(workspace, state)

    success("Session ended.")
