---
name: plan-calendar
description: Analyze keyword gaps and research data, then build or update the content calendar with prioritized article topics. Use when you need to decide what to write next.
argument-hint: [count]
allowed-tools: Bash, Read, Grep, Glob, Write
---

# Plan Content Calendar

Analyze research data and build a prioritized content calendar. Target: **$ARGUMENTS** articles (default to 10 if not specified).

## Step 1: Read strategic context

**Before touching the database, read existing intelligence:**

1. Check if `research/keyword-strategy.md` exists — read it for keyword targeting tiers, difficulty assessments, and identified gaps
2. Check if `research/competitor-seo-intel.md` exists — read it for competitor content strategies and keyword opportunities

These files capture the "so what" narrative from previous research sessions. Use them to inform prioritization — e.g., a keyword gap identified as "wide open, no competitor owns this" should score higher than raw volume alone would suggest.

## Step 2: Understand current state

Check what we already have:

```
seedrank status
seedrank data articles --json
seedrank data calendar --json
```

Note:
- How many articles are already registered (and their statuses)
- What's already in the calendar
- What topics/keywords are already covered

## Step 3: Identify opportunities

Pull the gap analysis and keyword data:

```
seedrank data gaps --json
seedrank data keywords --json
```

From the gaps data, identify keywords where:
1. Competitors rank and we don't have content
2. Search volume is meaningful (> 50/month)
3. Keyword difficulty is achievable (< 60 KD)

From the keyword data, find additional opportunities:
- High-volume keywords not yet assigned to any article
- Clusters of related keywords that could be targeted by a single article

## Step 4: Read the config for context

```
cat seedrank.config.yaml
```

Consider:
- **Personas**: Which topics serve which persona? Prioritize topics that serve your highest-value personas.
- **Competitors**: Which competitor gaps are most strategically important?
- **Content types**: Match topics to the right content type (comparison, guide, blog post).
- **Positioning**: Use `positioning_against` to understand which comparisons matter most.

## Step 5: Design the article plan

For each recommended article, determine:
- **Slug**: URL-friendly identifier
- **Title concept**: Working title (doesn't need to be final)
- **Content type**: comparison, guide, blog, etc.
- **Primary keywords**: 1-3 target keywords from the database
- **Rationale**: Why this article, why now (volume, gap, strategic value)

Group articles into tiers:
- **Tier 1 (write first)**: High volume + low KD + competitor gap — maximum opportunity
- **Tier 2 (write next)**: Good volume or strategic value, moderate difficulty
- **Tier 3 (backlog)**: Lower priority but worth planning

## Step 6: Add to calendar

For each Tier 1 and Tier 2 article:

```
seedrank calendar add <slug> --keywords "<k1, k2, k3>"
```

The CLI auto-computes a priority score based on volume, KD, gap bonus, and GSC opportunity. Let it calculate — only override with `--priority` if you have a strong strategic reason.

## Step 7: Show the plan

Display the final calendar:

```
seedrank calendar next --count <total> --json
```

Then present a human-readable summary:

### Content Calendar

| Priority | Slug | Keywords | Type | Rationale |
|----------|------|----------|------|-----------|
| 1 | ... | ... | ... | ... |

### Next steps
- Which article to write first and why
- Any research gaps that need filling before writing
- Briefs to create (suggest running `/write-article` for the top item)

## Important

- Don't add articles to the calendar that duplicate existing content. Check `seedrank data articles --json` first.
- Don't guess keyword metrics. Only use data from `seedrank data keywords --json` and `seedrank data gaps --json`.
- If there isn't enough research data to make informed decisions, say so and recommend running `/research-session` first.
- Quality over quantity. 5 well-targeted articles beat 20 random ones.
- Consider the full funnel: comparison articles capture bottom-of-funnel searchers, guides capture mid-funnel, blog posts capture top-of-funnel. A healthy calendar has a mix.
