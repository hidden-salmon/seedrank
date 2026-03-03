"""Tests for GSC URL matching and normalization."""

from __future__ import annotations

from seedrank.integrations.gsc import match_url_to_slug, normalize_url


class TestNormalizeUrl:
    """Test URL normalization."""

    def test_strips_protocol(self) -> None:
        assert normalize_url("https://example.com/blog/foo") == "example.com/blog/foo"

    def test_strips_http(self) -> None:
        assert normalize_url("http://example.com/blog/foo") == "example.com/blog/foo"

    def test_strips_www(self) -> None:
        assert normalize_url("https://www.example.com/blog/foo") == "example.com/blog/foo"

    def test_strips_trailing_slash(self) -> None:
        assert normalize_url("https://example.com/blog/foo/") == "example.com/blog/foo"

    def test_strips_query_params(self) -> None:
        assert normalize_url("https://example.com/blog/foo?ref=1&utm=x") == "example.com/blog/foo"

    def test_strips_fragment(self) -> None:
        assert normalize_url("https://example.com/blog/foo#section") == "example.com/blog/foo"

    def test_all_together(self) -> None:
        assert (
            normalize_url("http://www.example.com/blog/foo/?q=1#top")
            == "example.com/blog/foo"
        )

    def test_root_path(self) -> None:
        assert normalize_url("https://example.com/") == "example.com"

    def test_root_no_slash(self) -> None:
        assert normalize_url("https://example.com") == "example.com"


class TestMatchUrlToSlug:
    """Test URL-to-slug matching."""

    ARTICLES = [
        {"slug": "deploy-nextjs", "url": "/blog/deploy-nextjs"},
        {"slug": "email-marketing-guide", "url": "https://example.com/guides/email-marketing-guide"},
        {"slug": "mailchimp-vs-moonbeam", "url": "https://www.example.com/compare/mailchimp-vs-moonbeam/"},
    ]

    def test_exact_match(self) -> None:
        result = match_url_to_slug("/blog/deploy-nextjs", self.ARTICLES)
        assert result == "deploy-nextjs"

    def test_normalized_match_strips_www(self) -> None:
        result = match_url_to_slug(
            "https://example.com/compare/mailchimp-vs-moonbeam",
            self.ARTICLES,
        )
        assert result == "mailchimp-vs-moonbeam"

    def test_normalized_match_strips_trailing_slash(self) -> None:
        result = match_url_to_slug(
            "https://example.com/guides/email-marketing-guide/",
            self.ARTICLES,
        )
        assert result == "email-marketing-guide"

    def test_normalized_match_strips_query(self) -> None:
        result = match_url_to_slug(
            "https://example.com/guides/email-marketing-guide?ref=gsc",
            self.ARTICLES,
        )
        assert result == "email-marketing-guide"

    def test_slug_fallback(self) -> None:
        """Match by slug in the last path segment."""
        result = match_url_to_slug(
            "https://other-domain.com/blog/deploy-nextjs",
            self.ARTICLES,
        )
        assert result == "deploy-nextjs"

    def test_no_match(self) -> None:
        result = match_url_to_slug(
            "https://example.com/totally-unknown-page",
            self.ARTICLES,
        )
        assert result is None

    def test_empty_articles(self) -> None:
        result = match_url_to_slug("https://example.com/foo", [])
        assert result is None
