[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

# Seedrank

A CLI toolkit for programmatic SEO. Researches keywords, manages content, tracks performance, and monitors AI brand visibility — all from the command line, designed to be orchestrated by [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## How it works

Seedrank is a set of commands that Claude Code calls to do the mechanical work of SEO: fetching keyword data, tracking articles, computing crosslinks, syncing Google Search Console metrics, and monitoring how AI models talk about your brand.

```
Claude Code (reads CLAUDE.md, makes decisions)
    |
    |-- seedrank research keywords "..."      --> DataForSEO API --> SQLite
    |-- seedrank research competitors ...     --> DataForSEO API --> SQLite
    |-- seedrank research geo queries.yaml    --> OpenAI / Anthropic / Gemini / Perplexity --> SQLite
    |-- seedrank data keywords --json         --> SQLite --> stdout (Claude reads)
    |-- seedrank data gaps --json             --> SQLite --> stdout
    |-- seedrank articles crosslinks slug     --> SQLite --> stdout
    |-- seedrank calendar next --json         --> SQLite --> stdout
    |-- seedrank gsc sync                     --> Google Search Console --> SQLite
    '-- seedrank session start/end            --> YAML state files
```

Claude Code is the brain. Seedrank is the hands.

## Install

```bash
git clone https://github.com/seedrank/seedrank.git
cd seedrank
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Requires **Python 3.11+**.

## Quick start

### 1. Create a workspace

```bash
mkdir my-project && cd my-project
seedrank init
```

This creates the directory structure, initializes a SQLite database, and generates a `CLAUDE.md` that teaches Claude Code how to use every command.

### 2. Add your config

Create `seedrank.config.yaml` in the workspace root (see [Configuration](#configuration) below or copy `examples/seedrank.config.yaml`).

### 3. Set up API keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Re-initialize with your product name

```bash
seedrank init
```

Running `init` again regenerates `CLAUDE.md` with your product name and domain from the config.

### 5. Start working

Open Claude Code in the workspace directory:

```bash
claude
```

Claude Code reads `CLAUDE.md` and knows how to use every `seedrank` command. A typical session:

```
> Start a new SEO research session for my product
> Find keyword gaps against our competitors
> Plan the next 5 articles based on opportunity score
> Write the highest-priority article with crosslinks
```

## Environment variables

Seedrank loads a `.env` file from the current working directory on startup. Copy `.env.example` to `.env` and fill in your keys:

| Variable | Service | Required for |
|---|---|---|
| `DATAFORSEO_LOGIN` | [DataForSEO](https://dataforseo.com) | `seedrank research keywords`, `serp`, `competitors`, `expand` |
| `DATAFORSEO_PASSWORD` | [DataForSEO](https://dataforseo.com) | Same as above |
| `OPENAI_API_KEY` | [OpenAI](https://platform.openai.com) | `seedrank research geo` (ChatGPT queries) |
| `ANTHROPIC_API_KEY` | [Anthropic](https://console.anthropic.com) | `seedrank research geo` (Claude queries) |
| `PERPLEXITY_API_KEY` | [Perplexity](https://docs.perplexity.ai) | `seedrank research geo` (Perplexity queries) |
| `GEMINI_API_KEY` | [Google AI](https://ai.google.dev) | `seedrank research geo` (Gemini queries) |

Google Search Console uses OAuth instead of an API key. Run `seedrank gsc auth` to authenticate interactively.

DataForSEO credentials can also be set in `seedrank.config.yaml` under `dataforseo.login` / `dataforseo.password`, but environment variables are preferred.

## CLI reference

### Workspace

| Command | Description |
|---|---|
| `seedrank init` | Create workspace, initialize database, generate CLAUDE.md |
| `seedrank status` | Show workspace overview: config, database stats, pipeline state |
| `seedrank session start` | Load context from the last session |
| `seedrank session end "summary"` | Write session log and update state |

### Research

| Command | Description |
|---|---|
| `seedrank research keywords "k1, k2, k3"` | Fetch keyword metrics from DataForSEO |
| `seedrank research keywords "k1" --expand` | Fetch metrics + keyword suggestions |
| `seedrank research serp "keyword"` | Get SERP snapshot (top organic results) |
| `seedrank research competitors domain.com` | Fetch keywords a competitor ranks for |
| `seedrank research expand "seed keyword"` | Get keyword suggestions for a seed |
| `seedrank research geo queries.yaml` | Run queries across AI models, analyze brand mentions |
| `seedrank research questions "query"` | Discover questions via People Also Ask + AI responses |

### Data queries

All data commands support `--json` for structured output that Claude Code can parse.

| Command | Description |
|---|---|
| `seedrank data keywords` | List all keywords with volume, KD, CPC, intent |
| `seedrank data gaps` | Keywords competitors rank for that you don't cover |
| `seedrank data articles` | List all registered articles |
| `seedrank data performance` | Aggregated GSC metrics per article |
| `seedrank data calendar` | Content calendar sorted by priority |
| `seedrank data questions` | List discovered questions with status and source |
| `seedrank data geo` | GEO query results — brand mentions, sentiment, citations |
| `seedrank data geo-trends` | Brand mention rate over time, grouped by week |
| `seedrank data geo-gaps` | Queries where competitors appear but your brand doesn't |
| `seedrank data costs` | API spend tracking by provider and endpoint |

### Content management

| Command | Description |
|---|---|
| `seedrank articles register <slug> --title "..." --keywords "k1, k2"` | Register a new article |
| `seedrank articles update <slug> --status published --url "/blog/slug"` | Update article metadata |
| `seedrank articles crosslinks <slug>` | Get crosslink suggestions (forward + backward) |
| `seedrank articles crosslinks <slug> --direction forward` | Articles this slug should link to |
| `seedrank articles crosslinks <slug> --direction backward` | Articles that should link to this slug |
| `seedrank articles backlinks <slug>` | Shorthand for `--direction backward` |

### Content calendar

| Command | Description |
|---|---|
| `seedrank calendar add <slug> --keywords "k1, k2"` | Add article to calendar (auto-computes priority) |
| `seedrank calendar add <slug> --priority 0.85` | Add with manual priority override |
| `seedrank calendar next --count 5` | Show top priority items |
| `seedrank calendar update <slug> --status writing` | Update status: queued, writing, review, done, cancelled |

### Google Search Console

| Command | Description |
|---|---|
| `seedrank gsc auth` | Run OAuth flow (opens browser) |
| `seedrank gsc sync --days 30` | Fetch page performance and store in database |

### Competitors

| Command | Description |
|---|---|
| `seedrank competitors init <slug>` | Create a skeleton JSON profile for a competitor |
| `seedrank competitors show <slug>` | Display a competitor profile |
| `seedrank competitors list` | List all competitor profiles with freshness status |
| `seedrank competitors verify <slug>` | Fetch verification URLs and update last_verified date |
| `seedrank competitors freshness` | Check which competitor profiles are stale |

### Validation

| Command | Description |
|---|---|
| `seedrank validate config` | Check config file validity |
| `seedrank validate research` | Check research data quality (KD distribution, volume, coverage) |
| `seedrank validate article <path>` | Check word count, internal links, voice, legal compliance |
| `seedrank validate legal` | Workspace-wide legal compliance (data staleness, disclaimers) |

## Configuration

All product-specific settings live in `seedrank.config.yaml` at the workspace root. Here's every section:

```yaml
# Product information
product:
  name: Moonbeam
  domain: moonbeam.example.com
  category: Email Marketing
  tagline: "Email that actually gets read."
  description: "Moonbeam is an email marketing platform with AI-powered send-time optimization."
  pricing_url: "https://moonbeam.example.com/pricing"
  docs_url: "https://docs.moonbeam.example.com"
  signup_url: "https://app.moonbeam.example.com"
  features:
    - name: AI send-time optimization
      status: live                    # live | in_development | planned | early_access
      description: Automatically sends emails when subscribers are most likely to open.

# Brand voice rules
voice:
  tone: [direct, friendly, confident, helpful]
  cta_style: direct                   # direct | soft | technical
  cta_primary: "Start sending"
  cta_never: ["Get Started", "Try it now!"]
  banned_words: [supercharge, revolutionize, game-changing, seamless, leverage]

# Target user personas
personas:
  - slug: switcher
    name: The Switcher
    description: "Frustrated with current email platform pricing or deliverability."
    pain_points:
      - "Paying too much for email marketing"
      - "Poor deliverability"
    search_behavior:
      - "best mailchimp alternative"
      - "cheaper email marketing tool"

# Competitors
competitors:
  - slug: mailchimp
    name: Mailchimp
    domain: mailchimp.com
    tier: 1                           # 1 = direct, 2 = adjacent
    strengths: ["Huge brand recognition", "Large template library"]
    positioning_against: "Gets expensive fast. We offer better deliverability at half the cost."

# Content types
content_types:
  - slug: blog
    route: "/blog/[slug]"
    content_dir: blog
    label: Blog Posts
    min_words: 1500

# Legal
legal:
  company_name: "Moonbeam Inc."
  corrections_email: "corrections@moonbeam.example.com"
  data_staleness_days: 90

# DataForSEO API (or use DATAFORSEO_LOGIN/DATAFORSEO_PASSWORD env vars)
dataforseo:
  location: 2840                      # 2840 = United States
  language: en

# Google Search Console
gsc:
  property_url: "sc-domain:moonbeam.example.com"
  credentials_path: "credentials.json"

# AI models for GEO monitoring
ai_models:
  - slug: chatgpt
    model: gpt-4o
    api_key_env: OPENAI_API_KEY
    provider: openai
  - slug: claude
    model: claude-sonnet-4-20250514
    api_key_env: ANTHROPIC_API_KEY
    provider: anthropic
  - slug: perplexity
    model: sonar
    api_key_env: PERPLEXITY_API_KEY
    provider: perplexity
    endpoint: "https://api.perplexity.ai"
  - slug: gemini
    model: gemini-2.0-flash
    api_key_env: GEMINI_API_KEY
    provider: gemini
```

Only `product.name` and `product.domain` are required. Everything else has sensible defaults.

## Database

All structured data lives in a single SQLite database at `data/seedrank.db`. The schema:

| Table | What it stores |
|---|---|
| `keywords` | Keyword metrics: volume, KD, CPC, competition, intent, SERP features |
| `serp_snapshots` | Point-in-time SERP results per keyword |
| `competitor_keywords` | Keywords competitors rank for, with rank and URL |
| `serp_competitor_visibility` | Cross-keyword landscape: which domains rank across a set of target keywords |
| `geo_queries` | AI model responses with brand mention analysis |
| `articles` | Article registry: slug, title, status, target keywords, topics |
| `article_links` | Crosslinks between articles |
| `article_performance` | GSC data: impressions, clicks, avg position, CTR per day |
| `content_calendar` | Prioritized queue of articles to write |
| `questions` | Discovered questions from PAA and AI responses, with source and priority |
| `api_costs` | API spend tracking by provider and endpoint |

The database is initialized by `seedrank init` and accessed by every command. You never need to touch it directly — the CLI handles all reads and writes.

## Strategic intelligence layer

Raw data in SQLite is necessary but not sufficient for good SEO decisions. Seedrank uses a three-layer architecture:

```
Layer 1: Raw data        → data/seedrank.db (numbers, timestamps, queryable)
Layer 2: Strategic files  → research/keyword-strategy.md, research/competitor-seo-intel.md (narrative insights)
Layer 3: Action items     → content_calendar table (what to build next)
```

**Why this matters:** When you research keywords today and come back 3 weeks later, the database has the numbers — but not the analysis. "Bring your own cloud has KD 1 and nobody owns it" is an insight that lives in `keyword-strategy.md`. The skills (`/research-session`, `/plan-calendar`, `/write-article`) read these files first so they build on previous analysis instead of starting from scratch.

### How the strategy files work

Both files follow a **living document** pattern:

- **Fixed structure** — sections don't change (Tier 1 keywords, Tier 2, etc.)
- **Timestamped snapshots** — each section has a "Latest snapshot: YYYY-MM-DD" heading
- **Additive history** — when updating, old snapshot moves to a dated history entry, new one takes its place
- **Changelog at the top** — 1-line entries tracking when the file was last updated and what changed

Template files are generated by `seedrank init`. The `/research-session` skill updates them with actual data after research.

### `serp_competitor_visibility` table

This table captures a cross-keyword view of the SERP landscape. Instead of looking at who ranks for individual keywords, it shows which domains appear across a *set* of target keywords — revealing who truly dominates your competitive space.

| Column | Description |
|---|---|
| `domain` | The competing domain |
| `keywords_count` | How many of your target keywords this domain ranks for |
| `avg_position` | Average ranking position across those keywords |
| `median_position` | Median ranking position |
| `rating` | DataForSEO rating score |
| `etv` | Estimated traffic value from these keywords |
| `visibility` | Visibility score (0-100) |
| `keyword_positions` | JSON map of `{"keyword": position, ...}` |
| `research_set` | Label grouping keywords analyzed together (e.g., "hero-keywords", "deploy-cluster") |
| `fetched_at` | When the data was collected |

Use `research_set` to track multiple keyword analyses over time — each research session gets its own label.

## Priority scoring

When you add an article to the calendar without a manual priority, Seedrank computes a score:

```
score = (avg_volume / 1000) * 0.4        # search demand (capped at 1.0)
      + (1 - avg_kd / 100) * 0.3         # keyword difficulty (easier = higher)
      + content_gap_bonus * 0.2           # competitors rank here, you don't
      + gsc_opportunity * 0.1             # you're already close to page 1
```

Higher score = higher priority. The formula balances demand, difficulty, competitive gaps, and existing momentum.

## Crosslink algorithm

Seedrank suggests internal links based on keyword and topic overlap between articles.

**Forward links** (articles to link TO while writing):
- Compares the target article's keywords and topics against all published articles
- Score = `topic_overlap * 2 + keyword_overlap`
- Returns top 10 matches

**Backward links** (articles that should link TO a newly published article):
- Same scoring, but excludes articles that already link to the target
- Run this after publishing to find existing articles that need a new internal link

## Workspace layout

After `seedrank init`, the workspace looks like this:

```
my-project/
├── seedrank.config.yaml          # Product config (single source of truth)
├── CLAUDE.md                 # Auto-generated instructions for Claude Code
├── .env                      # API keys (not committed)
├── data/
│   ├── seedrank.db               # SQLite database
│   └── competitors/          # Competitor JSON profiles
│       └── mailchimp.json
├── pipeline/
│   └── state.yaml            # Current phase, progress, next action
├── sessions/
│   └── 2025-03-15-1430.md    # Session logs (timestamped)
├── decisions/
│   └── (reasoning logs)      # Decision documentation
├── research/
│   ├── keyword-strategy.md   # LIVING DOC: keyword tiers, SERP landscape, targeting rationale
│   ├── competitor-seo-intel.md # LIVING DOC: competitor strategies, traffic, gaps
│   └── (qualitative notes)   # Additional research notes
├── briefs/
│   └── deploy-nextjs.md      # Article briefs
└── content/
    └── blog/
        └── deploy-nextjs.mdx # Written articles
```

## Integrations

### DataForSEO

Used for keyword research and SERP data. Seedrank calls four endpoints:

- **Keyword overview** — volume, keyword difficulty, CPC, competition, intent
- **Keyword suggestions** — expand a seed keyword into related terms
- **SERP results** — top organic results for a keyword
- **Ranked keywords** — keywords a competitor domain ranks for

Requires a [DataForSEO](https://dataforseo.com) account. Set `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD` in your `.env`.

### Google Search Console

Used for performance tracking. Fetches page-level impressions, clicks, average position, and CTR. Seedrank maps URLs back to article slugs automatically.

Requires OAuth setup:
1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the Search Console API
3. Create OAuth 2.0 credentials and download as `credentials.json`
4. Run `seedrank gsc auth` to authenticate

### GEO (Generative Engine Optimization)

Monitors how AI models mention your brand. Sends queries to multiple providers and analyzes responses for:
- Whether your brand is mentioned
- Sentiment (positive / neutral / negative)
- Competitor mentions
- Citations / URLs referenced

Supported providers:

| Provider | SDK | Config key |
|---|---|---|
| OpenAI (ChatGPT) | `openai` | `OPENAI_API_KEY` |
| Anthropic (Claude) | `anthropic` | `ANTHROPIC_API_KEY` |
| Perplexity | `openai` (compatible) | `PERPLEXITY_API_KEY` |
| Google Gemini | REST via `httpx` | `GEMINI_API_KEY` |

## Skills (Slash Commands)

Seedrank includes Claude Code skills — predefined workflows that orchestrate multiple CLI commands into complete tasks. Skills live in `.claude/skills/` and are invoked as slash commands.

| Skill | Description |
|---|---|
| `/research-session "seed keywords"` | Full research workflow: fetch keywords, expand, analyze competitors, identify gaps |
| `/write-article <slug>` | Write a complete article with crosslinks, voice compliance, and legal checks |
| `/review-article <path>` | Review an article: voice, legal, SEO, crosslinks, structured checklist |
| `/audit-legal` | Workspace-wide legal compliance audit |
| `/plan-calendar [count]` | Analyze gaps and build a prioritized content calendar |
| `/geo-optimize <path>` | Optimize an article for AI model citability (C1-C5 checks + fixes) |
| `/aeo-monitor` | Run periodic AI visibility monitoring — track brand mentions over time |

### Typical workflow

```
> /research-session "email marketing, newsletter tools"
> /plan-calendar 10
> /write-article mailchimp-vs-moonbeam
> /review-article content/compare/mailchimp-vs-moonbeam.mdx
> /audit-legal
```

Skills are the orchestration layer — they tell Claude Code **what to do** step by step, while the CLI commands are the **tools** that do the mechanical work.

## Development

```bash
git clone https://github.com/seedrank/seedrank.git
cd seedrank
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Run the linter:

```bash
ruff check src/seedrank/ tests/
```

### Project structure

```
src/seedrank/
├── cli/                 # Typer CLI commands
│   ├── __init__.py      # App definition + sub-app registration
│   ├── init_cmd.py      # seedrank init (workspace + DB + CLAUDE.md)
│   ├── status.py        # seedrank status
│   ├── research.py      # seedrank research (keywords, serp, competitors, expand, geo, questions)
│   ├── data.py          # seedrank data (keywords, gaps, articles, performance, calendar, questions, geo)
│   ├── articles.py      # seedrank articles (register, update, crosslinks, backlinks)
│   ├── calendar.py      # seedrank calendar (add, next, update)
│   ├── competitors.py   # seedrank competitors (init, show, list, verify, freshness)
│   ├── session.py       # seedrank session (start, end)
│   ├── gsc.py           # seedrank gsc (auth, sync)
│   └── validate.py      # seedrank validate (config, research, article, legal)
├── config/
│   ├── schema.py        # Pydantic models for seedrank.config.yaml
│   └── loader.py        # YAML loading + validation
├── data/
│   ├── db.py            # SQLite schema, init, connection management
│   ├── keywords.py      # Keyword queries + gap analysis
│   ├── articles.py      # Article CRUD + crosslink candidates
│   ├── calendar.py      # Calendar CRUD + priority scoring
│   ├── cache.py         # Cache-first data access (check DB before API calls)
│   ├── competitors.py   # Competitor JSON profile management
│   ├── costs.py         # API cost tracking
│   ├── geo.py           # GEO trends, gaps, competitor leaderboard
│   ├── migrations.py    # Database schema migrations
│   └── performance.py   # GSC performance data
├── research/
│   ├── dataforseo.py    # DataForSEO API client
│   ├── geo.py           # Multi-provider GEO query client
│   └── validator.py     # Research data sanity checks
├── integrations/
│   └── gsc.py           # Google Search Console OAuth + API client
├── articles/
│   └── crosslinks.py    # Forward/backward crosslink engine
└── utils/
    ├── console.py       # Rich terminal output helpers
    ├── paths.py         # Workspace path resolution
    └── retry.py         # Exponential backoff retry for API calls
```

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.
