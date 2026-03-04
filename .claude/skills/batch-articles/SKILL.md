---
name: batch-articles
description: "Write multiple articles in parallel — each sub-agent researches the topic deeply via web search, then writes with full keyword/competitor/legal context."
argument-hint: <count-or-slugs>
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, Agent, WebSearch, WebFetch
---

# Batch Articles

Write multiple articles in parallel with deep research. Each sub-agent researches its topic via web search, then writes with full context.

**Arguments**: $ARGUMENTS

Parse the arguments:
- If a number (e.g. `3`): pull the top N articles from the content calendar
- If comma-separated slugs (e.g. `mailchimp-vs-convertkit, email-guide`): use those slugs directly
- **Maximum 5 articles per batch.** If more are requested, warn the user and cap at 5.

---

## Phase 1: Gather Shared Context

Collect data that every sub-agent will need. Do this ONCE, not per article.

1. Read `research/keyword-strategy.md` (if it exists) — keyword targets, difficulty tiers, SERP landscape
2. Read `research/competitor-seo-intel.md` (if it exists) — competitor angles and gaps
3. Read `seedrank.config.yaml` — voice rules, legal requirements, product info, personas, content types, banned words, CTA
4. Run: `seedrank data keywords --json` → save as `keywords_data`
5. Run: `seedrank data questions --json` → save as `questions_data`
6. Run: `seedrank competitors freshness` → note any stale competitors (>30 days). If stale, run `seedrank competitors verify <slug>` for each before continuing.
7. Run: `seedrank data articles --json` → save as `articles_data` (for crosslink context)
8. If arguments were a number, run: `seedrank calendar next --count <N> --json` → extract the slugs

Read the write-article skill to extract writing rules:

```
Read .claude/skills/write-article/SKILL.md
```

Extract the content of **Phase 4: Write the Article** (lines 103-169) — these are the canonical writing rules. You will embed them verbatim in each sub-agent prompt.

---

## Phase 2: Build Per-Article Bundles

For each slug, assemble an article bundle:

1. **Calendar entry**: Extract from calendar data — target keywords, priority, content type
2. **Filtered keywords**: From `keywords_data`, filter to this article's target keywords
3. **Filtered questions**: From `questions_data`, filter questions assigned to this slug. If none assigned, include related questions based on the topic.
4. **Competitor profiles**: Read `data/competitors/*.json` for each competitor this article references. Trim to essential fields only:
   - `name`, `tagline`, `pricing` (plans + tiers), `features` (list), `strengths`, `weaknesses`, `last_verified`
   - Drop raw SERP data, keyword data, and other bulk fields
5. **Forward crosslinks**: Run `seedrank articles crosslinks <slug> --direction forward --json`
6. **Brief**: Read `briefs/<slug>.md` if it exists
7. **Content directory**: From config's `content_types`, determine the correct `content_dir` for this article's type

---

## Phase 3: Dispatch Sub-Agents in Parallel

Spawn all sub-agents in a **single message** using multiple `Agent` tool calls. Each agent gets `subagent_type: "general-purpose"`.

**IMPORTANT**: All Agent tool calls MUST be in the same message to run in parallel.

### Sub-agent prompt template

For each article, construct a prompt containing these sections in order:

---

#### Section 1: Research Instructions

```
# Research Phase — Do This FIRST

Before writing anything, deeply research the topic: **[article title/slug]**

Use WebSearch and WebFetch to:
1. Search for the actual subject matter — what real users/developers say about it
2. Read 3-5 top results (docs, blog posts, community discussions, benchmarks)
3. Search for recent developments (last 6 months) on this topic
4. Search for competitor approaches and how they compare
5. Look for real benchmarks, performance data, or user testimonials

Take notes on what you learn. You will use this research to write a deeply informed article — not a generic overview.

Save your research notes (key findings, sources, quotes) — you'll reference them while writing.
```

#### Section 2: Seedrank Data Bundle

Include all of the following, clearly labeled:

```
# Article Data

## Target Keywords
[filtered keywords for this slug]

## Questions to Answer
[filtered questions for this slug]

## Competitor Profiles
[trimmed competitor JSON data]

## Forward Crosslink Targets
[crosslink suggestions — aim for 3-8 internal links]

## Brief
[brief content, or "No brief exists — write based on calendar entry and keywords"]

## Existing Articles (for crosslinks)
[list of existing article slugs/titles for internal linking context]
```

#### Section 3: Writing Rules (from write-article skill)

Embed the extracted Phase 4 writing rules verbatim. Preface with:

```
# Writing Rules — Follow These Exactly

These rules are from the canonical write-article skill. Follow them precisely.

[...Phase 4 content from write-article/SKILL.md...]
```

#### Section 4: AI-Tell Checklist

