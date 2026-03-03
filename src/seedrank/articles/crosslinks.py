"""Forward/backward crosslink suggestion engine.

Scoring formula:
    score = (topic_overlap * 2 + kw_overlap)
          + volume_bonus            # higher-volume keywords matter more
          + content_type_bonus      # same content type gets a boost
          + recency_bonus           # recently published articles preferred
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime


def _compute_score(
    conn: sqlite3.Connection,
    target_kws: set[str],
    target_topics: set[str],
    target_content_type: str | None,
    other: sqlite3.Row,
) -> dict | None:
    """Score a candidate article for crosslink relevance."""
    other_kws = set(json.loads(other["target_keywords"] or "[]"))
    other_topics = set(json.loads(other["topics"] or "[]"))

    kw_overlap = len(target_kws & other_kws)
    topic_overlap = len(target_topics & other_topics)
    base_score = topic_overlap * 2 + kw_overlap

    if base_score == 0:
        return None

    # Volume bonus: overlapping keywords with higher search volume → stronger link
    volume_bonus = 0.0
    overlapping_kws = target_kws & other_kws
    if overlapping_kws:
        placeholders = ", ".join("?" for _ in overlapping_kws)
        rows = conn.execute(
            f"SELECT volume FROM keywords WHERE keyword IN ({placeholders})",
            list(overlapping_kws),
        ).fetchall()
        total_vol = sum(r["volume"] or 0 for r in rows)
        # Normalize: 1000 volume → +0.5 bonus, capped at 1.0
        volume_bonus = min(total_vol / 2000, 1.0)

    # Content type affinity: same type gets a boost
    content_type_bonus = 0.0
    if target_content_type and other["content_type"] == target_content_type:
        content_type_bonus = 0.5

    # Recency bonus: articles published in last 90 days get a boost
    recency_bonus = 0.0
    published_at = other["published_at"]
    if published_at:
        try:
            pub_date = datetime.fromisoformat(published_at)
            days_ago = (datetime.now(UTC) - pub_date.replace(tzinfo=UTC)).days
            if days_ago < 30:
                recency_bonus = 0.5
            elif days_ago < 90:
                recency_bonus = 0.25
        except (ValueError, TypeError):
            pass

    total_score = base_score + volume_bonus + content_type_bonus + recency_bonus

    return {
        "slug": other["slug"],
        "title": other["title"],
        "url": other["url"],
        "score": total_score,
        "keyword_overlap": kw_overlap,
        "topic_overlap": topic_overlap,
    }


def find_forward_links(
    conn: sqlite3.Connection,
    slug: str,
    limit: int = 10,
) -> list[dict]:
    """Find published articles this slug should link TO.

    Uses enriched scoring: topic/keyword overlap + volume + content type + recency.
    """
    article = conn.execute(
        "SELECT target_keywords, topics, content_type FROM articles WHERE slug = ?",
        (slug,),
    ).fetchone()
    if not article:
        return []

    target_kws = set(json.loads(article["target_keywords"] or "[]"))
    target_topics = set(json.loads(article["topics"] or "[]"))
    target_ct = article["content_type"]

    if not target_kws and not target_topics:
        return []

    others = conn.execute(
        """SELECT slug, title, target_keywords, topics, url,
                  content_type, published_at
           FROM articles
           WHERE slug != ? AND status = 'published'""",
        (slug,),
    ).fetchall()

    scored = []
    for other in others:
        result = _compute_score(conn, target_kws, target_topics, target_ct, other)
        if result:
            scored.append(result)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def find_backward_links(
    conn: sqlite3.Connection,
    slug: str,
    limit: int = 10,
) -> list[dict]:
    """Find published articles that should link TO this new slug.

    Same enriched scoring, but excludes articles that already link to this slug.
    """
    article = conn.execute(
        "SELECT target_keywords, topics, content_type FROM articles WHERE slug = ?",
        (slug,),
    ).fetchone()
    if not article:
        return []

    target_kws = set(json.loads(article["target_keywords"] or "[]"))
    target_topics = set(json.loads(article["topics"] or "[]"))
    target_ct = article["content_type"]

    if not target_kws and not target_topics:
        return []

    existing_links = {
        r["from_slug"]
        for r in conn.execute(
            "SELECT from_slug FROM article_links WHERE to_slug = ?", (slug,)
        ).fetchall()
    }

    others = conn.execute(
        """SELECT slug, title, target_keywords, topics, url,
                  content_type, published_at
           FROM articles
           WHERE slug != ? AND status = 'published'""",
        (slug,),
    ).fetchall()

    scored = []
    for other in others:
        if other["slug"] in existing_links:
            continue
        result = _compute_score(conn, target_kws, target_topics, target_ct, other)
        if result:
            scored.append(result)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def register_link(
    conn: sqlite3.Connection,
    from_slug: str,
    to_slug: str,
    anchor_text: str | None = None,
) -> None:
    """Register a crosslink between two articles."""
    conn.execute(
        """INSERT OR IGNORE INTO article_links (from_slug, to_slug, anchor_text)
           VALUES (?, ?, ?)""",
        (from_slug, to_slug, anchor_text),
    )
