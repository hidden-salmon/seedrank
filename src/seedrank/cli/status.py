"""seedrank status — Show workspace overview."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml

from seedrank.config.loader import load_config
from seedrank.data.db import get_db_path, get_table_counts
from seedrank.utils.console import console, error, heading, info, render_table


def status_cmd(
    config: Path = typer.Option(
        Path("seedrank.config.yaml"),
        "--config",
        "-c",
        help="Path to config file.",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace root directory.",
    ),
) -> None:
    """Show workspace overview — config, database stats, and pipeline state."""
    heading("pSEO Status")
    ws = workspace.resolve()

    # Load config
    try:
        cfg = load_config(config)
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    info(f"Product: {cfg.product.name} ({cfg.product.domain})")
    info(f"Competitors: {len(cfg.competitors)} | Personas: {len(cfg.personas)}")

    # Database stats
    db_path = get_db_path(ws)
    if db_path.exists():
        counts = get_table_counts(db_path)
        rows = [[name.replace("_", " ").title(), str(count)] for name, count in counts.items()]
        render_table(title="Database", columns=["Table", "Rows"], rows=rows)
    else:
        info("Database not initialized. Run 'seedrank init' first.")

    # Pipeline state
    state_path = ws / "pipeline" / "state.yaml"
    if state_path.exists():
        state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
        phase = state.get("phase", "unknown")
        next_action = state.get("next_action", "—")
        info(f"Phase: {phase}")
        info(f"Next: {next_action}")

    # Session logs count
    sessions_dir = ws / "sessions"
    if sessions_dir.exists():
        session_count = len(list(sessions_dir.glob("*.md")))
        info(f"Session logs: {session_count}")

    console.print()