```
# AI-Tell Avoidance Checklist

While writing, actively avoid these 12 patterns. Self-edit as you write — do not leave these for a later pass.

1. **No tricolons** — never three parallel short sentences with identical structure. Vary sentence length.
2. **No crutch phrases** — delete: "worth noting", "let's dive in", "when it comes to", "at the end of the day", "it's important to note", "the bottom line", "in a nutshell", "here's what you need to know", "in today's [landscape]", "stands out", "really shines", "let's break it down".
3. **Limit date stamps** — 1-3 inline "(as of Month Year)" max. If more needed, add a single "Data last verified: Month Year" note at top.
4. **No self-announcing honesty** — delete: "verified pricing", "honest trade-offs", "to be frank", "the truth is", "let me be real".
5. **No meta-commentary** — delete: "in this section", "as mentioned earlier", "now let's move on to", "this guide breaks down", "we've covered X, now let's look at Y".
6. **Break perfect symmetry** — vary section lengths. Not every H2 should be ~300 words. Some FAQ answers should be 1 sentence, others a paragraph.
7. **No FAQ body repetition** — FAQ answers must add new info or a more direct angle, not rephrase what the body already says.
8. **Show editorial voice** — take genuine stances. "We think X is better for Y because Z." Not "both have their pros and cons."
9. **No gratuitous competitor compliments** — state facts without performative praise. "Railway has a generous free tier" not "Railway is an impressive platform."
10. **No counting before listing** — don't announce "Three things matter here:" — just list them.
11. **No over-explaining basics** — know your audience from the config personas. Don't explain containers to senior devs.
12. **Limit diplomatic hedging** — max one "it depends" per article. Replace hedges with specific recommendations.
```

#### Section 5: Voice, Legal, and Config Rules

```
# Voice and Legal Rules

## Voice
[tone, persona, banned_words, cta_primary from config]

## Legal
[legal requirements from config — disclaimers, comparison article rules]

## Product
[product info from config — features with status, positioning]
```

#### Section 6: Output Instructions

```
# Output Instructions

1. Save the article to: `content/[content_dir]/[slug].mdx`
2. Run validation: `seedrank validate article content/[content_dir]/[slug].mdx`
3. Fix any RED issues. Re-validate until no RED issues remain. YELLOW warnings: fix if straightforward, otherwise note them.
4. Register the article: `seedrank articles register [slug] --title "[title]" --keywords "[k1, k2, ...]" --topics "[t1, t2, ...]"`
5. Update calendar: `seedrank calendar update [slug] --status done`
6. Report back with:
   - File path
   - Word count
   - Validation result (RED/YELLOW/GREEN counts)
   - Research sources used (URLs you read)
   - Questions answered
   - Internal links included
   - Any competitor data gaps
```

---

## Phase 4: Parent Review

After ALL sub-agents complete, perform these review steps:

### 4.1 Verify files exist

For each slug, confirm the article file was created at the expected path.

### 4.2 Re-validate each article

```
seedrank validate article content/<type>/<slug>.mdx
```

### 4.3 Cross-batch consistency check

If multiple articles in this batch mention the same competitor:
- Verify they use the **same pricing numbers**
- Verify they use the **same feature claims**
- Verify dates are consistent
- If inconsistencies found, fix them to match the most recently verified data

### 4.4 Workspace-wide legal validation

```
seedrank validate legal
```

### 4.5 Backward crosslinks

For each new article:
```
seedrank articles crosslinks <slug> --direction backward --json
```

Collect all backward link suggestions — these are existing articles that should now link to the new articles.

### 4.6 Batch Report

Produce a summary table:

```
## Batch Report

| Slug | Status | Words | Legal | Citability | AI Tells | Research Sources |
|------|--------|-------|-------|------------|----------|-----------------|
| slug-1 | done | 2,450 | GREEN | C4/C5 | 1 minor | 4 URLs |
| slug-2 | done | 1,800 | YELLOW (1) | C3/C5 | 0 | 3 URLs |
| slug-3 | FAILED | - | - | - | - | - |
```

Then list:
- **Backward link suggestions**: which existing articles should link to each new article
- **Cross-batch consistency**: any issues found and fixed
- **Legal validation**: workspace-wide result
- **Failed articles**: suggest running `/write-article <slug>` for each

---

## Failure Handling

- If a sub-agent fails (returns an error or doesn't produce an article file):
  - Log it in the batch report as FAILED
  - Suggest running `/write-article <slug>` individually for that article
  - Do NOT retry automatically
- Complete the review for all successful articles regardless of failures
- If ALL sub-agents fail, report the errors and suggest debugging with a single `/write-article <slug>` first

---

## Output

When done, provide:
1. The batch report table (above)
2. Total articles written vs. attempted
3. Backward link suggestions for all new articles
4. Any cross-batch consistency fixes applied
5. Workspace-wide legal validation result
6. Next steps (failed articles to retry, backward links to add)
