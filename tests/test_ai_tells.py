"""Tests for AI-tell detection in article validation."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from seedrank.cli import app
from seedrank.cli.validate import _check_ai_tells
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


def _run_check(text: str) -> list[dict]:
    """Helper: run _check_ai_tells on text, return issues."""
    issues: list[dict] = []
    _check_ai_tells(text, text.lower(), issues)
    return issues


def _issue_checks(issues: list[dict]) -> set[str]:
    """Extract the set of check names from issues."""
    return {i["check"] for i in issues}


class TestCrutchPhrases:
    """AI crutch phrase detection."""

    def test_detects_worth_noting(self) -> None:
        text = "It's worth noting that deploys take 30 seconds."
        issues = _run_check(text)
        assert "ai_tell_crutch_phrases" in _issue_checks(issues)

    def test_detects_lets_dive_in(self) -> None:
        text = "Now that we have the basics, let's dive in to the comparison."
        issues = _run_check(text)
        assert "ai_tell_crutch_phrases" in _issue_checks(issues)

    def test_detects_when_it_comes_to(self) -> None:
        text = "When it comes to pricing, Railway is more expensive."
        issues = _run_check(text)
        assert "ai_tell_crutch_phrases" in _issue_checks(issues)

    def test_clean_text_passes(self) -> None:
        text = "Deploys take 30 seconds. Railway costs $5/month."
        issues = _run_check(text)
        assert "ai_tell_crutch_phrases" not in _issue_checks(issues)

    def test_counts_multiple_instances(self) -> None:
        text = (
            "It's worth noting that X. It's worth noting that Y. "
            "When it comes to Z, things change."
        )
        issues = _run_check(text)
        crutch_issues = [i for i in issues if i["check"] == "ai_tell_crutch_phrases"]
        assert len(crutch_issues) == 1
        assert "2x" in crutch_issues[0]["message"]  # worth noting appears 2x


class TestSelfAnnouncingHonesty:
    """Self-announcing honesty detection."""

    def test_detects_verified_pricing(self) -> None:
        text = "We provide verified pricing data for all competitors."
        issues = _run_check(text)
        assert "ai_tell_self_announcing_honesty" in _issue_checks(issues)

    def test_detects_honest_trade_offs(self) -> None:
        text = "Here are the honest trade-offs between the two platforms."
        issues = _run_check(text)
        assert "ai_tell_self_announcing_honesty" in _issue_checks(issues)

    def test_clean_text_passes(self) -> None:
        text = "Pricing data as of March 2026. Trade-offs exist between latency and cost."
        issues = _run_check(text)
        assert "ai_tell_self_announcing_honesty" not in _issue_checks(issues)


class TestMetaCommentary:
    """Meta-commentary detection."""

    def test_detects_this_guide_breaks_down(self) -> None:
        text = "This guide breaks down the differences between Railway and Render."
        issues = _run_check(text)
        assert "ai_tell_meta_commentary" in _issue_checks(issues)

    def test_detects_as_mentioned_earlier(self) -> None:
        text = "As mentioned earlier, the pricing model differs significantly."
        issues = _run_check(text)
        assert "ai_tell_meta_commentary" in _issue_checks(issues)

    def test_detects_now_lets_move_on(self) -> None:
        text = "Now let's move on to the deployment comparison."
        issues = _run_check(text)
        assert "ai_tell_meta_commentary" in _issue_checks(issues)

    def test_clean_text_passes(self) -> None:
        text = "Railway deploys in 30 seconds. Render takes 45 seconds."
        issues = _run_check(text)
        assert "ai_tell_meta_commentary" not in _issue_checks(issues)


class TestCountingBeforeListing:
    """Counting-before-listing detection."""

    def test_detects_three_things_matter(self) -> None:
        text = "Three things matter when choosing a platform: speed, cost, and reliability."
        issues = _run_check(text)
        assert "ai_tell_counting_before_listing" in _issue_checks(issues)

    def test_detects_five_reasons_that(self) -> None:
        text = "Five reasons that make this platform stand out from alternatives."
        issues = _run_check(text)
        assert "ai_tell_counting_before_listing" in _issue_checks(issues)

    def test_clean_text_passes(self) -> None:
        text = "Speed, cost, and reliability matter when choosing a platform."
        issues = _run_check(text)
        assert "ai_tell_counting_before_listing" not in _issue_checks(issues)


class TestGratuitousCompliments:
    """Gratuitous competitor compliment detection."""

    def test_detects_impressive_project(self) -> None:
        text = "Railway is an impressive platform, but it lacks BYOC support."
        issues = _run_check(text)
        assert "ai_tell_gratuitous_compliments" in _issue_checks(issues)

    def test_detects_fantastic_option(self) -> None:
        text = "Render is a fantastic option for static sites."
        issues = _run_check(text)
        assert "ai_tell_gratuitous_compliments" in _issue_checks(issues)

    def test_clean_text_passes(self) -> None:
        text = "Railway has a generous free tier. Render supports static sites."
        issues = _run_check(text)
        assert "ai_tell_gratuitous_compliments" not in _issue_checks(issues)


class TestDiplomaticHedging:
    """Diplomatic hedging detection (requires 2+ hedges to trigger)."""

    def test_single_hedge_is_ok(self) -> None:
        text = "Neither is universally better — it depends on your stack."
        issues = _run_check(text)
        assert "ai_tell_diplomatic_hedging" not in _issue_checks(issues)

    def test_multiple_hedges_flagged(self) -> None:
        text = (
            "Neither is universally better. Both have their pros and cons. "
            "The best choice depends on your requirements."
        )
        issues = _run_check(text)
        assert "ai_tell_diplomatic_hedging" in _issue_checks(issues)

    def test_clean_text_passes(self) -> None:
        text = "For multi-region, choose Fly.io. For lower cost, choose Railway."
        issues = _run_check(text)
        assert "ai_tell_diplomatic_hedging" not in _issue_checks(issues)


class TestExcessiveDateStamps:
    """Excessive date stamp detection."""

    def test_few_date_stamps_ok(self) -> None:
        text = (
            "Railway costs $5/month (as of March 2026). "
            "Render starts at $7/month (as of March 2026). "
            "Fly.io charges $1.94/month (as of March 2026)."
        )
        issues = _run_check(text)
        assert "ai_tell_excessive_date_stamps" not in _issue_checks(issues)

    def test_excessive_date_stamps_flagged(self) -> None:
        claims = [
            f"Feature {i} costs ${i}/month (as of March 2026)."
            for i in range(1, 9)
        ]
        text = " ".join(claims)
        issues = _run_check(text)
        assert "ai_tell_excessive_date_stamps" in _issue_checks(issues)

    def test_threshold_at_seven(self) -> None:
        claims = [
            f"Item {i} (as of March 2026)."
            for i in range(1, 7)  # exactly 6
        ]
        text = " ".join(claims)
        issues = _run_check(text)
        assert "ai_tell_excessive_date_stamps" not in _issue_checks(issues)


class TestTricolons:
    """Tricolon detection — three parallel short sentences."""

    def test_detects_tricolon_same_ending(self) -> None:
        text = "Speed matters. Reliability matters. Cost matters."
        issues = _run_check(text)
        assert "ai_tell_tricolons" in _issue_checks(issues)

    def test_detects_tricolon_same_start(self) -> None:
        text = "It handles routing. It manages state. It scales containers."
        issues = _run_check(text)
        assert "ai_tell_tricolons" in _issue_checks(issues)

    def test_varied_sentences_pass(self) -> None:
        text = (
            "Speed matters for user experience. "
            "You also need to think about long-term reliability and uptime guarantees. "
            "Cost is a factor."
        )
        issues = _run_check(text)
        assert "ai_tell_tricolons" not in _issue_checks(issues)


class TestIntegrationWithCLI:
    """Test that AI-tell checks appear in validate article output."""

    def test_ai_tells_in_json_output(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# Platform Comparison\n\n"
            "It's worth noting that this platform stands out. "
            "When it comes to pricing, let's dive in. "
            "This guide breaks down the key differences. "
            "We provide verified pricing and honest trade-offs. "
            "Neither is universally better. Both have their pros and cons. "
            "The best choice depends on your requirements.\n"
            + "More content here. " * 50
            + "\n[Link](/blog/other)\n",
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
        output = result.output
        try:
            json_start = output.index("{")
            json_end = output.rindex("}") + 1
        except ValueError:
            raise AssertionError(f"No JSON object found in output:\n{output}")
        data = json.loads(output[json_start:json_end])

        ai_tell_checks = {
            i["check"] for i in data["issues"] if i["check"].startswith("ai_tell_")
        }
        assert "ai_tell_crutch_phrases" in ai_tell_checks
        assert "ai_tell_self_announcing_honesty" in ai_tell_checks
        assert "ai_tell_meta_commentary" in ai_tell_checks
        assert "ai_tell_diplomatic_hedging" in ai_tell_checks

    def test_clean_article_no_ai_tells(self, tmp_path: Path) -> None:
        ws = _make_workspace_with_config(tmp_path)
        article = ws / "test.md"
        article.write_text(
            "# Platform Comparison\n\n"
            "Railway costs $5/month (as of March 2026). Render starts at $7/month.\n\n"
            "For multi-region deployments, Fly.io is the better choice. "
            "For simpler apps that only need one region, Railway is faster to set up "
            "and costs less.\n\n"
            "The deployment process takes about 30 seconds on average for a typical "
            "Node.js application with standard dependencies. Docker builds may take "
            "longer depending on image size and layer caching.\n\n"
            "Pricing scales linearly with resource usage. A small team running three "
            "services would pay roughly $15/month on Railway versus $21/month on Render, "
            "though the exact cost depends on memory and CPU allocation.\n\n"
            "Database support differs between platforms. Railway bundles PostgreSQL and "
            "Redis as first-class add-ons with automatic backups. Render requires a "
            "separate database plan that starts at $7/month for a managed PostgreSQL "
            "instance with 1GB storage.\n\n"
            + "\n[Internal link](/blog/guide)\n",
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
        output = result.output
        try:
            json_start = output.index("{")
            json_end = output.rindex("}") + 1
        except ValueError:
            raise AssertionError(f"No JSON object found in output:\n{output}")
        data = json.loads(output[json_start:json_end])

        ai_tell_checks = [
            i for i in data["issues"] if i["check"].startswith("ai_tell_")
        ]
        assert len(ai_tell_checks) == 0
