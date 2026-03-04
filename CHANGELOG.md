# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-03-04

### Fixed

- Gate `run_legal_checks()` on competitor mentions — universal checks (multiplier, exclusivity, unscoped best, undated pricing, unattributed stats) always run; competitor-context checks only when competitor names are present
- Remove duplicate unsourced-claims and last-verified checks from `_check_legal()` — now handled by `legal_checks` module
- Remove "limited" and "basic" from default disparaging words (too many false positives like "Basic plan", "Ltd")
- Tighten overly greedy `lacks?\s+\w+` and `missing\s+\w+` regexes to require feature-related nouns
- Remove dead "better than" exclusion code (regex `\bbetter\s+{name}\b` can never match "better than {name}")
- Fix double-penalizing cherry-picked comparisons — split into `_onesided` and `_toomany` check names
- Fix `checklist_score` default from `0` to `None` (not scored when no competitors present)
- Replace hardcoded `12` with `len(_CHECKLIST_ITEMS)` throughout
- Replace `getattr` calls with direct `cfg.legal.foo` access (fields are defined on `LegalConfig`)
- Fix `extra_disparaging or None` — pass list directly
- Handle CRLF line endings in table regex
- Fix "per" attribution marker to use `\bper\b` word-boundary
- Fix docstring mismatch on `check_cherry_picked_comparison`
- Fix single-word competitor regex in AI tells to match multi-word names (e.g. "Digital Ocean")
- Use word-boundary matching for crutch/honesty phrase detection
- Strip YAML frontmatter before AI-tell checks to prevent false positives
- Add "frankly" to honesty phrases
- Add missing counting-before-listing verb phrases (`why`, `between`, `you should`, `make`, `set`, `help`)
- Fix fragile JSON test parsing with error handling around `index()`/`rindex()`

### Changed

- `/review-article` skill updated from 9-dimension to 10-dimension audit (AI-tell detection added as Dimension 10 in PR #1)
- 354 tests, all passing

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
- AI-tell detection: crutch phrases, tricolons, diplomatic hedging, meta-commentary, gratuitous compliments
- Cache-first data access — checks database before calling APIs
- API cost tracking by provider and endpoint
- Database migrations system
- Exponential backoff retry for API calls
- 8 Claude Code skills: `/research-session`, `/write-article`, `/review-article`, `/audit-legal`, `/plan-calendar`, `/geo-optimize`, `/qa-ai-tells`, `/aeo-monitor`
- Auto-generated CLAUDE.md with full command reference and API usage rules
- Pydantic configuration with example config
