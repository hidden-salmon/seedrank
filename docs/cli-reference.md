# CLI Reference

Every Seedrank command, organized by category. All commands are run from your workspace root (the directory with `seedrank.config.yaml`).

## Workspace

| Command | Description |
|---|---|
| `seedrank init` | Create workspace, initialize database, generate `.claude/seedrank.md` |
| `seedrank status` | Show workspace overview: config, database stats, pipeline state |
| `seedrank session start` | Load context from the last session |
| `seedrank session end "summary"` | Write session log and update state |

### `seedrank init`

Creates the full workspace directory structure, initializes the SQLite database, and generates `.claude/seedrank.md`. Safe to run multiple times — it won't overwrite existing data, but will regenerate the Claude Code instructions with current config values.

Run this inside your project directory, not inside the seedrank source repo.

### `seedrank status`

Prints a dashboard: whether config is loaded, database stats (keyword count, article count, question count), pipeline state, and API cost summary.

### `seedrank session start / end`

Sessions provide continuity between Claude Code conversations. `start` loads the last session's context. `end` writes a timestamped log to `sessions/`.

```bash
seedrank session start
# ... do work ...
seedrank session end "Researched email marketing keywords, found 15 gaps"
```

## Research

Commands that fetch data from external APIs and store results in the database.

| Command | Description |
|---|---|
| `seedrank research keywords "k1, k2, k3"` | Fetch keyword metrics from DataForSEO |
| `seedrank research keywords "k1" --expand` | Fetch metrics + keyword suggestions |
| `seedrank research serp "keyword"` | Get SERP snapshot (top organic results) |
| `seedrank research competitors domain.com` | Fetch keywords a competitor ranks for |
| `seedrank research expand "seed keyword"` | Get keyword suggestions for a seed |
| `seedrank research geo queries.yaml` | Run queries across AI models, analyze brand mentions |
| `seedrank research questions "query"` | Discover questions via People Also Ask + AI responses |

### `seedrank research keywords`

Fetches volume, keyword difficulty (KD), CPC, competition index, and search intent for one or more keywords. Pass multiple keywords comma-separated.

```bash
seedrank research keywords "email marketing, newsletter tools, drip campaigns"
```

With `--expand`, also fetches keyword suggestions for each seed:

```bash
seedrank research keywords "email marketing" --expand
```

### `seedrank research serp`

Gets the current top organic results for a keyword — URLs, titles, positions.

```bash
seedrank research serp "best email marketing platform"
```

### `seedrank research competitors`

Fetches the keywords a competitor domain ranks for, with their position and URL.

```bash
seedrank research competitors mailchimp.com --limit 200
```

### `seedrank research expand`

Gets keyword suggestions related to a seed keyword. Use this to discover long-tail variations.

```bash
seedrank research expand "email automation"
```

### `seedrank research geo`

Sends queries to AI models (ChatGPT, Claude, Perplexity, Gemini) and analyzes whether your brand is mentioned. Queries are defined in a YAML file.

```bash
seedrank research geo queries.yaml
```

### `seedrank research questions`

Discovers questions people ask about a topic, from People Also Ask and AI model responses.

```bash
seedrank research questions "email marketing"
seedrank research questions "email marketing" --provider chatgpt
```

## Data Queries

Read-only commands that query the database. All support `--json` for structured output.

| Command | Description |
|---|---|
| `seedrank data keywords` | List all keywords with volume, KD, CPC, intent |
| `seedrank data gaps` | Keywords competitors rank for that you don't cover |
| `seedrank data articles` | List all registered articles |
| `seedrank data performance` | GSC metrics per article |
| `seedrank data calendar` | Content calendar sorted by priority |
| `seedrank data questions` | Discovered questions with status and source |
| `seedrank data geo` | GEO query results — brand mentions, sentiment, citations |
| `seedrank data geo-trends` | Brand mention rate over time |
| `seedrank data geo-gaps` | Queries where competitors appear but you don't |
| `seedrank data links` | Internal link graph |
| `seedrank data costs` | API spend by provider and endpoint |

