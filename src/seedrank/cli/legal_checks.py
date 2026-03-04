"""Legal compliance checks for competitor content.

Provides regex/heuristic checks covering US Lanham Act, EU Directive 2006/114/EC,
and general comparative advertising best practices. Not legal advice — this is a
risk-screening tool.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from seedrank.config.schema import PseoConfig


class RiskLevel(Enum):
    """Maps to error / warning / info in existing issue format."""

    RED = "error"
    YELLOW = "warning"
    GREEN = "info"


class LegalFramework(Enum):
    """Which legal regime a finding relates to."""

    GENERAL = "general"
    LANHAM_ACT = "lanham_act"
    EU_DIRECTIVE = "eu_directive"


@dataclass
class LegalFinding:
    """A single legal compliance finding."""

    level: RiskLevel
    check: str
    message: str
    framework: LegalFramework = LegalFramework.GENERAL
    statement: str = ""
    recommended_fix: str = ""

    def to_issue(self) -> dict:
        """Convert to existing issues list format."""
        return {
            "level": self.level.value,
            "check": self.check,
            "message": self.message,
        }


# ---------------------------------------------------------------------------
# 12-item Safe Comparative Advertising Checklist
# ---------------------------------------------------------------------------

_CHECKLIST_ITEMS = [
    "All factual claims about competitors are verifiable and currently accurate",
    "Pricing comparisons specify plan tier, billing period, and date verified",
    "Feature comparisons note the date of assessment",
    "Opinions are clearly framed as opinions",
    "The comparison includes areas where the competitor genuinely excels",
    "No competitor trademarks used beyond nominative fair use",
    "No implication of competitor dishonesty, incompetence, or harm",
    "No claims that the competitor's product is an imitation or inferior copy",
    "Comparison criteria are representative and material (not cherry-picked)",
    "Sourced claims link to or reference the source",
    "Content has a 'last verified' or 'last updated' date",
    "No superlatives presented as factual without evidence",
]


@dataclass
class LegalReport:
    """Aggregated legal compliance report."""

    findings: list[LegalFinding] = field(default_factory=list)
    checklist_score: int | None = None
    checklist_total: int = field(default_factory=lambda: len(_CHECKLIST_ITEMS))
    checklist_failures: list[str] = field(default_factory=list)

    @property
    def overall_risk(self) -> RiskLevel:
        if any(f.level == RiskLevel.RED for f in self.findings):
            return RiskLevel.RED
        if any(f.level == RiskLevel.YELLOW for f in self.findings):
            return RiskLevel.YELLOW
        return RiskLevel.GREEN

    def to_issues_list(self) -> list[dict]:
        """Convert to existing list[dict] format for backward compat."""
        return [f.to_issue() for f in self.findings]


# ---------------------------------------------------------------------------
# Helper: extract competitor names from config
# ---------------------------------------------------------------------------

def _competitor_names(cfg: PseoConfig) -> tuple[list[str], list[str]]:
    """Return (original_names, lowered_names) from config."""
    names = [c.name for c in cfg.competitors]
    return names, [n.lower() for n in names]


def _near_competitor(
    text_lower: str,
    match_start: int,
    match_end: int,
    competitor_names_lower: list[str],
    window: int = 100,
) -> bool:
    """Check if any competitor name is within *window* chars of the match."""
    start = max(0, match_start - window)
    end = min(len(text_lower), match_end + window)
    ctx = text_lower[start:end]
    return any(cn in ctx for cn in competitor_names_lower)


# ===========================================================================
# Migrated checks (from _check_legal_tiers)
# ===========================================================================


def check_multiplier_claims(content_lower: str) -> list[LegalFinding]:
    """RED: '3x cheaper', '10x faster', etc."""
    findings: list[LegalFinding] = []
    for m in re.finditer(r"\b\d+x\s+(cheaper|faster|better|more\s+\w+)\b", content_lower):
        findings.append(LegalFinding(
            level=RiskLevel.RED,
            check="legal_red_multiplier",
            message=f"RED: Multiplier claim found: '{m.group()}'",
            framework=LegalFramework.LANHAM_ACT,
            statement=m.group(),
            recommended_fix="Replace with specific, benchmarked comparison or remove multiplier.",
        ))
    return findings


def check_disparaging_words(
    content_lower: str,
    competitor_names_lower: list[str],
    extra_words: list[str] | None = None,
) -> list[LegalFinding]:
    """RED: Disparaging words within 100 chars of a competitor name."""
    disparaging = [
        "outdated", "opaque", "stagnated",
        "went downhill", "can't match", "clunky", "disappointing",
    ]
    if extra_words:
        disparaging.extend(w.lower() for w in extra_words)

    findings: list[LegalFinding] = []
    for disp_word in disparaging:
        for dm in re.finditer(re.escape(disp_word), content_lower):
            if _near_competitor(content_lower, dm.start(), dm.end(), competitor_names_lower, window=100):
                findings.append(LegalFinding(
                    level=RiskLevel.RED,
                    check="legal_red_disparaging",
                    message=f"RED: Potentially disparaging '{disp_word}' near competitor name",
                    framework=LegalFramework.LANHAM_ACT,
                    statement=disp_word,
                    recommended_fix=f"Remove '{disp_word}' or replace with objective, sourced observation.",
                ))
                break  # One per disparaging word
    return findings


def check_exclusivity_claims(content_lower: str) -> list[LegalFinding]:
    """RED: 'the only platform/tool/service that...' without hedge."""
    findings: list[LegalFinding] = []
    for m in re.finditer(
        r"\b(?:the\s+)?only\s+(?:platform|tool|service|product|solution)\s+that\b",
        content_lower,
    ):
        start = max(0, m.start() - 50)
        end = min(len(content_lower), m.end() + 50)
        context = content_lower[start:end]
        if not any(hedge in context for hedge in ["we are aware of", "as of", "to our knowledge"]):
            findings.append(LegalFinding(
                level=RiskLevel.RED,
                check="legal_red_exclusivity",
                message=f"RED: Unhedged exclusivity claim: '{m.group()}'",
                framework=LegalFramework.LANHAM_ACT,
                statement=m.group(),
                recommended_fix="Add 'to our knowledge' or 'as of [date]' hedge.",
            ))
    return findings


def check_performance_claims(content_lower: str) -> list[LegalFinding]:
    """RED: 'faster/slower/more efficient than' without benchmark evidence."""
    findings: list[LegalFinding] = []
    for m in re.finditer(r"\b(faster|slower|quicker|more efficient)\s+than\b", content_lower):
        start = max(0, m.start() - 100)
        end = min(len(content_lower), m.end() + 100)
        context = content_lower[start:end]
        benchmark_words = ["benchmark", "test", "measured", "ms", "seconds", "%"]
        if not any(w in context for w in benchmark_words):
            findings.append(LegalFinding(
                level=RiskLevel.RED,
                check="legal_red_performance",
                message=f"RED: Performance claim without benchmark: '{m.group()}'",
                framework=LegalFramework.LANHAM_ACT,
                statement=m.group(),
                recommended_fix="Add benchmark data or rephrase as subjective experience.",
            ))
    return findings


def check_unattributed_stats(content: str, content_lower: str) -> list[LegalFinding]:
    """YELLOW: Statistics like '100,000 users' without attribution."""
    findings: list[LegalFinding] = []
    stat_pattern = r"\b\d[\d,]*\+?\s*(?:users|developers|customers|downloads|stars)\b"
    for m in re.finditer(stat_pattern, content_lower):
        start = max(0, m.start() - 80)
        end = min(len(content_lower), m.end() + 80)
        context = content_lower[start:end]
        attributed = any(w in context for w in ["according to", "reports", "source:"]) or bool(
            re.search(r"\bper\b", context)
        )
        has_link = bool(re.search(r"\[.*?\]\(https?://", content[start:end]))
        if not attributed and not has_link:
            findings.append(LegalFinding(
                level=RiskLevel.YELLOW,
                check="legal_yellow_unattributed_stat",
                message=f"YELLOW: Unattributed statistic: '{m.group()}'",
                framework=LegalFramework.GENERAL,
                statement=m.group(),
                recommended_fix="Add source attribution or link.",
            ))
    return findings


def check_unscoped_best(content_lower: str) -> list[LegalFinding]:
    """YELLOW: 'best for/alternative/option' without scoping."""
    findings: list[LegalFinding] = []
    for m in re.finditer(r"\bbest\s+(?:for|alternative|option|choice|platform)\b", content_lower):
        findings.append(LegalFinding(
            level=RiskLevel.YELLOW,
            check="legal_yellow_unscoped_best",
            message=f"YELLOW: Unscoped 'best' claim: '{m.group()}'",
            framework=LegalFramework.GENERAL,
            statement=m.group(),
            recommended_fix="Scope the claim: 'best for [specific use case] in our testing'.",
        ))
    return findings


def check_undated_pricing(content: str, content_lower: str) -> list[LegalFinding]:
    """YELLOW: '$X' without 'as of' date nearby."""
    findings: list[LegalFinding] = []
    for m in re.finditer(r"\$\d+", content):
        start = max(0, m.start() - 80)
        end = min(len(content), m.end() + 80)
        context = content_lower[start:end]
        if "as of" not in context:
            findings.append(LegalFinding(
                level=RiskLevel.YELLOW,
                check="legal_yellow_undated_pricing",
                message=f"YELLOW: Pricing without 'as of' date near: '{m.group()}'",
                framework=LegalFramework.GENERAL,
                statement=m.group(),
                recommended_fix="Add 'as of [month year]' near the pricing mention.",
            ))
            break  # One warning is enough
    return findings


# ===========================================================================
# New checks (from legal-review skill)
# ===========================================================================


def check_trademark_misuse(
    content: str,
    content_lower: str,
    competitor_names: list[str],
    competitor_names_lower: list[str],
    max_mentions: int = 15,
) -> list[LegalFinding]:
    """RED: 'the X killer', 'X-like', 'better X', or competitor name > max_mentions."""
    findings: list[LegalFinding] = []

    for name, name_lower in zip(competitor_names, competitor_names_lower):
        # "the X killer"
        pattern = rf"\bthe\s+{re.escape(name_lower)}\s+killer\b"
        if re.search(pattern, content_lower):
            findings.append(LegalFinding(
                level=RiskLevel.RED,
                check="legal_red_trademark_misuse",
                message=f"RED: Trademark misuse — 'the {name} killer'",
                framework=LegalFramework.LANHAM_ACT,
                statement=f"the {name} killer",
                recommended_fix=f"Remove 'killer' phrasing. Use '{name} alternative' instead.",
            ))

        # "X-like"
        pattern = rf"\b{re.escape(name_lower)}-like\b"
        if re.search(pattern, content_lower):
            findings.append(LegalFinding(
                level=RiskLevel.RED,
                check="legal_red_trademark_misuse",
                message=f"RED: Trademark misuse — '{name}-like' implies imitation",
                framework=LegalFramework.EU_DIRECTIVE,
                statement=f"{name}-like",
                recommended_fix=f"Replace with 'similar to {name}' or describe the specific feature.",
            ))

        # "better X" (standalone, not "better than X")
        pattern = rf"\bbetter\s+{re.escape(name_lower)}\b"
        if re.search(pattern, content_lower):
            findings.append(LegalFinding(
                level=RiskLevel.RED,
                check="legal_red_trademark_misuse",
                message=f"RED: Trademark misuse — 'better {name}' implies replacement",
                framework=LegalFramework.LANHAM_ACT,
                statement=f"better {name}",
                recommended_fix=f"Use 'alternative to {name}' instead.",
            ))

        # Excessive mentions
        count = len(re.findall(re.escape(name_lower), content_lower))
        if count > max_mentions:
            findings.append(LegalFinding(
                level=RiskLevel.YELLOW,
                check="legal_yellow_excessive_mentions",
                message=f"YELLOW: '{name}' mentioned {count} times (threshold: {max_mentions})",
                framework=LegalFramework.EU_DIRECTIVE,
                statement=f"{name} x{count}",
                recommended_fix="Reduce mentions — excessive use may imply unfair advantage of trademark.",
            ))

    return findings


def check_implied_deficiency(
    content_lower: str,
    competitor_names_lower: list[str],
) -> list[LegalFinding]:
    """YELLOW: 'no hidden fees', 'without the hassle', 'actually works' near competitor."""
    patterns = [
        "no hidden fees",
        "no hidden costs",
        "without the hassle",
        "without the headache",
        "actually works",
        "actually reliable",
        "no lock-in",
        "no vendor lock-in",
        "truly unlimited",
    ]
    findings: list[LegalFinding] = []
    for pat in patterns:
        for m in re.finditer(re.escape(pat), content_lower):
            if _near_competitor(content_lower, m.start(), m.end(), competitor_names_lower, window=200):
                findings.append(LegalFinding(
                    level=RiskLevel.YELLOW,
                    check="legal_yellow_implied_deficiency",
                    message=f"YELLOW: Implied deficiency '{pat}' near competitor name",
                    framework=LegalFramework.LANHAM_ACT,
                    statement=pat,
                    recommended_fix="State your feature positively without implying competitor lacks it.",
                ))
                break  # One per pattern
    return findings


def check_opinion_as_fact(
    content_lower: str,
    competitor_names_lower: list[str],
) -> list[LegalFinding]:
    """YELLOW: 'X is broken', 'X's support is slow' without hedging."""
    opinion_patterns = [
        r"is\s+broken",
        r"is\s+terrible",
        r"is\s+awful",
        r"is\s+unreliable",
        r"support\s+is\s+slow",
        r"support\s+is\s+terrible",
        r"is\s+buggy",
        r"is\s+unusable",
    ]
    hedges = ["in our testing", "in our experience", "we found", "we noticed", "we observed", "some users report"]
    findings: list[LegalFinding] = []

    for pat in opinion_patterns:
        for m in re.finditer(pat, content_lower):
            if _near_competitor(content_lower, m.start(), m.end(), competitor_names_lower, window=150):
                # Check for hedge phrases nearby
                start = max(0, m.start() - 150)
                end = min(len(content_lower), m.end() + 150)
                context = content_lower[start:end]
                if not any(h in context for h in hedges):
                    findings.append(LegalFinding(
                        level=RiskLevel.YELLOW,
                        check="legal_yellow_opinion_as_fact",
                        message=f"YELLOW: Opinion presented as fact: '{m.group()}' near competitor",
                        framework=LegalFramework.LANHAM_ACT,
                        statement=m.group(),
                        recommended_fix="Add 'in our testing' or 'we found' to frame as observation.",
                    ))
                    break  # One per pattern
    return findings


