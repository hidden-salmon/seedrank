"""seedrank calendar — Content calendar management."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from seedrank.utils.console import console, error, heading, info, render_table, success

calendar_app = typer.Typer(help="Content calendar commands.", no_args_is_help=True)


@calendar_app.command(name="add")
def calendar_add(
    slug: str = typer.Argument(help="Article slug to add to calendar."),
    keywords: str = typer.Option("", "--keywords", "-k", help="Comma-separated target keywords."),
    priority: float = typer.Option(0.0, "--priority", "-p", help="Manual priority score override."),
    explain: bool = typer.Option(
        False, "--explain", help="Show priority score breakdown."
    ),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Add an article to the content calendar."""
    heading("Add to Calendar")

    from seedrank.data.calendar import add_to_calendar, explain_priority_score
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    kw_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []

    with connect(db_path) as conn:
        add_to_calendar(conn, slug=slug, target_keywords=kw_list, priority_score=priority)

        if explain and kw_list and priority == 0.0:
            breakdown = explain_priority_score(conn, kw_list)
            info(f"Priority score: {breakdown['total']:.3f}")
            info(f"Keywords matched: {breakdown['keywords_found']}/{len(kw_list)}")
            for name, comp in breakdown["components"].items():
                info(f"  {name}: {comp['score']:.3f} (weight={comp['weight']})")

    success(f"Added '{slug}' to content calendar.")


@calendar_app.command(name="next")
def calendar_next(
    count: int = typer.Option(5, "--count", "-n", help="Number of items to show."),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Show next priority items from the content calendar."""
    from seedrank.data.calendar import get_next_items
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        rows = get_next_items(conn, count=count)

    if as_json:
        console.print_json(json.dumps(rows, default=str))
        return

    heading("Next Calendar Items")
    if not rows:
        info("Calendar is empty.")
        return

    table_rows = [
        [
            r["slug"],
            f"{r.get('priority_score', 0):.2f}",
            r.get("status", "—"),
            r.get("target_keywords") or "—",
        ]
        for r in rows
    ]
    render_table("Next Up", ["Slug", "Priority", "Status", "Keywords"], table_rows)


@calendar_app.command(name="update")
def calendar_update(
    slug: str = typer.Argument(help="Article slug to update."),
    status: str = typer.Option(
        ..., "--status", "-s", help="New status: queued, writing, review, done, cancelled."
    ),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Update calendar item status."""
    heading("Update Calendar")

    from seedrank.data.calendar import update_calendar_status
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    valid_statuses = {"queued", "writing", "review", "done", "cancelled"}
    if status not in valid_statuses:
        error(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        update_calendar_status(conn, slug=slug, status=status)

    success(f"Updated '{slug}' status to '{status}'.")
