"""Tests for legal tier validation patterns (_check_legal_tiers)."""

from __future__ import annotations

import pytest

from seedrank.cli.validate import _check_legal_tiers
from seedrank.config.schema import Competitor, ProductConfig, PseoConfig


@pytest.fixture
def cfg() -> PseoConfig:
    """Minimal PseoConfig with a product name and one competitor."""
    return PseoConfig(
        product=ProductConfig(
            name="TestProduct",
            domain="testproduct.com",
        ),
        competitors=[
            Competitor(
                slug="rival",
                name="RivalApp",
                domain="rivalapp.com",
                tier=1,
            ),
        ],
    )


def _run_check(content: str, cfg: PseoConfig) -> list[dict]:
    """Helper to run _check_legal_tiers and return the issues list."""
    issues: list[dict] = []
    _check_legal_tiers(content, content.lower(), cfg, issues)
    return issues


def _issues_with_check(issues: list[dict], check_name: str) -> list[dict]:
    """Filter issues by check name."""
    return [i for i in issues if i["check"] == check_name]


# ---------------------------------------------------------------------------
# RED tier: Multiplier claims
# ---------------------------------------------------------------------------
class TestRedMultiplierClaims:
    def test_multiplier_cheaper_detected(self, cfg: PseoConfig) -> None:
        issues = _run_check("Our tool is 3x cheaper than alternatives.", cfg)
        matched = _issues_with_check(issues, "legal_red_multiplier")
        assert len(matched) >= 1
        assert matched[0]["level"] == "error"
        assert "3x cheaper" in matched[0]["message"]

    def test_multiplier_faster_detected(self, cfg: PseoConfig) -> None:
        issues = _run_check("We are 10x faster at processing data.", cfg)
        matched = _issues_with_check(issues, "legal_red_multiplier")
        assert len(matched) >= 1
        assert "10x faster" in matched[0]["message"]

    def test_multiplier_better_detected(self, cfg: PseoConfig) -> None:
        issues = _run_check("This is 5x better for your workflow.", cfg)
        matched = _issues_with_check(issues, "legal_red_multiplier")
        assert len(matched) >= 1

    def test_no_multiplier_clean(self, cfg: PseoConfig) -> None:
        issues = _run_check("Our tool processes data efficiently.", cfg)
        matched = _issues_with_check(issues, "legal_red_multiplier")
        assert len(matched) == 0


# ---------------------------------------------------------------------------
# RED tier: Disparaging words near competitor names
# ---------------------------------------------------------------------------
class TestRedDisparaging:
    def test_disparaging_near_competitor_flagged(self, cfg: PseoConfig) -> None:
        content = "RivalApp has a limited feature set compared to us."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_disparaging")
        assert len(matched) >= 1
        assert matched[0]["level"] == "error"
        assert "limited" in matched[0]["message"]

    def test_disparaging_far_from_competitor_not_flagged(self, cfg: PseoConfig) -> None:
        # Place the disparaging word very far from the competitor name
        # (> 100 chars away in both directions)
        filler = "x " * 80  # 160 chars of filler
        content = f"RivalApp is a great product. {filler}The old system was limited."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_disparaging")
        assert len(matched) == 0

    def test_multiple_disparaging_words(self, cfg: PseoConfig) -> None:
        content = "RivalApp is outdated and clunky."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_disparaging")
        # Should flag at least one disparaging word near competitor
        assert len(matched) >= 1

    def test_disparaging_without_competitor_not_flagged(self, cfg: PseoConfig) -> None:
        content = "The old system was outdated and clunky."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_disparaging")
        assert len(matched) == 0


# ---------------------------------------------------------------------------
# RED tier: Unhedged exclusivity
# ---------------------------------------------------------------------------
class TestRedExclusivity:
    def test_unhedged_exclusivity_detected(self, cfg: PseoConfig) -> None:
        content = "We are the only platform that offers real-time syncing."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_exclusivity")
        assert len(matched) >= 1
        assert matched[0]["level"] == "error"

    def test_hedged_exclusivity_passes(self, cfg: PseoConfig) -> None:
        content = "To our knowledge, the only platform that offers real-time syncing."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_exclusivity")
        assert len(matched) == 0

    def test_hedged_with_as_of_passes(self, cfg: PseoConfig) -> None:
        content = "As of March 2025, the only tool that supports this feature."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_exclusivity")
        assert len(matched) == 0

    def test_other_entity_types(self, cfg: PseoConfig) -> None:
        content = "The only tool that handles real-time data."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_exclusivity")
        assert len(matched) >= 1


