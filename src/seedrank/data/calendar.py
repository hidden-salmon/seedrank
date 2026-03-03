"""Content calendar CRUD and priority scoring."""

from __future__ import annotations

import json
import sqlite3


def add_to_calendar(
    conn: sqlite3.Connection,
    *,
    slug: str,
    target_keywords: list[str] | None = None,
    priority_score: float = 0.0,
    brief_path: str | None = None,
) -> None:
    """Add an article to the content calendar."""
    # Auto-compute priority if not manually set
    if priority_score == 0.0:
        priority_score = compute_priority_score(conn, target_keywords or [])

    conn.execute(
        """INSERT OR REPLACE INTO content_calendar
           (slug, priority_score, status, target_keywords, brief_path, updated_at)
           VALUES (?, ?, 'queued', ?, ?, datetime('now'))""",
        (
            slug,
            priority_score,
            json.dumps(target_keywords or []),
            brief_path,
        ),
    )


def get_next_items(conn: sqlite3.Connection, count: int = 5) -> list[dict]:
    """Get top priority items that are queued or writing."""
    rows = conn.execute(
        """SELECT slug, priority_score, status, target_keywords, brief_path,
                  created_at, updated_at
           FROM content_calendar
           WHERE status IN ('queued', 'writing')
           ORDER BY priority_score DESC
           LIMIT ?""",
        (count,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_calendar_items(
    conn: sqlite3.Connection,
    status: str | None = None,
) -> list[dict]:
    """Get all calendar items, optionally filtered by status."""
    if status:
        rows = conn.execute(
            """SELECT slug, priority_score, status, target_keywords, brief_path,
                      created_at, updated_at
               FROM content_calendar
               WHERE status = ?
               ORDER BY priority_score DESC""",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT slug, priority_score, status, target_keywords, brief_path,
                      created_at, updated_at
               FROM content_calendar
               ORDER BY priority_score DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def update_calendar_status(conn: sqlite3.Connection, *, slug: str, status: str) -> None:
    """Update calendar item status."""
    conn.execute(
        "UPDATE content_calendar SET status = ?, updated_at = datetime('now') WHERE slug = ?",
        (status, slug),
    )


def compute_priority_score(
    conn: sqlite3.Connection,
    target_keywords: list[str],
) -> float:
    """Compute priority score for a calendar item based on keyword data.

    Formula:
        score = (avg_volume / 1000) * 0.4
              + (1 - avg_kd / 100) * 0.3
              + content_gap_bonus * 0.2
              + gsc_opportunity * 0.1
    """
    if not target_keywords:
        return 0.0

    placeholders = ", ".join("?" for _ in target_keywords)

    # Get keyword metrics
    rows = conn.execute(
        f"SELECT volume, kd FROM keywords WHERE keyword IN ({placeholders})",
        target_keywords,
    ).fetchall()

    if not rows:
        return 0.0

    volumes = [r["volume"] or 0 for r in rows]
    kds = [r["kd"] or 0 for r in rows]

    avg_volume = sum(volumes) / len(volumes)
    avg_kd = sum(kds) / len(kds)

    # Volume component (normalized)
    volume_score = min(avg_volume / 1000, 1.0) * 0.4

    # KD component (inverse — easier is better)
    kd_score = (1 - min(avg_kd / 100, 1.0)) * 0.3

    # Content gap bonus: competitors rank for these keywords, we don't have articles
    gap_count = conn.execute(
        f"""SELECT COUNT(DISTINCT ck.keyword)
            FROM competitor_keywords ck
            LEFT JOIN articles a ON a.target_keywords LIKE '%' || ck.keyword || '%'
            WHERE ck.keyword IN ({placeholders}) AND a.slug IS NULL""",
        target_keywords,
    ).fetchone()[0]
    gap_bonus = min(gap_count / len(target_keywords), 1.0) * 0.2

    # GSC opportunity: we're close to page 1 already
    # Check ALL target keywords, take the best opportunity
    gsc_opportunity = 0.0
    for kw in target_keywords:
        perf_row = conn.execute(
            """SELECT MIN(ap.position_avg) as best_pos
                FROM article_performance ap
                JOIN articles a ON a.slug = ap.slug
                WHERE a.target_keywords LIKE '%' || ? || '%'""",
            (kw,),
        ).fetchone()
        if perf_row and perf_row["best_pos"]:
            pos = perf_row["best_pos"]
            # Graduated bonus: closer to page 1 = higher score
            if 8 < pos <= 12:
                gsc_opportunity = max(gsc_opportunity, 0.15)
            elif 12 < pos <= 20:
                gsc_opportunity = max(gsc_opportunity, 0.10)
            elif 20 < pos <= 30:
                gsc_opportunity = max(gsc_opportunity, 0.05)

    total = volume_score + kd_score + gap_bonus + gsc_opportunity
    return total


def explain_priority_score(
    conn: sqlite3.Connection,
    target_keywords: list[str],
) -> dict:
    """Compute priority score with a full breakdown of each component."""
    if not target_keywords:
        return {"total": 0.0, "components": {}, "keywords_found": 0}

    placeholders = ", ".join("?" for _ in target_keywords)

    rows = conn.execute(
        f"SELECT volume, kd FROM keywords WHERE keyword IN ({placeholders})",
        target_keywords,
    ).fetchall()

    if not rows:
        return {"total": 0.0, "components": {}, "keywords_found": 0}

    volumes = [r["volume"] or 0 for r in rows]
    kds = [r["kd"] or 0 for r in rows]
    avg_volume = sum(volumes) / len(volumes)
    avg_kd = sum(kds) / len(kds)

    volume_score = min(avg_volume / 1000, 1.0) * 0.4
    kd_score = (1 - min(avg_kd / 100, 1.0)) * 0.3

    gap_count = conn.execute(
        f"""SELECT COUNT(DISTINCT ck.keyword)
            FROM competitor_keywords ck
            LEFT JOIN articles a ON a.target_keywords LIKE '%' || ck.keyword || '%'
            WHERE ck.keyword IN ({placeholders}) AND a.slug IS NULL""",
        target_keywords,
    ).fetchone()[0]
    gap_bonus = min(gap_count / len(target_keywords), 1.0) * 0.2

    gsc_opportunity = 0.0
    gsc_best_pos = None
    gsc_best_kw = None
    for kw in target_keywords:
        perf_row = conn.execute(
            """SELECT MIN(ap.position_avg) as best_pos
                FROM article_performance ap
                JOIN articles a ON a.slug = ap.slug
                WHERE a.target_keywords LIKE '%' || ? || '%'""",
            (kw,),
        ).fetchone()
        if perf_row and perf_row["best_pos"]:
            pos = perf_row["best_pos"]
            bonus = 0.0
            if 8 < pos <= 12:
                bonus = 0.15
            elif 12 < pos <= 20:
                bonus = 0.10
            elif 20 < pos <= 30:
                bonus = 0.05
            if bonus > gsc_opportunity:
                gsc_opportunity = bonus
                gsc_best_pos = pos
                gsc_best_kw = kw

    total = volume_score + kd_score + gap_bonus + gsc_opportunity

    return {
        "total": total,
        "keywords_found": len(rows),
        "components": {
            "volume": {
                "score": volume_score,
                "weight": 0.4,
                "avg_volume": avg_volume,
            },
            "kd": {
                "score": kd_score,
                "weight": 0.3,
                "avg_kd": avg_kd,
            },
            "content_gap": {
                "score": gap_bonus,
                "weight": 0.2,
                "gaps_found": gap_count,
            },
            "gsc_opportunity": {
                "score": gsc_opportunity,
                "weight": 0.1,
                "best_position": gsc_best_pos,
                "best_keyword": gsc_best_kw,
            },
        },
    }
