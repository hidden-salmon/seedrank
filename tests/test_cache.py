"""Tests for cache-first data access (seedrank.data.cache)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from seedrank.data.cache import (
    get_fresh_competitor_keywords,
    get_fresh_geo_queries,
    get_fresh_keywords,
    get_fresh_questions,
    get_fresh_serp,
)
from seedrank.data.db import SCHEMA_SQL


@pytest.fixture
def conn():
    """In-memory SQLite database with full schema."""
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA_SQL)
    db.execute(
        "INSERT INTO schema_info (key, value) VALUES ('version', '1')"
    )
    # Also create questions table
    db.executescript("""
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
    """)
    db.commit()
    yield db
    db.close()


def _recent_timestamp() -> str:
    """Timestamp from 5 days ago."""
    return (datetime.now(UTC) - timedelta(days=5)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _old_timestamp() -> str:
    """Timestamp from 120 days ago."""
    return (datetime.now(UTC) - timedelta(days=120)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


class TestGetFreshKeywords:
    def test_all_fresh(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO keywords (keyword, volume, fetched_at)"
            " VALUES (?, ?, ?)",
            ("django hosting", 1000, _recent_timestamp()),
        )
        conn.commit()

        stale, cached = get_fresh_keywords(conn, ["django hosting"])
        assert stale == []
        assert len(cached) == 1
        assert cached[0]["keyword"] == "django hosting"

    def test_all_stale(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO keywords (keyword, volume, fetched_at)"
            " VALUES (?, ?, ?)",
            ("old keyword", 500, _old_timestamp()),
        )
        conn.commit()

        stale, cached = get_fresh_keywords(conn, ["old keyword"])
        assert stale == ["old keyword"]
        assert cached == []

    def test_missing_keyword(self, conn: sqlite3.Connection) -> None:
        stale, cached = get_fresh_keywords(conn, ["nonexistent"])
        assert stale == ["nonexistent"]
        assert cached == []

    def test_mixed_fresh_and_stale(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO keywords (keyword, volume, fetched_at)"
            " VALUES (?, ?, ?)",
            ("fresh-kw", 800, _recent_timestamp()),
        )
        conn.execute(
            "INSERT INTO keywords (keyword, volume, fetched_at)"
            " VALUES (?, ?, ?)",
            ("stale-kw", 200, _old_timestamp()),
        )
        conn.commit()

        stale, cached = get_fresh_keywords(
            conn, ["fresh-kw", "stale-kw", "missing-kw"]
        )
        assert set(stale) == {"stale-kw", "missing-kw"}
        assert len(cached) == 1
        assert cached[0]["keyword"] == "fresh-kw"

    def test_custom_max_age(self, conn: sqlite3.Connection) -> None:
        ts = (datetime.now(UTC) - timedelta(days=10)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        conn.execute(
            "INSERT INTO keywords (keyword, volume, fetched_at)"
            " VALUES (?, ?, ?)",
            ("mid-age", 300, ts),
        )
        conn.commit()

        # Fresh with 30-day window
        stale, cached = get_fresh_keywords(conn, ["mid-age"], max_age_days=30)
        assert stale == []
        assert len(cached) == 1

        # Stale with 5-day window
        stale, cached = get_fresh_keywords(conn, ["mid-age"], max_age_days=5)
        assert stale == ["mid-age"]
        assert cached == []


class TestGetFreshSerp:
    def test_fresh_serp(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO serp_snapshots"
            " (keyword, rank, url, domain, fetched_at)"
            " VALUES (?, ?, ?, ?, ?)",
            ("django deploy", 1, "https://a.com", "a.com", _recent_timestamp()),
        )
        conn.commit()

        cached = get_fresh_serp(conn, "django deploy")
        assert len(cached) == 1

    def test_stale_serp(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO serp_snapshots"
            " (keyword, rank, url, domain, fetched_at)"
            " VALUES (?, ?, ?, ?, ?)",
            ("old query", 1, "https://a.com", "a.com", _old_timestamp()),
        )
        conn.commit()

        cached = get_fresh_serp(conn, "old query")
        assert cached == []

    def test_missing_serp(self, conn: sqlite3.Connection) -> None:
        cached = get_fresh_serp(conn, "nonexistent")
        assert cached == []


class TestGetFreshCompetitorKeywords:
    def test_fresh_data(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO competitor_keywords"
            " (competitor_slug, keyword, rank, volume, fetched_at)"
            " VALUES (?, ?, ?, ?, ?)",
            ("vercel", "deploy app", 3, 2000, _recent_timestamp()),
        )
        conn.commit()

        cached = get_fresh_competitor_keywords(conn, "vercel")
        assert len(cached) == 1

    def test_stale_data(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO competitor_keywords"
            " (competitor_slug, keyword, rank, volume, fetched_at)"
            " VALUES (?, ?, ?, ?, ?)",
            ("heroku", "deploy app", 5, 1500, _old_timestamp()),
        )
        conn.commit()

        cached = get_fresh_competitor_keywords(conn, "heroku")
        assert cached == []

    def test_wrong_slug(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO competitor_keywords"
            " (competitor_slug, keyword, rank, volume, fetched_at)"
            " VALUES (?, ?, ?, ?, ?)",
            ("vercel", "deploy app", 3, 2000, _recent_timestamp()),
        )
        conn.commit()

        cached = get_fresh_competitor_keywords(conn, "heroku")
        assert cached == []


class TestGetFreshQuestions:
    def test_fresh_questions(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO questions"
            " (question, source, source_keyword, fetched_at)"
            " VALUES (?, ?, ?, ?)",
            ("How to deploy Django?", "paa", "django deploy",
             _recent_timestamp()),
        )
        conn.commit()

        cached = get_fresh_questions(conn, "django deploy")
        assert len(cached) == 1

    def test_stale_questions(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO questions"
            " (question, source, source_keyword, fetched_at)"
            " VALUES (?, ?, ?, ?)",
            ("Old question?", "paa", "old topic", _old_timestamp()),
        )
        conn.commit()

        cached = get_fresh_questions(conn, "old topic")
        assert cached == []

    def test_no_questions_table(self) -> None:
        """Works even if questions table doesn't exist."""
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        cached = get_fresh_questions(db, "anything")
        assert cached == []
        db.close()


