.PHONY: install dev test coverage lint format check clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

coverage:
	pytest tests/ --cov=seedrank --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

check: lint test

clean:
	rm -rf build/ dist/ src/*.egg-info .pytest_cache .coverage htmlcov/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