# ---------------------------------------------------------------------------
# RED tier: Performance claims without benchmarks
# ---------------------------------------------------------------------------
class TestRedPerformance:
    def test_faster_than_without_benchmark_flagged(self, cfg: PseoConfig) -> None:
        content = "Our engine is faster than any competitor on the market."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_performance")
        assert len(matched) >= 1
        assert matched[0]["level"] == "error"

    def test_faster_than_with_benchmark_passes(self, cfg: PseoConfig) -> None:
        content = "Our engine is faster than competitors, averaging 120ms in benchmark tests."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_performance")
        assert len(matched) == 0

    def test_more_efficient_than_without_benchmark(self, cfg: PseoConfig) -> None:
        content = "Our solution is more efficient than the old approach."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_performance")
        assert len(matched) >= 1

    def test_slower_than_with_percentage(self, cfg: PseoConfig) -> None:
        content = "The legacy system is 30% slower than our new version."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_red_performance")
        assert len(matched) == 0  # "%" is recognized as benchmark data


# ---------------------------------------------------------------------------
# YELLOW tier: Unattributed statistics
# ---------------------------------------------------------------------------
class TestYellowUnattributedStats:
    def test_unattributed_user_count_flagged(self, cfg: PseoConfig) -> None:
        content = "Join our community of 100,000 users worldwide."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_yellow_unattributed_stat")
        assert len(matched) >= 1
        assert matched[0]["level"] == "warning"

    def test_attributed_stat_passes(self, cfg: PseoConfig) -> None:
        content = "According to reports, the platform has 100,000 users."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_yellow_unattributed_stat")
        assert len(matched) == 0

    def test_stat_with_link_passes(self, cfg: PseoConfig) -> None:
        content = "The platform has 50,000 developers [source](https://example.com/stats)."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_yellow_unattributed_stat")
        assert len(matched) == 0

    def test_stat_with_source_keyword_passes(self, cfg: PseoConfig) -> None:
        content = "The platform has 50,000 developers (source: company blog)."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_yellow_unattributed_stat")
        assert len(matched) == 0


# ---------------------------------------------------------------------------
# YELLOW tier: Unscoped "best for"
# ---------------------------------------------------------------------------
class TestYellowUnscopedBest:
    def test_unscoped_best_for_flagged(self, cfg: PseoConfig) -> None:
        content = "This is the best for startups looking to scale."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_yellow_unscoped_best")
        assert len(matched) >= 1
        assert matched[0]["level"] == "warning"

    def test_best_alternative_flagged(self, cfg: PseoConfig) -> None:
        content = "The best alternative to legacy tools is here."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_yellow_unscoped_best")
        assert len(matched) >= 1

    def test_no_best_claim_passes(self, cfg: PseoConfig) -> None:
        content = "A strong option for startups looking to scale."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_yellow_unscoped_best")
        assert len(matched) == 0


# ---------------------------------------------------------------------------
# YELLOW tier: Undated pricing
# ---------------------------------------------------------------------------
class TestYellowUndatedPricing:
    def test_undated_pricing_flagged(self, cfg: PseoConfig) -> None:
        content = "Our starter plan is $29 per month."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_yellow_undated_pricing")
        assert len(matched) >= 1
        assert matched[0]["level"] == "warning"

    def test_dated_pricing_passes(self, cfg: PseoConfig) -> None:
        content = "As of March 2025, our starter plan is $29 per month."
        issues = _run_check(content, cfg)
        matched = _issues_with_check(issues, "legal_yellow_undated_pricing")
        assert len(matched) == 0


# ---------------------------------------------------------------------------
# Clean content
# ---------------------------------------------------------------------------
class TestCleanContent:
    def test_clean_content_no_issues(self, cfg: PseoConfig) -> None:
        content = (
            "Our product provides a reliable data processing pipeline. "
            "Teams can integrate it with their existing infrastructure. "
            "The documentation covers all major use cases."
        )
        issues = _run_check(content, cfg)
        assert len(issues) == 0
