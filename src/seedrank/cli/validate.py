"""seedrank validate — Validate config, research, articles, and legal compliance."""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import typer

from seedrank.config.schema import PseoConfig
from seedrank.utils.console import console, error, heading, info, success, warning

validate_app = typer.Typer(help="Validation commands.", no_args_is_help=True)


@validate_app.command(name="config")
def validate_config(
    config: Path = typer.Option(
        Path("seedrank.config.yaml"),
        "--config",
        "-c",
        help="Path to config file.",
    ),
) -> None:
    """Validate the config file."""
    heading("Validate Config")

    from seedrank.config.loader import load_config

    try:
        cfg = load_config(config)
        success(f"Config valid: {cfg.product.name} ({cfg.product.domain})")
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    # Check for recommended fields
    issues = 0
    if not cfg.competitors:
        warning("No competitors defined")
        issues += 1
    if not cfg.personas:
        warning("No personas defined")
        issues += 1
    if not cfg.content_types:
        warning("No content types defined")
        issues += 1
    if not cfg.legal.corrections_email:
        warning("No corrections email set (legal.corrections_email)")
        issues += 1
    if not cfg.legal.company_name:
        warning("No company name set (legal.company_name)")
        issues += 1

    if issues == 0:
        success("All checks passed.")
    else:
        warning(f"Config valid with {issues} warning(s)")


@validate_app.command(name="research")
def validate_research_cmd(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace root directory.",
    ),
) -> None:
    """Check research data quality."""
    heading("Validate Research")

    from seedrank.data.db import connect, get_db_path
    from seedrank.research.validator import validate_research

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    with connect(db_path) as conn:
        result = validate_research(conn)

    for check in result.checks:
        if check.level == "error":
            error(check.message)
        elif check.level == "warning":
            warning(check.message)
        elif check.passed:
            success(check.message)
        else:
            info(check.message)

    console.print()


@validate_app.command(name="article")
def validate_article(
    path: Path = typer.Argument(help="Path to article file."),
    config: Path = typer.Option(
        Path("seedrank.config.yaml"),
        "--config",
        "-c",
        help="Path to config file (for voice/legal rules).",
    ),
    as_json: bool = typer.Option(False, "--json", help="Output results as JSON."),
    eu_checks: bool = typer.Option(False, "--eu-checks", help="Include EU/German law checks."),
    legal_report: bool = typer.Option(
        False, "--legal-report", help="Show detailed legal report with checklist."
    ),
) -> None:
    """Validate an article — word count, links, voice, legal compliance."""
    heading("Validate Article")

    if not path.exists():
        error(f"File not found: {path}")
        raise typer.Exit(1)

    content = path.read_text(encoding="utf-8")
    content_lower = content.lower()
    word_count = len(content.split())
    issues: list[dict] = []

    # --- Word count ---
    info(f"File: {path.name}")
    info(f"Word count: {word_count}")

    if word_count < 300:
        issues.append({
            "level": "error", "check": "word_count",
            "message": "Very short (< 300 words)",
        })
    elif word_count < 800:
        issues.append({
            "level": "warning", "check": "word_count",
            "message": "Below typical minimum (< 800 words)",
        })

    # --- Internal links ---
    links = re.findall(r"\[([^\]]+)\]\((/[^\)]+)\)", content)
    if links:
        info(f"Internal links found: {len(links)}")
    else:
        issues.append({
            "level": "warning",
            "check": "internal_links",
            "message": "No internal links found — add crosslinks",
        })

    # --- Load config for voice/legal checks ---
    cfg = None
    try:
        from seedrank.config.loader import load_config

        cfg = load_config(config)
    except (FileNotFoundError, ValueError):
        info("Config not found — skipping voice/legal checks")

    # --- Structural checks (no config needed) ---
    _check_structure(content, issues)
    _check_ai_tells(content, content_lower, issues)

    report = None
    if cfg:
        _check_voice(content, content_lower, cfg, issues)
        _check_legal(content, content_lower, cfg, issues)

        # Run legal tier checks via new module
        from seedrank.cli.legal_checks import run_legal_checks

        use_eu = eu_checks or getattr(cfg.legal, "eu_checks_enabled", False)
        report = run_legal_checks(content, cfg, eu_checks=use_eu)
        issues.extend(report.to_issues_list())

        _check_citability(content, content_lower, issues)

        # Content-type-aware word count override
        _check_content_type_word_count(
            path, word_count, cfg, issues
        )

    # --- Output ---
    if as_json:
        import json

        result = {
            "file": str(path),
            "word_count": word_count,
            "internal_links": len(links),
            "issues": issues,
            "pass": all(i["level"] != "error" for i in issues),
        }
        if report:
            result["legal_report"] = {
                "overall_risk": report.overall_risk.value,
                "checklist_score": report.checklist_score,
                "checklist_total": report.checklist_total,
                "checklist_failures": report.checklist_failures,
                "findings": [
                    {
                        "level": f.level.value,
                        "check": f.check,
                        "message": f.message,
                        "framework": f.framework.value,
                        "statement": f.statement,
                        "recommended_fix": f.recommended_fix,
                    }
                    for f in report.findings
                ],
            }
        typer.echo(json.dumps(result, indent=2))
    else:
        for issue in issues:
            # Escape brackets so Rich doesn't interpret check names as markup
            check = issue["check"]
            msg = issue["message"]
            if issue["level"] == "error":
                error(f"{check}: {msg}")
            elif issue["level"] == "warning":
                warning(f"{check}: {msg}")
            else:
                info(f"{check}: {msg}")

        if not issues:
            success("All checks passed.")
        elif any(i["level"] == "error" for i in issues):
            error(f"Validation failed — {len(issues)} issue(s)")
        else:
            warning(f"Passed with {len(issues)} warning(s)")

        # Render detailed legal report if requested
        if legal_report and report:
            _render_legal_report(report)

    console.print()


