"""Tests for research modules — DataForSEO client, GEO client, and validator."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from seedrank.config.schema import AIModelConfig, DataForSeoConfig
from seedrank.data.db import init_db
from seedrank.research.dataforseo import DataForSEOClient
from seedrank.research.geo import GEOClient
from seedrank.research.validator import validate_research


class TestDataForSEOClient:
    """Test DataForSEO client with mocked HTTP calls."""

    def test_init_requires_credentials(self) -> None:
        config = DataForSeoConfig(login="", password="")
        with pytest.raises(ValueError, match="credentials not found"):
            DataForSEOClient(config)

    def test_init_from_config(self) -> None:
        config = DataForSeoConfig(login="user", password="pass")
        client = DataForSEOClient(config)
        assert client.login == "user"
        assert client.password == "pass"
        assert client.default_location == 2840

    @patch.dict("os.environ", {"DATAFORSEO_LOGIN": "env_user", "DATAFORSEO_PASSWORD": "env_pass"})
    def test_init_from_env(self) -> None:
        config = DataForSeoConfig(login="", password="")
        client = DataForSEOClient(config)
        assert client.login == "env_user"
        assert client.password == "env_pass"

    def test_extract_results(self) -> None:
        config = DataForSeoConfig(login="user", password="pass")
        client = DataForSEOClient(config)
        tasks = [
            {
                "status_code": 20000,
                "result": [{"items": [{"keyword": "test", "search_volume": 100}]}],
            }
        ]
        items = client._extract_results(tasks)
        assert len(items) == 1
        assert items[0]["keyword"] == "test"

    def test_extract_results_direct_format(self) -> None:
        """Google Ads Search Volume returns keyword data directly in result[], not nested in items."""
        config = DataForSeoConfig(login="user", password="pass")
        client = DataForSEOClient(config)
        tasks = [
            {
                "status_code": 20000,
                "result": [
                    {"keyword": "fzf", "search_volume": 4400, "competition": "LOW"},
                    {"keyword": "ripgrep", "search_volume": 2900, "competition": "LOW"},
                ],
            }
        ]
        items = client._extract_results(tasks)
        assert len(items) == 2
        assert items[0]["keyword"] == "fzf"
        assert items[1]["keyword"] == "ripgrep"

    def test_extract_results_skips_errors(self) -> None:
        config = DataForSeoConfig(login="user", password="pass")
        client = DataForSEOClient(config)
        tasks = [
            {"status_code": 40000, "result": []},
            {
                "status_code": 20000,
                "result": [{"items": [{"keyword": "good"}]}],
            },
        ]
        items = client._extract_results(tasks)
        assert len(items) == 1
        assert items[0]["keyword"] == "good"

    @patch("seedrank.research.dataforseo.httpx.Client")
    def test_fetch_keyword_overview(self, mock_client_cls: MagicMock) -> None:
        """Google Ads Search Volume endpoint returns data directly in result[]."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status_code": 20000,
            "tasks": [
                {
                    "status_code": 20000,
                    "result": [
                        {
                            "keyword": "email marketing",
                            "search_volume": 5000,
                            "keyword_difficulty": 45,
                            "cpc": 2.5,
                            "competition": 0.8,
                            "search_intent": {"main": "informational"},
                            "serp_features": ["featured_snippet"],
                        }
                    ],
                }
            ],
        }
        mock_client_cls.return_value.__enter__ = lambda self: MagicMock(
            post=lambda *a, **kw: mock_response
        )
        mock_client_cls.return_value.__exit__ = lambda *a: None

        config = DataForSeoConfig(login="user", password="pass")
        client = DataForSEOClient(config)
        results = client.fetch_keyword_overview(["email marketing"])

        assert len(results) == 1
        assert results[0]["keyword"] == "email marketing"
        assert results[0]["volume"] == 5000
        assert results[0]["kd"] == 45
        assert results[0]["intent"] == "informational"


