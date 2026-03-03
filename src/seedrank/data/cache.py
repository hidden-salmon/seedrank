"""Cache-first data access — check DB for fresh data before calling APIs."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta


def get_fresh_keywords(
    conn: sqlite3.Connection,
    keywords: list[str],
    max_age_days: int = 90,
) -> tuple[list[str], list[dict]]:
    """Check which keywords have fresh data in the DB.

    Returns:
        (stale_keywords, cached_rows) — keywords that need refreshing,
        and rows for keywords that are still fresh.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    placeholders = ",".join("?" for _ in keywords)
    rows = conn.execute(
        f"""SELECT keyword, volume, kd, cpc, competition, intent,
                   serp_features, cluster_id, fetched_at
            FROM keywords
            WHERE keyword IN ({placeholders})
              AND fetched_at >= ?""",
        [*keywords, cutoff],
    ).fetchall()

    cached = {r["keyword"]: dict(r) for r in rows}
    cached_rows = list(cached.values())
    stale = [k for k in keywords if k not in cached]
    return stale, cached_rows


def get_fresh_serp(
    conn: sqlite3.Connection,
    keyword: str,
    max_age_days: int = 90,
) -> list[dict]:
    """Check if we have a fresh SERP snapshot for this keyword.

    Returns cached rows if fresh, empty list if stale/missing.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    rows = conn.execute(
        """SELECT keyword, rank, url, domain, title, snippet,
                  result_type, fetched_at
           FROM serp_snapshots
           WHERE keyword = ? AND fetched_at >= ?
           ORDER BY rank ASC""",
        (keyword, cutoff),
    ).fetchall()
    return [dict(r) for r in rows]


def get_fresh_competitor_keywords(
    conn: sqlite3.Connection,
    competitor_slug: str,
    max_age_days: int = 90,
) -> list[dict]:
    """Check if we have fresh competitor keyword data.

    Returns cached rows if fresh, empty list if stale/missing.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    rows = conn.execute(
        """SELECT competitor_slug, keyword, rank, url, volume, kd, fetched_at
           FROM competitor_keywords
           WHERE competitor_slug = ? AND fetched_at >= ?
           ORDER BY volume DESC NULLS LAST""",
        (competitor_slug, cutoff),
    ).fetchall()
    return [dict(r) for r in rows]


def get_fresh_questions(
    conn: sqlite3.Connection,
    source_keyword: str,
    max_age_days: int = 90,
) -> list[dict]:
    """Check if we have fresh questions for this source keyword.

    Returns cached rows if fresh, empty list if stale/missing.
    """
    # Check if questions table exists
    table_check = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='questions'"
    ).fetchone()
    if not table_check:
        return []

    cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    rows = conn.execute(
        """SELECT question, source, source_keyword, fetched_at
           FROM questions
           WHERE source_keyword = ? AND fetched_at >= ?""",
        (source_keyword, cutoff),
    ).fetchall()
    return [dict(r) for r in rows]


def get_fresh_geo_queries(
    conn: sqlite3.Connection,
    query: str,
    model: str,
    max_age_days: int = 7,
) -> list[dict]:
    """Check if we have a fresh GEO query result.

    GEO data uses a shorter default freshness window (7 days)
    because AI model responses change more frequently.

    Returns cached rows if fresh, empty list if stale/missing.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=max_age_days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    rows = conn.execute(
        """SELECT query, model, response_text, mentions_brand,
                  brand_sentiment, mentions_competitors, citations,
                  queried_at
           FROM geo_queries
           WHERE query = ? AND model = ? AND queried_at >= ?""",
        (query, model, cutoff),
    ).fetchall()
    return [dict(r) for r in rows]
