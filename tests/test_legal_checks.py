"""Tests for the legal_checks module — new checks, dataclasses, and orchestrator."""

from __future__ import annotations

import pytest

from seedrank.cli.legal_checks import (
    LegalFinding,
    LegalFramework,
    LegalReport,
    RiskLevel,
    check_cherry_picked_comparison,
    check_disparaging_words,
    check_eu_denigration,
    check_exclusivity_claims,
    check_implied_deficiency,
    check_missing_methodology,
    check_multiplier_claims,
    check_opinion_as_fact,
    check_outdated_claims,
    check_performance_claims,
    check_pricing_specificity,
    check_screenshot_fair_use,
    check_trademark_in_headings,
    check_trademark_misuse,
    check_unattributed_stats,
    check_undated_pricing,
    check_unscoped_best,
    compute_checklist_score,
    run_legal_checks,
)
from seedrank.config.schema import Competitor, ProductConfig, PseoConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cfg() -> PseoConfig:
    return PseoConfig(
        product=ProductConfig(name="TestProduct", domain="testproduct.com"),
        competitors=[
            Competitor(slug="rival", name="RivalApp", domain="rivalapp.com", tier=1),
        ],
    )


@pytest.fixture
def names() -> tuple[list[str], list[str]]:
    return (["RivalApp"], ["rivalapp"])


# ===========================================================================
# Dataclass tests
# ===========================================================================


class TestLegalFinding:
    def test_to_issue(self) -> None:
        f = LegalFinding(
            level=RiskLevel.RED,
            check="test_check",
            message="test message",
        )
        issue = f.to_issue()
        assert issue == {"level": "error", "check": "test_check", "message": "test message"}

    def test_framework_default(self) -> None:
        f = LegalFinding(level=RiskLevel.YELLOW, check="c", message="m")
        assert f.framework == LegalFramework.GENERAL


class TestLegalReport:
    def test_overall_risk_red(self) -> None:
        report = LegalReport(findings=[
            LegalFinding(level=RiskLevel.RED, check="a", message="m"),
            LegalFinding(level=RiskLevel.YELLOW, check="b", message="m"),
        ])
        assert report.overall_risk == RiskLevel.RED

    def test_overall_risk_yellow(self) -> None:
        report = LegalReport(findings=[
            LegalFinding(level=RiskLevel.YELLOW, check="a", message="m"),
        ])
        assert report.overall_risk == RiskLevel.YELLOW

    def test_overall_risk_green(self) -> None:
        report = LegalReport(findings=[])
        assert report.overall_risk == RiskLevel.GREEN

    def test_to_issues_list(self) -> None:
        report = LegalReport(findings=[
            LegalFinding(level=RiskLevel.RED, check="a", message="m1"),
            LegalFinding(level=RiskLevel.YELLOW, check="b", message="m2"),
        ])
        issues = report.to_issues_list()
        assert len(issues) == 2
        assert issues[0]["level"] == "error"
        assert issues[1]["level"] == "warning"

    def test_empty_report(self) -> None:
        report = LegalReport()
        assert report.checklist_score is None
        assert report.checklist_total == 12
        assert report.to_issues_list() == []


# ===========================================================================
# Trademark misuse
# ===========================================================================


