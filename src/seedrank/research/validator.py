"""Research data sanity checks."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of a validation check."""

    passed: bool
    message: str
    level: str = "info"  # info, warning, error


@dataclass
class ResearchValidation:
    """Aggregate validation results."""

    checks: list[ValidationResult] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(c.level == "error" for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(c.level == "warning" for c in self.checks)


def validate_research(conn: sqlite3.Connection) -> ResearchValidation:
    """Run all research validation checks."""
    result = ResearchValidation()

    # Keyword count
    kw_count = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]
    if kw_count == 0:
        result.checks.append(ValidationResult(False, "No keywords in database", "error"))
    elif kw_count < 10:
        result.checks.append(
            ValidationResult(
                False, f"Only {kw_count} keywords — consider researching more", "warning"
            )
        )
    else:
        result.checks.append(ValidationResult(True, f"{kw_count} keywords in database"))

    if kw_count > 0:
        # KD all-zero check
        zero_kd = conn.execute(
            "SELECT COUNT(*) FROM keywords WHERE kd = 0 OR kd IS NULL"
        ).fetchone()[0]
        pct = (zero_kd / kw_count) * 100
        if pct > 80:
            result.checks.append(
                ValidationResult(False, f"{pct:.0f}% of keywords have zero/null KD", "warning")
            )
        else:
            result.checks.append(
                ValidationResult(True, f"KD distribution OK ({100 - pct:.0f}% have values)")
            )

        # Volume distribution
        zero_vol = conn.execute(
            "SELECT COUNT(*) FROM keywords WHERE volume = 0 OR volume IS NULL"
        ).fetchone()[0]
        pct = (zero_vol / kw_count) * 100
        if pct > 50:
            result.checks.append(
                ValidationResult(False, f"{pct:.0f}% of keywords have zero/null volume", "warning")
            )
        else:
            result.checks.append(
                ValidationResult(True, f"Volume distribution OK ({100 - pct:.0f}% have values)")
            )

    # SERP coverage
    serp_count = conn.execute("SELECT COUNT(DISTINCT keyword) FROM serp_snapshots").fetchone()[0]
    if serp_count == 0 and kw_count > 0:
        result.checks.append(
            ValidationResult(
                False, "No SERP snapshots — run 'seedrank research serp' for top keywords", "info"
            )
        )
    elif serp_count > 0:
        result.checks.append(ValidationResult(True, f"SERP snapshots for {serp_count} keywords"))

    # Competitor keyword coverage
    comp_count = conn.execute(
        "SELECT COUNT(DISTINCT competitor_slug) FROM competitor_keywords"
    ).fetchone()[0]
    if comp_count == 0:
        result.checks.append(
            ValidationResult(
                False, "No competitor data — run 'seedrank research competitors'", "info"
            )
        )
    else:
        result.checks.append(
            ValidationResult(True, f"Competitor data for {comp_count} competitor(s)")
        )

    return result
