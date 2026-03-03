"""Tests for crosslink suggestion engine."""

from __future__ import annotations

from pathlib import Path

from seedrank.articles.crosslinks import find_backward_links, find_forward_links, register_link
from seedrank.data.articles import register_article
from seedrank.data.db import connect, get_db_path


class TestForwardLinks:
    """Test finding articles to link TO."""

    def test_finds_overlapping_articles(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(
                conn,
                slug="new-article",
                title="New",
                target_keywords=["email marketing", "automation"],
                topics=["marketing"],
                status="writing",
            )
            register_article(
                conn,
                slug="published-1",
                title="Published 1",
                target_keywords=["email marketing", "templates"],
                topics=["marketing"],
                status="published",
            )
            register_article(
                conn,
                slug="published-2",
                title="Published 2",
                target_keywords=["sms marketing"],
                topics=["sales"],
                status="published",
            )

        with connect(db_path) as conn:
            links = find_forward_links(conn, "new-article")
            assert len(links) == 1
            assert links[0]["slug"] == "published-1"
            assert links[0]["score"] > 0

    def test_returns_empty_for_no_overlap(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(
                conn,
                slug="a1",
                title="A1",
                target_keywords=["topic-a"],
                status="writing",
            )
            register_article(
                conn,
                slug="a2",
                title="A2",
                target_keywords=["topic-z"],
                status="published",
            )

        with connect(db_path) as conn:
            links = find_forward_links(conn, "a1")
            assert len(links) == 0


class TestBackwardLinks:
    """Test finding articles that should link TO a new article."""

    def test_excludes_existing_links(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(
                conn,
                slug="target",
                title="Target",
                target_keywords=["kw1"],
                topics=["t1"],
                status="published",
            )
            register_article(
                conn,
                slug="linker",
                title="Linker",
                target_keywords=["kw1"],
                topics=["t1"],
                status="published",
            )
            register_link(conn, "linker", "target", "click here")

        with connect(db_path) as conn:
            links = find_backward_links(conn, "target")
            assert len(links) == 0

    def test_finds_unlinked_articles(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(
                conn,
                slug="target",
                title="Target",
                target_keywords=["shared-kw"],
                topics=["shared-topic"],
                status="published",
            )
            register_article(
                conn,
                slug="candidate",
                title="Candidate",
                target_keywords=["shared-kw"],
                topics=["shared-topic"],
                status="published",
            )

        with connect(db_path) as conn:
            links = find_backward_links(conn, "target")
            assert len(links) == 1
            assert links[0]["slug"] == "candidate"


class TestRegisterLink:
    """Test link registration."""

    def test_register_link(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(conn, slug="from", title="From")
            register_article(conn, slug="to", title="To")
            register_link(conn, "from", "to", "link text")

        with connect(db_path) as conn:
            row = conn.execute("SELECT * FROM article_links WHERE from_slug = 'from'").fetchone()
            assert row is not None
            assert row["to_slug"] == "to"
            assert row["anchor_text"] == "link text"

    def test_duplicate_link_ignored(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(conn, slug="from", title="From")
            register_article(conn, slug="to", title="To")
            register_link(conn, "from", "to")
            register_link(conn, "from", "to")  # Should not raise

        with connect(db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM article_links WHERE from_slug = 'from'"
            ).fetchone()[0]
            assert count == 1