class TestGetFreshGeoQueries:
    def test_fresh_geo(self, conn: sqlite3.Connection) -> None:
        ts = (datetime.now(UTC) - timedelta(days=3)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        conn.execute(
            "INSERT INTO geo_queries"
            " (query, model, response_text, mentions_brand, queried_at)"
            " VALUES (?, ?, ?, ?, ?)",
            ("best hosting", "gpt4", "response here", 1, ts),
        )
        conn.commit()

        cached = get_fresh_geo_queries(conn, "best hosting", "gpt4")
        assert len(cached) == 1

    def test_stale_geo_7_day_window(self, conn: sqlite3.Connection) -> None:
        ts = (datetime.now(UTC) - timedelta(days=10)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        conn.execute(
            "INSERT INTO geo_queries"
            " (query, model, response_text, mentions_brand, queried_at)"
            " VALUES (?, ?, ?, ?, ?)",
            ("best hosting", "gpt4", "response here", 1, ts),
        )
        conn.commit()

        # Default 7-day window — 10 days ago is stale
        cached = get_fresh_geo_queries(conn, "best hosting", "gpt4")
        assert cached == []

    def test_different_model_not_cached(
        self, conn: sqlite3.Connection
    ) -> None:
        ts = (datetime.now(UTC) - timedelta(days=1)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        conn.execute(
            "INSERT INTO geo_queries"
            " (query, model, response_text, mentions_brand, queried_at)"
            " VALUES (?, ?, ?, ?, ?)",
            ("best hosting", "gpt4", "response", 1, ts),
        )
        conn.commit()

        # Different model = not cached
        cached = get_fresh_geo_queries(conn, "best hosting", "claude")
        assert cached == []
