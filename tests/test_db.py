"""Tests for database operations."""

from __future__ import annotations

from pathlib import Path

from seedrank.data.articles import list_articles, register_article, update_article
from seedrank.data.calendar import (
    add_to_calendar,
    get_calendar_items,
    get_next_items,
    update_calendar_status,
)
from seedrank.data.db import connect, get_db_path, get_table_counts, init_db
from seedrank.data.keywords import get_keyword_gaps, query_keywords
from seedrank.data.performance import get_performance, upsert_performance


class TestDatabaseInit:
    """Test database initialization."""

    def test_init_creates_db(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data" / "seedrank.db"
        init_db(db_path)
        assert db_path.exists()

    def test_init_creates_tables(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data" / "seedrank.db"
        init_db(db_path)
        counts = get_table_counts(db_path)
        assert "keywords" in counts
        assert "articles" in counts
        assert "content_calendar" in counts

    def test_schema_version(self, tmp_path: Path) -> None:
        db_path = tmp_path / "data" / "seedrank.db"
        init_db(db_path)
        with connect(db_path) as conn:
            row = conn.execute("SELECT value FROM schema_info WHERE key = 'version'").fetchone()
            assert row is not None
            assert row["value"] == "1"


class TestKeywords:
    """Test keyword operations."""

    def test_insert_and_query(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            conn.execute(
                """INSERT INTO keywords (keyword, volume, kd, cpc, intent, fetched_at)
                   VALUES ('test keyword', 1000, 25.5, 1.50, 'informational', datetime('now'))"""
            )

        with connect(db_path) as conn:
            rows = query_keywords(conn, limit=10)
            assert len(rows) == 1
            assert rows[0]["keyword"] == "test keyword"
            assert rows[0]["volume"] == 1000

    def test_keyword_gaps(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            conn.execute(
                """INSERT INTO competitor_keywords
                   (competitor_slug, keyword, rank, volume, fetched_at)
                   VALUES ('comp1', 'gap keyword', 5, 500, datetime('now'))"""
            )

        with connect(db_path) as conn:
            gaps = get_keyword_gaps(conn)
            assert len(gaps) == 1
            assert gaps[0]["keyword"] == "gap keyword"


class TestArticles:
    """Test article operations."""

    def test_register_and_list(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(
                conn,
                slug="test-article",
                title="Test Article",
                target_keywords=["keyword1", "keyword2"],
                topics=["topic1"],
            )

        with connect(db_path) as conn:
            articles = list_articles(conn)
            assert len(articles) == 1
            assert articles[0]["slug"] == "test-article"
            assert articles[0]["title"] == "Test Article"

    def test_update_article(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(conn, slug="test", title="Test")

        with connect(db_path) as conn:
            update_article(conn, slug="test", status="published", url="/blog/test")

        with connect(db_path) as conn:
            articles = list_articles(conn)
            assert articles[0]["status"] == "published"
            assert articles[0]["url"] == "/blog/test"

    def test_list_by_status(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(conn, slug="a1", title="A1", status="planned")
            register_article(conn, slug="a2", title="A2", status="published")

        with connect(db_path) as conn:
            planned = list_articles(conn, status="planned")
            assert len(planned) == 1
            assert planned[0]["slug"] == "a1"


class TestCalendar:
    """Test calendar operations."""

    def test_add_and_get(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            add_to_calendar(conn, slug="article-1", target_keywords=["kw1"], priority_score=0.8)

        with connect(db_path) as conn:
            items = get_calendar_items(conn)
            assert len(items) == 1
            assert items[0]["slug"] == "article-1"
            assert items[0]["priority_score"] == 0.8

    def test_next_items_ordered_by_priority(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            add_to_calendar(conn, slug="low", priority_score=0.2)
            add_to_calendar(conn, slug="high", priority_score=0.9)
            add_to_calendar(conn, slug="mid", priority_score=0.5)

        with connect(db_path) as conn:
            items = get_next_items(conn, count=3)
            slugs = [i["slug"] for i in items]
            assert slugs == ["high", "mid", "low"]

    def test_update_status(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            add_to_calendar(conn, slug="test")

        with connect(db_path) as conn:
            update_calendar_status(conn, slug="test", status="writing")

        with connect(db_path) as conn:
            items = get_calendar_items(conn, status="writing")
            assert len(items) == 1


class TestPerformance:
    """Test performance data operations."""

    def test_upsert_and_query(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        # Need an article first
        with connect(db_path) as conn:
            register_article(conn, slug="perf-test", title="Perf Test")

        with connect(db_path) as conn:
            from datetime import date

            upsert_performance(
                conn,
                slug="perf-test",
                date=date.today().isoformat(),
                impressions=100,
                clicks=10,
                position_avg=5.5,
                ctr=0.1,
            )

        with connect(db_path) as conn:
            rows = get_performance(conn, days=7)
            assert len(rows) == 1
            assert rows[0]["impressions"] == 100
