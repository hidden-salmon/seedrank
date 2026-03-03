"""SQLite database schema, initialization, and connection management."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Keywords from DataForSEO
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,
    volume INTEGER,
    kd REAL,
    cpc REAL,
    competition REAL,
    intent TEXT,
    serp_features TEXT,  -- JSON array
    cluster_id TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_keywords_cluster ON keywords(cluster_id);

-- SERP snapshots
CREATE TABLE IF NOT EXISTS serp_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    rank INTEGER NOT NULL,
    url TEXT,
    domain TEXT,
    title TEXT,
    snippet TEXT,
    result_type TEXT DEFAULT 'organic',
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (keyword) REFERENCES keywords(keyword)
);
CREATE INDEX IF NOT EXISTS idx_serp_keyword ON serp_snapshots(keyword);

-- Competitor keywords from DataForSEO
CREATE TABLE IF NOT EXISTS competitor_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_slug TEXT NOT NULL,
    keyword TEXT NOT NULL,
    rank INTEGER,
    url TEXT,
    volume INTEGER,
    kd REAL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_comp_kw_slug ON competitor_keywords(competitor_slug);
CREATE INDEX IF NOT EXISTS idx_comp_kw_keyword ON competitor_keywords(keyword);

-- GEO query results
CREATE TABLE IF NOT EXISTS geo_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    model TEXT NOT NULL,
    response_text TEXT,
    mentions_brand INTEGER DEFAULT 0,
    brand_sentiment TEXT,
    mentions_competitors TEXT,  -- JSON array
    citations TEXT,  -- JSON array
    queried_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_geo_query ON geo_queries(query);
CREATE INDEX IF NOT EXISTS idx_geo_model ON geo_queries(model);

-- Article directory
CREATE TABLE IF NOT EXISTS articles (
    slug TEXT PRIMARY KEY,
    url TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned',
    content_type TEXT,
    target_keywords TEXT,  -- JSON array
    topics TEXT,  -- JSON array
    brief_path TEXT,
    content_path TEXT,
    published_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);

-- Article cross-links
CREATE TABLE IF NOT EXISTS article_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_slug TEXT NOT NULL,
    to_slug TEXT NOT NULL,
    anchor_text TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (from_slug) REFERENCES articles(slug),
    FOREIGN KEY (to_slug) REFERENCES articles(slug),
    UNIQUE(from_slug, to_slug)
);

-- Article performance from GSC
CREATE TABLE IF NOT EXISTS article_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL,
    date TEXT NOT NULL,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    position_avg REAL,
    ctr REAL,
    FOREIGN KEY (slug) REFERENCES articles(slug),
    UNIQUE(slug, date)
);
CREATE INDEX IF NOT EXISTS idx_perf_slug ON article_performance(slug);
CREATE INDEX IF NOT EXISTS idx_perf_date ON article_performance(date);

-- Content calendar
CREATE TABLE IF NOT EXISTS content_calendar (
    slug TEXT PRIMARY KEY,
    priority_score REAL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'queued',
    target_keywords TEXT,  -- JSON array
    brief_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_calendar_status ON content_calendar(status);
CREATE INDEX IF NOT EXISTS idx_calendar_priority ON content_calendar(priority_score DESC);

-- API cost tracking
CREATE TABLE IF NOT EXISTS api_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    endpoint TEXT,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    context TEXT,
    called_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_db_path(workspace: Path) -> Path:
    """Return the path to the SQLite database file."""
    return workspace / "data" / "seedrank.db"


def init_db(db_path: Path) -> None:
    """Initialize the database with the full schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.execute(
            "INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)",
            ("version", str(SCHEMA_VERSION)),
        )
        conn.commit()
    finally:
        conn.close()


@contextmanager
def connect(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections with WAL mode and foreign keys."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_table_counts(db_path: Path) -> dict[str, int]:
    """Return row counts for all data tables."""
    tables = [
        "keywords",
        "serp_snapshots",
        "competitor_keywords",
        "serp_competitor_visibility",
        "geo_queries",
        "articles",
        "article_links",
        "article_performance",
        "content_calendar",
        "api_costs",
    ]
    counts = {}
    with connect(db_path) as conn:
        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
                counts[table] = row[0]
            except sqlite3.OperationalError:
                # Table may not exist yet (created by migration, not base schema)
                pass
    return counts
