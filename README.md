[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

# Seedrank

A CLI toolkit for programmatic SEO. Researches keywords, manages content, tracks performance, and monitors AI brand visibility — all from the command line, designed to be orchestrated by [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

## How it works

Seedrank is a set of commands that Claude Code calls to do the mechanical work of SEO: fetching keyword data, tracking articles, computing crosslinks, syncing Google Search Console metrics, and monitoring how AI models talk about your brand.

```
Claude Code (reads .claude/seedrank.md, makes decisions)
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

## Quick start

Requires **Python 3.11+**.

```bash
# Install
pip install git+https://github.com/hidden-salmon/seedrank.git

# Create a workspace
mkdir my-product-seo && cd my-product-seo
seedrank init

# Configure (at minimum, set product.name and product.domain)
cat > seedrank.config.yaml << 'EOF'
product:
  name: My Product
  domain: myproduct.com
EOF

# Re-init with your config, set up API keys
seedrank init
cp .env.example .env    # Edit .env with your DataForSEO credentials

# Start working
claude
```

Then in Claude Code:

```
> /research-session "your topic, related keyword"
> /plan-calendar 5
> /write-article best-article-slug
> /review-article content/blog/best-article-slug.mdx
```

See the [Getting Started guide](docs/getting-started.md) for a full walkthrough.

## Documentation

| Guide | What it covers |
|---|---|
| [Getting Started](docs/getting-started.md) | Install, workspace setup, first research-to-article session |
| [Concepts](docs/concepts.md) | Architecture, three-layer data model, priority scoring, crosslinks, legal, GEO |
| [CLI Reference](docs/cli-reference.md) | Every command with options and examples |
| [Configuration](docs/configuration.md) | Full `seedrank.config.yaml` reference and environment variables |
| [Skills](docs/skills.md) | All slash-command workflows — when to use each one and what they do |

## Skills (Slash Commands)

Skills are the primary interface — multi-step workflows invoked as slash commands in Claude Code.

| Skill | Description |
|---|---|
| `/research-session` | Full keyword research: questions, metrics, competitors, gaps |
| `/plan-calendar` | Build prioritized content calendar from gap analysis |
| `/write-article <slug>` | Write article with crosslinks, voice, legal checks, schema |
| `/batch-articles <count>` | Write multiple articles in parallel |
| `/review-article <path>` | 10-dimension article audit |
| `/qa-ai-tells <path>` | Detect AI writing patterns |
| `/refresh-article <slug>` | Refresh declining content using GSC data |
| `/optimize-links` | Internal link graph analysis |
| `/generate-schema <slug>` | JSON-LD structured data |
| `/geo-optimize <path>` | Optimize for AI model citability |
| `/audit-legal` | Workspace-wide legal compliance audit |
| `/aeo-monitor` | Track AI brand visibility over time |

See [Skills documentation](docs/skills.md) for details on each workflow.

## Development

```bash
git clone https://github.com/hidden-salmon/seedrank.git
cd seedrank
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check src/seedrank/ tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.
