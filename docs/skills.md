# Skills

Skills are slash commands that orchestrate multi-step workflows in Claude Code. They combine multiple Seedrank CLI commands into complete tasks — research, writing, review, monitoring.

Use skills instead of running individual CLI commands. They handle the right order of operations, read strategic context, and validate output.

## Overview

| Skill | When to use |
|---|---|
| `/research-session` | Starting research on a new topic or refreshing existing data |
| `/plan-calendar` | Deciding what to write next |
| `/write-article` | Writing an article from start to finish |
| `/batch-articles` | Writing multiple articles in parallel |
| `/review-article` | Auditing an article before publishing |
| `/refresh-article` | Fixing a declining article using GSC data |
| `/optimize-links` | Improving internal linking after publishing 10+ articles |
| `/generate-schema` | Adding structured data to an article |
| `/geo-optimize` | Making an article more citable by AI models |
| `/qa-ai-tells` | Detecting AI writing patterns |
| `/audit-legal` | Checking legal compliance across all content |
| `/aeo-monitor` | Tracking AI brand visibility over time |

## `/research-session`

**Usage:** `/research-session "email marketing, newsletter tools"`

Runs a full keyword research workflow:

1. Reads existing strategy files to avoid duplicate work
2. Discovers questions people ask (People Also Ask + AI responses)
3. Fetches keyword metrics and expands seed keywords
4. Analyzes competitor keyword rankings
5. Identifies gaps — keywords competitors rank for that you don't cover
6. Synthesizes findings into a summary with clusters and quick wins
7. Updates `research/keyword-strategy.md` and `research/competitor-seo-intel.md`

**Output:** A decision log in `decisions/`, updated strategy files, and a summary of opportunities.

**When to re-run:** When entering a new topic area, when you suspect the competitive landscape has changed, or monthly as a refresh.

## `/plan-calendar`

**Usage:** `/plan-calendar 10`

Analyzes keyword gaps and research data, then builds a prioritized content calendar:

