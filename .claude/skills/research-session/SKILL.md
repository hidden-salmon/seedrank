---
name: research-session
description: Run a full keyword research session — discover questions, fetch keyword data, analyze competitors, identify gaps, and summarize findings. Use when starting research on a new topic or refreshing existing data.
argument-hint: <seed-keywords>
allowed-tools: Bash, Read, Grep, Glob, Write, Edit, Agent
---

# Research Session

Run a structured research session for: **$ARGUMENTS**

## Before you start

**Read existing intelligence first** to avoid duplicate work and build on prior findings:

1. Check if `research/keyword-strategy.md` exists — read it for existing keyword analysis, SERP landscape, and targeting decisions
2. Check if `research/competitor-seo-intel.md` exists — read it for known competitor strategies, traffic sources, and identified gaps
3. Compare your seed keywords against what's already documented. Focus new research on unknowns.

Then load session context:

```
seedrank session start
seedrank status
```

Review the output. Note how many keywords, questions, and articles already exist so you can report what's new at the end.

## Phase 1: Question Discovery

Think about which personas this topic serves and what they'd literally type into Google or ChatGPT.

Generate 5-10 candidate questions per relevant persona mentally, then validate with real data.

Run question discovery against the topic:

```
seedrank research questions "$ARGUMENTS"
```

Then run with a second AI provider for another perspective:

```
seedrank research questions "$ARGUMENTS" --provider chatgpt
```

Review what was discovered:

```
seedrank data questions --json
```

Note which questions are validated by real search data (appeared in PAA or AI responses). These are your highest-confidence content targets.

## Phase 2: Keyword Research

Fetch keyword metrics for the seed keywords.

```
seedrank research keywords "$ARGUMENTS"
```

Then expand each seed keyword to discover related terms.

```
seedrank research expand "<keyword>"
```

Run `expand` for each distinct seed keyword (split by comma from the arguments).

## Phase 3: Competitor Analysis

Read `seedrank.config.yaml` to get competitor domains. For each tier-1 competitor, fetch their keyword data if not already in the database.

```
seedrank research competitors <domain> --limit 200
```

Only run this for competitors that haven't been researched yet or whose data is stale.

Also check competitor data freshness:

```
seedrank competitors freshness
```

Flag any stale competitor profiles — these need verification before writing content that references them.

## Phase 4: Gap Analysis

Identify opportunities — keywords competitors rank for that we don't cover, and questions we've discovered but haven't answered.

```
seedrank data gaps --json
seedrank data keywords --json
seedrank data questions --status new --json
```

Synthesize keyword gaps AND question gaps together.

## Phase 5: Synthesis

Produce a clear summary covering:

1. **New questions discovered** — how many, from which sources (PAA, Perplexity, ChatGPT)
2. **Top keyword opportunities** — the 10 highest-value keyword gaps (high volume, low KD, competitors rank)
3. **Question-to-article mapping** — suggest which discovered questions map to which article topics
4. **Keyword clusters** — group related keywords by topic/intent
5. **Quick wins** — keywords with volume > 100, KD < 30 that competitors rank for
6. **Competitor data freshness** — which competitor profiles are stale and need updating

Present the analysis in a clear table format. Be specific — include actual volume, KD, and competitor coverage numbers.

Write a session summary to `decisions/research-session-<date>.md`.

## Phase 6: Update Strategy Files

After synthesizing findings, update the living strategy documents:

**If `research/keyword-strategy.md` exists:**
- Move the current "Latest snapshot" section to a dated history entry
- Write a new "Latest snapshot" with updated keyword tiers, SERP landscape changes, and new gaps identified
- Add a changelog entry at the top

**If it doesn't exist yet, create it** with sections for:
- Keyword targeting tiers (Tier 1: easy wins KD < 15, Tier 2: achievable KD 15-45, Tier 3: hard KD > 45)
- SERP landscape — who dominates across your target keywords
- Keyword gaps identified — content opportunities from competitor and SERP analysis
- Search trends — which keywords are growing or declining

**If `research/competitor-seo-intel.md` exists:**
- Update any competitor sections with new data (move old snapshot to history)
- Add new competitors discovered during research

**If it doesn't exist yet, create it** with per-competitor sections covering:
- Domain overview (ranked keywords, traffic, top positions)
- Content strategy (what type of content drives their traffic)
- Key keywords they rank for
- What your product can learn from their approach

This is the narrative "so what" layer on top of the raw database numbers. The strategy files ensure insights persist across sessions.

## Phase 7: Wrap up

Validate the research quality.

```
seedrank validate research
```

End the session with a concise summary of what was accomplished.

```
seedrank session end "<summary of questions discovered, keywords researched, gaps found, recommendations>"
```

## Important

- Do NOT make up keyword data. Only report what the CLI returns.
- If DataForSEO credentials are missing or a command fails, tell the user clearly and suggest how to fix it.
- If the database is empty (first run), say so and focus on building the initial keyword set.
- Keep the analysis grounded in data. Numbers, not adjectives.
- Question discovery is the NEW first step — it reframes research around what developers actually ask, not just keyword volume.
