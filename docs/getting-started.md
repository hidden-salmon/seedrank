# Getting Started

This guide walks you through installing Seedrank, setting up a workspace, and running your first research-to-article workflow.

## Prerequisites

- **Python 3.11+**
- **Claude Code** — Seedrank is designed to be orchestrated by [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Install it if you haven't already.
- **API keys** — at minimum, a [DataForSEO](https://dataforseo.com) account for keyword research. See [Configuration](configuration.md#environment-variables) for all supported services.

## Install Seedrank

```bash
pip install git+https://github.com/hidden-salmon/seedrank.git
```

Or with `pipx` to keep it isolated:

```bash
pipx install git+https://github.com/hidden-salmon/seedrank.git
```

Verify it works:

```bash
seedrank --help
```

## Create a Workspace

A workspace is a project directory where Seedrank stores its database, config, and content. You typically create one workspace per website or product.

```bash
mkdir my-product-seo
cd my-product-seo
seedrank init
```

This creates the directory structure:

```
my-product-seo/
├── .claude/seedrank.md      # Auto-generated instructions for Claude Code
├── .env.example             # Template for API keys
├── data/seedrank.db         # SQLite database
├── data/competitors/        # Competitor JSON profiles
├── pipeline/state.yaml      # Session state
├── sessions/                # Session logs
├── decisions/               # Decision documentation
├── research/                # Strategy documents
├── briefs/                  # Article briefs
└── content/                 # Written articles
```

## Configure Your Product

Create `seedrank.config.yaml` in the workspace root. At minimum:

```yaml
product:
  name: My Product
  domain: myproduct.com
```

For a full example with voice rules, competitors, legal settings, and more, see the [example config](../examples/seedrank.config.yaml) or the [Configuration guide](configuration.md).

Then re-run init to regenerate the Claude Code instructions with your product info:

```bash
seedrank init
```

## Set Up API Keys

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
DATAFORSEO_LOGIN=your_login
DATAFORSEO_PASSWORD=your_password
OPENAI_API_KEY=sk-...          # Optional: for GEO monitoring
ANTHROPIC_API_KEY=sk-ant-...   # Optional: for GEO monitoring
```

See [Configuration — Environment Variables](configuration.md#environment-variables) for all supported keys.

## Your First Session

Open Claude Code in your workspace:

```bash
claude
```

Claude Code automatically reads `.claude/seedrank.md` and knows every Seedrank command. Here's a typical first session:

### 1. Research keywords

```
> /research-session "your topic, related keyword"
```

This runs a multi-step workflow: discovers questions people ask, fetches keyword metrics, analyzes competitors, identifies gaps, and writes a summary. It takes a few minutes.

### 2. Plan content

```
> /plan-calendar 5
```

Analyzes your keyword gaps and builds a prioritized list of 5 articles to write, ranked by opportunity score.

### 3. Write an article

```
> /write-article best-email-marketing-tool
```

Writes a complete article: gathers context, verifies competitor data, finds crosslinks, writes with voice/legal compliance, validates, registers in the database, and generates schema markup.

### 4. Review before publishing

```
> /review-article content/blog/best-email-marketing-tool.mdx
> /qa-ai-tells content/blog/best-email-marketing-tool.mdx
```

Runs a 10-dimension audit and checks for AI writing patterns.

## What's Next

- [Concepts](concepts.md) — understand the architecture, data flow, and how Seedrank thinks
- [CLI Reference](cli-reference.md) — every command with options and examples
- [Skills](skills.md) — the slash-command workflows that orchestrate multi-step tasks
- [Configuration](configuration.md) — full config reference and integration setup
