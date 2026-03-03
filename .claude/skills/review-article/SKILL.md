---
name: review-article
description: 9-dimension audit of an article — question coverage, fact-check, product accuracy, legal tiers, citability, cross-linking, structure, cross-batch consistency, and developer sniff test. Use when you need to review an article before publishing.
argument-hint: <path-to-article>
allowed-tools: Bash, Read, Grep, Glob, Edit
---

# Review Article — 9-Dimension Audit

Perform a comprehensive 9-dimension review of: **$ARGUMENTS**

A page can pass every technical check and still be bad content. This audit catches both.

## Step 1: Run automated validation

```
seedrank validate article $ARGUMENTS --json
```

Parse the JSON output. Separate issues by type: legal RED/YELLOW tiers, citability C1-C5, structural, voice.

## Step 2: Read the article

Read the full article content. Then evaluate all 9 dimensions:

## Dimension 1: Question Coverage

Get the article's slug from its path or filename. Check assigned questions:

```
seedrank data questions --slug <slug> --json
```

For each assigned question:
- Is it answered in the article?
- Where in the page? (heading, paragraph, FAQ)
- Is the answer direct (first sentence) or buried?

**FAIL criteria**: Primary question not in lead paragraph.

## Dimension 2: Fact-Check

Extract EVERY factual competitor claim from the article. For each claim:

Read the competitor's JSON profile:

```
cat data/competitors/<slug>.json
```

Check:
- Does the number match the JSON profile?
- Is the claim dated with "(as of [Month Year])"?
- Is it attributed with a source link?

Run freshness check:

```
seedrank competitors freshness
```

**FAIL criteria**: Any claim that contradicts the JSON profile or uses stale data.

## Dimension 3: Product Accuracy

Read `seedrank.config.yaml` and cross-reference every claim about the own product against `product.features[]`.

Check feature status:
- **LIVE**: Can be stated as current capability
- **IN_DEVELOPMENT**: Must say "currently in development" or similar
- **PLANNED**: Must say "planned" — cannot imply availability
- **EARLY_ACCESS**: Must note limited availability

**FAIL criteria**: Claiming a planned or in-development feature is generally available.

## Dimension 4: Legal RED Tier

From the `seedrank validate article` output, check for RED tier violations:
- Multiplier claims ("3x cheaper", "10x faster")
- Disparaging language near competitor names ("limited", "basic", "outdated")
- Unhedged exclusivity ("the only platform that..." without "to our knowledge")
- Performance claims without benchmarks ("faster than" without measured data)

**FAIL criteria**: Any RED tier issue. Must fix before publish.

## Dimension 5: GEO Citability

From the validation output, check C1-C5:
- **C1**: Are all pricing and competitor facts dated with "(as of [date])"?
- **C2**: Does comparison/listicle content have structured comparison tables?
- **C3**: Is there an FAQ section?
- **C4**: Is the first sentence after each H2 a direct answer (not transitional filler)?
- **C5**: Are there specific numbers (not vague claims like "affordable" or "fast")?

Also manually verify:
- FAQ questions match real AI queries (not manufactured SEO phrases)
- Comparison tables have specific dated numbers

## Dimension 6: Cross-Linking

```
seedrank articles crosslinks <slug> --direction both --json
```

Check:
- Are 3-5 outgoing internal links present?
- Are there 2+ published articles that should link TO this one?
- Flag missing high-relevance links

## Dimension 7: Technical/Structure

From the validation output and manual reading:
- Word count meets content type minimum
- Heading hierarchy valid (no skipped levels)
- Meta description present in frontmatter
- Image alt text present on all images
- No structural issues from automated validation

## Dimension 8: Cross-Batch Consistency

If other articles reference the same competitors, verify they use the same numbers.

Search for competitor names across the content directory:

```
grep -r "<competitor name>" content/ --include="*.md" --include="*.mdx" -l
```

For each file found, spot-check key numbers (pricing, region counts, feature claims). Flag any contradictions — e.g., Article A says "4 regions" and this article says "5 regions".

## Dimension 9: Developer Sniff Test

Read the entire article as the target persona. Ask yourself:
- Would I trust this?
- Would I share it with a colleague?
- Did I get my answer in the first 30 seconds?
- Does it try too hard to sell?
- Is there anything I'd have to Google after reading this?
- If a competitor read this, would they feel misrepresented?

This is subjective but critical. Technical accuracy without readability is useless.

## Output: Structured Audit Report

Produce a structured report with this format:

### Verdict: PASS / PASS WITH FIXES / FAIL

### Summary
2-3 sentence overall assessment.

### Scores by Dimension
| Dimension | Status | Issues |
|-----------|--------|--------|
| 1. Question Coverage | PASS/FAIL | count |
| 2. Fact-Check | PASS/FAIL | count |
| 3. Product Accuracy | PASS/FAIL | count |
| 4. Legal RED Tier | PASS/FAIL | count |
| 5. GEO Citability | X/5 | count |
| 6. Cross-Linking | PASS/WARN | count |
| 7. Technical/Structure | PASS/WARN | count |
| 8. Cross-Batch Consistency | PASS/WARN | count |
| 9. Developer Sniff Test | PASS/WARN | notes |

### Critical Issues (must fix)
Numbered list with exact text, location, and how to fix.

### Minor Issues (fix if time)
Numbered list of suggestions.

## Important

- Be direct. If the article has problems, say so clearly.
- Quote specific text when pointing out issues.
- Distinguish between blocking issues (must fix) and suggestions.
- Do NOT rewrite the article. Your job is to review, not edit. Only fix minor issues (typos, banned words) if you're confident in the fix.
- A FAIL verdict means the article cannot be published as-is. Be clear about what must change.
