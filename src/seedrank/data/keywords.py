"""Keyword CRUD and query functions."""

from __future__ import annotations

import sqlite3


def query_keywords(
    conn: sqlite3.Connection,
    limit: int = 100,
    sort_by: str = "volume",
) -> list[dict]:
    """Query keywords with metrics."""
    valid_sorts = {"volume", "kd", "cpc", "keyword"}
    if sort_by not in valid_sorts:
        sort_by = "volume"

    order = "DESC" if sort_by != "keyword" else "ASC"
    # Handle NULLs: sort nulls last
    rows = conn.execute(
        f"""SELECT keyword, volume, kd, cpc, competition, intent, serp_features,
                   cluster_id, fetched_at
            FROM keywords
            ORDER BY {sort_by} {order} NULLS LAST
            LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_keyword_gaps(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    """Find keywords competitors rank for that we don't have articles targeting.

    A "gap" is a competitor keyword that doesn't appear in any article's target_keywords.
    """
    rows = conn.execute(
        """SELECT ck.keyword, ck.volume, ck.competitor_slug, ck.rank as competitor_rank
           FROM competitor_keywords ck
           LEFT JOIN articles a ON a.target_keywords LIKE '%' || ck.keyword || '%'
           WHERE a.slug IS NULL
           ORDER BY ck.volume DESC NULLS LAST
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