def check_outdated_claims(
    content_lower: str,
    competitor_names_lower: list[str],
) -> list[LegalFinding]:
    """YELLOW: 'X doesn't support Y', 'X lacks Y' without date scope."""
    claim_patterns = [
        r"doesn't\s+support",
        r"does\s+not\s+support",
        r"doesn't\s+offer",
        r"does\s+not\s+offer",
        r"\blacks?\s+(?:support|integration|feature|api|capability|functionality|option)\w*",
        r"\bmissing\s+(?:key|critical|important|basic|native|built-in|proper)\s+\w+",
        r"doesn't\s+have",
        r"does\s+not\s+have",
        r"doesn't\s+include",
        r"does\s+not\s+include",
        r"no\s+support\s+for",
    ]
    date_scopes = ["as of", "when we checked", "when we last checked", "last verified", "at the time of writing"]
    findings: list[LegalFinding] = []

    for pat in claim_patterns:
        for m in re.finditer(pat, content_lower):
            if _near_competitor(content_lower, m.start(), m.end(), competitor_names_lower, window=150):
                start = max(0, m.start() - 150)
                end = min(len(content_lower), m.end() + 150)
                context = content_lower[start:end]
                if not any(d in context for d in date_scopes):
                    findings.append(LegalFinding(
                        level=RiskLevel.YELLOW,
                        check="legal_yellow_outdated_claim",
                        message=f"YELLOW: Potentially outdated claim '{m.group()}' near competitor without date",
                        framework=LegalFramework.LANHAM_ACT,
                        statement=m.group(),
                        recommended_fix="Add 'as of [date]' to scope the claim.",
                    ))
                    break  # One per pattern
    return findings