class TestTrademarkMisuse:
    def test_killer_detected(self, names: tuple) -> None:
        findings = check_trademark_misuse(
            "The RivalApp killer is here",
            "the rivalapp killer is here",
            *names,
        )
        assert any(f.check == "legal_red_trademark_misuse" for f in findings)
        assert any("killer" in f.message for f in findings)

    def test_like_detected(self, names: tuple) -> None:
        findings = check_trademark_misuse(
            "Our rivalapp-like tool", "our rivalapp-like tool", *names,
        )
        assert any("like" in f.message.lower() for f in findings)

    def test_better_x_detected(self, names: tuple) -> None:
        findings = check_trademark_misuse(
            "A better RivalApp", "a better rivalapp", *names,
        )
        assert any("better" in f.message.lower() for f in findings)

    def test_better_than_not_flagged(self, names: tuple) -> None:
        # "better than RivalApp" should NOT trigger "better X" check
        findings = check_trademark_misuse(
            "better than RivalApp", "better than rivalapp", *names,
        )
        tm_findings = [f for f in findings if "better" in f.message.lower() and "implies replacement" in f.message]
        assert len(tm_findings) == 0

    def test_excessive_mentions(self, names: tuple) -> None:
        content = "RivalApp " * 20
        findings = check_trademark_misuse(
            content, content.lower(), *names, max_mentions=15,
        )
        assert any(f.check == "legal_yellow_excessive_mentions" for f in findings)

    def test_normal_mentions_pass(self, names: tuple) -> None:
        content = "RivalApp " * 5
        findings = check_trademark_misuse(
            content, content.lower(), *names, max_mentions=15,
        )
        assert not any(f.check == "legal_yellow_excessive_mentions" for f in findings)

    def test_clean_content(self, names: tuple) -> None:
        findings = check_trademark_misuse(
            "RivalApp is a product.", "rivalapp is a product.", *names,
        )
        assert len(findings) == 0


# ===========================================================================
# Implied deficiency
# ===========================================================================


class TestImpliedDeficiency:
    def test_no_hidden_fees_near_competitor(self) -> None:
        content = "unlike rivalapp, we have no hidden fees"
        findings = check_implied_deficiency(content, ["rivalapp"])
        assert any(f.check == "legal_yellow_implied_deficiency" for f in findings)

    def test_no_hidden_fees_far_from_competitor(self) -> None:
        filler = "x " * 200
        content = f"rivalapp is great. {filler} no hidden fees here."
        findings = check_implied_deficiency(content, ["rivalapp"])
        assert not any(f.check == "legal_yellow_implied_deficiency" for f in findings)

    def test_actually_works_detected(self) -> None:
        content = "our tool actually works, unlike rivalapp"
        findings = check_implied_deficiency(content, ["rivalapp"])
        assert len(findings) >= 1

    def test_clean_content(self) -> None:
        content = "our tool is great and rivalapp is also a competitor"
        findings = check_implied_deficiency(content, ["rivalapp"])
        assert len(findings) == 0

    def test_without_the_hassle(self) -> None:
        content = "switch from rivalapp without the hassle"
        findings = check_implied_deficiency(content, ["rivalapp"])
        assert len(findings) >= 1

    def test_no_competitor_no_flag(self) -> None:
        content = "we have no hidden fees"
        findings = check_implied_deficiency(content, ["rivalapp"])
        assert len(findings) == 0


# ===========================================================================
# Opinion as fact
# ===========================================================================


class TestOpinionAsFact:
    def test_is_broken_near_competitor(self) -> None:
        content = "rivalapp is broken and unreliable"
        findings = check_opinion_as_fact(content, ["rivalapp"])
        assert any(f.check == "legal_yellow_opinion_as_fact" for f in findings)

    def test_hedged_opinion_passes(self) -> None:
        content = "in our testing, rivalapp is broken occasionally"
        findings = check_opinion_as_fact(content, ["rivalapp"])
        assert len(findings) == 0

    def test_is_buggy_detected(self) -> None:
        content = "rivalapp is buggy and crashes"
        findings = check_opinion_as_fact(content, ["rivalapp"])
        assert len(findings) >= 1

    def test_no_competitor_clean(self) -> None:
        content = "this old system is broken"
        findings = check_opinion_as_fact(content, ["rivalapp"])
        assert len(findings) == 0

    def test_support_is_slow(self) -> None:
        content = "rivalapp's support is slow and unresponsive"
        findings = check_opinion_as_fact(content, ["rivalapp"])
        assert len(findings) >= 1

    def test_we_found_hedge(self) -> None:
        content = "we found that rivalapp is buggy in edge cases"
        findings = check_opinion_as_fact(content, ["rivalapp"])
        assert len(findings) == 0


