"""seedrank init — Bootstrap a new Seedrank workspace."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer
import yaml

from seedrank.config.schema import PseoConfig
from seedrank.data.db import get_db_path, init_db
from seedrank.utils.console import console, info, success
from seedrank.utils.paths import ensure_workspace_dirs


def _generate_claude_md(cfg: PseoConfig | None) -> str:
    """Generate .claude/seedrank.md content for the workspace.

    Pulls company-specific rules from config when available.
    Falls back to sensible generic defaults otherwise.
    """
    if cfg:
        product_name = cfg.product.name
        domain = cfg.product.domain

        # Voice rules from config
        tone_list = ", ".join(cfg.voice.tone) if cfg.voice.tone else "direct, helpful, confident"
        banned_words = ", ".join(cfg.voice.banned_words) if cfg.voice.banned_words else "(none configured)"
        cta_primary = cfg.voice.cta_primary or "Get started"
        cta_never = ", ".join(f'"{c}"' for c in cfg.voice.cta_never) if cfg.voice.cta_never else "(none)"

        # Legal
        corrections_email = cfg.legal.corrections_email or "corrections@" + domain
        staleness_days = cfg.legal.data_staleness_days

        # Comparison rules
        comp_rules = cfg.legal.comparison
        disclaimer_text = comp_rules.disclaimer_text.replace(
            "{corrections_email}", corrections_email
        )
        banned_claims = comp_rules.banned_claims

        # Competitors
        competitor_names = [c.name for c in cfg.competitors]
        competitor_section = ""
        if competitor_names:
            competitor_section = "Competitor names: " + ", ".join(competitor_names) + "\n"

        # Personas
        persona_section = ""
        if cfg.personas:
            lines = []
            for p in cfg.personas:
                lines.append(f"- **{p.name}** ({p.slug}): {p.description}")
                if p.pain_points:
                    lines.append(f"  Pain points: {'; '.join(p.pain_points)}")
            persona_section = "\n".join(lines) + "\n"
    else:
        product_name = "Your Product"
        domain = "example.com"
        tone_list = "direct, helpful, confident"
        banned_words = "supercharge, revolutionize, game-changing, seamless, leverage"
        cta_primary = "Get started"
        cta_never = "(none)"
        corrections_email = "corrections@example.com"
        staleness_days = 90
        disclaimer_text = (
            "We research and fact-check every claim in our articles. Pricing and features "
            "may change; we update periodically. If you spot an inaccuracy, email "
            + corrections_email + "."
        )
        banned_claims = []
        competitor_section = ""
        persona_section = ""

    banned_claims_text = ""
    if banned_claims:
        banned_claims_text = "\n**Never write these claims:**\n" + "\n".join(f"- {c}" for c in banned_claims) + "\n"

    return f"""# Seedrank System — {product_name}

## Overview

This workspace uses the `seedrank` CLI toolkit to manage programmatic SEO for **{product_name}** ({domain}).
All structured data lives in `data/seedrank.db` (SQLite). Use the `seedrank` commands below to query and manage it.

## Session Protocol

1. **Start**: Run `seedrank session start` to load context from the last session
2. **Work**: Use seedrank commands to research, plan, write, and evaluate
3. **End**: Run `seedrank session end "summary of what was accomplished"` to log progress

## Tool Reference

### Research
- `seedrank research keywords "k1, k2, k3"` — Fetch keyword data from DataForSEO
- `seedrank research questions "query"` — Discover questions via PAA + AI responses
- `seedrank research serp "keyword"` — Get SERP snapshot for a keyword
- `seedrank research competitors domain.com` — Fetch competitor keyword data
- `seedrank research expand "seed keyword"` — Get keyword suggestions
- `seedrank research geo queries.yaml` — Run GEO queries across AI models

