"""Tests for batch 3: crosslink scoring, structural validation, content type word count."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from seedrank.data.db import init_db


# ---------------------------------------------------------------------------
# Task #27: Improved crosslink scoring
# ---------------------------------------------------------------------------
class TestCrosslinkScoring:
    """Test enriched crosslink scoring with volume, content type, recency."""

    @pytest.fixture
    def db_conn(self, tmp_path) -> sqlite3.Connection:
        db_path = tmp_path / "data" / "seedrank.db"
        db_path.parent.mkdir()
        init_db(db_path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _insert_article(
        self, conn, slug, title, kws, topics, status="published",
        content_type="blog", published_at=None,
    ):
        conn.execute(
            """INSERT INTO articles
               (slug, title, target_keywords, topics, status, content_type, published_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (slug, title, json.dumps(kws), json.dumps(topics),
             status, content_type, published_at),
        )

    def test_basic_overlap(self, db_conn: sqlite3.Connection) -> None:
        from seedrank.articles.crosslinks import find_forward_links

        self._insert_article(db_conn, "a", "Article A", ["kw1", "kw2"], ["seo"])
        self._insert_article(db_conn, "b", "Article B", ["kw1"], ["seo"])
        db_conn.commit()

        results = find_forward_links(db_conn, "a")
        assert len(results) == 1
        assert results[0]["slug"] == "b"
        assert results[0]["keyword_overlap"] == 1
        assert results[0]["topic_overlap"] == 1

    def test_volume_bonus(self, db_conn: sqlite3.Connection) -> None:
        """Articles with higher-volume overlapping keywords score higher."""
        from seedrank.articles.crosslinks import find_forward_links

        self._insert_article(db_conn, "a", "A", ["kw1", "kw2"], [])
        self._insert_article(db_conn, "b", "B", ["kw1"], [])
        self._insert_article(db_conn, "c", "C", ["kw2"], [])

        # kw1 has high volume, kw2 has low volume
        db_conn.execute(
            "INSERT INTO keywords (keyword, volume) VALUES (?, ?)", ("kw1", 5000)
        )
        db_conn.execute(
            "INSERT INTO keywords (keyword, volume) VALUES (?, ?)", ("kw2", 100)
        )
        db_conn.commit()

        results = find_forward_links(db_conn, "a")
        assert len(results) == 2
        # b overlaps on kw1 (high vol) → higher volume bonus
        b_result = next(r for r in results if r["slug"] == "b")
        c_result = next(r for r in results if r["slug"] == "c")
        assert b_result["score"] > c_result["score"]

    def test_content_type_bonus(self, db_conn: sqlite3.Connection) -> None:
        """Same content type gets a scoring boost."""
        from seedrank.articles.crosslinks import find_forward_links

        self._insert_article(
            db_conn, "a", "A", ["kw1"], [], content_type="blog"
        )
        self._insert_article(
            db_conn, "b", "B", ["kw1"], [], content_type="blog"
        )
        self._insert_article(
            db_conn, "c", "C", ["kw1"], [], content_type="landing"
        )
        db_conn.commit()

        results = find_forward_links(db_conn, "a")
        b_result = next(r for r in results if r["slug"] == "b")
        c_result = next(r for r in results if r["slug"] == "c")
        assert b_result["score"] > c_result["score"]

    def test_recency_bonus(self, db_conn: sqlite3.Connection) -> None:
        """Recently published articles get a recency boost."""
        from seedrank.articles.crosslinks import find_forward_links

        self._insert_article(db_conn, "a", "A", ["kw1"], [])
        self._insert_article(
            db_conn, "b", "B", ["kw1"], [],
            published_at="2026-03-01T00:00:00",
        )
        self._insert_article(
            db_conn, "c", "C", ["kw1"], [],
            published_at="2024-01-01T00:00:00",
        )
        db_conn.commit()

        results = find_forward_links(db_conn, "a")
        b_result = next(r for r in results if r["slug"] == "b")
        c_result = next(r for r in results if r["slug"] == "c")
        assert b_result["score"] > c_result["score"]

    def test_backward_excludes_existing_links(
        self, db_conn: sqlite3.Connection,
    ) -> None:
        from seedrank.articles.crosslinks import find_backward_links, register_link

        self._insert_article(db_conn, "a", "A", ["kw1"], [])
        self._insert_article(db_conn, "b", "B", ["kw1"], [])
        self._insert_article(db_conn, "c", "C", ["kw1"], [])
        register_link(db_conn, "b", "a")
        db_conn.commit()

        results = find_backward_links(db_conn, "a")
        slugs = [r["slug"] for r in results]
        assert "c" in slugs
        assert "b" not in slugs

    def test_no_overlap_returns_empty(self, db_conn: sqlite3.Connection) -> None:
        from seedrank.articles.crosslinks import find_forward_links

        self._insert_article(db_conn, "a", "A", ["kw1"], ["seo"])
        self._insert_article(db_conn, "b", "B", ["kw99"], ["cooking"])
        db_conn.commit()

        results = find_forward_links(db_conn, "a")
        assert results == []