def check_cherry_picked_comparison(content: str) -> list[LegalFinding]:
    """YELLOW: Markdown tables where a competitor column has >70% negative marks, or >8 rows."""
    findings: list[LegalFinding] = []

    # Find markdown tables
    table_pattern = re.compile(
        r"^(\|.+\|)\r?\n(\|[-:\s|]+\|)\r?\n((?:\|.+\|\r?\n?)+)",
        re.MULTILINE,
    )

    for table_match in table_pattern.finditer(content):
        header = table_match.group(1)
        body = table_match.group(3)
        rows = [r.strip() for r in body.strip().splitlines() if r.strip()]

        if len(rows) > 8:
            findings.append(LegalFinding(
                level=RiskLevel.YELLOW,
                check="legal_yellow_cherry_picked_toomany",
                message=f"YELLOW: Comparison table has {len(rows)} rows — may appear cherry-picked",
                framework=LegalFramework.EU_DIRECTIVE,
                statement=f"Table with {len(rows)} rows",
                recommended_fix="Keep comparison tables to 6-8 representative criteria.",
            ))
            continue

        # Check win/loss ratio per column (skip first column which is feature names)
        cols = [c.strip() for c in header.split("|") if c.strip()]
        if len(cols) < 3:
            continue

        positive_marks = {"✅", "✓", "yes", "included", "full", "unlimited"}
        negative_marks = {"❌", "✗", "no", "none", "limited", "—", "-"}

        for col_idx in range(1, len(cols)):
            pos_count = 0
            neg_count = 0
            for row in rows:
                cells = [c.strip() for c in row.split("|") if c.strip()]
                if col_idx < len(cells):
                    cell_lower = cells[col_idx].lower().strip()
                    if cell_lower in positive_marks:
                        pos_count += 1
                    elif cell_lower in negative_marks:
                        neg_count += 1
            total = pos_count + neg_count
            if total >= 4:
                pos_pct = pos_count / total
                neg_pct = neg_count / total
                if pos_pct > 0.8:
                    # This column is mostly positive — that's the "own product" column
                    pass
                elif neg_pct > 0.7:
                    # This column is mostly negative — flag if another column is mostly positive
                    findings.append(LegalFinding(
                        level=RiskLevel.YELLOW,
                        check="legal_yellow_cherry_picked_onesided",
                        message=(
                            f"YELLOW: Comparison table may be cherry-picked — "
                            f"column '{cols[col_idx]}' has {neg_count}/{total} negative marks"
                        ),
                        framework=LegalFramework.EU_DIRECTIVE,
                        statement=f"Column '{cols[col_idx]}': {neg_count}/{total} negative",
                        recommended_fix="Include criteria where the competitor genuinely excels.",
                    ))
                    break  # One finding per table

    return findings


