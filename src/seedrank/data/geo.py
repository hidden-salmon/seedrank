"""GEO/AEO data query functions — trends, gaps, and competitor leaderboard."""

from __future__ import annotations

import json
import sqlite3


def get_geo_trends(conn: sqlite3.Connection, days: int = 90) -> list[dict]:
    """Brand mention rate over time, grouped by week.

    Returns rows with: week, total_queries, brand_mentions, mention_rate,
    avg_sentiment_confidence.
    """
    rows = conn.execute(
        """SELECT
               strftime('%%Y-W%%W', queried_at) AS week,
               COUNT(*) AS total_queries,
               SUM(CASE WHEN mentions_brand > 0 THEN 1 ELSE 0 END) AS brand_mentions,
               CAST(SUM(CASE WHEN mentions_brand > 0 THEN 1 ELSE 0 END) AS REAL)
                   / COUNT(*) AS mention_rate,
               AVG(COALESCE(sentiment_confidence, 0)) AS avg_sentiment_confidence
           FROM geo_queries
           WHERE queried_at >= datetime('now', ?)
           GROUP BY week
           ORDER BY week ASC""",
        (f"-{days} days",),
    ).fetchall()
    return [dict(r) for r in rows]


def get_geo_gaps(conn: sqlite3.Connection, brand_name: str = "") -> list[dict]:
    """Queries where competitors are mentioned but brand is not.

    Returns rows with: query, model, mentions_competitors, queried_at.
    """
    rows = conn.execute(
        """SELECT query, model, mentions_competitors, queried_at
           FROM geo_queries
           WHERE mentions_brand = 0
             AND mentions_competitors IS NOT NULL
             AND mentions_competitors != '[]'
             AND mentions_competitors != ''
           ORDER BY queried_at DESC""",
    ).fetchall()
    return [dict(r) for r in rows]


def get_geo_competitor_leaderboard(conn: sqlite3.Connection) -> list[dict]:
    """Which competitors get mentioned most across GEO queries.

    Parses the mentions_competitors JSON array and counts per competitor.
    Returns: [{"competitor": str, "mention_count": int}, ...]
    """
    rows = conn.execute(
        "SELECT mentions_competitors FROM geo_queries WHERE mentions_competitors IS NOT NULL"
    ).fetchall()

    counts: dict[str, int] = {}
    for row in rows:
        mc = row["mentions_competitors"]
        if not mc:
            continue
        try:
            competitors = json.loads(mc) if isinstance(mc, str) else mc
            if isinstance(competitors, list):
                for comp in competitors:
                    if isinstance(comp, str) and comp:
                        counts[comp] = counts.get(comp, 0) + 1
        except (json.JSONDecodeError, TypeError):
            continue

    return sorted(
        [{"competitor": k, "mention_count": v} for k, v in counts.items()],
        key=lambda x: x["mention_count"],
        reverse=True,
    )
