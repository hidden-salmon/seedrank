"""Tests for new performance queries (declining articles, per-slug)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from seedrank.data.articles import register_article
from seedrank.data.db import connect, get_db_path
from seedrank.data.performance import (
    get_declining_articles,
    get_performance_for_slug,
    upsert_performance,
)


class TestGetPerformanceForSlug:
    """Test daily performance data for a specific article."""

    def test_returns_daily_data(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        today = date.today()
        with connect(db_path) as conn:
            register_article(conn, slug="test-article", title="Test")
            for i in range(5):
                d = (today - timedelta(days=i)).isoformat()
                upsert_performance(
                    conn,
                    slug="test-article",
                    date=d,
                    impressions=100 - i * 10,
                    clicks=10 - i,
                )

        with connect(db_path) as conn:
            rows = get_performance_for_slug(conn, "test-article", days=30)
            assert len(rows) == 5
            assert "date" in rows[0]
            assert "impressions" in rows[0]

    def test_returns_empty_for_unknown_slug(
        self, workspace_with_db: Path
    ) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            rows = get_performance_for_slug(conn, "nonexistent", days=30)
            assert rows == []


class TestGetDecliningArticles:
    """Test finding articles with declining traffic."""

    def test_detects_declining_traffic(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        today = date.today()
        with connect(db_path) as conn:
            register_article(conn, slug="declining", title="Declining")
            # Prior period: high traffic (days 60-31)
            for i in range(30, 60):
                d = (today - timedelta(days=i)).isoformat()
                upsert_performance(
                    conn,
                    slug="declining",
                    date=d,
                    impressions=100,
                    clicks=10,
                    position_avg=5.0,
                )
            # Recent period: low traffic (days 0-29)
            for i in range(30):
                d = (today - timedelta(days=i)).isoformat()
                upsert_performance(
                    conn,
                    slug="declining",
                    date=d,
                    impressions=30,
                    clicks=3,
                    position_avg=12.0,
                )

        with connect(db_path) as conn:
            rows = get_declining_articles(conn, days=60)
            assert len(rows) == 1
            assert rows[0]["slug"] == "declining"
            assert rows[0]["impressions_change_pct"] < 0

    def test_stable_article_not_flagged(
        self, workspace_with_db: Path
    ) -> None:
        db_path = get_db_path(workspace_with_db)
        today = date.today()
        with connect(db_path) as conn:
            register_article(conn, slug="stable", title="Stable")
            # Same traffic in both periods
            for i in range(60):
                d = (today - timedelta(days=i)).isoformat()
                upsert_performance(
                    conn,
                    slug="stable",
                    date=d,
                    impressions=100,
                    clicks=10,
                    position_avg=5.0,
                )

        with connect(db_path) as conn:
            rows = get_declining_articles(conn, days=60)
            assert len(rows) == 0
