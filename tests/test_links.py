"""Tests for link graph queries."""

from __future__ import annotations

from pathlib import Path

from seedrank.articles.crosslinks import register_link
from seedrank.data.articles import register_article
from seedrank.data.db import connect, get_db_path
from seedrank.data.links import get_all_links, get_link_stats, get_orphan_articles


class TestGetAllLinks:
    """Test dumping the full link graph."""

    def test_returns_all_links(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(conn, slug="a", title="A")
            register_article(conn, slug="b", title="B")
            register_article(conn, slug="c", title="C")
            register_link(conn, "a", "b", "link to b")
            register_link(conn, "b", "c", "link to c")

        with connect(db_path) as conn:
            links = get_all_links(conn)
            assert len(links) == 2
            slugs = {(lnk["from_slug"], lnk["to_slug"]) for lnk in links}
            assert ("a", "b") in slugs
            assert ("b", "c") in slugs

    def test_empty_when_no_links(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            links = get_all_links(conn)
            assert links == []


class TestOrphanArticles:
    """Test finding articles with no inbound links."""

    def test_finds_orphans(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(
                conn, slug="linked", title="Linked", status="published"
            )
            register_article(
                conn, slug="orphan", title="Orphan", status="published"
            )
            register_article(
                conn, slug="source", title="Source", status="published"
            )
            register_link(conn, "source", "linked")

        with connect(db_path) as conn:
            orphans = get_orphan_articles(conn)
            orphan_slugs = [o["slug"] for o in orphans]
            assert "orphan" in orphan_slugs
            assert "source" in orphan_slugs
            assert "linked" not in orphan_slugs

    def test_excludes_unpublished(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(
                conn, slug="draft", title="Draft", status="writing"
            )

        with connect(db_path) as conn:
            orphans = get_orphan_articles(conn)
            assert len(orphans) == 0


class TestLinkStats:
    """Test per-article link count stats."""

    def test_counts_inbound_outbound(self, workspace_with_db: Path) -> None:
        db_path = get_db_path(workspace_with_db)
        with connect(db_path) as conn:
            register_article(
                conn, slug="hub", title="Hub", status="published"
            )
            register_article(
                conn, slug="spoke1", title="Spoke 1", status="published"
            )
            register_article(
                conn, slug="spoke2", title="Spoke 2", status="published"
            )
            register_link(conn, "hub", "spoke1")
            register_link(conn, "hub", "spoke2")
            register_link(conn, "spoke1", "hub")

        with connect(db_path) as conn:
            stats = get_link_stats(conn)
            by_slug = {s["slug"]: s for s in stats}

            assert by_slug["hub"]["outbound_links"] == 2
            assert by_slug["hub"]["inbound_links"] == 1
            assert by_slug["spoke1"]["outbound_links"] == 1
            assert by_slug["spoke1"]["inbound_links"] == 1
            assert by_slug["spoke2"]["outbound_links"] == 0
            assert by_slug["spoke2"]["inbound_links"] == 1