def _check_structure(content: str, issues: list[dict]) -> None:
    """Check article structural quality — headings, paragraphs, images."""
    lines = content.split("\n")
    headings = [(i, line) for i, line in enumerate(lines) if re.match(r"^#{1,6}\s", line)]

    # Heading hierarchy: H1 should come before H2, no skipping levels
    if headings:
        first_level = len(re.match(r"^(#+)", headings[0][1]).group(1))
        if first_level != 1:
            issues.append({
                "level": "warning",
                "check": "heading_hierarchy",
                "message": f"First heading is H{first_level}, expected H1",
            })

        prev_level = 0
        for _, heading_line in headings:
            level = len(re.match(r"^(#+)", heading_line).group(1))
            if level > prev_level + 1 and prev_level > 0:
                issues.append({
                    "level": "warning",
                    "check": "heading_skip",
                    "message": (
                        f"Heading level skipped: H{prev_level} → H{level}"
                    ),
                })
                break  # One warning is enough
            prev_level = level
    else:
        issues.append({
            "level": "warning",
            "check": "no_headings",
            "message": "No markdown headings found",
        })

    # Check for very long paragraphs (>300 words)
    paragraphs = re.split(r"\n\s*\n", content)
    for i, para in enumerate(paragraphs):
        para_words = len(para.split())
        if para_words > 300:
            issues.append({
                "level": "warning",
                "check": "long_paragraph",
                "message": (
                    f"Paragraph {i + 1} has {para_words} words"
                    " (>300) — consider breaking up"
                ),
            })
            break  # One warning per article

    # Check images have alt text
    images_no_alt = re.findall(r"!\[\]\(", content)
    if images_no_alt:
        issues.append({
            "level": "warning",
            "check": "image_alt",
            "message": (
                f"{len(images_no_alt)} image(s) without alt text"
            ),
        })

    # Check for meta description (frontmatter)
    if content.startswith("---"):
        frontmatter_end = content.find("---", 3)
        if frontmatter_end > 0:
            frontmatter = content[3:frontmatter_end]
            if "description" not in frontmatter.lower():
                issues.append({
                    "level": "warning",
                    "check": "meta_description",
                    "message": "Frontmatter missing 'description' field",
                })


