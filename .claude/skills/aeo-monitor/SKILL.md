---
name: aeo-monitor
description: "Run a periodic AI visibility monitoring session — query AI models about key topics, track brand mentions over time, identify gaps where competitors appear but we don't. Use weekly or bi-weekly."
allowed-tools: Bash, Read, Grep, Glob, Write
---

# AEO Monitor — AI Visibility Tracking

Run a periodic AI visibility monitoring session.

## Step 1: Establish baseline

Read config for AI models and competitors:

```
cat seedrank.config.yaml
```

Check current baseline:

```
seedrank data geo-trends --json
```

Note the most recent week's mention rate and competitor leaderboard.

## Step 2: Define monitoring queries

Read answered questions — these are queries we should appear in:

```
seedrank data questions --status answered --json
```

Also get top keywords:

```
seedrank data keywords --sort volume --limit 20 --json
```

Create a YAML queries file with 15-25 developer-phrased questions (not keyword strings). These should be:
- Questions a developer would type into ChatGPT, Perplexity, or Google
- Related to your product's core use cases
- Include competitor-comparison queries
- Include "how to" and "best for" queries

Example queries (adapt to your product):
```yaml
- "What's the best platform for deploying Python applications?"
- "How do I deploy a Django app to production?"
- "Compare [Product] vs [Competitor] for web hosting"
- "[Product] vs [Competitor] pricing 2026"
- "What are the alternatives to [Competitor] for [use case]?"
```

Save to a temporary file (e.g., `research/aeo-queries-<date>.yaml`).

## Step 3: Run GEO queries

```
seedrank research geo research/aeo-queries-<date>.yaml
```

This queries all configured AI models with each question and records brand mentions, sentiment, competitor mentions, and citations.

## Step 4: Analyze results

Get the updated trends:

```
seedrank data geo-trends --json
```

Get the gaps:

```
seedrank data geo-gaps --json
```

Get the latest GEO results:

```
seedrank data geo --json --limit 50
```

## Step 5: Write monitoring report

Write the report to `decisions/aeo-monitor-<date>.md`:

```markdown
# AEO Monitoring Report — <date>

## Brand Mention Rate
- This week: X% (Y/Z queries)
- Last week: X% (if available)
- Trend: improving / declining / stable

## Competitor Mention Leaderboard
| Competitor | Mentions | Rate |
|------------|----------|------|
| Name       | 15       | 60%  |

## Gaps (competitors mentioned, brand absent)
Queries where one or more competitors are cited but our brand is not:
1. "Query text" — competitors mentioned: [list]
2. ...

## Opportunities
High-AI-volume queries where we have content but aren't cited:
- Query: "..." — We have content at [slug] but aren't mentioned

## Sentiment Analysis
- Positive mentions: X
- Neutral mentions: Y
- Negative mentions: Z
- Average confidence: X.XX

## Recommended Actions
1. **New content needed**: Topics where we have no content and competitors are cited
2. **Content updates needed**: Existing articles that need GEO optimization
3. **External citation building**: Topics where we need more authoritative backlinks
4. **FAQ improvements**: Questions we should answer more directly

## Queries Run
<list of all queries with mention status per model>
```

## Step 6: Wrap up

End with a session log:

```
seedrank session end "AEO monitoring: <brief summary of key findings>"
```

## Important

- Run this weekly or bi-weekly for meaningful trend data.
- Queries should be phrased as real developer questions, not keyword strings.
- Track the same queries over time for consistent trend data.
- If mention rate drops, investigate which queries lost brand presence.
- Focus recommendations on actionable items — new content to write, existing content to optimize.
- Do NOT make up data. Only report what the CLI returns from actual AI model queries.