1. Reads strategy files and existing calendar
2. Reviews gaps, keyword clusters, and question data
3. Ranks opportunities by the [priority score](concepts.md#priority-scoring)
4. Adds entries to the content calendar

**Output:** A prioritized list of articles to write, with target keywords and rationale.

## `/write-article`

**Usage:** `/write-article mailchimp-vs-moonbeam`

Writes a complete article through six phases:

1. **Strategic context** — reads keyword strategy and competitor intel
2. **Gather context** — checks calendar, briefs, keywords, questions, config
3. **Verify competitor data** — checks freshness of competitor profiles, updates if stale
4. **Crosslinks** — finds articles to link to
5. **Write** — produces the article following voice, accuracy, legal, and SEO rules
6. **Validate** — runs legal tier checks, citability scoring, and AI-tell detection
7. **Register** — adds to database, updates calendar, generates schema, reports backward links

Key rules enforced during writing:
- Every competitor fact must trace to a `data/competitors/<slug>.json` profile
- All pricing must be dated ("$5/month as of March 2026")
- Only `live` features can be claimed; others must be qualified
- Comparison articles require a disclaimer and "When to choose [Competitor]" section
- Banned words and CTAs from voice config are checked

**Output:** Article file, validation results, crosslinks included, backward link suggestions.

## `/batch-articles`

**Usage:** `/batch-articles 3`

Writes multiple articles in parallel. Each article gets its own sub-agent that runs the full `/write-article` workflow independently. Use this when you have several articles planned and want to produce them faster.

## `/review-article`

**Usage:** `/review-article content/blog/my-article.mdx`

Runs a 10-dimension audit:

1. **Question coverage** — does the article answer the questions it should?
2. **Fact-check** — are claims supported by data?
3. **Product accuracy** — do feature claims match config?
4. **Legal tiers** — RED/YELLOW/GREEN compliance
5. **Citability** — C1-C5 GEO checklist
6. **Cross-linking** — internal link quantity and quality
7. **Structure** — heading hierarchy, word count, meta description
8. **Cross-batch consistency** — does it align with other articles?
9. **Developer sniff test** — would a technical reader trust this?
10. **AI-tell detection** — patterns that make content read as machine-generated

**Output:** Per-dimension pass/fail with specific issues and fix suggestions.

## `/refresh-article`

**Usage:** `/refresh-article declining-slug`

Diagnoses and refreshes a declining article:

1. Pulls GSC performance data to identify decay signals
2. Checks for stale competitor data, outdated pricing, broken links
3. Re-optimizes for current keyword landscape
4. Updates content and re-validates

**When to use:** Monthly, for articles losing rankings or traffic. Use `seedrank data performance --declining` to find candidates.

## `/optimize-links`

**Usage:** `/optimize-links`

Analyzes the full internal link graph:

1. Finds orphan pages (no incoming links)
2. Assesses link distribution across the site
3. Identifies topic cluster gaps
4. Generates a linking plan with specific suggestions

**When to use:** After publishing 10+ articles, or when site architecture needs attention.

## `/generate-schema`

**Usage:** `/generate-schema my-article`

Generates JSON-LD structured data for an article:
- `BlogPosting` / `Article` schema
- `FAQPage` schema (if the article has FAQ content)
- `BreadcrumbList` schema
- `Organization` schema

**Output:** Ready-to-use JSON-LD blocks.

## `/geo-optimize`

**Usage:** `/geo-optimize content/blog/my-article.mdx`

Optimizes an article for AI model citability using the C1-C5 checklist:

- **C1:** Dated facts with specific numbers
- **C2:** Comparison tables with structured data
- **C3:** FAQ section targeting conversational queries
- **C4:** Answer-first structure (direct answers in first sentences)
- **C5:** Specific, quotable statements (not vague claims)

**Output:** Per-criterion score with specific improvement suggestions.

## `/qa-ai-tells`

**Usage:** `/qa-ai-tells content/blog/my-article.mdx`

Thorough scan for AI writing patterns:

- Crutch phrases ("it's worth noting", "at the end of the day")
- Tricolons (three-part lists used excessively)
- Diplomatic hedging ("while X has its merits")
- Meta-commentary ("in this article, we'll explore")
- Gratuitous compliments before criticism
- Counting before listing ("there are three reasons")
- Self-announcing honesty ("frankly", "to be honest")

**Output:** Flagged patterns with line numbers and suggested rewrites.

## `/audit-legal`

**Usage:** `/audit-legal`

Workspace-wide legal compliance audit:

1. Scans all articles for RED/YELLOW tier legal patterns
2. Checks data staleness across competitor profiles
3. Verifies disclaimer presence in comparison content
4. Checks for trademark overuse
5. Produces an actionable report with tier classification

**When to use:** Before publishing a batch of articles, or on a regular schedule.

## `/aeo-monitor`

**Usage:** `/aeo-monitor`

Runs an AI visibility monitoring session:

1. Queries AI models about your key topics
2. Tracks whether your brand is mentioned
3. Compares against competitor mentions
4. Identifies gaps where competitors appear but you don't
5. Tracks trends over time

**When to use:** Weekly or bi-weekly. Results accumulate in the database — use `seedrank data geo-trends` to see mention rates over time.

## Typical Workflow

```
/research-session "email marketing, newsletter tools"   # Research
/plan-calendar 10                                        # Plan
/write-article mailchimp-vs-moonbeam                     # Write
/review-article content/compare/mailchimp-vs-moonbeam.mdx  # Review
/qa-ai-tells content/compare/mailchimp-vs-moonbeam.mdx     # QA
/audit-legal                                             # Legal check
/optimize-links                                          # After 10+ articles
/refresh-article declining-slug                          # Monthly maintenance
/aeo-monitor                                             # Weekly AI visibility
```