### Data Queries
- `seedrank data keywords --json` — List all keywords with metrics
- `seedrank data gaps --json` — Find keyword gaps (competitors rank, we don't)
- `seedrank data questions --json` — List discovered questions
- `seedrank data articles --json` — List all registered articles
- `seedrank data performance --json` — Show GSC performance data
- `seedrank data geo-trends --json` — Brand mention rate over time
- `seedrank data geo-gaps --json` — Queries where competitors appear but brand doesn't
- `seedrank data calendar --json` — Show content calendar

### Competitor Profiles
- `seedrank competitors init <slug> --name "Name" --domain domain.com` — Create skeleton profile
- `seedrank competitors show <slug> [--json]` — Display competitor profile
- `seedrank competitors list [--json]` — List profiles with freshness status
- `seedrank competitors verify <slug>` — Fetch verification URLs and update last_verified
- `seedrank competitors freshness [--days N]` — Check which profiles are stale

### Content Management
- `seedrank articles register <slug> --title "..." --keywords "k1, k2"` — Register new article
- `seedrank articles update <slug> --status published --url "/blog/slug"` — Update article
- `seedrank articles crosslinks <slug> --json` — Get crosslink suggestions
- `seedrank articles backlinks <slug> --json` — Get backward link suggestions

### Calendar
- `seedrank calendar add <slug> --keywords "k1, k2"` — Add to calendar
- `seedrank calendar next --count 5 --json` — Get next priority items
- `seedrank calendar update <slug> --status writing` — Update calendar status

### Performance
- `seedrank gsc auth` — Authenticate with Google Search Console
- `seedrank gsc sync --days 30` — Sync performance data

### Validation
- `seedrank validate config` — Validate config file
- `seedrank validate research` — Check research data quality
- `seedrank validate article <path>` — Validate article (word count, links, voice, legal tiers, citability)
- `seedrank validate legal` — Workspace-wide legal compliance check

## Strategic Intelligence

Two living documents in `research/` capture insights across sessions:

- **`research/keyword-strategy.md`** — Keyword targeting tiers, SERP landscape analysis, keyword gaps, search trends. Updated after every research session.
- **`research/competitor-seo-intel.md`** — Per-competitor content strategies, traffic sources, ranked keywords, competitive gaps. Updated after every competitor analysis.

**Read these BEFORE** starting any research session, content planning, or article writing. They prevent duplicate work and ensure continuity across conversations.

**Update protocol:**
1. Raw data always goes to SQLite (`data/seedrank.db`) — timestamped, queryable
2. "So what" insights go to the strategy markdown files — narrative layer
3. Action items go to the content calendar — what to actually build

When updating strategy files: move the current "Latest snapshot" to a dated history entry, write the new snapshot, and add a changelog line at the top.

## Workflow Phases

1. **Research**: Use `seedrank research` commands to gather keyword data, SERP snapshots, competitor analysis. Update strategy files with findings.
2. **Prioritize**: Use `seedrank data gaps` and `seedrank data keywords` to identify opportunities
3. **Plan**: Use `seedrank calendar add` to build content calendar, `seedrank calendar next` to pick next article
4. **Execute**: Write content, use `seedrank articles crosslinks` for internal linking
5. **Review**: Register articles with `seedrank articles register`, validate with `seedrank validate article`
6. **Evaluate**: Sync GSC data with `seedrank gsc sync`, check `seedrank data performance`

## Skills (Slash Commands)

These skills orchestrate multi-step workflows. Use them for complete tasks:

| Skill | What it does |
|---|---|
| `/research-session "seed keywords"` | Full research workflow: discover questions, fetch keywords, analyze competitors, identify gaps |
| `/write-article <slug>` | Two-pass article writing: verify competitor data first, then write with voice/legal/citability compliance |
| `/review-article <path>` | 9-dimension audit: question coverage, fact-check, legal tiers, citability, cross-batch consistency |
| `/audit-legal` | Tiered legal audit: RED/YELLOW/GREEN classification, disclaimer templates, competitor lawyer test |
| `/geo-optimize <path>` | Optimize article for AI citability: C1-C5 checks, FAQ targeting, answer-first rewrites |
| `/aeo-monitor` | Periodic AI visibility monitoring: query AI models, track mention trends, identify gaps |
| `/plan-calendar [count]` | Analyze gaps, design article plan, add to calendar with auto-priority scoring |

**Typical workflow using skills:**
1. `/research-session "email marketing, newsletter tools"` — discover questions + build keyword foundation
2. `/plan-calendar 10` — decide what to write and in what order
3. `/write-article mailchimp-vs-moonbeam` — verify data, then write the top-priority article
4. `/review-article content/compare/mailchimp-vs-moonbeam.mdx` — 9-dimension audit before publishing
5. `/geo-optimize content/compare/mailchimp-vs-moonbeam.mdx` — optimize for AI citation
6. `/audit-legal` — periodic tiered compliance check across all content
7. `/aeo-monitor` — weekly AI visibility monitoring

---

## API Usage Rules

Research commands call external APIs (DataForSEO, OpenAI, Anthropic, etc.) that cost money. Follow these rules to avoid unnecessary spending.

### Cache-first: always check existing data before calling APIs

Research commands have built-in cache. If the database already has fresh data (less than {staleness_days} days old), the command will skip the API call and tell you. Use `--force` to override.

**Before researching keywords**, check what you already have:
```
seedrank data keywords --json
```
Only call `seedrank research keywords` for keywords not already in the database.

**Before researching competitors**, check existing data:
```
seedrank data gaps --json
```
Only call `seedrank research competitors <domain>` if the competitor hasn't been researched or data is stale.

**Before running GEO queries**, check existing results:
```
seedrank data geo --json
```
GEO results are cached for 7 days. Don't re-query the same topics within a week.

### Batch efficiently

- Combine keywords into a single call: `seedrank research keywords "k1, k2, k3, k4, k5"` instead of 5 separate calls.
- Don't run `seedrank research expand` on keywords you've already expanded — suggestions are stored permanently.
- Run `seedrank research questions` once per topic, not per keyword variant.

### Know what costs money

| Command | API called | Approx cost |
|---------|-----------|-------------|
| `research keywords` | DataForSEO | ~$0.05/call |
| `research expand` | DataForSEO | ~$0.10/call |
| `research serp` | DataForSEO | ~$0.10/call |
| `research competitors` | DataForSEO | ~$0.10/call |
| `research questions` | DataForSEO (2 calls) | ~$0.15/call |
| `research geo` | AI model providers | ~$0.005-0.01/query/model |
| `competitors verify` | Direct HTTP (free) | $0 |

**Free commands** (database queries only): `data keywords`, `data gaps`, `data questions`, `data articles`, `data geo`, `data geo-trends`, `data geo-gaps`, `data costs`, `data calendar`, `validate article`, `validate research`, `validate legal`, `competitors list`, `competitors show`, `competitors freshness`.

### Check your spending

```
seedrank data costs --days 30
```

Review API costs periodically. If costs seem high, you're probably re-fetching data that's already in the database.

---

## Content Writing Principles

These are guiding principles, not rigid templates. Articles vary in format, purpose, length, and audience. Apply these thoughtfully — the goal is great content, not checkbox compliance.

### Voice and Tone

Tone: **{tone_list}**
Primary CTA: **{cta_primary}**
Never-use CTAs: {cta_never}

**Banned words/phrases:** {banned_words}

These are marketing-speak words that dilute trust. Use concrete, specific language instead. Say what the product actually does, not how it makes you feel.

**Do:**
- Use plain language. Write how you'd explain it to a smart colleague.
- Be specific: "reduces email bounce rate by 15%" beats "dramatically improves deliverability."
- Let the product's actual capabilities speak. If a feature is good, describe what it does.
- Match the reader's sophistication level. Technical content can be technical.

**Don't:**
- Hedge excessively: "arguably", "perhaps", "it could be said that" — commit to your point or drop it.
- Use filler intros: "In today's fast-paced digital world..." — get to the point.
- Stuff keywords unnaturally. If the keyword doesn't fit the sentence, rewrite the sentence.
- Use clickbait: "You won't believe..." — respect the reader's intelligence.

### Structure and Format

There is no single correct format. Choose the structure that best serves the reader's intent:

- **Comparison articles**: Feature tables, pros/cons, pricing breakdowns, verdict sections
- **How-to guides**: Numbered steps, code blocks, screenshots, expected outcomes
- **Listicles**: Ranked or categorized items with brief analysis per item
- **Deep dives**: Long-form with clear section hierarchy, internal navigation
- **Landing pages**: Problem → solution → proof → CTA, concise and scannable

**Universal structure rules:**
- Every article needs a clear purpose stated in the first 2-3 sentences
- Use H2/H3 hierarchy — never skip heading levels
- Break up walls of text. If a paragraph exceeds 4-5 sentences, it probably needs splitting
- End with a concrete next step for the reader (not necessarily a hard sell)

### Accuracy and Sourcing

**All factual claims must be verifiable.** This is non-negotiable.

- Statistics, pricing, feature comparisons: link to the primary source
- Competitor information: link to the competitor's own documentation, pricing page, or changelog
- Industry data: cite the study, report, or dataset — not a third-party blog that cites it
- Your own product claims: only reference features with status "live" in the config
- If you can't source a claim, don't make it. Rephrase or remove it.

**Data freshness:**
- Competitor pricing and features change. Always note when data was last verified.
- Data older than {staleness_days} days should be re-verified before publishing.
- Use `seedrank validate legal` to check for stale data across the workspace.

{persona_section}
{competitor_section}
### Comparison Article Rules

Comparison articles carry the highest legal and reputational risk. Follow these principles carefully.

**Fairness:**
- Present competitors accurately. Acknowledge their genuine strengths.
- Never cherry-pick metrics to make competitors look bad.
- If {product_name} loses on a dimension, say so honestly. Readers trust balanced comparisons.
- Compare like with like. Don't compare a competitor's free tier to your paid tier (or vice versa).

**Sourcing (mandatory for comparison content):**
- Every competitor claim needs a source URL — their pricing page, docs, or changelog
- Price comparisons must include the plan tier, billing frequency, and as-of date
- Feature claims must link to the competitor's documentation, not your interpretation
- "Last verified: [date]" is required on all comparison data

**Legal compliance:**
- Under the Lanham Act (US), literally false claims about competitors don't require proof of consumer confusion — they're per-se actionable. Don't make them.
- Under EU Directive 2006/114/EC, comparative advertising must compare "like with like" and not denigrate competitors.
- Never claim a competitor "can't" do something unless their own docs confirm it. "Does not offer" or "not available" with a source link is safer.
- Pricing claims must be date-stamped. Stale pricing data is a legal risk.
- Never use competitor trademarks in ways that imply endorsement or association.

**Disclaimer:**
{disclaimer_text}

Include a version of this disclaimer (as an editorial note or footer) on every comparison article.
{banned_claims_text}
### Internal Linking (Crosslinks)

- Every article should have 3–8 internal links to other articles in the system
- Run `seedrank articles crosslinks <slug>` to get AI-scored suggestions
- Link using descriptive anchor text, not "click here" or "read more"
- After publishing, run `seedrank articles backlinks <slug>` to find existing articles that should link back
- Crosslinks serve readers first, SEO second. Only link when it genuinely adds value.

### SEO Fundamentals

- Target 1-3 primary keywords per article (from `seedrank data keywords`)
- Use the primary keyword in the H1, first paragraph, and at least one H2
- Write meta descriptions (150-160 chars) that include the primary keyword and a value proposition
- Use semantic variations naturally — don't repeat the exact keyword phrase excessively
- URL slug should be short, descriptive, and include the primary keyword

### Content Quality Checklist

Before marking an article as done, verify:

1. **Purpose**: Does the first paragraph make the article's value clear?
2. **Accuracy**: Are all factual claims sourced? Run `seedrank validate article <path>`
3. **Voice**: No banned words? Tone matches config? Check with `seedrank validate article`
4. **Links**: 3-8 internal crosslinks? External sources for claims?
5. **Legal**: Comparison articles have disclaimers and verified dates?
6. **Format**: Clean heading hierarchy? No walls of text? Clear next step?
7. **Keywords**: Primary keyword in H1, first paragraph, and at least one H2?

---

## File Layout

```
data/seedrank.db              — All structured data (keywords, articles, performance, questions)
data/competitors/         — Rich JSON profiles for each competitor
pipeline/state.yaml       — Current phase and progress
sessions/                 — Session logs (timestamped markdown)
decisions/                — Decision reasoning logs
research/                 — Strategic intelligence (read BEFORE research/planning/writing)
  keyword-strategy.md     — LIVING DOC: keyword tiers, SERP landscape, targeting rationale
  competitor-seo-intel.md — LIVING DOC: competitor content strategies, traffic, gaps
briefs/                   — Article briefs
content/                  — Written articles
```
"""


_KEYWORD_STRATEGY_TEMPLATE = """\
# Keyword Strategy — Living Document

This document captures keyword research insights, SERP landscape analysis, and targeting decisions.
It is read by `/research-session`, `/plan-calendar`, and `/write-article` to ensure continuity across sessions.

## Changelog

- (date): Initial setup — run `/research-session` to populate

---

## Keyword Targeting

### Latest snapshot: (not yet populated)

Use `/research-session` to research keywords. After research, update this section with:

### Tier 1: Easy Wins (KD < 15)

| Keyword | Volume | KD | CPC | Intent | Notes |
|---|---|---|---|---|---|
| (run research first) | | | | | |

### Tier 2: Achievable with Effort (KD 15-45)

| Keyword | Volume | KD | CPC | Intent | Notes |
|---|---|---|---|---|---|
| (run research first) | | | | | |

### Tier 3: Hard / Long-term (KD > 45)

| Keyword | Volume | KD | Notes |
|---|---|---|---|
| (run research first) | | | |

---

## Keyword Gaps Identified

| Gap | Source | Volume | KD | Notes |
|---|---|---|---|---|
| (populated by `/research-session`) | | | | |

---

## SERP Landscape

Top domains ranked by how many of your target keywords they appear for.
Populated by analyzing SERP competitor visibility data.

| Domain | Keywords | Avg Position | Est. Traffic | Character |
|---|---|---|---|---|
| (run research first) | | | | |

---

## Search Trends

| Keyword | YoY Trend | QoQ Trend | Notes |
|---|---|---|---|
| (populated after research) | | | |

---

## Data Sources

All raw data is stored in `data/seedrank.db`:
- `keywords` table — volume, KD, CPC, intent per keyword
- `serp_snapshots` table — point-in-time SERP results
- `serp_competitor_visibility` table — cross-keyword domain visibility
- `competitor_keywords` table — what competitors rank for
"""

_COMPETITOR_SEO_INTEL_TEMPLATE = """\
# Competitor SEO Intelligence — Living Document

This document captures what competitors are doing in organic search: which keywords they rank for,
their content strategies, traffic sources, and what you can learn. Read by `/research-session`,
`/plan-calendar`, and `/write-article`.

## Changelog

- (date): Initial setup — run `/research-session` with competitor analysis to populate

---

## (Competitor Name)

### Latest snapshot: (not yet populated)

**Domain overview:**
- Total ranked keywords: —
- Top-10 positions: —
- Estimated organic traffic: —
- Estimated traffic value: —

**Content strategy:**

(After running `seedrank research competitors domain.com`, analyze what type of content drives
their traffic: blog posts, documentation, comparison pages, educational content, etc.)

**Top keywords:**

| Keyword | Rank | Volume | KD | URL |
|---|---|---|---|---|
| (run research first) | | | | |

**What to learn from their approach:**
- (analysis goes here)

---

## Competitive Gaps

Content types or keyword clusters that no competitor has covered well.

| Gap | Competitors Checked | Volume | Notes |
|---|---|---|---|
| (populated by research) | | | |

---

## Competitors to Research Next

| Domain | Priority | Reason |
|---|---|---|
| (from config) | | |

---

## Data Sources

All raw data is stored in `data/seedrank.db`:
- `competitor_keywords` table — keywords per competitor with rank, volume, KD
- `serp_competitor_visibility` table — cross-keyword domain visibility

Query examples:
```sql
-- Top-ranking keywords for a competitor
SELECT keyword, rank, volume, kd FROM competitor_keywords
WHERE competitor_slug = 'competitor-name' AND rank <= 20
ORDER BY volume DESC;

-- Cross-keyword visibility
SELECT domain, keywords_count, avg_position, etv
FROM serp_competitor_visibility
WHERE research_set = 'your-research-set'
ORDER BY rating DESC;
```
"""


def _generate_strategy_templates(workspace: Path) -> None:
    """Create strategy file templates in research/ if they don't already exist."""
    research_dir = workspace / "research"
    research_dir.mkdir(parents=True, exist_ok=True)

    ks_path = research_dir / "keyword-strategy.md"
    if not ks_path.exists():
        ks_path.write_text(_KEYWORD_STRATEGY_TEMPLATE, encoding="utf-8")

    ci_path = research_dir / "competitor-seo-intel.md"
    if not ci_path.exists():
        ci_path.write_text(_COMPETITOR_SEO_INTEL_TEMPLATE, encoding="utf-8")


def _generate_state_yaml() -> dict:
    """Generate initial state.yaml content."""
    return {
        "phase": "research",
        "started_at": datetime.now(UTC).isoformat(),
        "last_session": None,
        "progress": {
            "keywords_fetched": 0,
            "articles_planned": 0,
            "articles_published": 0,
        },
        "next_action": "Run seedrank research keywords to begin keyword research",
    }


def init_cmd(
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Directory to create the workspace in.",
    ),
) -> None:
    """Create a new Seedrank workspace with database and directory structure."""
    workspace = output.resolve()

    seedrank_md = workspace / ".claude" / "seedrank.md"
    if seedrank_md.exists():
        result = (
            console.input(
                "  [yellow]Workspace already exists.[/yellow] Overwrite? [y/N]: "
            )
            .strip()
            .lower()
        )
        if result not in ("y", "yes"):
            raise typer.Exit(0)

    # Create directory structure
    ensure_workspace_dirs(workspace)

    # Initialize database and run migrations
    db_path = get_db_path(workspace)
    init_db(db_path)
    from seedrank.data.db import connect
    from seedrank.data.migrations import migrate_db

    with connect(db_path) as conn:
        migrate_db(conn)
    info(f"Database initialized: {db_path.relative_to(workspace)}")

    # Generate .claude/seedrank.md — requires config for product name + rules
    config_path = workspace / "seedrank.config.yaml"
    cfg = None
    if config_path.exists():
        from seedrank.config.loader import load_config

        cfg = load_config(config_path)

    # Auto-create competitor skeleton profiles
    if cfg and cfg.competitors:
        from seedrank.data.competitors import init_profile

        for comp in cfg.competitors:
            path = init_profile(workspace, comp.slug, comp.name, comp.domain)
            if path.exists():
                info(f"Competitor profile: {comp.slug} ({path.relative_to(workspace)})")

    claude_md = _generate_claude_md(cfg)

    seedrank_md.parent.mkdir(parents=True, exist_ok=True)
    seedrank_md.write_text(claude_md, encoding="utf-8")
    info("Generated .claude/seedrank.md")

    # Create .env.example if it doesn't exist
    env_example = workspace / ".env.example"
    if not env_example.exists():
        env_example.write_text(
            "# DataForSEO — required for keyword research, SERP analysis, competitor commands\n"
            "# Sign up at https://dataforseo.com\n"
            "DATAFORSEO_LOGIN=\n"
            "DATAFORSEO_PASSWORD=\n"
            "\n"
            "# AI model API keys — required for GEO (AI visibility) monitoring\n"
            "# Only set the ones you plan to use\n"
            "\n"
            "# OpenAI (ChatGPT queries) — https://platform.openai.com\n"
            "OPENAI_API_KEY=\n"
            "\n"
            "# Anthropic (Claude queries) — https://console.anthropic.com\n"
            "ANTHROPIC_API_KEY=\n"
            "\n"
            "# Perplexity — https://docs.perplexity.ai\n"
            "PERPLEXITY_API_KEY=\n"
            "\n"
            "# Google Gemini — https://ai.google.dev\n"
            "GEMINI_API_KEY=\n",
            encoding="utf-8",
        )
        info("Created .env.example")

    # Generate strategy file templates (if they don't already exist)
    _generate_strategy_templates(workspace)
    info("Strategy file templates ready in research/")

    # Write initial state
    state_path = workspace / "pipeline" / "state.yaml"
    state_path.write_text(
        yaml.dump(_generate_state_yaml(), default_flow_style=False),
        encoding="utf-8",
    )
    info("Created pipeline/state.yaml")

    console.print()
    success("Workspace initialized.")
    console.print()
    console.print("  [bold]Next steps:[/bold]")
    console.print(
        "    1. Create/edit [cyan]seedrank.config.yaml[/cyan] with your product details"
    )
    console.print(
        "    2. Run [cyan]seedrank init[/cyan] again to regenerate"
        " .claude/seedrank.md with your product name"
    )
    console.print(
        '    3. Run [cyan]seedrank research keywords "your keywords"[/cyan]'
        " to start research"
    )
    console.print()
