---
name: audit-legal
description: Run a full legal compliance audit with RED/YELLOW/GREEN tier classification — check data staleness, scan all articles for legal risk patterns, verify disclaimer appropriateness, and produce an actionable report. Use before publishing a batch or on a regular schedule.
allowed-tools: Bash, Read, Grep, Glob, Write
---

# Legal Compliance Audit — Tiered Scanning

Run a comprehensive legal compliance audit across the entire workspace with RED/YELLOW/GREEN tier classification.

## Step 1: Workspace-level checks

Run the built-in legal validator:

```
seedrank validate legal
```

Note all warnings — stale data, missing config fields.

Check competitor data freshness:

```
seedrank competitors freshness
```

List stale competitor profiles — these represent legal risk (outdated claims in articles).

## Step 2: Find all content files

Locate all article files:

```
find content/ -name "*.md" -o -name "*.mdx" 2>/dev/null
```

Also check registered articles:

```
seedrank data articles --json
```

## Step 3: Tiered validation of each article

For every article file found, run validation with JSON output:

```
seedrank validate article <path> --json
```

Parse the output and classify legal issues by tier:

### RED Tier (errors — MUST fix before publishing)
- `legal_red_multiplier` — Multiplier claims ("3x cheaper", "10x faster")
- `legal_red_disparaging` — Disparaging language near competitor names ("limited", "basic", "outdated", "clunky")
- `legal_red_exclusivity` — Unhedged exclusivity ("the only platform that..." without "to our knowledge")
- `legal_red_performance` — Performance claims without benchmarks ("faster than" without measured data)
- `banned_claim` — Claims from the banned_claims list in config
- Claims about competitor future plans (never claim what competitors will or won't do)

### YELLOW Tier (warnings — SHOULD fix)
- `legal_yellow_unattributed_stat` — Unattributed statistics ("100,000 users" without source)
- `legal_yellow_unscoped_best` — Unscoped "best for" claims
- `legal_yellow_undated_pricing` — Pricing without "as of [date]"
- `unsourced_claim` — Competitor claims without source URLs
- `last_verified` — Missing last-verified date on comparison articles
- Plan descriptions using "limited" or "basic" near competitor names

### GREEN (safe patterns — note as positive)
- Dated comparisons with "(as of [Month Year])"
- Hedged exclusivity with "to our knowledge"
- "When to choose [Competitor]" sections
- Attributed statistics with source links
- Fair competitor representations

## Step 4: Disclaimer template appropriateness

Read `seedrank.config.yaml` to get the disclaimer templates.

For each article, check which disclaimer type is needed and whether it's present:
- **Comparison pages** → need `comparison` disclaimer
- **Pages with pricing data** ($X amounts) → need `pricing` disclaimer
- **Pages with feature comparison tables** → need `feature` disclaimer
- **Listicle/ranking pages** → need `listicle` disclaimer
- **Pages with exclusivity claims** → need `exclusivity` disclaimer
- **"Alternative to X" pages** → need `alternative` disclaimer
- **Pages citing competitor statistics** → need `statistics` disclaimer

Flag articles that need a specific disclaimer type but don't have one.

## Step 5: Five-question test

For each comparison claim in each article, apply this test:

1. **Fact or opinion?** — If fact, it must be verifiable. If opinion, it must be clearly labeled as such.
2. **Independently verifiable?** — Can a reader verify this claim from the cited source?
3. **Dated?** — Is there an "as of [date]" marker?
4. **Neutral tone?** — Does the language avoid disparagement?
5. **Shows both sides?** — Is the competitor's perspective acknowledged?

A claim that fails 2+ questions is a YELLOW tier risk. Failing on #1 (presenting opinion as fact) or #2 (unverifiable) makes it RED.

## Step 6: Produce the audit report

Write the report to `decisions/legal-audit-<date>.md`:

```markdown
# Legal Compliance Audit — <date>

## Summary
X RED issues (must fix immediately), Y YELLOW issues (should address), Z GREEN patterns found.
Overall risk level: HIGH / MEDIUM / LOW.

## RED Tier Issues (must fix before publishing)
For each:
1. **File**: <path>
   **Issue**: <description>
   **Text**: "<exact quote>"
   **Fix**: <suggested rewrite>

## YELLOW Tier Issues (should address)
For each:
1. **File**: <path>
   **Issue**: <description>
   **Suggestion**: <how to fix>

## GREEN Patterns (positive)
List of good legal practices found across articles.

## Disclaimer Status
| Article | Needs | Has | Status |
|---------|-------|-----|--------|
| slug    | comparison, pricing | comparison | MISSING: pricing |

## Data Freshness Report
| Competitor | Last Verified | Days Old | Status |
|------------|--------------|----------|--------|
| slug       | 2026-01-15   | 47       | STALE  |

## The Competitor Lawyer Test
For each RED tier issue, answer: "Could a competitor's lawyer argue this is false or misleading?"
If yes, it must be fixed regardless of intent.

## Recommendations
Concrete next steps to resolve all issues, ordered by legal risk.
```

## Important

- This is a compliance audit, not a content review. Focus on legal risk, not writing quality.
- Be conservative. If something could be a legal risk, flag it.
- RED tier issues are blocking — the article should not be published until they're fixed.
- Always note the specific legal basis: Lanham Act (US), FTC guidelines, EU Directive 2006/114/EC.
- The competitor lawyer test is the ultimate filter: if their lawyer could use it against you, fix it.