def _check_content_type_word_count(
    path: Path,
    word_count: int,
    cfg: PseoConfig,
    issues: list[dict],
) -> None:
    """Check word count against content-type-specific minimums."""
    # Try to detect content type from file path
    path_str = str(path)
    matched_ct = None
    for ct in cfg.content_types:
        if ct.content_dir and ct.content_dir in path_str:
            matched_ct = ct
            break

    if matched_ct and word_count < matched_ct.min_words:
        issues.append({
            "level": "warning",
            "check": "content_type_word_count",
            "message": (
                f"Content type '{matched_ct.label}' requires"
                f" {matched_ct.min_words} words, got {word_count}"
            ),
        })


def _check_voice(
    content: str,
    content_lower: str,
    cfg: PseoConfig,
    issues: list[dict],
) -> None:
    """Check voice/brand compliance."""
    # Banned words
    found_banned = []
    for word in cfg.voice.banned_words:
        pattern = r"\b" + re.escape(word.lower()) + r"\b"
        matches = re.findall(pattern, content_lower)
        if matches:
            found_banned.append((word, len(matches)))

    if found_banned:
        words_str = ", ".join(f"'{w}' ({n}x)" for w, n in found_banned)
        issues.append({
            "level": "warning",
            "check": "banned_words",
            "message": f"Banned words found: {words_str}",
        })

    # CTA never-use list
    for cta in cfg.voice.cta_never:
        if cta.lower() in content_lower:
            issues.append({
                "level": "warning",
                "check": "banned_cta",
                "message": f"Uses banned CTA: '{cta}'",
            })


def _check_legal(
    content: str,
    content_lower: str,
    cfg: PseoConfig,
    issues: list[dict],
) -> None:
    """Check legal compliance for the article."""
    comp_rules = cfg.legal.comparison

    # Detect if this is a comparison article (mentions competitor names)
    mentioned_competitors = [
        c.name for c in cfg.competitors if c.name.lower() in content_lower
    ]
    is_comparison = len(mentioned_competitors) > 0

    if not is_comparison:
        return

    info(f"Competitors mentioned: {', '.join(mentioned_competitors)}")

    # Check for comparison disclaimer
    if comp_rules.require_disclaimer:
        has_disclaimer = any(
            marker in content_lower
            for marker in [
                "editorial note",
                "disclaimer",
                "we research",
                "fact-check",
                "last verified",
                "last updated",
                "editorial disclaimer",
            ]
        )
        if not has_disclaimer:
            issues.append({
                "level": "warning",
                "check": "comparison_disclaimer",
                "message": (
                    "Comparison article without disclaimer. Add an editorial note with "
                    "verification date and corrections contact."
                ),
            })

    # Check for source URLs on competitor claims
    if comp_rules.require_source_urls:
        # Look for pricing/feature claims without nearby links
        claim_patterns = [
            r"(?:costs?|pric(?:e|ing)|starts? at|per month|\$/mo)",
            r"(?:doesn't|does not|lacks?|missing|no support for)",
            r"(?:only|just|limited to|max(?:imum)?)\s+\d+",
        ]
        for pattern in claim_patterns:
            claim_matches = list(re.finditer(pattern, content_lower))
            for match in claim_matches:
                # Check if there's a link within 200 chars of the claim
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 200)
                context = content[start:end]
                has_link = bool(re.search(r"\[.*?\]\(https?://", context))
                has_footnote = bool(re.search(r"\[\d+\]", context))
                if not has_link and not has_footnote:
                    claim_text = content[match.start() : match.end() + 30].strip()
                    if len(claim_text) > 60:
                        claim_text = claim_text[:57] + "..."
                    issues.append({
                        "level": "warning",
                        "check": "unsourced_claim",
                        "message": (
                            f"Possible unsourced competitor claim near: '...{claim_text}...'"
                        ),
                    })
                    break  # One warning per pattern is enough

    # Check for last-verified date
    if comp_rules.require_last_verified:
        has_verified = bool(
            re.search(
                r"(?:last (?:verified|updated|checked|reviewed))[:\s]*"
                r"(?:\w+ \d{1,2},? \d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})",
                content_lower,
            )
        )
        if not has_verified:
            issues.append({
                "level": "warning",
                "check": "last_verified",
                "message": (
                    "Comparison article without 'last verified' date. "
                    "Add a date so readers know data freshness."
                ),
            })

    # Check for banned competitor claims
    for claim in comp_rules.banned_claims:
        if claim.lower() in content_lower:
            issues.append({
                "level": "error",
                "check": "banned_claim",
                "message": f"Contains banned claim: '{claim}'",
            })

    # Check for affiliate disclosure
    if cfg.legal.require_affiliate_disclosure:
        has_affiliate_links = bool(
            re.search(r"\[.*?\]\(https?://.*?(?:ref=|affiliate|partner|aff)", content)
        )
        if has_affiliate_links:
            has_disclosure = any(
                marker in content_lower
                for marker in ["affiliate", "commission", "earn a commission"]
            )
            if not has_disclosure:
                issues.append({
                    "level": "error",
                    "check": "affiliate_disclosure",
                    "message": "Contains affiliate links without FTC disclosure",
                })


