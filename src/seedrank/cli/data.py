"""seedrank data — Query stored research and article data."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from seedrank.utils.console import console, error, heading, info, render_table

data_app = typer.Typer(
    help="Data query commands — keywords, gaps, articles, performance, calendar.",
    no_args_is_help=True,
)


def _json_output(rows: list[dict]) -> None:
    """Print rows as JSON to stdout."""
    console.print_json(json.dumps(rows, default=str))


@data_app.command(name="keywords")
def data_keywords(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    limit: int = typer.Option(100, "--limit", "-n", help="Max rows to return."),
    sort: str = typer.Option("volume", "--sort", "-s", help="Sort by: volume, kd, cpc, keyword."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """List all keywords with metrics."""
    from seedrank.data.db import connect, get_db_path
    from seedrank.data.keywords import query_keywords

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        rows = query_keywords(conn, limit=limit, sort_by=sort)

    if as_json:
        _json_output(rows)
        return

    heading("Keywords")
    table_rows = [
        [
            r["keyword"],
            str(r.get("volume") or "—"),
            f"{r.get('kd', 0) or 0:.0f}",
            f"${r.get('cpc', 0) or 0:.2f}",
            r.get("intent") or "—",
        ]
        for r in rows
    ]
    render_table("Keywords", ["Keyword", "Volume", "KD", "CPC", "Intent"], table_rows)


@data_app.command(name="gaps")
def data_gaps(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    limit: int = typer.Option(50, "--limit", "-n", help="Max rows."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Find keyword gaps — keywords competitors rank for but we don't cover."""
    from seedrank.data.db import connect, get_db_path
    from seedrank.data.keywords import get_keyword_gaps

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        rows = get_keyword_gaps(conn, limit=limit)

    if as_json:
        _json_output(rows)
        return

    heading("Keyword Gaps")
    if not rows:
        info("No gaps found. Fetch competitor data with 'seedrank research competitors'.")
        return

    table_rows = [
        [
            r["keyword"],
            str(r.get("volume") or "—"),
            r.get("competitor_slug", "—"),
            str(r.get("competitor_rank") or "—"),
        ]
        for r in rows
    ]
    render_table("Keyword Gaps", ["Keyword", "Volume", "Competitor", "Rank"], table_rows)