def check_pricing_specificity(
    content: str,
    content_lower: str,
    competitor_names_lower: list[str],
) -> list[LegalFinding]:
    """YELLOW: '$X' near competitor name without plan tier or billing period."""
    findings: list[LegalFinding] = []
    billing_markers = ["/mo", "/yr", "/year", "/month", "per month", "per year", "annually", "monthly"]
    tier_markers = ["plan", "tier", "starter", "pro", "premium", "enterprise", "basic", "free"]

    for m in re.finditer(r"\$\d+", content):
        if _near_competitor(content_lower, m.start(), m.end(), competitor_names_lower, window=150):
            start = max(0, m.start() - 80)
            end = min(len(content), m.end() + 80)
            context = content_lower[start:end]
            has_billing = any(b in context for b in billing_markers)
            has_tier = any(t in context for t in tier_markers)
            if not has_billing or not has_tier:
                missing = []
                if not has_tier:
                    missing.append("plan tier")
                if not has_billing:
                    missing.append("billing period")
                findings.append(LegalFinding(
                    level=RiskLevel.YELLOW,
                    check="legal_yellow_pricing_specificity",
                    message=(
                        f"YELLOW: Competitor pricing '{m.group()}' missing {' and '.join(missing)}"
                    ),
                    framework=LegalFramework.LANHAM_ACT,
                    statement=m.group(),
                    recommended_fix="Add specific plan name and billing period (e.g., 'Pro plan, $49/mo').",
                ))
                break  # One warning is enough
    return findings