def _render_legal_report(report: "LegalReport") -> None:
    """Render a detailed legal compliance report using Rich."""
    from rich.panel import Panel
    from rich.table import Table

    from seedrank.cli.legal_checks import LegalReport, RiskLevel

    # Summary panel
    risk_colors = {RiskLevel.RED: "red", RiskLevel.YELLOW: "yellow", RiskLevel.GREEN: "green"}
    risk_label = {RiskLevel.RED: "HIGH", RiskLevel.YELLOW: "MEDIUM", RiskLevel.GREEN: "LOW"}
    risk = report.overall_risk
    color = risk_colors[risk]

    red_count = sum(1 for f in report.findings if f.level == RiskLevel.RED)
    yellow_count = sum(1 for f in report.findings if f.level == RiskLevel.YELLOW)

    summary = (
        f"[bold {color}]Overall Risk: {risk_label[risk]}[/]\n"
        f"Findings: {red_count} high, {yellow_count} medium\n"
        f"Checklist: {report.checklist_score}/{report.checklist_total}"
    )
    console.print(Panel(summary, title="Legal Compliance Report", border_style=color))

    # Findings table
    if report.findings:
        table = Table(title="Findings", show_lines=True)
        table.add_column("Level", style="bold", width=8)
        table.add_column("Check", width=30)
        table.add_column("Message")
        table.add_column("Fix", width=40)

        for f in report.findings:
            lvl_color = "red" if f.level == RiskLevel.RED else "yellow"
            table.add_row(
                f"[{lvl_color}]{f.level.name}[/]",
                f.check,
                f.message,
                f.recommended_fix or "",
            )
        console.print(table)

    # Checklist failures
    if report.checklist_failures:
        console.print("\n[bold]Checklist failures:[/]")
        for item in report.checklist_failures:
            console.print(f"  [red]✗[/] {item}")
    elif report.checklist_score == 12:
        console.print("\n[green]All 12 checklist items passed.[/]")


