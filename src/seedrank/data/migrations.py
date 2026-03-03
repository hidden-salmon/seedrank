"""Schema migration system for SQLite database.

Each migration is a function that takes a connection and applies DDL changes.
Migrations are numbered sequentially and tracked via schema_info.version.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

# List of migrations indexed by version number.
# Migration at index 0 is for upgrading from version 1 → 2, etc.
# The base schema (version 1) is applied by init_db in db.py.
MIGRATIONS: list[tuple[str, str]] = [
    # (description, SQL)
    # Version 1 → 2: add questions table and sentiment_confidence to geo_queries
    (
        "Add questions table and sentiment_confidence column",
        """
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            source TEXT NOT NULL,
            source_keyword TEXT,
            persona_slug TEXT,
            ai_volume INTEGER,
            google_volume INTEGER,
            priority TEXT DEFAULT 'secondary',
            status TEXT DEFAULT 'new',
            assigned_slug TEXT,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(question, source)
        );
        CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status);
        CREATE INDEX IF NOT EXISTS idx_questions_assigned ON questions(assigned_slug);

        -- Add sentiment_confidence to geo_queries if not present
        ALTER TABLE geo_queries ADD COLUMN sentiment_confidence REAL DEFAULT 0.0;
        """,
    ),
    # Version 2 → 3: add SERP competitor visibility table for cross-keyword landscape analysis
    (
        "Add serp_competitor_visibility table for cross-keyword SERP landscape tracking",
        """
        CREATE TABLE IF NOT EXISTS serp_competitor_visibility (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            keywords_count INTEGER,
            avg_position REAL,
            median_position INTEGER,
            rating INTEGER,
            etv REAL,
            visibility REAL,
            keyword_positions TEXT,  -- JSON: {"keyword": position, ...}
            research_set TEXT NOT NULL,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_scv_domain ON serp_competitor_visibility(domain);
        CREATE INDEX IF NOT EXISTS idx_scv_set ON serp_competitor_visibility(research_set);
        """,
    ),
]


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Get the current schema version from the database."""
    try:
        row = conn.execute(
            "SELECT value FROM schema_info WHERE key = 'version'"
        ).fetchone()
        if row:
            return int(row[0] if isinstance(row, tuple) else row["value"])
    except (sqlite3.OperationalError, KeyError):
        pass
    return 0


def migrate_db(conn: sqlite3.Connection) -> int:
    """Run any pending migrations and return the final schema version.

    Returns:
        The schema version after running all applicable migrations.
    """
    current = get_schema_version(conn)
    target = len(MIGRATIONS) + 1  # Version 1 is the base schema

    if current >= target:
        return current

    if current == 0:
        logger.warning("Schema version is 0 — database may not be initialized")
        return 0

    applied = 0
    for i in range(current - 1, len(MIGRATIONS)):
        description, sql = MIGRATIONS[i]
        new_version = i + 2  # Migrations start at version 2

        logger.info("Applying migration %d: %s", new_version, description)
        try:
            conn.executescript(sql)
            conn.execute(
                "INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)",
                ("version", str(new_version)),
            )
            conn.commit()
            applied += 1
        except sqlite3.Error:
            logger.exception("Migration %d failed", new_version)
            conn.rollback()
            raise

    if applied > 0:
        logger.info("Applied %d migration(s), now at version %d", applied, target)

    return target
