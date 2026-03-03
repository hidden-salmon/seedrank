"""Tests for article validation with voice and legal compliance checks."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from typer.testing import CliRunner

from seedrank.cli import app
from seedrank.data.db import get_db_path, init_db

runner = CliRunner()

EXAMPLE_CONFIG = Path(__file__).parent.parent / "examples" / "seedrank.config.yaml"


def _make_workspace_with_config(tmp_path: Path) -> Path:
    """Create a workspace with config and database."""
    ws = tmp_path / "ws"
    ws.mkdir()
    shutil.copy2(EXAMPLE_CONFIG, ws / "seedrank.config.yaml")
    (ws / "data").mkdir()
    init_db(get_db_path(ws))
    return ws


class TestValidateArticleVoice:
    """Test voice compliance checks in article validation."""

    def test_detects_banned_words(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# Great Article\n\n"
            "This tool will supercharge your email marketing and revolutionize "
            "how you leverage data for seamless campaigns.\n" * 20,
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["validate", "article", str(article), "-c", str(ws / "seedrank.config.yaml")],
        )
        assert result.exit_code == 0
        assert "banned_words" in result.output

    def test_detects_banned_cta(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# Great Article\n\n" + "Good content here. " * 200 + "\nGet Started today!\n",
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["validate", "article", str(article), "-c", str(ws / "seedrank.config.yaml")],
        )
        assert result.exit_code == 0
        assert "banned_cta" in result.output

    def test_clean_article_passes_voice(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# Email Marketing Guide\n\n"
            + "This guide covers [best practices](/blog/best-practices) for email marketing. " * 50
            + "\n[Learn more](/guides/advanced) about advanced features.\n",
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["validate", "article", str(article), "-c", str(ws / "seedrank.config.yaml")],
        )
        assert result.exit_code == 0
        assert "banned_words" not in result.output


class TestValidateArticleLegal:
    """Test legal compliance checks in article validation."""

    def test_comparison_missing_disclaimer(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# Mailchimp vs Moonbeam\n\n"
            "Mailchimp is an email marketing platform. "
            "Here is a comparison of features.\n" * 30,
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["validate", "article", str(article), "-c", str(ws / "seedrank.config.yaml")],
        )
        assert result.exit_code == 0
        assert "comparison_disclaimer" in result.output

    def test_comparison_missing_last_verified(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# Mailchimp vs Moonbeam\n\n"
            "Editorial disclaimer: We research and fact-check every claim.\n\n"
            "Mailchimp offers email marketing.\n" * 30,
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["validate", "article", str(article), "-c", str(ws / "seedrank.config.yaml")],
        )
        assert result.exit_code == 0
        assert "last_verified" in result.output

    def test_comparison_with_disclaimer_and_date_passes(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# Mailchimp vs Moonbeam\n\n"
            "Editorial disclaimer: We research and fact-check every claim.\n\n"
            "Last verified: March 1, 2026\n\n"
            "Mailchimp offers email marketing with a free tier. "
            "[Source](https://mailchimp.com/pricing)\n" * 20
            + "\n[Internal link](/blog/guide)\n",
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["validate", "article", str(article), "-c", str(ws / "seedrank.config.yaml")],
        )
        assert result.exit_code == 0
        assert "comparison_disclaimer" not in result.output
        assert "last_verified" not in result.output

    def test_banned_claim_is_error(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# Mailchimp Review\n\n"
            "Mailchimp is the worst email platform you can use.\n" * 20,
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["validate", "article", str(article), "-c", str(ws / "seedrank.config.yaml")],
        )
        assert result.exit_code == 0
        assert "banned_claim" in result.output

    def test_non_comparison_skips_legal(self, tmp_path: Path) -> None:
        """Articles without competitor mentions skip comparison checks."""
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# How to Write Great Emails\n\n"
            + "Here is a guide to writing great emails. " * 50
            + "\n[Learn more](/blog/tips)\n",
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            ["validate", "article", str(article), "-c", str(ws / "seedrank.config.yaml")],
        )
        assert result.exit_code == 0
        assert "comparison_disclaimer" not in result.output
        assert "last_verified" not in result.output


class TestValidateArticleJson:
    """Test JSON output from article validation."""

    def test_json_output(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# Test Article\n\n" + "Content here. " * 200 + "\n[Link](/blog/other)\n",
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            [
                "validate", "article", str(article),
                "-c", str(ws / "seedrank.config.yaml"),
                "--json",
            ],
        )
        assert result.exit_code == 0
        import json

        # Find the JSON block in the output (may have Rich formatting before it)
        output = result.output
        json_start = output.index("{")
        json_end = output.rindex("}") + 1
        data = json.loads(output[json_start:json_end])
        assert "word_count" in data
        assert "issues" in data
        assert "pass" in data


class TestValidateLegal:
    """Test the legal validation command."""

    def test_legal_with_empty_db(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        result = runner.invoke(
            app,
            ["validate", "legal", "-w", str(ws), "-c", str(ws / "seedrank.config.yaml")],
        )
        assert result.exit_code == 0

    def test_legal_warns_missing_email(self, tmp_path: Path) -> None:
        ws = tmp_path / "ws"
        ws.mkdir()
        (ws / "data").mkdir()
        init_db(get_db_path(ws))
        # Config without corrections email
        config_data = {"product": {"name": "Test", "domain": "test.com"}}
        (ws / "seedrank.config.yaml").write_text(
            yaml.dump(config_data), encoding="utf-8"
        )
        result = runner.invoke(
            app,
            ["validate", "legal", "-w", str(ws), "-c", str(ws / "seedrank.config.yaml")],
        )
        assert result.exit_code == 0
        assert "corrections email" in result.output.lower()


class TestValidateConfig:
    """Test config validation with legal fields."""

    def test_warns_missing_legal_fields(self, tmp_path: Path) -> None:
        config_data = {"product": {"name": "Test", "domain": "test.com"}}
        config_file = tmp_path / "seedrank.config.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")
        result = runner.invoke(app, ["validate", "config", "-c", str(config_file)])
        assert result.exit_code == 0
        assert "corrections email" in result.output.lower()