# ===========================================================================
# Outdated claims
# ===========================================================================


class TestOutdatedClaims:
    def test_doesnt_support_near_competitor(self) -> None:
        content = "rivalapp doesn't support offline mode"
        findings = check_outdated_claims(content, ["rivalapp"])
        assert any(f.check == "legal_yellow_outdated_claim" for f in findings)

    def test_with_as_of_passes(self) -> None:
        content = "as of march 2025, rivalapp doesn't support offline mode"
        findings = check_outdated_claims(content, ["rivalapp"])
        assert len(findings) == 0

    def test_lacks_feature(self) -> None:
        content = "rivalapp lacks support for dark mode"
        findings = check_outdated_claims(content, ["rivalapp"])
        assert len(findings) >= 1

    def test_no_competitor_clean(self) -> None:
        content = "the old system doesn't support this feature"
        findings = check_outdated_claims(content, ["rivalapp"])
        assert len(findings) == 0

    def test_last_verified_hedge(self) -> None:
        content = "last verified in february, rivalapp doesn't support api access"
        findings = check_outdated_claims(content, ["rivalapp"])
        assert len(findings) == 0

    def test_does_not_offer(self) -> None:
        content = "rivalapp does not offer enterprise plans"
        findings = check_outdated_claims(content, ["rivalapp"])
        assert len(findings) >= 1

    def test_missing_detected(self) -> None:
        content = "rivalapp is missing key integration with third-party tools"
        findings = check_outdated_claims(content, ["rivalapp"])
        assert len(findings) >= 1


# ===========================================================================
# Cherry-picked comparison
# ===========================================================================


class TestCherryPickedComparison:
    def test_too_many_rows(self) -> None:
        header = "| Feature | Us | Them |"
        sep = "|---|---|---|"
        rows = "\n".join(f"| Feature {i} | ✅ | ❌ |" for i in range(10))
        content = f"{header}\n{sep}\n{rows}"
        findings = check_cherry_picked_comparison(content)
        assert any(f.check in ("legal_yellow_cherry_picked_onesided", "legal_yellow_cherry_picked_toomany") for f in findings)

    def test_balanced_table_passes(self) -> None:
        content = (
            "| Feature | Us | Them |\n"
            "|---|---|---|\n"
            "| Speed | ✅ | ❌ |\n"
            "| Price | ❌ | ✅ |\n"
            "| Support | ✅ | ✅ |\n"
            "| API | ❌ | ✅ |\n"
        )
        findings = check_cherry_picked_comparison(content)
        assert len(findings) == 0

    def test_one_sided_table_flagged(self) -> None:
        content = (
            "| Feature | Us | Them |\n"
            "|---|---|---|\n"
            "| Speed | ✅ | ❌ |\n"
            "| Price | ✅ | ❌ |\n"
            "| Support | ✅ | ❌ |\n"
            "| API | ✅ | ❌ |\n"
            "| Docs | ✅ | ❌ |\n"
        )
        findings = check_cherry_picked_comparison(content)
        assert any(f.check in ("legal_yellow_cherry_picked_onesided", "legal_yellow_cherry_picked_toomany") for f in findings)

    def test_no_table_clean(self) -> None:
        content = "Just a regular article without tables."
        findings = check_cherry_picked_comparison(content)
        assert len(findings) == 0

    def test_small_table_passes(self) -> None:
        content = (
            "| Feature | Us |\n"
            "|---|---|\n"
            "| Speed | ✅ |\n"
        )
        findings = check_cherry_picked_comparison(content)
        assert len(findings) == 0


# ===========================================================================
# Pricing specificity
# ===========================================================================