def check_eu_denigration(
    content_lower: str,
    competitor_names_lower: list[str],
) -> list[LegalFinding]:
    """YELLOW: Extended denigrating language near competitor (EU-specific)."""
    eu_words = [
        "inferior", "subpar", "mediocre", "overpriced", "waste of money",
        "poor quality", "second-rate", "low-quality", "third-rate",
        "barely functional", "not worth",
    ]
    findings: list[LegalFinding] = []
    for word in eu_words:
        for m in re.finditer(re.escape(word), content_lower):
            if _near_competitor(content_lower, m.start(), m.end(), competitor_names_lower, window=150):
                findings.append(LegalFinding(
                    level=RiskLevel.YELLOW,
                    check="legal_yellow_eu_denigration",
                    message=f"YELLOW: EU denigration risk — '{word}' near competitor name",
                    framework=LegalFramework.EU_DIRECTIVE,
                    statement=word,
                    recommended_fix="Remove denigrating language. EU law prohibits discrediting competitors even if true.",
                ))
                break  # One per word
    return findings


def check_missing_methodology(content: str, content_lower: str) -> list[LegalFinding]:
    """YELLOW: Comparison articles without methodology disclosure."""
    findings: list[LegalFinding] = []

    # Is this a comparison article?
    comparison_markers = ["vs ", "vs.", "versus", "compare", "comparison", "alternative"]
    is_comparison = any(m in content_lower for m in comparison_markers)
    has_table = bool(re.search(r"\|.+\|.+\|", content))

    if not (is_comparison and has_table):
        return findings

    methodology_markers = [
        "methodology", "how we evaluated", "how we compared",
        "our evaluation criteria", "scoring criteria", "our approach",
        "how we tested", "evaluation process", "how we chose",
        "selection criteria",
    ]
    has_methodology = any(m in content_lower for m in methodology_markers)

    if not has_methodology:
        findings.append(LegalFinding(
            level=RiskLevel.YELLOW,
            check="legal_yellow_missing_methodology",
            message="YELLOW: Comparison article with table but no methodology disclosure",
            framework=LegalFramework.EU_DIRECTIVE,
            statement="(article-level)",
            recommended_fix="Add a 'How We Evaluated' or 'Methodology' section.",
        ))

    return findings


