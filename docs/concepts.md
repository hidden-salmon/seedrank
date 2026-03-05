# Concepts

How Seedrank is structured, how data flows, and how decisions are made.

## Architecture

Seedrank follows a simple principle: **Claude Code is the brain, Seedrank is the hands.**

Claude Code reads context, makes decisions, and orchestrates. Seedrank fetches data, stores it, computes scores, and validates output. Neither works well alone — together they form a complete SEO workflow.

```
Claude Code (reads .claude/seedrank.md, makes decisions)
    |
    |-- seedrank research ...     --> External APIs --> SQLite
    |-- seedrank data ...         --> SQLite --> stdout (Claude reads)
    |-- seedrank articles ...     --> SQLite --> stdout
    |-- seedrank validate ...     --> File system --> stdout
    '-- seedrank session ...      --> YAML state files
```

## Three-Layer Data Model

Raw numbers aren't enough for good SEO decisions. Seedrank uses three layers:

### Layer 1: Raw Data (SQLite)

`data/seedrank.db` stores everything queryable: keyword metrics, SERP snapshots, competitor rankings, article metadata, GSC performance, GEO query results, and API costs.

Every `seedrank research` command writes here. Every `seedrank data` command reads from here. You never edit the database manually.

### Layer 2: Strategic Intelligence (Markdown)

The `research/` directory contains living strategy documents:

- **`keyword-strategy.md`** — keyword tiers, SERP landscape analysis, targeting rationale
- **`competitor-seo-intel.md`** — competitor strategies, traffic sources, content gaps

These files capture the *analysis* — the "so what" that raw numbers don't convey. "Keyword X has KD 1 and nobody owns it" is an insight that lives here, not in the database.

Both files follow a living document pattern:
- Fixed section structure (Tier 1 keywords, Tier 2, etc.)
- Timestamped snapshots under each section
- When updating, the old snapshot moves to a dated history entry
- Changelog at the top tracks what changed and when

The `/research-session` skill creates and updates these files automatically.

### Layer 3: Action Items (Calendar)

The `content_calendar` table is where analysis becomes action. Each entry has a slug, target keywords, and a computed priority score. The `/plan-calendar` skill populates it from gap analysis; `/write-article` consumes it.

## Priority Scoring

When you add an article to the calendar without a manual priority, Seedrank computes:

```
score = (avg_volume / 1000) * 0.4        # search demand (capped at 1.0)
      + (1 - avg_kd / 100) * 0.3         # keyword difficulty (easier = higher)
      + content_gap_bonus * 0.2           # competitors rank, you don't
      + gsc_opportunity * 0.1             # you're already close to page 1
```

Higher score = write this first. The formula balances demand, difficulty, competitive gaps, and existing momentum.

## Crosslink Engine

Seedrank suggests internal links based on keyword and topic overlap between articles.

**Forward links** — articles to link TO while writing:
- Compares the target article's keywords/topics against all published articles
- Score = `topic_overlap * 2 + keyword_overlap`
- Returns top 10 matches

**Backward links** — existing articles that should link TO your new article:
- Same scoring, excludes articles that already have the link
- Run after publishing to find articles that need updating

## Competitor Profiles

Competitor data lives in `data/competitors/<slug>.json`. These JSON files store pricing, features, regions, and source URLs — everything needed for accurate comparison content.

Key rules:
- Every fact in an article must trace back to a competitor JSON profile
- Profiles have a `last_verified` date — stale profiles get flagged
- The `/write-article` skill verifies freshness before writing
- `seedrank competitors verify <slug>` fetches live data and updates the profile

## Legal Compliance

Seedrank validates content against legal risk patterns, organized into tiers:

| Tier | Severity | Examples |
|---|---|---|
| RED | Must fix | Multiplier claims ("10x faster"), disparaging language, unhedged exclusivity ("the only") |
| YELLOW | Should fix | Undated pricing, unattributed statistics, missing methodology section |
| GREEN | Clean | Properly sourced, dated, and hedged content |

Additional checks:
- Trademark mention frequency (configurable threshold)
- EU unfair competition law patterns (optional)
- Required disclaimer presence in comparison content
- "When to choose [Competitor]" section in comparison articles

## GEO (Generative Engine Optimization)

GEO monitoring tracks how AI models (ChatGPT, Claude, Perplexity, Gemini) mention your brand. Seedrank sends queries to each provider and analyzes responses for:

- Whether your brand is mentioned
- Sentiment (positive / neutral / negative)
- Which competitors are mentioned instead
- Citations and URLs referenced

The `/aeo-monitor` skill runs this periodically. `seedrank data geo-trends` shows mention rates over time, and `seedrank data geo-gaps` reveals queries where competitors appear but you don't.

## AI-Tell Detection

Content written by AI often has detectable patterns that reduce trust. Seedrank checks for:

- **Crutch phrases** — "it's worth noting", "at the end of the day"
- **Tricolons** — three-part lists used excessively ("fast, reliable, and scalable")
- **Diplomatic hedging** — "while X has its merits" before every criticism
- **Meta-commentary** — "in this article, we'll explore"
- **Gratuitous compliments** — praising competitors excessively before comparing
- **Counting before listing** — "there are three key reasons" then listing them

The `/qa-ai-tells` skill runs a thorough check. The `/write-article` skill includes a lighter version in its validation phase.

## Sessions

Sessions track work across time. `seedrank session start` loads context from the last session so Claude Code knows what happened previously. `seedrank session end "summary"` writes a log with what was accomplished.

Session logs live in `sessions/` with timestamped filenames. They're useful for continuity when returning to a project after days or weeks.