def _check_citability(content: str, content_lower: str, issues: list[dict]) -> None:
    """Check GEO citability rules C1-C5."""
    word_count = len(content.split())

    # C1: Dated facts — pricing ($X) should have "as of" within 100 chars
    pricing_matches = list(re.finditer(r"\$\d+", content))
    undated_count = 0
    for m in pricing_matches:
        start = max(0, m.start() - 100)
        end = min(len(content), m.end() + 100)
        context = content_lower[start:end]
        if "as of" not in context:
            undated_count += 1
    if undated_count > 0:
        issues.append({
            "level": "warning",
            "check": "citability_c1_dated_facts",
            "message": f"C1: {undated_count} pricing reference(s) without 'as of [date]'",
        })

    # C2: Comparison tables — check for markdown table syntax
    has_table = bool(re.search(r"\|.+\|.+\|", content))
    # Only flag for articles that look like comparisons (mention "vs" or "compare" or "alternative")
    looks_like_comparison = any(
        w in content_lower for w in ["vs ", "versus", "compare", "comparison", "alternative"]
    )
    if looks_like_comparison and not has_table:
        issues.append({
            "level": "warning",
            "check": "citability_c2_comparison_table",
            "message": "C2: Comparison content without a structured comparison table",
        })

    # C3: FAQ section
    faq_pattern = r"^##\s*(?:FAQ|Frequently Asked)"
    has_faq = bool(re.search(faq_pattern, content, re.MULTILINE | re.IGNORECASE))
    if word_count >= 1000 and not has_faq:
        issues.append({
            "level": "warning",
            "check": "citability_c3_faq_section",
            "message": "C3: No FAQ section found (improves AI citability)",
        })

    # C4: Answer-first structure — first sentence after H2 should not be transitional filler
    filler_starts = [
        "in this section", "let's explore", "there are many",
        "when it comes to", "as we all know", "it's important to",
        "before we dive", "let's take a look",
    ]
    h2_matches = list(re.finditer(r"^##\s+.+$", content, re.MULTILINE))
    for h2m in h2_matches:
        # Get the text after this heading until next heading or 200 chars
        after_start = h2m.end()
        after_text = content[after_start:after_start + 300].strip()
        # Skip empty lines
        lines = [ln for ln in after_text.split("\n") if ln.strip()]
        if lines:
            first_sentence = lines[0].lower().strip()
            if any(first_sentence.startswith(filler) for filler in filler_starts):
                issues.append({
                    "level": "warning",
                    "check": "citability_c4_answer_first",
                    "message": f"C4: Transitional filler after heading: '{lines[0][:60]}...'",
                })
                break  # One warning is enough

    # C5: Specific numbers — article should contain concrete numbers
    if word_count >= 1000:
        number_patterns = [
            r"\$\d+",               # Dollar amounts
            r"\d+%",                # Percentages
            r"\b\d{2,}\b",          # Specific counts (2+ digits)
        ]
        total_numbers = 0
        for pat in number_patterns:
            total_numbers += len(re.findall(pat, content))
        if total_numbers < 3:
            issues.append({
                "level": "warning",
                "check": "citability_c5_specific_numbers",
                "message": (
                    f"C5: Only {total_numbers} specific numbers found"
                    " — add concrete data points"
                ),
            })