class TestGEOClient:
    """Test GEO client analysis logic (no actual API calls)."""

    def test_analyze_brand_mentioned(self) -> None:
        client = GEOClient([], "Moonbeam")
        result = client._analyze_response(
            "Moonbeam is a recommended email marketing platform with excellent features."
        )
        assert result["mentions_brand"] == 1
        assert result["brand_sentiment"] == "positive"

    def test_analyze_brand_not_mentioned(self) -> None:
        client = GEOClient([], "Moonbeam")
        result = client._analyze_response(
            "Mailchimp is a popular email marketing platform."
        )
        assert result["mentions_brand"] == 0
        assert result["brand_sentiment"] is None

    def test_analyze_negative_sentiment(self) -> None:
        client = GEOClient([], "Moonbeam")
        result = client._analyze_response(
            "Moonbeam has issues with deliverability and problems with automation."
        )
        assert result["mentions_brand"] == 1
        assert result["brand_sentiment"] == "negative"

    def test_analyze_neutral_sentiment(self) -> None:
        client = GEOClient([], "Moonbeam")
        result = client._analyze_response(
            "Moonbeam is a tool that exists in the market."
        )
        assert result["mentions_brand"] == 1
        assert result["brand_sentiment"] == "neutral"

    def test_analyze_extracts_citations(self) -> None:
        client = GEOClient([], "Moonbeam")
        result = client._analyze_response(
            "Check out https://moonbeam.com and https://docs.moonbeam.com for more."
        )
        assert len(result["citations"]) == 2

    def test_analyze_no_citations(self) -> None:
        client = GEOClient([], "Moonbeam")
        result = client._analyze_response("No links here.")
        assert result["citations"] == []

    def test_query_requires_api_key(self) -> None:
        model = AIModelConfig(
            slug="test", model="gpt-4o",
            api_key_env="NONEXISTENT_KEY_12345", provider="openai",
        )
        client = GEOClient([model], "Moonbeam")
        with pytest.raises(ValueError, match="API key not found"):
            client.query("test query", model)

    def test_unknown_provider_raises(self) -> None:
        model = AIModelConfig(
            slug="test", model="test-model",
            api_key_env="TEST_KEY", provider="unknown_provider",
        )
        client = GEOClient([model], "Moonbeam")
        with patch.dict("os.environ", {"TEST_KEY": "fake-key"}):
            with pytest.raises(ValueError, match="Unknown provider"):
                client.query("test", model)


class TestResearchValidator:
    """Test research validation checks."""

    @pytest.fixture
    def db_conn(self, tmp_path) -> sqlite3.Connection:
        db_path = tmp_path / "data" / "seedrank.db"
        db_path.parent.mkdir()
        init_db(db_path)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def test_empty_db(self, db_conn: sqlite3.Connection) -> None:
        result = validate_research(db_conn)
        assert result.has_errors
        assert any("No keywords" in c.message for c in result.checks)

    def test_few_keywords(self, db_conn: sqlite3.Connection) -> None:
        for i in range(5):
            db_conn.execute(
                "INSERT INTO keywords (keyword, volume, kd) VALUES (?, ?, ?)",
                (f"kw{i}", 100, 30),
            )
        db_conn.commit()
        result = validate_research(db_conn)
        assert result.has_warnings
        assert any("Only 5" in c.message for c in result.checks)

    def test_healthy_db(self, db_conn: sqlite3.Connection) -> None:
        for i in range(20):
            db_conn.execute(
                "INSERT INTO keywords (keyword, volume, kd) VALUES (?, ?, ?)",
                (f"kw{i}", 100 + i * 10, 20 + i),
            )
        db_conn.execute(
            "INSERT INTO serp_snapshots (keyword, rank, url, fetched_at) "
            "VALUES ('kw0', 1, 'https://example.com', datetime('now'))"
        )
        db_conn.execute(
            "INSERT INTO competitor_keywords (competitor_slug, keyword, rank, fetched_at) "
            "VALUES ('comp1', 'kw0', 5, datetime('now'))"
        )
        db_conn.commit()
        result = validate_research(db_conn)
        assert not result.has_errors
        assert any("20 keywords" in c.message for c in result.checks)
        assert any("SERP" in c.message for c in result.checks)
        assert any("Competitor" in c.message for c in result.checks)

    def test_all_zero_kd_warns(self, db_conn: sqlite3.Connection) -> None:
        for i in range(15):
            db_conn.execute(
                "INSERT INTO keywords (keyword, volume, kd) VALUES (?, ?, ?)",
                (f"kw{i}", 100, 0),
            )
        db_conn.commit()
        result = validate_research(db_conn)
        assert result.has_warnings
        assert any("KD" in c.message and "100%" in c.message for c in result.checks)
