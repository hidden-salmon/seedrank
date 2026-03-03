"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from seedrank.config.loader import load_config
from seedrank.config.schema import PseoConfig
from seedrank.data.db import get_db_path, init_db

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLE_CONFIG = EXAMPLES_DIR / "seedrank.config.yaml"


@pytest.fixture
def example_config() -> PseoConfig:
    """Load the example config."""
    return load_config(EXAMPLE_CONFIG)


@pytest.fixture
def minimal_config(tmp_path: Path) -> PseoConfig:
    """Create a minimal valid config."""
    config_data = {
        "product": {
            "name": "TestProduct",
            "domain": "test.example.com",
            "category": "SaaS",
        },
    }
    config_file = tmp_path / "seedrank.config.yaml"
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")
    return load_config(config_file)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Provide a clean temporary workspace directory."""
    return tmp_path / "workspace"


@pytest.fixture
def workspace_with_db(tmp_path: Path) -> Path:
    """Provide a workspace with an initialized database."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "data").mkdir()
    db_path = get_db_path(ws)
    init_db(db_path)
    return ws
