---
name: optimize-links
description: Analyze the full internal link graph — find orphan pages, assess link distribution, identify topic cluster gaps, and generate a linking plan. Use periodically after publishing 10+ articles, or when site architecture needs attention.
allowed-tools: Bash, Read, Grep, Glob, Write, Edit
---

# Optimize Links

Analyze and optimize the internal link structure across all published articles.

## Phase 1: Assess Current State

Gather the full picture of the link graph:

```
seedrank data links --json
```

Get per-article link counts:

```
seedrank data links --stats --json
```

Find orphan articles (published but no inbound links):

```
seedrank data links --orphans --json
```

Get all published articles with their keywords and topics:

```
seedrank data articles --status published --json
```

Read the keyword strategy for topic cluster context:

```
cat research/keyword-strategy.md 2>/dev/null
```

### State Summary

Calculate and report:
- **Total published articles**: count
- **Total registered links**: count
- **Average inbound links per article**: number
- **Average outbound links per article**: number
- **Orphan articles** (zero inbound): list with titles
- **Under-linked articles** (1 inbound link): list
- **Hub articles** (5+ outbound): list — these are your pillar pages

## Phase 2: Topic Cluster Analysis

Group articles by their topics (from the `topics` JSON field in the articles table).

For each topic cluster:
1. List all articles in the cluster
2. Count links within the cluster (intra-cluster)
3. Count links between clusters (inter-cluster)
4. Identify the **hub article** (most outbound links within cluster) — this is the pillar
5. Flag articles in the cluster with no links to/from the hub

### Cluster Health Criteria
- **Healthy**: Hub exists, all spokes link to/from hub, 80%+ intra-cluster connectivity
- **Weak**: Hub exists but some spokes are disconnected
- **Missing hub**: No clear pillar page — recommend creating one or promoting an existing article
- **Isolated**: Articles share a topic but have zero intra-cluster links

## Phase 3: Find Linking Opportunities

For each orphan or under-linked article, find the best candidates:

```
seedrank articles crosslinks <slug> --direction backward --json
```

For articles with zero outbound links, find forward opportunities:

```
seedrank articles crosslinks <slug> --direction forward --json
```

### Anchor Text Guidelines
- Use descriptive anchor text (not "click here" or "read more")
- Include the target article's primary keyword when natural
- Vary anchor text — don't use the exact same phrase for every link to the same page
- Keep anchors under 6 words when possible

## Phase 4: Generate Link Implementation Plan

Create a prioritized action plan. Priority order:

### Priority 1: Fix orphan pages
These get zero link equity. For each orphan:
- Identify 2-3 published articles that share keywords/topics
- Suggest specific anchor text and which section to place the link in

### Priority 2: Connect topic clusters
For each weak or isolated cluster:
- Ensure the hub/pillar page links to all spoke articles
- Ensure all spoke articles link back to the hub
- Add 1-2 cross-spoke links where topics overlap

### Priority 3: Strengthen high-value pages
For articles targeting high-volume keywords (check `seedrank data keywords --json`):
- Ensure they have 3+ inbound links
- Prioritize links from topically related, already-ranking articles

### Priority 4: Cross-cluster bridges
Find natural connection points between different topic clusters:
- Articles that share keywords across clusters
- Comparison articles that naturally reference multiple topics

## Phase 5: Write Report

Save the analysis to `decisions/link-audit-{date}.md` with this structure:

```markdown
# Internal Link Audit — {date}

## Current State
- Published articles: X
- Registered links: X
- Avg inbound: X | Avg outbound: X
- Orphan articles: X

## Topic Clusters
[cluster analysis]

## Action Plan
### Priority 1: Orphan Fixes (X items)
| Source Article | Target (orphan) | Anchor Text | Section |
...

### Priority 2: Cluster Connections (X items)
| Source | Target | Cluster | Anchor Text |
...

### Priority 3: High-Value Reinforcement (X items)
...

### Priority 4: Cross-Cluster Bridges (X items)
...

## Summary
- Total links to add: X
- Estimated effort: X articles need editing
```

## Output

When done, provide:
1. **Current state summary**: article count, link count, orphan count
2. **Topic cluster health**: which clusters are healthy vs weak
3. **Top 10 highest-priority links to add** (with source, target, anchor text)
4. **Path to the full report**: `decisions/link-audit-*.md`
