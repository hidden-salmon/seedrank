# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-03

### Added

- CLI toolkit with Typer: `seedrank init`, `seedrank status`, `seedrank session`
- Keyword research via DataForSEO: `seedrank research keywords`, `serp`, `competitors`, `expand`
- Question discovery: `seedrank research questions` (People Also Ask + AI responses)
- GEO monitoring: `seedrank research geo` (OpenAI, Anthropic, Perplexity, Gemini)
- Data queries: `seedrank data keywords`, `gaps`, `articles`, `performance`, `calendar`, `questions`, `geo`, `geo-trends`, `geo-gaps`, `costs`
- Article management: `seedrank articles register`, `update`, `crosslinks`, `backlinks`
- Content calendar with priority scoring: `seedrank calendar add`, `next`, `update`
- Competitor profile management: `seedrank competitors init`, `show`, `list`, `verify`, `freshness`
- Google Search Console integration: `seedrank gsc auth`, `sync`
- Validation: `seedrank validate config`, `research`, `article`, `legal`
- Legal tier validation (RED/YELLOW/GREEN) for comparison content
- GEO citability checks (C1-C5) for AI model optimization
- Cache-first data access — checks database before calling APIs
- API cost tracking by provider and endpoint
- Database migrations system
- Exponential backoff retry for API calls
- 7 Claude Code skills: `/research-session`, `/write-article`, `/review-article`, `/audit-legal`, `/plan-calendar`, `/geo-optimize`, `/aeo-monitor`
- Auto-generated CLAUDE.md with full command reference and API usage rules
- Pydantic configuration with example config
- 252 tests, ruff lint clean
