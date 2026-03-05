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


def get_declining_articles(
    conn: sqlite3.Connection,
    days: int = 60,
    min_impressions: int = 50,
) -> list[dict]:
    """Find articles with declining traffic comparing recent vs prior period.

    Splits the window into two halves and compares impressions/clicks/position.
    Returns articles where recent performance is worse than the prior period.
    """
    today = date.today()
    recent_start = (today - timedelta(days=days // 2)).isoformat()
    prior_start = (today - timedelta(days=days)).isoformat()
    recent_end = today.isoformat()

    rows = conn.execute(
        """
        WITH recent AS (
            SELECT slug,
                   SUM(impressions) AS impressions,
                   SUM(clicks) AS clicks,
                   AVG(position_avg) AS position_avg,
                   AVG(ctr) AS ctr
            FROM article_performance
            WHERE date >= ? AND date <= ?
            GROUP BY slug
        ),
        prior AS (
            SELECT slug,
                   SUM(impressions) AS impressions,
                   SUM(clicks) AS clicks,
                   AVG(position_avg) AS position_avg,
                   AVG(ctr) AS ctr
            FROM article_performance
            WHERE date >= ? AND date < ?
            GROUP BY slug
        )
        SELECT
            r.slug,
            r.impressions AS recent_impressions,
            p.impressions AS prior_impressions,
            r.clicks AS recent_clicks,
            p.clicks AS prior_clicks,
            r.position_avg AS recent_position,
            p.position_avg AS prior_position,
            r.ctr AS recent_ctr,
            p.ctr AS prior_ctr,
            CASE WHEN p.impressions > 0
                 THEN ROUND((r.impressions - p.impressions) * 100.0
                       / p.impressions, 1)
                 ELSE 0 END AS impressions_change_pct,
            CASE WHEN p.clicks > 0
                 THEN ROUND((r.clicks - p.clicks) * 100.0
                       / p.clicks, 1)
                 ELSE 0 END AS clicks_change_pct
        FROM recent r
        JOIN prior p ON r.slug = p.slug
        WHERE p.impressions >= ?
          AND (r.impressions < p.impressions
               OR r.clicks < p.clicks
               OR r.position_avg > p.position_avg + 1)
        ORDER BY impressions_change_pct ASC
        """,
        (recent_start, recent_end, prior_start, recent_start,
         min_impressions),
    ).fetchall()
    return [dict(r) for r in rows]


def get_performance_for_slug(
    conn: sqlite3.Connection,
    slug: str,
    days: int = 90,
) -> list[dict]:
    """Get daily performance data for a specific article."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        """SELECT date, impressions, clicks, position_avg, ctr
           FROM article_performance
           WHERE slug = ? AND date >= ?
           ORDER BY date ASC""",
        (slug, cutoff),
    ).fetchall()
    return [dict(r) for r in rows]