### Useful flags

```bash
seedrank data performance --slug my-article     # Performance for a specific article
seedrank data performance --declining           # Articles losing traffic
seedrank data performance --underperformers     # Articles below expected CTR
seedrank data questions --status new --json     # Unanswered questions only
seedrank data questions --slug my-article       # Questions assigned to an article
seedrank data links --orphans                   # Pages with no internal links pointing to them
seedrank data links --stats                     # Link graph summary stats
```

## Content Management

| Command | Description |
|---|---|
| `seedrank articles register <slug>` | Register a new article |
| `seedrank articles update <slug>` | Update article metadata |
| `seedrank articles crosslinks <slug>` | Get crosslink suggestions |
| `seedrank articles backlinks <slug>` | Articles that should link to this slug |
| `seedrank articles schema <slug>` | Generate JSON-LD structured data |

### `seedrank articles register`

```bash
seedrank articles register mailchimp-vs-moonbeam \
  --title "Mailchimp vs Moonbeam: Honest Comparison" \
  --keywords "mailchimp alternative, mailchimp vs moonbeam" \
  --topics "comparison, email marketing"
```

### `seedrank articles update`

```bash
seedrank articles update mailchimp-vs-moonbeam \
  --status published \
  --url "/compare/mailchimp-vs-moonbeam"
```

### `seedrank articles crosslinks`

```bash
seedrank articles crosslinks my-article --direction forward --json   # Articles to link TO
seedrank articles crosslinks my-article --direction backward --json  # Articles that should link here
```

### `seedrank articles schema`

Generates JSON-LD structured data (BlogPosting, FAQPage, BreadcrumbList, Organization):

```bash
seedrank articles schema my-article --json
```

## Content Calendar

| Command | Description |
|---|---|
| `seedrank calendar add <slug>` | Add article to calendar |
| `seedrank calendar next --count 5` | Show top priority items |
| `seedrank calendar update <slug>` | Update status |

### `seedrank calendar add`

```bash
seedrank calendar add email-automation-guide --keywords "email automation, drip campaigns"
seedrank calendar add urgent-topic --priority 0.95  # Manual priority override
```

### `seedrank calendar update`

Statuses: `queued`, `writing`, `review`, `done`, `cancelled`.

```bash
seedrank calendar update email-automation-guide --status writing
```

## Google Search Console

| Command | Description |
|---|---|
| `seedrank gsc auth` | Run OAuth flow (opens browser) |
| `seedrank gsc sync --days 30` | Fetch performance data |

### Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the Search Console API
3. Create OAuth 2.0 credentials, download as `credentials.json`
4. Set `gsc.credentials_path` in your config (defaults to `credentials.json`)
5. Run `seedrank gsc auth` to authenticate

## Competitors

| Command | Description |
|---|---|
| `seedrank competitors init <slug>` | Create skeleton JSON profile |
| `seedrank competitors show <slug>` | Display a profile |
| `seedrank competitors list` | List all profiles with freshness |
| `seedrank competitors verify <slug>` | Fetch live data and update |
| `seedrank competitors freshness` | Check which profiles are stale |

## Validation

| Command | Description |
|---|---|
| `seedrank validate config` | Check config file validity |
| `seedrank validate research` | Check research data quality |
| `seedrank validate article <path>` | Check word count, links, voice, legal |
| `seedrank validate legal` | Workspace-wide legal compliance |

### `seedrank validate article`

Runs all checks on an article file:

```bash
seedrank validate article content/compare/mailchimp-vs-moonbeam.mdx
```

Checks: word count, internal link count, voice compliance (banned words, CTA), legal tier validation (RED/YELLOW/GREEN), citability score (C1-C5), and AI-tell detection.
