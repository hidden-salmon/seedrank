"""seedrank gsc — Google Search Console commands."""

from __future__ import annotations

from pathlib import Path

import typer

from seedrank.utils.console import error, heading, info, success, warning

gsc_app = typer.Typer(help="Google Search Console commands.", no_args_is_help=True)


@gsc_app.command(name="auth")
def gsc_auth(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Authenticate with Google Search Console via OAuth."""
    heading("GSC Authentication")

    from seedrank.config.loader import load_config
    from seedrank.integrations.gsc import authenticate

    try:
        cfg = load_config(workspace / "seedrank.config.yaml")
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    if not cfg.gsc.property_url:
        error("GSC property_url not set in config. Add gsc.property_url to seedrank.config.yaml.")
        raise typer.Exit(1)

    credentials_path = Path(cfg.gsc.credentials_path)
    if not credentials_path.is_absolute():
        credentials_path = workspace.resolve() / credentials_path

    authenticate(credentials_path)
    success("GSC authentication complete.")


@gsc_app.command(name="sync")
def gsc_sync(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to sync."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Sync performance data from Google Search Console."""
    heading("GSC Sync")

    from seedrank.config.loader import load_config
    from seedrank.data.db import connect, get_db_path
    from seedrank.data.performance import upsert_performance
    from seedrank.integrations.gsc import GSCClient, match_url_to_slug

    try:
        cfg = load_config(workspace / "seedrank.config.yaml")
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    if not cfg.gsc.property_url:
        error("GSC property_url not set in config.")
        raise typer.Exit(1)

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    credentials_path = Path(cfg.gsc.credentials_path)
    if not credentials_path.is_absolute():
        credentials_path = workspace.resolve() / credentials_path

    info(f"Syncing last {days} days from GSC...")

    client = GSCClient(cfg.gsc.property_url, credentials_path)
    rows = client.get_page_performance(days=days)

    with connect(db_path) as conn:
        # Load all articles once for matching
        article_rows = conn.execute(
            "SELECT slug, url FROM articles WHERE url IS NOT NULL AND url != ''"
        ).fetchall()
        articles = [{"slug": r["slug"], "url": r["url"]} for r in article_rows]

        count = 0
        unmatched_urls: set[str] = set()

        for row in rows:
            slug = match_url_to_slug(row["page"], articles)
            if slug:
                upsert_performance(
                    conn,
                    slug=slug,
                    date=row["date"],
                    impressions=row["impressions"],
                    clicks=row["clicks"],
                    position_avg=row["position"],
                    ctr=row["ctr"],
                )
                count += 1
            else:
                unmatched_urls.add(row["page"])

    success(f"Synced {count} performance records.")
    if unmatched_urls:
        warning(
            f"{len(unmatched_urls)} URL(s) could not be matched to articles"
        )
        for url in sorted(unmatched_urls)[:10]:
            info(f"  Unmatched: {url}")
        if len(unmatched_urls) > 10:
            info(f"  ... and {len(unmatched_urls) - 10} more")