# ---------------------------------------------------------------------------
# Task #28: Structural article validation
# ---------------------------------------------------------------------------
class TestStructuralValidation:
    """Test structural article validation checks."""

    def _run_check(self, content: str) -> list[dict]:
        """Run _check_structure and return issues."""
        from seedrank.cli.validate import _check_structure

        issues: list[dict] = []
        _check_structure(content, issues)
        return issues

    def test_good_structure(self) -> None:
        content = "# Main Title\n\nSome intro text.\n\n## Section 1\n\nContent.\n"
        issues = self._run_check(content)
        structure_issues = [
            i for i in issues if i["check"] in (
                "heading_hierarchy", "heading_skip", "no_headings",
                "long_paragraph", "image_alt", "meta_description",
            )
        ]
        assert structure_issues == []

    def test_no_headings(self) -> None:
        content = "Just a plain text article with no headings at all."
        issues = self._run_check(content)
        assert any(i["check"] == "no_headings" for i in issues)

    def test_first_heading_not_h1(self) -> None:
        content = "## Section\n\nContent.\n"
        issues = self._run_check(content)
        assert any(i["check"] == "heading_hierarchy" for i in issues)

    def test_heading_level_skip(self) -> None:
        content = "# Title\n\n### Skipped H2\n\nContent.\n"
        issues = self._run_check(content)
        assert any(i["check"] == "heading_skip" for i in issues)

    def test_long_paragraph(self) -> None:
        long_para = " ".join(["word"] * 350)
        content = f"# Title\n\n{long_para}\n"
        issues = self._run_check(content)
        assert any(i["check"] == "long_paragraph" for i in issues)

    def test_image_without_alt(self) -> None:
        content = "# Title\n\n![](image.png)\n"
        issues = self._run_check(content)
        assert any(i["check"] == "image_alt" for i in issues)

    def test_image_with_alt_ok(self) -> None:
        content = "# Title\n\n![A good description](image.png)\n"
        issues = self._run_check(content)
        assert not any(i["check"] == "image_alt" for i in issues)

    def test_frontmatter_missing_description(self) -> None:
        content = "---\ntitle: Test\n---\n\n# Title\n\nContent.\n"
        issues = self._run_check(content)
        assert any(i["check"] == "meta_description" for i in issues)

    def test_frontmatter_with_description_ok(self) -> None:
        content = "---\ntitle: Test\ndescription: A test article.\n---\n\n# Title\n"
        issues = self._run_check(content)
        assert not any(i["check"] == "meta_description" for i in issues)


# ---------------------------------------------------------------------------
# Task #29: Content type-aware word count
# ---------------------------------------------------------------------------
class TestContentTypeWordCount:
    """Test word count validation based on content type."""

    def test_below_content_type_minimum(self, tmp_path: Path) -> None:
        from seedrank.cli.validate import _check_content_type_word_count
        from seedrank.config.schema import ContentType, ProductConfig, PseoConfig

        cfg = PseoConfig(
            product=ProductConfig(name="Test", domain="test.com"),
            content_types=[
                ContentType(
                    slug="blog", route="/blog/[slug]",
                    content_dir="blog", label="Blog Post", min_words=1200,
                ),
            ],
        )

        path = tmp_path / "content" / "blog" / "test.md"
        path.parent.mkdir(parents=True)
        path.write_text("short article", encoding="utf-8")

        issues: list[dict] = []
        _check_content_type_word_count(path, 500, cfg, issues)
        assert len(issues) == 1
        assert "1200 words" in issues[0]["message"]
        assert "500" in issues[0]["message"]

    def test_above_content_type_minimum(self, tmp_path: Path) -> None:
        from seedrank.cli.validate import _check_content_type_word_count
        from seedrank.config.schema import ContentType, ProductConfig, PseoConfig

        cfg = PseoConfig(
            product=ProductConfig(name="Test", domain="test.com"),
            content_types=[
                ContentType(
                    slug="blog", route="/blog/[slug]",
                    content_dir="blog", label="Blog Post", min_words=800,
                ),
            ],
        )

        path = tmp_path / "content" / "blog" / "test.md"
        path.parent.mkdir(parents=True)

        issues: list[dict] = []
        _check_content_type_word_count(path, 1200, cfg, issues)
        assert issues == []

    def test_no_matching_content_type(self, tmp_path: Path) -> None:
        from seedrank.cli.validate import _check_content_type_word_count
        from seedrank.config.schema import ContentType, ProductConfig, PseoConfig

        cfg = PseoConfig(
            product=ProductConfig(name="Test", domain="test.com"),
            content_types=[
                ContentType(
                    slug="blog", route="/blog/[slug]",
                    content_dir="blog", label="Blog Post", min_words=1200,
                ),
            ],
        )

        path = tmp_path / "content" / "landing" / "test.md"
        path.parent.mkdir(parents=True)

        issues: list[dict] = []
        _check_content_type_word_count(path, 100, cfg, issues)
        assert issues == []  # No matching content type, no warning