def check_trademark_in_headings(
    content: str,
    competitor_names_lower: list[str],
) -> list[LegalFinding]:
    """YELLOW: Competitor name + negative modifier in H1/H2."""
    findings: list[LegalFinding] = []
    negative_modifiers = [
        "falls short", "fails", "lacks", "can't", "doesn't",
        "problems with", "issues with", "trouble with",
        "why not", "avoid", "worst",
    ]

    for m in re.finditer(r"^#{1,2}\s+(.+)$", content, re.MULTILINE):
        heading_lower = m.group(1).lower()
        for name in competitor_names_lower:
            if name in heading_lower:
                for neg in negative_modifiers:
                    if neg in heading_lower:
                        findings.append(LegalFinding(
                            level=RiskLevel.YELLOW,
                            check="legal_yellow_trademark_heading",
                            message=f"YELLOW: Competitor name with negative modifier in heading: '{m.group(1)}'",
                            framework=LegalFramework.LANHAM_ACT,
                            statement=m.group(1),
                            recommended_fix="Rephrase heading to be neutral (e.g., 'Comparing X and Y').",
                        ))
                        break
                break  # Only check one competitor per heading

    return findings


def check_screenshot_fair_use(
    content: str,
    content_lower: str,
    competitor_names_lower: list[str],
) -> list[LegalFinding]:
    """YELLOW: Image references near competitor names."""
    findings: list[LegalFinding] = []
    for m in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", content):
        if _near_competitor(content_lower, m.start(), m.end(), competitor_names_lower, window=200):
            findings.append(LegalFinding(
                level=RiskLevel.YELLOW,
                check="legal_yellow_screenshot_fair_use",
                message=f"YELLOW: Image near competitor name — verify fair use: '{m.group(2)[:60]}'",
                framework=LegalFramework.GENERAL,
                statement=m.group(0)[:80],
                recommended_fix="Ensure screenshot use is fair use. Prefer your own images or clearly attribute.",
            ))
    return findings


# ===========================================================================
# Checklist scorer
# ===========================================================================


