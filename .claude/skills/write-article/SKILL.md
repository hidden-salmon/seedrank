---
name: write-article
description: Write a complete article from brief to finished draft — with keyword targeting, crosslinks, voice compliance, and legal checks. Uses two-pass approach: verify data first, then write. Use when you need to write or draft an article.
argument-hint: <slug>
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, Agent
---

# Write Article

Write a complete article for slug: **$ARGUMENTS**

## Phase 0: Read Strategic Context

Before gathering article-specific data, check the strategic intelligence files for keyword targeting and competitive angles:

1. Check if `research/keyword-strategy.md` exists — read it for which keywords to target on this topic, their difficulty tiers, and SERP landscape
2. Check if `research/competitor-seo-intel.md` exists — read it for what competitors rank for on this topic, what content angles they use, and identified gaps to exploit

Use these insights to inform keyword selection, content angle, and competitive positioning.

## Phase 1: Gather Context

First, understand what this article should be.

Check if this slug is in the content calendar:

```
seedrank calendar next --count 20 --json
```

Check if there's an existing brief:

```
ls briefs/$ARGUMENTS.md 2>/dev/null
```

Get the keyword data for this article's target keywords:

```
seedrank data keywords --json
```

Read the config to understand voice, tone, competitors, and legal requirements:

```
cat seedrank.config.yaml
```

Read competitor JSON profiles for each competitor this article will reference:

```
cat data/competitors/<slug>.json
```

Read the question map — what questions should this article answer:

```
seedrank data questions --slug $ARGUMENTS --json
```

If no questions are assigned, check for related questions:

```
seedrank data questions --json
```

If a brief exists in `briefs/`, read it. If not, create the article based on the calendar entry's target keywords and discovered questions.

## Phase 2: Verify Competitor Data (Pass 1)

**Do NOT write yet.** First verify that all competitor data is fresh and accurate.

Check freshness for competitors this article references:

```
seedrank competitors freshness
```

If any competitor is stale (>30 days since last_verified):

```
seedrank competitors verify <slug>
```

Read the verification output. Compare against the JSON profile. Update the JSON if any data has changed.

This is Pass 1 — data verification only. Writing happens in Phase 4.

## Phase 3: Crosslinks

Find articles to link TO from this article:

```
seedrank articles crosslinks $ARGUMENTS --direction forward --json
```

Note the top suggestions. Aim for 3-8 internal links depending on article length.

Check content types to determine the correct output directory:

Read the `content_types` section of `seedrank.config.yaml` to find the correct `content_dir`.

## Phase 4: Write the Article

Now write, following these enhanced rules:

### Question-first approach
- State the primary question this article answers
- Answer it in the first 1-2 sentences
- If questions are assigned from the questions table, ensure each is addressed

### Answer-first H2s
- First sentence after every H2 must directly answer a sub-question
- Never start with transitional filler like "Let's explore...", "There are many factors...", "In this section...", "When it comes to..."
- Instead, lead with the direct answer, then explain

### Competitor data from JSON only
- Every competitor fact MUST trace to `data/competitors/<slug>.json`
- Never invent pricing, region counts, or feature claims
- If the JSON profile is missing data you need, note it as a gap — don't make it up

### Comparison tables
- Required for comparison and listicle content types
- Must include specific, dated numbers
- Format as markdown tables with clear column headers

### "When to choose [Competitor]" section
- Required for comparison and alternative content types
- Acknowledge competitor strengths honestly
- This is both legally protective and trust-building

### FAQ targeting AI queries
- FAQ questions should match what someone would type into ChatGPT/Perplexity
- Not manufactured SEO phrases
- Cross-reference with `seedrank data questions --json` for real questions

### Dated facts
- Every pricing number and feature comparison must include "(as of [Month Year])"
- This is both a legal requirement and a citability signal

### Specific numbers
- Exact pricing, region counts, deploy times — no vague claims
- "Affordable" → "$5/month (as of March 2026)"
- "Multiple regions" → "12 regions across 4 continents (as of March 2026)"

### Voice
- Follow the tone defined in the config
- Never use words from the `voice.banned_words` list
- Use the primary CTA from `voice.cta_primary` when appropriate

### Accuracy
- Only claim features with status "live" in the config
- Features with status "in_development", "planned", or "early_access" must be qualified
- All competitor claims must link to their source

### Comparison articles (if applicable)
- Include editorial disclaimer (check config for template)
- Add "Last verified: [today's date]"
- Present competitors fairly
- Every pricing claim needs plan tier, billing frequency, source URL

### SEO
- Primary keyword in H1, first paragraph, and at least one H2
- Write a meta description (150-160 chars) with the primary keyword

### Internal links
- Weave in crosslink targets from Phase 3 using descriptive anchor text
- Don't force links — only link when it adds genuine value

Save the article to the appropriate content directory.

## Phase 5: Validate

Run the article through validation — includes legal tiers, citability checks, AND AI-tell detection:

```
seedrank validate article content/<type>/$ARGUMENTS.mdx
```

Fix any issues:
- **RED tier** (errors): multiplier claims, disparaging language, unhedged exclusivity — must fix
- **YELLOW tier** (warnings): undated pricing, unattributed stats — should fix
- **Citability** (C1-C5): dated facts, comparison tables, FAQ section, answer-first structure, specific numbers
- **AI tells** (`ai_tell_*`): crutch phrases, meta-commentary, tricolons, gratuitous compliments, diplomatic hedging, excessive date stamps, counting before listing, self-announcing honesty — fix to avoid machine-generated tone

Re-validate until clean. For a deeper AI-tell audit, run `/qa-ai-tells content/<type>/$ARGUMENTS.mdx`.

## Phase 6: Register and Update

Register the article in the database:

```
seedrank articles register $ARGUMENTS --title "<title>" --keywords "<k1, k2>" --topics "<t1, t2>"
```

Update the calendar status:

```
seedrank calendar update $ARGUMENTS --status done
```

Generate structured data for the article:

```
seedrank articles schema $ARGUMENTS --json
```

Include the JSON-LD in the article output or note it for the user to add to their site template.

Check for backward links:

```
seedrank articles crosslinks $ARGUMENTS --direction backward --json
```

Report the backward link suggestions so the user knows which existing articles to update.

## Output

When done, provide:
1. The file path of the written article
2. Word count
3. Validation result (pass/warnings), including legal tier and citability status
4. List of internal links included
5. Questions answered (from the questions table)
6. Backward link suggestions (articles that should link to this one)
7. Any competitor data gaps found during verification
