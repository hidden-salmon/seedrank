"""Tests for GEO citability checks (_check_citability)."""

from __future__ import annotations

from seedrank.cli.validate import _check_citability


def _run_check(content: str) -> list[dict]:
    """Helper to run _check_citability and return the issues list."""
    issues: list[dict] = []
    _check_citability(content, content.lower(), issues)
    return issues


def _issues_with_check(issues: list[dict], check_name: str) -> list[dict]:
    """Filter issues by check name."""
    return [i for i in issues if i["check"] == check_name]


# ---------------------------------------------------------------------------
# C1: Pricing without "as of" date
# ---------------------------------------------------------------------------
class TestC1DatedFacts:
    def test_pricing_without_as_of_flagged(self) -> None:
        content = "The pro plan costs $49 per month."
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c1_dated_facts")
        assert len(matched) == 1
        assert matched[0]["level"] == "warning"
        assert "1 pricing reference" in matched[0]["message"]

    def test_pricing_with_as_of_passes(self) -> None:
        content = "As of January 2025, the pro plan costs $49 per month."
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c1_dated_facts")
        assert len(matched) == 0

    def test_multiple_undated_pricing(self) -> None:
        content = "Plans start at $19 for basic and $99 for enterprise."
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c1_dated_facts")
        assert len(matched) == 1
        assert "2 pricing reference" in matched[0]["message"]

    def test_no_pricing_passes(self) -> None:
        content = "This is a guide about data processing techniques."
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c1_dated_facts")
        assert len(matched) == 0


# ---------------------------------------------------------------------------
# C2: Comparison content without table
# ---------------------------------------------------------------------------
class TestC2ComparisonTable:
    def test_comparison_without_table_flagged(self) -> None:
        content = "Product A vs Product B: which one is right for you?"
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c2_comparison_table")
        assert len(matched) == 1
        assert matched[0]["level"] == "warning"

    def test_comparison_with_table_passes(self) -> None:
        content = (
            "Product A vs Product B: which one is right for you?\n\n"
            "| Feature | Product A | Product B |\n"
            "|---------|-----------|----------|\n"
            "| Price   | $10       | $20      |\n"
        )
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c2_comparison_table")
        assert len(matched) == 0

    def test_non_comparison_content_passes(self) -> None:
        content = "This is a tutorial about setting up your environment."
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c2_comparison_table")
        assert len(matched) == 0

    def test_alternative_keyword_triggers(self) -> None:
        content = "Looking for an alternative to WidgetCo? Here are your options."
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c2_comparison_table")
        assert len(matched) == 1


# ---------------------------------------------------------------------------
# C3: FAQ section
# ---------------------------------------------------------------------------
class TestC3FaqSection:
    def test_long_article_without_faq_flagged(self) -> None:
        # Generate content >= 1000 words
        words = "word " * 1100
        content = f"# Guide\n\n{words}"
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c3_faq_section")
        assert len(matched) == 1
        assert matched[0]["level"] == "warning"

    def test_short_article_without_faq_passes(self) -> None:
        words = "word " * 500
        content = f"# Guide\n\n{words}"
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c3_faq_section")
        assert len(matched) == 0

    def test_long_article_with_faq_passes(self) -> None:
        words = "word " * 1100
        content = f"# Guide\n\n{words}\n\n## FAQ\n\n**Q: How does it work?**\nA: It just works."
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c3_faq_section")
        assert len(matched) == 0

    def test_faq_heading_case_insensitive(self) -> None:
        words = "word " * 1100
        content = f"# Guide\n\n{words}\n\n## Frequently Asked Questions\n\nQ1: Why?"
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c3_faq_section")
        assert len(matched) == 0


# ---------------------------------------------------------------------------
# C4: Transitional filler after H2
# ---------------------------------------------------------------------------
class TestC4AnswerFirst:
    def test_filler_after_h2_flagged(self) -> None:
        content = (
            "# Main Title\n\n"
            "## Features\n\n"
            "In this section we will explore the key features of the product.\n\n"
            "Feature one is great."
        )
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c4_answer_first")
        assert len(matched) == 1
        assert matched[0]["level"] == "warning"

    def test_direct_answer_after_h2_passes(self) -> None:
        content = (
            "# Main Title\n\n"
            "## Features\n\n"
            "The product supports real-time data processing and batch ETL.\n\n"
            "Additional details follow."
        )
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c4_answer_first")
        assert len(matched) == 0

    def test_lets_explore_flagged(self) -> None:
        content = (
            "# Title\n\n"
            "## Pricing\n\n"
            "Let's explore the different pricing tiers available.\n\n"
            "The starter plan is $19/mo."
        )
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c4_answer_first")
        assert len(matched) == 1

    def test_when_it_comes_to_flagged(self) -> None:
        content = (
            "# Title\n\n"
            "## Performance\n\n"
            "When it comes to raw performance, many factors play a role.\n\n"
            "Benchmark results show improvement."
        )
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c4_answer_first")
        assert len(matched) == 1

    def test_multiple_h2_only_one_warning(self) -> None:
        content = (
            "# Title\n\n"
            "## Section A\n\n"
            "Before we dive into the details, let us set the stage.\n\n"
            "## Section B\n\n"
            "Let's take a look at the options.\n\n"
        )
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c4_answer_first")
        # Only one warning (first match triggers, then break)
        assert len(matched) == 1


# ---------------------------------------------------------------------------
# C5: Specific numbers
# ---------------------------------------------------------------------------
class TestC5SpecificNumbers:
    def test_long_article_with_few_numbers_flagged(self) -> None:
        # 1100 words with only 1 number
        words = "word " * 1095
        content = f"# Guide\n\n{words}\n\nThere is 1 option available."
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c5_specific_numbers")
        assert len(matched) == 1
        assert matched[0]["level"] == "warning"

    def test_long_article_with_many_numbers_passes(self) -> None:
        words = "word " * 1050
        content = (
            f"# Guide\n\n{words}\n\n"
            "The system handles $199 plans, 50% faster processing, "
            "and supports 1000 concurrent connections with 99.9% uptime."
        )
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c5_specific_numbers")
        assert len(matched) == 0

    def test_short_article_with_few_numbers_passes(self) -> None:
        # Under 1000 words, C5 is not checked
        words = "word " * 500
        content = f"# Short Guide\n\n{words}"
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c5_specific_numbers")
        assert len(matched) == 0

    def test_numbers_include_percentages(self) -> None:
        words = "word " * 1050
        content = f"# Report\n\n{words}\n\n85% approval, 92% retention, 77% growth."
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c5_specific_numbers")
        assert len(matched) == 0

    def test_numbers_include_dollar_amounts(self) -> None:
        words = "word " * 1050
        # Use "as of" so C1 doesn't add noise, but C5 cares about count
        content = f"# Report\n\n{words}\n\nAs of 2025, prices are $19, $49, and $99."
        issues = _run_check(content)
        matched = _issues_with_check(issues, "citability_c5_specific_numbers")
        assert len(matched) == 0