def _check_ai_tells(content: str, content_lower: str, issues: list[dict]) -> None:
    """Detect AI writing tells — patterns that make content read as machine-generated."""

    # --- AI crutch phrases ---
    crutch_phrases = [
        "here's what you need to know",
        "here's the thing",
        "worth noting",
        "it's worth noting",
        "whether you need",
        "let's dive in",
        "let's break it down",
        "let's break down",
        "in today's landscape",
        "in today's world",
        "in today's market",
        "stands out from",
        "really shines",
        "when it comes to",
        "at the end of the day",
        "it's important to note",
        "the bottom line",
        "in a nutshell",
    ]
    found_crutches = []
    for phrase in crutch_phrases:
        count = content_lower.count(phrase)
        if count > 0:
            found_crutches.append((phrase, count))
    if found_crutches:
        details = ", ".join(f"'{p}' ({n}x)" for p, n in found_crutches)
        issues.append({
            "level": "warning",
            "check": "ai_tell_crutch_phrases",
            "message": f"AI crutch phrases found: {details}",
        })

    # --- Self-announcing honesty ---
    honesty_phrases = [
        "verified pricing",
        "honest trade-offs",
        "honest trade-off",
        "the honest answer",
        "we honestly",
        "to be frank",
        "the truth is",
        "in all honesty",
        "let me be real",
    ]
    found_honesty = [p for p in honesty_phrases if p in content_lower]
    if found_honesty:
        details = ", ".join(f"'{p}'" for p in found_honesty)
        issues.append({
            "level": "warning",
            "check": "ai_tell_self_announcing_honesty",
            "message": f"Self-announcing honesty (just state the fact): {details}",
        })

    # --- Meta-commentary ---
    meta_patterns = [
        r"this is the section that",
        r"this guide breaks down",
        r"this guide will",
        r"this article breaks down",
        r"this article will",
        r"in this section,?\s+we",
        r"now let'?s move on to",
        r"as mentioned earlier",
        r"as we discussed above",
        r"we'?ve covered .+,?\s*now let",
    ]
    found_meta = []
    for pattern in meta_patterns:
        matches = re.findall(pattern, content_lower)
        if matches:
            found_meta.extend(matches)
    if found_meta:
        examples = found_meta[:3]
        details = ", ".join(f"'{m.strip()}'" for m in examples)
        suffix = f" (+{len(found_meta) - 3} more)" if len(found_meta) > 3 else ""
        issues.append({
            "level": "warning",
            "check": "ai_tell_meta_commentary",
            "message": f"Meta-commentary about article structure: {details}{suffix}",
        })

    # --- Counting before listing ---
    count_before_list = re.findall(
        r"\b(?:two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
        r"(?:things?|factors?|reasons?|ways?|forces?|differences?|points?|aspects?)"
        r"\s+(?:matter|drive|to consider|to keep|to know|stand out|are|that)\b",
        content_lower,
    )
    if count_before_list:
        details = ", ".join(f"'{m}'" for m in count_before_list[:3])
        issues.append({
            "level": "warning",
            "check": "ai_tell_counting_before_listing",
            "message": f"Counting before listing (just list them): {details}",
        })

    # --- Gratuitous competitor compliments ---
    compliment_patterns = [
        r"\b\w+\s+is\s+an?\s+(?:impressive|remarkable|fantastic|excellent|solid|great)\s+"
        r"(?:project|platform|tool|product|service|option|choice)",
        r"\bwe\s+have\s+(?:great\s+)?respect\s+for\b",
        r"\bhave\s+done\s+(?:remarkable|impressive|great)\s+work\b",
    ]
    found_compliments = []
    for pattern in compliment_patterns:
        for m in re.finditer(pattern, content_lower):
            found_compliments.append(m.group())
    if found_compliments:
        details = ", ".join(f"'{c}'" for c in found_compliments[:3])
        issues.append({
            "level": "warning",
            "check": "ai_tell_gratuitous_compliments",
            "message": f"Gratuitous competitor compliments (state facts plainly): {details}",
        })

    # --- Balanced diplomatic hedging ---
    hedge_phrases = [
        "neither is universally better",
        "none of these are deal-breakers",
        "none of these are deal breakers",
        "it depends on your specific needs",
        "both have their pros and cons",
        "the best choice depends on your requirements",
        "there's no one-size-fits-all",
        "each has its own strengths",
        "your mileage may vary",
    ]
    found_hedges = [p for p in hedge_phrases if p in content_lower]
    if len(found_hedges) >= 2:
        details = ", ".join(f"'{h}'" for h in found_hedges)
        issues.append({
            "level": "warning",
            "check": "ai_tell_diplomatic_hedging",
            "message": (
                f"Multiple diplomatic hedges ({len(found_hedges)}x) — "
                f"make a specific recommendation: {details}"
            ),
        })

    # --- Excessive date stamps ---
    date_stamp_pattern = r"\(as of \w+ \d{4}\)"
    date_stamps = re.findall(date_stamp_pattern, content, re.IGNORECASE)
    if len(date_stamps) > 6:
        issues.append({
            "level": "warning",
            "check": "ai_tell_excessive_date_stamps",
            "message": (
                f"{len(date_stamps)} date stamps found — consolidate into a single "
                f"'Data last verified: [date]' note, keep inline only on key claims"
            ),
        })

    # --- Tricolons (three parallel short sentences) ---
    sentences = re.split(r"(?<=[.!?])\s+", content)
    # Filter out single-word fragments, headings, and lines with markdown syntax
    sentences = [
        s for s in sentences
        if len(s.split()) >= 2
        and not s.startswith("#")
        and not s.startswith("[")
        and not s.startswith("|")
    ]
    tricolon_count = 0
    for i in range(len(sentences) - 2):
        s1, s2, s3 = sentences[i], sentences[i + 1], sentences[i + 2]
        w1, w2, w3 = len(s1.split()), len(s2.split()), len(s3.split())
        # All three are short (<=10 words) and similar length (within 3 words)
        if (
            w1 <= 10
            and w2 <= 10
            and w3 <= 10
            and abs(w1 - w2) <= 3
            and abs(w2 - w3) <= 3
            and abs(w1 - w3) <= 3
        ):
            # Check structural similarity: same ending word or same starting word
            endings = [
                re.sub(r"[.!?,;:]+$", "", s).split()[-1].lower()
                for s in (s1, s2, s3) if s.split()
            ]
            starts = [s.split()[0].lower() for s in (s1, s2, s3) if s.split()]
            if (
                len(endings) == 3
                and len(starts) == 3
                and (len(set(endings)) == 1 or len(set(starts)) == 1)
            ):
                tricolon_count += 1
    if tricolon_count > 0:
        issues.append({
            "level": "warning",
            "check": "ai_tell_tricolons",
            "message": (
                f"{tricolon_count} tricolon(s) detected — three parallel short sentences "
                f"with identical structure. Vary sentence length."
            ),
        })


