# Seedrank

Seedrank is a CLI toolkit for programmatic SEO, designed to be orchestrated by Claude Code. It handles keyword research, content creation, performance tracking, and AI visibility monitoring.

## First-time setup

If there is no `seedrank.config.yaml` in the current directory, the user needs to set up a workspace first. Guide them through these steps:

1. **Install seedrank**: `pip install -e .` (if in the seedrank repo) or `pip install git+https://github.com/hidden-salmon/seedrank.git`
2. **Navigate to their project directory** — seedrank should be initialized inside the user's project, not inside the seedrank repo itself
3. **Run `seedrank init`** — creates the database, directory structure, and `.claude/seedrank.md`
4. **Create `seedrank.config.yaml`** — at minimum, set `product.name` and `product.domain`. Copy from `examples/seedrank.config.yaml` for a full template
5. **Run `seedrank init` again** — regenerates `.claude/seedrank.md` with product-specific rules
6. **Set up API keys** — copy `.env.example` to `.env` and fill in keys (DataForSEO, OpenAI, etc.)

After setup, `.claude/seedrank.md` contains the full command reference and writing rules. It is loaded automatically by Claude Code.

## Important

- **Never run `seedrank init` inside the seedrank source repo** — it should be run in the user's project directory
- All data lives in `data/seedrank.db` (SQLite) — never edit it manually
- Strategy docs in `research/` are living documents — read them before research, planning, or writing
- Skills (slash commands) orchestrate multi-step workflows — prefer them over raw CLI commands

## Available skills

| Skill | Purpose |
|---|---|
| `/research-session` | Full keyword research workflow |
| `/plan-calendar` | Build prioritized content calendar |
| `/write-article <slug>` | Write article with crosslinks, voice, legal checks, schema markup |
| `/batch-articles <count>` | Write multiple articles in parallel |
| `/review-article <path>` | 10-dimension article audit |
| `/refresh-article <slug>` | Diagnose and refresh declining content using GSC data |
| `/optimize-links` | Analyze link graph, find orphans, generate linking plan |
| `/generate-schema <slug>` | Generate JSON-LD structured data for an article |
| `/geo-optimize <path>` | Optimize article for AI citability |
| `/qa-ai-tells <path>` | Detect AI writing patterns |
| `/audit-legal` | Workspace-wide legal compliance audit |
| `/aeo-monitor` | Track AI brand visibility over time |

## Development

- Python 3.11+, uses `ruff` for linting (line-length 100)
- Tests: `pytest tests/ -v`
- Lint: `ruff check src/ tests/`
- Entry point: `src/seedrank/cli/__init__.py`
