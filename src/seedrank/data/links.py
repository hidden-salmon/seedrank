"""Link graph queries — dump links, find orphans, compute stats."""

from __future__ import annotations

import sqlite3


def get_all_links(conn: sqlite3.Connection) -> list[dict]:
    """Return all article crosslinks."""
    rows = conn.execute(
        """SELECT from_slug, to_slug, anchor_text, created_at
           FROM article_links
           ORDER BY created_at DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_orphan_articles(conn: sqlite3.Connection) -> list[dict]:
    """Find published articles with zero inbound links."""
    rows = conn.execute(
        """SELECT a.slug, a.title, a.url, a.published_at,
                  a.target_keywords, a.topics
           FROM articles a
           LEFT JOIN article_links al ON a.slug = al.to_slug
           WHERE a.status = 'published' AND al.id IS NULL
           ORDER BY a.published_at ASC"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_link_stats(conn: sqlite3.Connection) -> list[dict]:
    """Per-article link counts (inbound and outbound) for published articles."""
    rows = conn.execute(
        """SELECT
               a.slug,
               a.title,
               COALESCE(outb.cnt, 0) AS outbound_links,
               COALESCE(inb.cnt, 0) AS inbound_links
           FROM articles a
           LEFT JOIN (
               SELECT from_slug, COUNT(*) AS cnt
               FROM article_links GROUP BY from_slug
           ) outb ON a.slug = outb.from_slug
           LEFT JOIN (
               SELECT to_slug, COUNT(*) AS cnt
               FROM article_links GROUP BY to_slug
           ) inb ON a.slug = inb.to_slug
           WHERE a.status = 'published'
           ORDER BY inbound_links ASC, outbound_links ASC"""
    ).fetchall()
    return [dict(r) for r in rows]