class TestPricingSpecificity:
    def test_missing_tier_and_billing(self) -> None:
        content = "RivalApp costs $49"
        findings = check_pricing_specificity(content, content.lower(), ["rivalapp"])
        assert any(f.check == "legal_yellow_pricing_specificity" for f in findings)

    def test_with_tier_and_billing_passes(self) -> None:
        content = "RivalApp Pro plan costs $49/mo"
        findings = check_pricing_specificity(content, content.lower(), ["rivalapp"])
        assert len(findings) == 0

    def test_with_billing_no_tier(self) -> None:
        content = "RivalApp costs $49/mo"
        findings = check_pricing_specificity(content, content.lower(), ["rivalapp"])
        assert any(f.check == "legal_yellow_pricing_specificity" for f in findings)
        # Should mention missing plan tier
        assert any("plan tier" in f.message for f in findings)

    def test_no_competitor_nearby_clean(self) -> None:
        filler = "x " * 200
        content = f"RivalApp is great. {filler} Our product is $49/mo."
        findings = check_pricing_specificity(content, content.lower(), ["rivalapp"])
        assert len(findings) == 0

    def test_own_pricing_not_flagged(self) -> None:
        content = "Our starter plan is $29/mo."
        findings = check_pricing_specificity(content, content.lower(), ["rivalapp"])
        assert len(findings) == 0


# ===========================================================================
# EU denigration
# ===========================================================================


class TestEUDenigration:
    def test_inferior_near_competitor(self) -> None:
        content = "rivalapp is inferior to our solution"
        findings = check_eu_denigration(content, ["rivalapp"])
        assert any(f.check == "legal_yellow_eu_denigration" for f in findings)

    def test_overpriced_detected(self) -> None:
        content = "rivalapp is overpriced for what it offers"
        findings = check_eu_denigration(content, ["rivalapp"])
        assert len(findings) >= 1

    def test_mediocre_detected(self) -> None:
        content = "rivalapp offers a mediocre experience"
        findings = check_eu_denigration(content, ["rivalapp"])
        assert len(findings) >= 1

    def test_no_competitor_clean(self) -> None:
        content = "the old system was inferior"
        findings = check_eu_denigration(content, ["rivalapp"])
        assert len(findings) == 0

    def test_far_from_competitor(self) -> None:
        filler = "x " * 200
        content = f"rivalapp is good. {filler} that other thing is inferior."
        findings = check_eu_denigration(content, ["rivalapp"])
        assert len(findings) == 0


# ===========================================================================
# Missing methodology
# ===========================================================================


class TestMissingMethodology:
    def test_comparison_with_table_no_methodology(self) -> None:
        content = (
            "# RivalApp vs TestProduct\n"
            "| Feature | Us | Them |\n"
            "|---|---|---|\n"
            "| Speed | ✅ | ❌ |\n"
        )
        findings = check_missing_methodology(content, content.lower())
        assert any(f.check == "legal_yellow_missing_methodology" for f in findings)

    def test_comparison_with_methodology_passes(self) -> None:
        content = (
            "# RivalApp vs TestProduct\n"
            "## How We Evaluated\n"
            "We tested each product...\n"
            "| Feature | Us | Them |\n"
            "|---|---|---|\n"
            "| Speed | ✅ | ❌ |\n"
        )
        findings = check_missing_methodology(content, content.lower())
        assert len(findings) == 0

    def test_non_comparison_clean(self) -> None:
        content = (
            "# Our Product Guide\n"
            "| Feature | Status |\n"
            "|---|---|\n"
            "| Speed | ✅ |\n"
        )
        findings = check_missing_methodology(content, content.lower())
        assert len(findings) == 0

    def test_alternative_keyword(self) -> None:
        content = (
            "# Best RivalApp Alternative\n"
            "| Feature | Us | Them |\n"
            "|---|---|---|\n"
            "| Speed | ✅ | ❌ |\n"
        )
        findings = check_missing_methodology(content, content.lower())
        assert len(findings) >= 1


# ===========================================================================
# Trademark in headings
# ===========================================================================