@validate_app.command(name="legal")
def validate_legal(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace root directory.",
    ),
    config: Path = typer.Option(
        Path("seedrank.config.yaml"),
        "--config",
        "-c",
        help="Path to config file.",
    ),
    format: str = typer.Option(
        "summary",
        "--format",
        "-f",
        help="Output format: 'summary' or 'detailed'.",
    ),
    eu_checks: bool = typer.Option(False, "--eu-checks", help="Include EU/German law checks."),
) -> None:
    """Check legal compliance across the workspace — data staleness, coverage."""
    heading("Legal Compliance Check")

    from seedrank.config.loader import load_config
    from seedrank.data.db import connect, get_db_path

    try:
        cfg = load_config(config)
    except (FileNotFoundError, ValueError) as e:
        error(str(e))
        raise typer.Exit(1)

    db_path = get_db_path(workspace.resolve())
    if not db_path.exists():
        error("Database not found. Run 'seedrank init' first.")
        raise typer.Exit(1)

    issues = 0

    with connect(db_path) as conn:
        # Check data staleness
        stale_days = cfg.legal.data_staleness_days
        cutoff = (datetime.now(UTC) - timedelta(days=stale_days)).isoformat()

        stale_keywords = conn.execute(
            "SELECT COUNT(*) FROM keywords WHERE fetched_at < ?", (cutoff,)
        ).fetchone()[0]
        total_keywords = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]

        if stale_keywords > 0 and total_keywords > 0:
            pct = (stale_keywords / total_keywords) * 100
            warning(
                f"{stale_keywords}/{total_keywords} keywords are stale"
                f" (>{stale_days} days old, {pct:.0f}%)"
            )
            issues += 1
        elif total_keywords > 0:
            success(f"All {total_keywords} keywords are fresh (<{stale_days} days)")

        # Check stale competitor data
        stale_comp = conn.execute(
            "SELECT COUNT(*) FROM competitor_keywords WHERE fetched_at < ?", (cutoff,)
        ).fetchone()[0]
        total_comp = conn.execute(
            "SELECT COUNT(*) FROM competitor_keywords"
        ).fetchone()[0]

        if stale_comp > 0 and total_comp > 0:
            pct = (stale_comp / total_comp) * 100
            warning(
                f"{stale_comp}/{total_comp} competitor keyword records are stale"
                f" (>{stale_days} days, {pct:.0f}%)"
            )
            issues += 1
        elif total_comp > 0:
            success(f"All {total_comp} competitor records are fresh")

        # Check stale SERP data
        stale_serp = conn.execute(
            "SELECT COUNT(DISTINCT keyword) FROM serp_snapshots WHERE fetched_at < ?",
            (cutoff,),
        ).fetchone()[0]
        if stale_serp > 0:
            warning(f"{stale_serp} SERP snapshot(s) are stale (>{stale_days} days)")
            issues += 1

        # Check for comparison articles missing disclaimers + run content checks
        from seedrank.cli.legal_checks import run_legal_checks

        comparison_articles = _find_comparison_articles(conn, cfg, workspace)
        article_reports: list[tuple[str, "LegalReport"]] = []
        use_eu = eu_checks or getattr(cfg.legal, "eu_checks_enabled", False)

        if comparison_articles:
            info(f"Found {len(comparison_articles)} comparison article(s) to audit")
            for slug, path in comparison_articles:
                if path and Path(path).exists():
                    article_content = Path(path).read_text(encoding="utf-8")
                    article_lower = article_content.lower()
                    has_disclaimer = any(
                        m in article_lower
                        for m in [
                            "editorial note",
                            "disclaimer",
                            "last verified",
                            "last updated",
                        ]
                    )
                    if not has_disclaimer:
                        warning(f"Article '{slug}' is a comparison without disclaimer")
                        issues += 1

                    # Run legal checks on article content
                    report = run_legal_checks(article_content, cfg, eu_checks=use_eu)
                    if report.findings:
                        article_reports.append((slug, report))
                        red = sum(1 for f in report.findings if f.level.value == "error")
                        yellow = sum(1 for f in report.findings if f.level.value == "warning")
                        if red:
                            error(f"Article '{slug}': {red} high-risk, {yellow} medium-risk finding(s)")
                        else:
                            warning(f"Article '{slug}': {yellow} medium-risk finding(s)")
                        issues += red + yellow

    # Config completeness
    if not cfg.legal.corrections_email:
        warning("No corrections email set — required for comparison article disclaimers")
        issues += 1

    if not cfg.legal.company_name:
        warning("No company name set — needed for legal disclaimers")
        issues += 1

    console.print()
    if issues == 0:
        success("All legal checks passed.")
    else:
        warning(f"Legal audit found {issues} issue(s) to address")

    # Detailed format: render per-article legal reports
    if format == "detailed" and article_reports:
        for slug, report in article_reports:
            console.print(f"\n[bold]--- {slug} ---[/]")
            _render_legal_report(report)


def _find_comparison_articles(
    conn: sqlite3.Connection,
    cfg: PseoConfig,
    workspace: Path,
) -> list[tuple[str, str | None]]:
    """Find articles that mention competitor names."""
    articles = conn.execute(
        "SELECT slug, content_path FROM articles WHERE status IN ('draft', 'review', 'published')"
    ).fetchall()

    competitor_names = {c.name.lower() for c in cfg.competitors}
    results = []

    for row in articles:
        slug = row["slug"]
        content_path = row["content_path"]
        if content_path:
            full_path = workspace.resolve() / content_path
            if full_path.exists():
                text = full_path.read_text(encoding="utf-8").lower()
                if any(name in text for name in competitor_names):
                    results.append((slug, str(full_path)))

    return results
