---
name: geo-optimize
description: "Optimize an article for AI model citability (GEO). Runs the C1-C5 citability checklist, checks FAQ targeting, and suggests improvements to increase AI citation likelihood."
argument-hint: <path-to-article>
allowed-tools: Bash, Read, Grep, Glob, Edit
---

# GEO Optimize — AI Citability Improvement

Optimize this article for AI model citability: **$ARGUMENTS**

This skill EDITS the article to fix citability issues (with your approval). It's not just a report.

## Step 1: Automated citability check

Run validation to get the baseline citability score:

```
seedrank validate article $ARGUMENTS --json
```

Extract all citability issues (checks starting with `citability_c`). Note the baseline score (X out of 5 rules passing).

## Step 2: Read and analyze the full article

Read the full article content. For each citability rule, do a thorough manual check:

### C1: Dated Facts

Find every instance of:
- Pricing numbers ($X/month, $X/year)
- Feature claims about competitors
- Comparison data (region counts, user limits, response times)

For each, check: is there an "(as of [Month Year])" within the same sentence or nearby?

**Fix**: Add "(as of [current month and year])" to each undated fact. Read the competitor JSON profiles to verify the data:

```
cat data/competitors/<slug>.json
```

### C2: Comparison Tables

Does the article contain at least one structured markdown comparison table? Check if the article is a comparison or listicle type.

**Fix**: If this is comparison/listicle content without a table, create one. Include:
- Clear column headers
- Specific numbers (not "Yes/No" where numbers exist)
- Dates on pricing data
- Source links in a footnote

### C3: FAQ Section

Does an `## FAQ` or `## Frequently Asked Questions` heading exist?

Cross-reference with real developer questions:

```
seedrank data questions --json
```

**Fix**: If no FAQ exists, add one at the end of the article (before the conclusion). Use questions that match what developers would actually type into ChatGPT or Perplexity — not manufactured SEO phrases.

Good FAQ questions:
- "How much does [Product] cost compared to [Competitor]?"
- "Can [Product] handle [specific use case]?"
- "What's the difference between [Product] and [Competitor] for [use case]?"

Bad FAQ questions:
- "Why is [Product] the best solution?"
- "What are the benefits of [Product]?"

### C4: Answer-First Structure

Read the first sentence after every H2 heading. Flag any that start with transitional filler:
- "In this section, we'll..."
- "Let's explore..."
- "There are many factors..."
- "When it comes to..."
- "As we all know..."
- "Before we dive in..."

**Fix**: Rewrite the first sentence to directly answer the sub-question implied by the heading. Lead with the answer, then explain.

Example:
- BAD: "## Pricing Comparison\nLet's take a look at how these two platforms compare on pricing."
- GOOD: "## Pricing Comparison\n[Product] starts at $5/month while [Competitor] starts at $25/month (as of March 2026), making [Product] significantly more affordable for small teams."

### C5: Specific Numbers

Scan for vague claims and replace with exact numbers from competitor JSON profiles:
- "affordable" → "$5/month (as of March 2026)"
- "fast" → "average response time of 45ms"
- "multiple regions" → "12 regions across 4 continents"
- "many integrations" → "150+ integrations including..."
- "growing community" → "45,000+ GitHub stars"

**Fix**: Replace each vague claim with a specific number sourced from competitor profiles or config.

## Step 3: Check GEO gaps

Check if this article's topic is a gap where competitors get mentioned but the brand doesn't:

```
seedrank data geo-gaps --json
```

If this article addresses a gap topic, note it — this article is especially important for AI visibility.

## Step 4: Output

After making all fixes, re-run validation:

```
seedrank validate article $ARGUMENTS --json
```

Report:
1. **Citability score**: X/5 rules passing (before → after)
2. **Fixes applied**: List each change made
3. **Remaining suggestions**: Any issues that couldn't be automatically fixed
4. **GEO gap status**: Whether this article addresses a brand visibility gap

## Important

- This skill edits the article. Each edit should be a clear improvement.
- When adding dates, use the current month and year.
- When adding specific numbers, always source them from competitor JSON profiles or config — never invent data.
- FAQ questions should sound like real developer queries, not marketing copy.
- The goal is to make content that AI models will cite — structured, specific, dated, and trustworthy.