class TestTrademarkInHeadings:
    def test_negative_heading_detected(self) -> None:
        content = "# Why RivalApp Falls Short\nSome text here."
        findings = check_trademark_in_headings(content, ["rivalapp"])
        assert any(f.check == "legal_yellow_trademark_heading" for f in findings)

    def test_neutral_heading_passes(self) -> None:
        content = "# RivalApp vs TestProduct\nA fair comparison."
        findings = check_trademark_in_headings(content, ["rivalapp"])
        assert len(findings) == 0

    def test_h2_negative(self) -> None:
        content = "## Problems With RivalApp\nDetails here."
        findings = check_trademark_in_headings(content, ["rivalapp"])
        assert len(findings) >= 1

    def test_h3_not_checked(self) -> None:
        content = "### Why RivalApp Fails\nDetails here."
        findings = check_trademark_in_headings(content, ["rivalapp"])
        assert len(findings) == 0  # Only H1/H2 checked

    def test_no_competitor_clean(self) -> None:
        content = "# Why Legacy Systems Fall Short\nSome text."
        findings = check_trademark_in_headings(content, ["rivalapp"])
        assert len(findings) == 0


# ===========================================================================
# Screenshot fair use
# ===========================================================================


class TestScreenshotFairUse:
    def test_image_near_competitor(self) -> None:
        content = "Here's a screenshot of RivalApp ![screenshot](/img/rival.png) showing the UI."
        findings = check_screenshot_fair_use(content, content.lower(), ["rivalapp"])
        assert any(f.check == "legal_yellow_screenshot_fair_use" for f in findings)

    def test_image_far_from_competitor(self) -> None:
        filler = "x " * 200
        content = f"RivalApp is great. {filler} ![our product](/img/us.png)"
        findings = check_screenshot_fair_use(content, content.lower(), ["rivalapp"])
        assert len(findings) == 0

    def test_no_images_clean(self) -> None:
        content = "RivalApp is a competitor."
        findings = check_screenshot_fair_use(content, content.lower(), ["rivalapp"])
        assert len(findings) == 0


# ===========================================================================
# Checklist scorer
# ===========================================================================


class TestChecklistScorer:
    def test_perfect_score(self) -> None:
        content = "last verified: march 1, 2025. as of march 2025, things look good."
        score, failed = compute_checklist_score([], content)
        assert score == 12
        assert len(failed) == 0

    def test_low_score(self) -> None:
        findings = [
            LegalFinding(level=RiskLevel.YELLOW, check="legal_yellow_outdated_claim", message="m"),
            LegalFinding(level=RiskLevel.YELLOW, check="legal_yellow_undated_pricing", message="m"),
            LegalFinding(level=RiskLevel.YELLOW, check="legal_yellow_opinion_as_fact", message="m"),
            LegalFinding(level=RiskLevel.YELLOW, check="legal_yellow_cherry_picked_onesided", message="m"),
            LegalFinding(level=RiskLevel.YELLOW, check="legal_yellow_cherry_picked_toomany", message="m"),
            LegalFinding(level=RiskLevel.RED, check="legal_red_trademark_misuse", message="m",
                         statement="rivalapp-like"),
            LegalFinding(level=RiskLevel.YELLOW, check="legal_yellow_implied_deficiency", message="m"),
            LegalFinding(level=RiskLevel.YELLOW, check="legal_yellow_unattributed_stat", message="m"),
            LegalFinding(level=RiskLevel.YELLOW, check="legal_yellow_unscoped_best", message="m"),
        ]
        score, failed = compute_checklist_score(findings, "no dates here")
        assert score <= 3
        assert len(failed) >= 9

    def test_partial_score(self) -> None:
        findings = [
            LegalFinding(level=RiskLevel.YELLOW, check="legal_yellow_outdated_claim", message="m"),
        ]
        content = "last verified: march 1, 2025. as of march 2025."
        score, failed = compute_checklist_score(findings, content)
        assert 8 <= score <= 11
        assert len(failed) >= 1

    def test_last_verified_detection(self) -> None:
        content = "last verified: 2025-03-01"
        _, failed = compute_checklist_score([], content)
        # Item 11 should pass
        assert not any("last verified" in f.lower() for f in failed)

    def test_no_last_verified(self) -> None:
        _, failed = compute_checklist_score([], "just some content")
        assert any("last verified" in f.lower() or "last updated" in f.lower() for f in failed)


