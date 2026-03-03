"""GSC performance data storage and queries."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta


def upsert_performance(
    conn: sqlite3.Connection,
    *,
    slug: str,
    date: str,
    impressions: int = 0,
    clicks: int = 0,
    position_avg: float | None = None,
    ctr: float | None = None,
) -> None:
    """Insert or update performance data for an article on a given date."""
    conn.execute(
        """INSERT INTO article_performance (slug, date, impressions, clicks, position_avg, ctr)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(slug, date) DO UPDATE SET
               impressions = excluded.impressions,
               clicks = excluded.clicks,
               position_avg = excluded.position_avg,
               ctr = excluded.ctr""",
        (slug, date, impressions, clicks, position_avg, ctr),
    )


def get_performance(
    conn: sqlite3.Connection,
    days: int = 30,
) -> list[dict]:
    """Get aggregated performance data per slug for the last N days."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT slug,
                  SUM(impressions) as impressions,
                  SUM(clicks) as clicks,
                  AVG(position_avg) as position_avg,
                  AVG(ctr) as ctr
           FROM article_performance
           WHERE date >= ?
           GROUP BY slug
           ORDER BY clicks DESC""",
        (cutoff,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_underperformers(
    conn: sqlite3.Connection,
    days: int = 30,
    min_impressions: int = 100,
    max_ctr: float = 0.02,
) -> list[dict]:
    """Find articles with high impressions but low CTR (underperformers)."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT slug,
                  SUM(impressions) as impressions,
                  SUM(clicks) as clicks,
                  AVG(position_avg) as position_avg,
                  AVG(ctr) as ctr
           FROM article_performance
           WHERE date >= ?
           GROUP BY slug
           HAVING SUM(impressions) >= ? AND AVG(ctr) < ?
           ORDER BY impressions DESC""",
        (cutoff, min_impressions, max_ctr),
    ).fetchall()
    return [dict(r) for r in rows]
