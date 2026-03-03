"""Article directory CRUD and query functions."""

from __future__ import annotations

import json
import sqlite3


def register_article(
    conn: sqlite3.Connection,
    *,
    slug: str,
    title: str,
    target_keywords: list[str] | None = None,
    topics: list[str] | None = None,
    content_type: str = "blog",
    url: str | None = None,
    status: str = "planned",
    brief_path: str | None = None,
    content_path: str | None = None,
) -> None:
    """Register a new article in the database."""
    conn.execute(
        """INSERT OR REPLACE INTO articles
           (slug, url, title, status, content_type, target_keywords, topics,
            brief_path, content_path, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (
            slug,
            url,
            title,
            status,
            content_type,
            json.dumps(target_keywords or []),
            json.dumps(topics or []),
            brief_path,
            content_path,
        ),
    )


def update_article(conn: sqlite3.Connection, *, slug: str, **kwargs: str | None) -> None:
    """Update article fields."""
    allowed = {"status", "url", "published_at", "title", "brief_path", "content_path"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        return

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values())
    values.append(slug)

    conn.execute(
        f"UPDATE articles SET {set_clause}, updated_at = datetime('now') WHERE slug = ?",
        values,
    )


def list_articles(
    conn: sqlite3.Connection,
    status: str | None = None,
) -> list[dict]:
    """List articles, optionally filtered by status."""
    if status:
        rows = conn.execute(
            "SELECT * FROM articles WHERE status = ? ORDER BY updated_at DESC", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM articles ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]
