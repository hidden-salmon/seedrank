# Contributing to Seedrank

Thanks for your interest in contributing to Seedrank.

## Development setup

```bash
git clone https://github.com/seedrank/seedrank.git
cd seedrank
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Requires **Python 3.11+**.

## Running tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=seedrank --cov-report=term-missing
```

## Linting

```bash
ruff check src/ tests/
```

Seedrank uses [ruff](https://docs.astral.sh/ruff/) with rules `E`, `F`, `I`, `UP`. All code must pass `ruff check` before merging.

## Making changes

1. Fork the repository and create a branch from `main`.
2. Make your changes. Add tests for new functionality.
3. Run `pytest` and `ruff check src/ tests/` to verify.
4. Submit a pull request with a clear description of the change.

## Pull request guidelines

- Keep PRs focused on a single change.
- Write clear commit messages that explain **why**, not just what.
- Add or update tests for any new behavior.
- Ensure all tests pass and lint is clean before requesting review.

## Reporting bugs

Open an issue at [github.com/seedrank/seedrank/issues](https://github.com/seedrank/seedrank/issues) with:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version and OS

## Code of conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