@data_app.command(name="articles")
def data_articles(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    status: str = typer.Option("", "--status", help="Filter by status."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """List all registered articles."""
    from seedrank.data.articles import list_articles
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        rows = list_articles(conn, status=status or None)

    if as_json:
        _json_output(rows)
        return

    heading("Articles")
    if not rows:
        info("No articles registered. Use 'seedrank articles register' to add one.")
        return

    table_rows = [
        [r["slug"], r.get("title", "—"), r.get("status", "—"), r.get("published_at") or "—"]
        for r in rows
    ]
    render_table("Articles", ["Slug", "Title", "Status", "Published"], table_rows)


@data_app.command(name="performance")
def data_performance(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    days: int = typer.Option(30, "--days", "-d", help="Number of days to show."),
    slug: str = typer.Option("", "--slug", help="Show daily data for a specific article."),
    declining: bool = typer.Option(
        False, "--declining",
        help="Show articles with declining traffic.",
    ),
    underperformers: bool = typer.Option(
        False, "--underperformers", "-u",
        help="Show only underperformers (high impressions, low CTR).",
    ),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Show article performance from GSC data."""
    from seedrank.data.db import connect, get_db_path
    from seedrank.data.performance import (
        get_declining_articles,
        get_performance,
        get_performance_for_slug,
        get_underperformers,
    )

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        if slug:
            rows = get_performance_for_slug(conn, slug=slug, days=days)
        elif declining:
            rows = get_declining_articles(conn, days=days)
        elif underperformers:
            rows = get_underperformers(conn, days=days)
        else:
            rows = get_performance(conn, days=days)

    if as_json:
        _json_output(rows)
        return

    if slug:
        title = f"Performance: {slug}"
    elif declining:
        title = "Declining Articles"
    elif underperformers:
        title = "Underperformers"
    else:
        title = "Performance"

    heading(title)
    if not rows:
        if slug:
            info(f"No performance data for '{slug}'.")
        elif declining:
            info("No declining articles found.")
        elif underperformers:
            info("No underperformers found.")
        else:
            info("No performance data. Sync GSC data with 'seedrank gsc sync'.")
        return

    if slug:
        table_rows = [
            [
                r["date"],
                str(r.get("impressions", 0)),
                str(r.get("clicks", 0)),
                f"{r.get('position_avg', 0):.1f}",
                f"{(r.get('ctr', 0) or 0) * 100:.1f}%",
            ]
            for r in rows
        ]
        render_table(
            f"{title} (last {days}d)",
            ["Date", "Impressions", "Clicks", "Avg Pos", "CTR"],
            table_rows,
        )
    elif declining:
        table_rows = [
            [
                r["slug"],
                str(r.get("prior_impressions", 0)),
                str(r.get("recent_impressions", 0)),
                f"{r.get('impressions_change_pct', 0):+.1f}%",
                f"{r.get('clicks_change_pct', 0):+.1f}%",
            ]
            for r in rows
        ]
        render_table(
            f"{title} (last {days}d)",
            ["Slug", "Prior Impr", "Recent Impr", "Impr %", "Clicks %"],
            table_rows,
        )
    else:
        table_rows = [
            [
                r["slug"],
                str(r.get("impressions", 0)),
                str(r.get("clicks", 0)),
                f"{r.get('position_avg', 0):.1f}",
                f"{(r.get('ctr', 0) or 0) * 100:.1f}%",
            ]
            for r in rows
        ]
        render_table(
            f"{title} (last {days}d)",
            ["Slug", "Impressions", "Clicks", "Avg Pos", "CTR"],
            table_rows,
        )


@data_app.command(name="links")
def data_links(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    orphans: bool = typer.Option(
        False, "--orphans",
        help="Show only articles with zero inbound links.",
    ),
    stats: bool = typer.Option(
        False, "--stats",
        help="Show per-article inbound/outbound link counts.",
    ),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Show internal link graph data."""
    from seedrank.data.db import connect, get_db_path
    from seedrank.data.links import get_all_links, get_link_stats, get_orphan_articles

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        if orphans:
            rows = get_orphan_articles(conn)
        elif stats:
            rows = get_link_stats(conn)
        else:
            rows = get_all_links(conn)

    if as_json:
        _json_output(rows)
        return

    if orphans:
        heading("Orphan Articles (no inbound links)")
        if not rows:
            info("No orphan articles found.")
            return
        table_rows = [
            [r["slug"], r.get("title", "—"), r.get("published_at") or "—"]
            for r in rows
        ]
        render_table("Orphans", ["Slug", "Title", "Published"], table_rows)
    elif stats:
        heading("Link Stats")
        if not rows:
            info("No published articles.")
            return
        table_rows = [
            [
                r["slug"],
                str(r.get("outbound_links", 0)),
                str(r.get("inbound_links", 0)),
            ]
            for r in rows
        ]
        render_table(
            "Link Stats", ["Slug", "Outbound", "Inbound"], table_rows
        )
    else:
        heading("All Links")
        if not rows:
            info("No links registered. Use 'seedrank articles crosslinks' to find suggestions.")
            return
        table_rows = [
            [
                r["from_slug"],
                r["to_slug"],
                r.get("anchor_text") or "—",
            ]
            for r in rows
        ]
        render_table("Links", ["From", "To", "Anchor"], table_rows)


@data_app.command(name="costs")
def data_costs(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    days: int = typer.Option(30, "--days", "-d", help="Number of days to show."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Show API cost summary by provider."""
    from seedrank.data.costs import get_cost_summary, get_total_cost
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        rows = get_cost_summary(conn, days=days)
        total = get_total_cost(conn, days=days)

    if as_json:
        _json_output({"providers": rows, "total_usd": total})
        return

    heading(f"API Costs (last {days}d)")
    if not rows:
        info("No API cost data recorded yet.")
        return

    table_rows = [
        [
            r["provider"],
            str(r["calls"]),
            f"${r['total_cost']:.4f}",
            f"${r['avg_cost']:.4f}",
        ]
        for r in rows
    ]
    render_table("Costs", ["Provider", "Calls", "Total", "Avg/Call"], table_rows)
    info(f"Total: ${total:.4f}")


@data_app.command(name="geo")
def data_geo(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    model: str = typer.Option("", "--model", "-m", help="Filter by model slug."),
    limit: int = typer.Option(50, "--limit", "-n", help="Max rows."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Show GEO query results — brand mentions across AI models."""
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        if model:
            rows = conn.execute(
                """SELECT query, model, mentions_brand, brand_sentiment,
                          mentions_competitors, citations, queried_at
                   FROM geo_queries WHERE model = ?
                   ORDER BY queried_at DESC LIMIT ?""",
                (model, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT query, model, mentions_brand, brand_sentiment,
                          mentions_competitors, citations, queried_at
                   FROM geo_queries
                   ORDER BY queried_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()

    results = [dict(r) for r in rows]

    if as_json:
        _json_output(results)
        return

    heading("GEO Results")
    if not results:
        info("No GEO data. Run 'seedrank research geo' first.")
        return

    table_rows = [
        [
            r["query"][:40] + ("..." if len(r["query"]) > 40 else ""),
            r["model"],
            "Yes" if r["mentions_brand"] else "No",
            r.get("brand_sentiment") or "—",
            r.get("mentions_competitors") or "[]",
        ]
        for r in results
    ]
    render_table(
        "GEO Results", ["Query", "Model", "Brand?", "Sentiment", "Competitors"], table_rows
    )


@data_app.command(name="questions")
def data_questions(
    status: str = typer.Option(
        "", "--status", "-s", help="Filter by status (new, answered, assigned)."
    ),
    slug: str = typer.Option("", "--slug", help="Filter by assigned article slug."),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """List discovered questions."""
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        # Check if questions table exists
        table_check = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='questions'"
        ).fetchone()
        if not table_check:
            if as_json:
                _json_output([])
            else:
                info("No questions table. Run 'seedrank research questions' first.")
            return

        query = "SELECT * FROM questions"
        params: list[str] = []
        conditions = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if slug:
            conditions.append("assigned_slug = ?")
            params.append(slug)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY fetched_at DESC"

        rows = conn.execute(query, params).fetchall()

    results = [dict(r) for r in rows]

    if as_json:
        _json_output(results)
        return

    heading("Discovered Questions")
    if not results:
        info("No questions found. Run 'seedrank research questions' to discover some.")
        return

    table_rows = [
        [
            r["question"][:60] + ("..." if len(r["question"]) > 60 else ""),
            r.get("source", "—"),
            r.get("status", "—"),
            r.get("assigned_slug") or "—",
        ]
        for r in results
    ]
    render_table("Questions", ["Question", "Source", "Status", "Assigned To"], table_rows)


@data_app.command(name="geo-trends")
def data_geo_trends(
    days: int = typer.Option(90, "--days", "-d", help="Number of days to analyze."),
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Show brand mention rate trends over time."""
    from seedrank.data.db import connect, get_db_path
    from seedrank.data.geo import get_geo_trends

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        rows = get_geo_trends(conn, days=days)

    if as_json:
        _json_output(rows)
        return

    heading(f"GEO Trends (last {days} days)")
    if not rows:
        info("No GEO data. Run 'seedrank research geo' first.")
        return

    table_rows = [
        [
            r["week"],
            str(r["total_queries"]),
            str(r["brand_mentions"]),
            f"{r['mention_rate']:.0%}",
            f"{r.get('avg_sentiment_confidence', 0):.2f}",
        ]
        for r in rows
    ]
    render_table("GEO Trends", ["Week", "Queries", "Mentions", "Rate", "Confidence"], table_rows)


@data_app.command(name="geo-gaps")
def data_geo_gaps(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Show queries where competitors are mentioned but brand is not."""
    from seedrank.config.loader import load_config
    from seedrank.data.db import connect, get_db_path
    from seedrank.data.geo import get_geo_gaps

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    try:
        cfg = load_config(workspace / "seedrank.config.yaml")
        brand_name = cfg.product.name
    except (FileNotFoundError, ValueError):
        brand_name = ""

    with connect(db_path) as conn:
        rows = get_geo_gaps(conn, brand_name=brand_name)

    if as_json:
        _json_output(rows)
        return

    heading("GEO Gaps")
    if not rows:
        info("No gaps found — brand appears in all queries where competitors are mentioned.")
        return

    table_rows = [
        [
            r["query"][:50] + ("..." if len(r["query"]) > 50 else ""),
            r["model"],
            r.get("mentions_competitors", "[]"),
        ]
        for r in rows
    ]
    render_table("GEO Gaps", ["Query", "Model", "Competitors Mentioned"], table_rows)


@data_app.command(name="calendar")
def data_calendar(
    as_json: bool = typer.Option(False, "--json", help="Output as JSON."),
    status: str = typer.Option("", "--status", help="Filter by status."),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Workspace root."),
) -> None:
    """Show content calendar items."""
    from seedrank.data.calendar import get_calendar_items
    from seedrank.data.db import connect, get_db_path

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        rows = get_calendar_items(conn, status=status or None)

    if as_json:
        _json_output(rows)
        return

    heading("Content Calendar")
    if not rows:
        info("Calendar is empty. Use 'seedrank calendar add' to add items.")
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
    render_table("Calendar", ["Slug", "Priority", "Status", "Keywords"], table_rows)