# ===========================================================================
# Orchestrator integration
# ===========================================================================


class TestRunLegalChecks:
    def test_clean_content(self, cfg: PseoConfig) -> None:
        content = (
            "Our product provides reliable data processing. "
            "Teams can integrate it with their existing infrastructure."
        )
        report = run_legal_checks(content, cfg)
        assert report.overall_risk == RiskLevel.GREEN
        # No competitors mentioned, so checklist is not scored
        assert report.checklist_score is None
        assert report.checklist_total == 12

    def test_problematic_content(self, cfg: PseoConfig) -> None:
        content = (
            "We are the only platform that does this. "
            "Our tool is 3x cheaper than alternatives. "
            "RivalApp is outdated and clunky. "
            "Join 100,000 users today. "
            "Best alternative to RivalApp. "
            "RivalApp costs $99. "
        )
        report = run_legal_checks(content, cfg)
        assert report.overall_risk == RiskLevel.RED
        assert len(report.findings) > 0
        assert report.checklist_score < 12

    def test_eu_checks_disabled_by_default(self, cfg: PseoConfig) -> None:
        content = "RivalApp is inferior to our solution."
        report = run_legal_checks(content, cfg, eu_checks=False)
        eu_findings = [f for f in report.findings if f.check == "legal_yellow_eu_denigration"]
        assert len(eu_findings) == 0

    def test_eu_checks_enabled(self, cfg: PseoConfig) -> None:
        content = "RivalApp is inferior to our solution."
        report = run_legal_checks(content, cfg, eu_checks=True)
        eu_findings = [f for f in report.findings if f.check == "legal_yellow_eu_denigration"]
        assert len(eu_findings) >= 1

    def test_backward_compat_issues_list(self, cfg: PseoConfig) -> None:
        content = "Our tool is 3x cheaper than others."
        report = run_legal_checks(content, cfg)
        issues = report.to_issues_list()
        assert isinstance(issues, list)
        assert all(isinstance(i, dict) for i in issues)
        assert all("level" in i and "check" in i and "message" in i for i in issues)

    def test_report_has_checklist(self, cfg: PseoConfig) -> None:
        content = "RivalApp is a product we compare against. Some clean content."
        report = run_legal_checks(content, cfg)
        assert report.checklist_total == 12
        assert isinstance(report.checklist_failures, list)
        assert report.checklist_score is not None
        assert 0 <= report.checklist_score <= 12

    def test_config_trademark_max_mentions(self) -> None:
        cfg = PseoConfig(
            product=ProductConfig(name="TestProduct", domain="test.com"),
            competitors=[Competitor(slug="rival", name="RivalApp", domain="rival.com", tier=1)],
        )
        cfg.legal.trademark_max_mentions = 5
        content = "RivalApp " * 10
        report = run_legal_checks(content, cfg)
        assert any(f.check == "legal_yellow_excessive_mentions" for f in report.findings)

    def test_additional_disparaging_words(self) -> None:
        cfg = PseoConfig(
            product=ProductConfig(name="TestProduct", domain="test.com"),
            competitors=[Competitor(slug="rival", name="RivalApp", domain="rival.com", tier=1)],
        )
        cfg.legal.additional_disparaging_words = ["bloated"]
        content = "RivalApp is bloated and slow."
        report = run_legal_checks(content, cfg)
        assert any(f.check == "legal_red_disparaging" for f in report.findings)