def compute_checklist_score(findings: list[LegalFinding], content_lower: str) -> tuple[int, list[str]]:
    """Compute the 12-item checklist score based on findings.

    Returns (score out of 12, list of failed item descriptions).
    """
    checks = {f.check for f in findings}
    failed: list[str] = []

    # Item 1: Verifiable claims — fails if outdated claims found
    if "legal_yellow_outdated_claim" in checks:
        failed.append(_CHECKLIST_ITEMS[0])

    # Item 2: Pricing specificity
    if "legal_yellow_pricing_specificity" in checks or "legal_yellow_undated_pricing" in checks:
        failed.append(_CHECKLIST_ITEMS[1])

    # Item 3: Dated comparisons — fails if missing methodology or no "as of"/"last verified"
    has_date = any(d in content_lower for d in ["as of", "last verified", "last updated", "last checked"])
    if not has_date:
        failed.append(_CHECKLIST_ITEMS[2])

    # Item 4: Opinions framed — fails if opinion-as-fact found
    if "legal_yellow_opinion_as_fact" in checks:
        failed.append(_CHECKLIST_ITEMS[3])

    # Item 5: Balanced comparison — fails if one-sided cherry-picked
    if "legal_yellow_cherry_picked_onesided" in checks:
        failed.append(_CHECKLIST_ITEMS[4])

    # Item 6: Trademark fair use — fails if trademark misuse found
    if "legal_red_trademark_misuse" in checks:
        failed.append(_CHECKLIST_ITEMS[5])

    # Item 7: No dishonesty implications — fails if implied deficiency found
    if "legal_yellow_implied_deficiency" in checks:
        failed.append(_CHECKLIST_ITEMS[6])

    # Item 8: No imitation claims — fails if trademark misuse (X-like, better X)
    if "legal_red_trademark_misuse" in checks:
        # Check specifically for imitation patterns
        for f in findings:
            if f.check == "legal_red_trademark_misuse" and ("like" in f.statement.lower() or "killer" in f.statement.lower()):
                failed.append(_CHECKLIST_ITEMS[7])
                break

    # Item 9: Representative criteria — fails if too many rows
    if "legal_yellow_cherry_picked_toomany" in checks:
        failed.append(_CHECKLIST_ITEMS[8])

    # Item 10: Sourced claims
    if "legal_yellow_unattributed_stat" in checks:
        failed.append(_CHECKLIST_ITEMS[9])

    # Item 11: Last verified date
    has_verified = bool(re.search(
        r"(?:last (?:verified|updated|checked|reviewed))[:\s]*"
        r"(?:\w+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
        content_lower,
    ))
    if not has_verified:
        failed.append(_CHECKLIST_ITEMS[10])

    # Item 12: No unsupported superlatives
    if "legal_yellow_unscoped_best" in checks or "legal_red_multiplier" in checks:
        failed.append(_CHECKLIST_ITEMS[11])

    score = len(_CHECKLIST_ITEMS) - len(failed)
    return score, failed


# ===========================================================================
# Orchestrator
# ===========================================================================


def run_legal_checks(
    content: str,
    cfg: PseoConfig,
    eu_checks: bool = False,
) -> LegalReport:
    """Run all legal checks and return a LegalReport.

    Checks are split into universal (always run) and competitor-context
    (only when competitor names are found in the content).
    """
    content_lower = content.lower()
    names, names_lower = _competitor_names(cfg)

    extra_disparaging = cfg.legal.additional_disparaging_words
    max_mentions = cfg.legal.trademark_max_mentions

    findings: list[LegalFinding] = []

    # --- Universal checks (always run) ---
    findings.extend(check_multiplier_claims(content_lower))
    findings.extend(check_exclusivity_claims(content_lower))
    findings.extend(check_unscoped_best(content_lower))
    findings.extend(check_undated_pricing(content, content_lower))
    findings.extend(check_unattributed_stats(content, content_lower))

    # --- Competitor-context checks (only when competitors are mentioned) ---
    has_competitors = any(n in content_lower for n in names_lower)

    if has_competitors:
        findings.extend(check_disparaging_words(content_lower, names_lower, extra_disparaging))
        findings.extend(check_performance_claims(content_lower))
        findings.extend(check_trademark_misuse(content, content_lower, names, names_lower, max_mentions))

        if cfg.legal.implied_deficiency_check:
            findings.extend(check_implied_deficiency(content_lower, names_lower))

        findings.extend(check_opinion_as_fact(content_lower, names_lower))
        findings.extend(check_outdated_claims(content_lower, names_lower))
        findings.extend(check_cherry_picked_comparison(content))
        findings.extend(check_pricing_specificity(content, content_lower, names_lower))

        if cfg.legal.require_comparison_methodology:
            findings.extend(check_missing_methodology(content, content_lower))

        findings.extend(check_trademark_in_headings(content, names_lower))
        findings.extend(check_screenshot_fair_use(content, content_lower, names_lower))

        # EU-specific checks
        if eu_checks:
            findings.extend(check_eu_denigration(content_lower, names_lower))

        # Checklist scoring only when competitors present
        score, failed = compute_checklist_score(findings, content_lower)
        return LegalReport(
            findings=findings,
            checklist_score=score,
            checklist_total=len(_CHECKLIST_ITEMS),
            checklist_failures=failed,
        )

    return LegalReport(findings=findings)
