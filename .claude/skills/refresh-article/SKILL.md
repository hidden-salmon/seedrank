---
name: refresh-article
description: Identify and refresh a declining or outdated article — analyze decay signals from GSC data, update stale content, re-optimize for SEO/GEO, and re-validate. Use when an article is losing rankings, traffic is declining, or content is outdated.
argument-hint: <slug>
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, Agent
---

# Refresh Article

Refresh the article for slug: **$ARGUMENTS**

## Phase 0: Read Strategic Context

1. Check if `research/keyword-strategy.md` exists — read it for current keyword targeting priorities
2. Check if `research/competitor-seo-intel.md` exists — read it for competitive landscape changes

## Phase 1: Diagnose Decay

Check if we have performance data for this article:

```
seedrank data performance --slug $ARGUMENTS --days 90 --json
```

Check the article against the overall declining list:

```
seedrank data performance --declining --days 60 --json
```

Get the article's current metadata:

```
seedrank data articles --json
```

Read the article file:

```
ls content/**/$ARGUMENTS.mdx 2>/dev/null || ls content/**/$ARGUMENTS.md 2>/dev/null
```

### Decay Assessment

Evaluate these signals from the GSC data:

1. **Traffic trend**: Compare recent 30d vs prior 30d — impressions and clicks
2. **Position drift**: Is average position worsening?
3. **CTR decline**: Same position but fewer clicks = title/description problem
4. **Competitive displacement**: Check if competitors have published newer content on this topic

Rate the decay severity:
- **Mild** (0-20% decline): Minor updates — refresh dates, add a new section
- **Moderate** (20-50% decline): Substantial rewrite — new data, restructure, add FAQ
- **Severe** (50%+ decline): Near-full rewrite — new angle, comprehensive update

### Refresh vs. Rewrite Decision

Choose REFRESH if:
- Core structure and angle are still sound
- Mostly needs updated data, dates, and a few new sections
- Estimated effort: update 30-60% of content

Choose REWRITE if:
- The topic landscape has fundamentally changed
- Competitor content is structured completely differently now
- The article's angle is no longer viable

## Phase 2: Verify Competitor Data

Check freshness of competitor data referenced in the article:

```
seedrank competitors freshness
```

If stale, re-verify:

```
seedrank competitors verify <slug>
```

Read any competitor JSON profiles the article references:

```
cat data/competitors/<slug>.json
```

## Phase 3: Identify Specific Updates

Scan the article for:

1. **Outdated dates** — any "(as of [old date])" that need updating
2. **Stale statistics** — numbers that may have changed
3. **Dead or changed links** — external references that may be broken
4. **Missing topics** — check `seedrank data questions --slug $ARGUMENTS --json` for unanswered questions
5. **Missing keywords** — compare article content against current `seedrank data keywords --json`
6. **Crosslink gaps** — run `seedrank articles crosslinks $ARGUMENTS --direction both --json` for new link opportunities since the article was published

## Phase 4: Refresh the Article

Apply updates following these rules:

### Preserve what works
- Keep the URL, slug, and overall structure if still sound
- Don't change the core angle unless it's a full rewrite
- Maintain existing internal links that are still valid

### Update content
- Replace all outdated dates with current dates
- Update statistics and pricing from verified competitor data
- Add new sections addressing gaps found in Phase 3
- Refresh the introduction — first paragraph should feel current
- Update or add FAQ section with newly discovered questions

### Re-optimize for GEO/AEO
- Ensure answer-first structure on all H2s
- Add comparison tables if missing (citability signal)
- Include specific, dated numbers throughout
- FAQ questions should match what someone would type into ChatGPT/Perplexity

### Internal links
- Add new crosslinks from Phase 3 suggestions
- Remove any links to articles that have been unpublished

## Phase 5: Validate

Run the refreshed article through validation:

```
seedrank validate article content/<type>/$ARGUMENTS.mdx
```

Fix any issues:
- **RED tier**: Must fix before republishing
- **YELLOW tier**: Should fix
- **Citability (C1-C5)**: Ensure all checks pass
- **AI tells**: Run `/qa-ai-tells` if the refresh introduced new AI-sounding content

## Phase 6: Update Metadata

Update the article's status in the database:

```
seedrank articles update $ARGUMENTS --status published
```

Check for backward link opportunities from newer articles:

```
seedrank articles crosslinks $ARGUMENTS --direction backward --json
```

## Output

When done, provide:
1. **Decay diagnosis**: severity level and key signals
2. **Decision**: refresh vs. rewrite (and why)
3. **Changes made**: bullet list of what was updated
4. **Sections added/removed**: structural changes
5. **Updated crosslinks**: new internal links added
6. **Validation result**: pass/warnings
7. **Backward link suggestions**: newer articles that should now link to this refreshed content
8. **Recommended re-check date**: when to evaluate performance again (30-60 days)
