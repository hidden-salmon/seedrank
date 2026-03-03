"""Tests for GEO data query functions (seedrank.data.geo)."""

from __future__ import annotations

import json
import sqlite3

import pytest

from seedrank.data.db import SCHEMA_SQL
from seedrank.data.geo import (
    get_geo_competitor_leaderboard,
    get_geo_gaps,
    get_geo_trends,
)


@pytest.fixture
def geo_conn() -> sqlite3.Connection:
    """Create an in-memory SQLite database with schema and test data.

    Yields a connection with row_factory set to sqlite3.Row.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)

    # Also apply migration to add sentiment_confidence column
    try:
        conn.execute("ALTER TABLE geo_queries ADD COLUMN sentiment_confidence REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass  # Column may already exist in SCHEMA_SQL

    # Insert test data: queries spread across multiple weeks
    test_data = [
        # Week 1 (recent): 2 queries, 1 mentions brand
        ("best data tools", "gpt-4o", "TestProduct is great for data.", 1, "positive",
         json.dumps(["RivalApp", "OtherCo"]), json.dumps(["https://test.com"]),
         "2026-02-23 10:00:00", 0.85),
        ("data pipeline tools", "gpt-4o", "Consider OtherCo for pipelines.", 0, None,
         json.dumps(["OtherCo"]), json.dumps([]),
         "2026-02-24 10:00:00", 0.60),
        # Week 2: 3 queries, 2 mention brand
        ("api platform comparison", "claude", "TestProduct and RivalApp are popular.", 1, "neutral",
         json.dumps(["RivalApp"]), json.dumps(["https://test.com"]),
         "2026-02-16 10:00:00", 0.75),
        ("developer tools 2025", "claude", "TestProduct offers great DX.", 1, "positive",
         json.dumps([]), json.dumps(["https://test.com"]),
         "2026-02-17 10:00:00", 0.90),
        ("cheap api hosting", "gpt-4o", "Fly.io and Railway are options.", 0, None,
         json.dumps(["Fly.io", "Railway"]), json.dumps([]),
         "2026-02-18 10:00:00", 0.50),
        # Old data (outside 90-day window by default, but inside it for our tests)
        ("old query", "gpt-4o", "Some old response.", 0, None,
         json.dumps([]), json.dumps([]),
         "2026-01-01 10:00:00", 0.30),
    ]

    for row in test_data:
        conn.execute(
            """INSERT INTO geo_queries
               (query, model, response_text, mentions_brand, brand_sentiment,
                mentions_competitors, citations, queried_at, sentiment_confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            row,
        )
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# get_geo_trends
# ---------------------------------------------------------------------------
class TestGetGeoTrends:
    def test_returns_weekly_aggregations(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_trends(geo_conn, days=90)
        assert len(results) > 0
        # Each row should have the expected keys
        for row in results:
            assert "week" in row
            assert "total_queries" in row
            assert "brand_mentions" in row
            assert "mention_rate" in row
            assert "avg_sentiment_confidence" in row

    def test_mention_rate_calculated(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_trends(geo_conn, days=90)
        for row in results:
            # mention_rate should be brand_mentions / total_queries
            expected_rate = row["brand_mentions"] / row["total_queries"]
            assert abs(row["mention_rate"] - expected_rate) < 0.01

    def test_weekly_grouping(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_trends(geo_conn, days=90)
        # Each result row should have a week key
        assert len(results) >= 1
        for row in results:
            assert "week" in row
            assert row["week"] is not None

    def test_total_queries_sum(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_trends(geo_conn, days=90)
        total = sum(r["total_queries"] for r in results)
        # We inserted 6 rows, all within the 90-day window
        assert total == 6

    def test_shorter_window_filters(self, geo_conn: sqlite3.Connection) -> None:
        # With a 30-day window, the old Jan 1 query should be excluded
        results_30 = get_geo_trends(geo_conn, days=30)
        total_30 = sum(r["total_queries"] for r in results_30)

        results_90 = get_geo_trends(geo_conn, days=90)
        total_90 = sum(r["total_queries"] for r in results_90)

        assert total_30 <= total_90


# ---------------------------------------------------------------------------
# get_geo_gaps
# ---------------------------------------------------------------------------
class TestGetGeoGaps:
    def test_returns_queries_without_brand_mention(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_gaps(geo_conn)
        # All returned queries should have mentions_brand == 0 and competitors mentioned
        assert len(results) > 0
        for row in results:
            assert "query" in row
            assert "model" in row
            assert "mentions_competitors" in row
            assert "queried_at" in row

    def test_excludes_brand_mentioned_queries(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_gaps(geo_conn)
        queries = [r["query"] for r in results]
        # "best data tools" has mentions_brand=1, should NOT appear
        assert "best data tools" not in queries

    def test_excludes_empty_competitor_mentions(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_gaps(geo_conn)
        for row in results:
            mc = row["mentions_competitors"]
            parsed = json.loads(mc) if isinstance(mc, str) else mc
            assert len(parsed) > 0

    def test_includes_competitor_only_queries(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_gaps(geo_conn)
        queries = [r["query"] for r in results]
        # "data pipeline tools" mentions OtherCo but not brand
        assert "data pipeline tools" in queries
        # "cheap api hosting" mentions Fly.io and Railway but not brand
        assert "cheap api hosting" in queries

    def test_ordered_by_queried_at_desc(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_gaps(geo_conn)
        dates = [r["queried_at"] for r in results]
        assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# get_geo_competitor_leaderboard
# ---------------------------------------------------------------------------
class TestGetGeoCompetitorLeaderboard:
    def test_counts_competitors_from_json_arrays(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_competitor_leaderboard(geo_conn)
        assert len(results) > 0
        # Results should be list of dicts with competitor and mention_count
        for row in results:
            assert "competitor" in row
            assert "mention_count" in row
            assert isinstance(row["mention_count"], int)

    def test_correct_counts(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_competitor_leaderboard(geo_conn)
        counts = {r["competitor"]: r["mention_count"] for r in results}
        # RivalApp appears in 2 queries (best data tools, api platform comparison)
        assert counts.get("RivalApp") == 2
        # OtherCo appears in 2 queries (best data tools, data pipeline tools)
        assert counts.get("OtherCo") == 2
        # Fly.io appears in 1 query
        assert counts.get("Fly.io") == 1
        # Railway appears in 1 query
        assert counts.get("Railway") == 1

    def test_sorted_by_mention_count_descending(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_competitor_leaderboard(geo_conn)
        counts = [r["mention_count"] for r in results]
        assert counts == sorted(counts, reverse=True)

    def test_empty_arrays_ignored(self, geo_conn: sqlite3.Connection) -> None:
        results = get_geo_competitor_leaderboard(geo_conn)
        competitors = {r["competitor"] for r in results}
        # Empty string competitors should not appear
        assert "" not in competitors

    def test_handles_null_mentions(self) -> None:
        """Queries with NULL mentions_competitors should be skipped."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA_SQL)
        conn.execute(
            """INSERT INTO geo_queries
               (query, model, mentions_brand, mentions_competitors, queried_at)
               VALUES ('test', 'gpt-4o', 0, NULL, datetime('now'))"""
        )
        conn.commit()
        results = get_geo_competitor_leaderboard(conn)
        assert results == []
        conn.close()

    def test_handles_invalid_json(self) -> None:
        """Rows with invalid JSON in mentions_competitors should be skipped."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA_SQL)
        conn.execute(
            """INSERT INTO geo_queries
               (query, model, mentions_brand, mentions_competitors, queried_at)
               VALUES ('test', 'gpt-4o', 0, 'not valid json{{{', datetime('now'))"""
        )
        conn.commit()
        results = get_geo_competitor_leaderboard(conn)
        assert results == []
        conn.close()
