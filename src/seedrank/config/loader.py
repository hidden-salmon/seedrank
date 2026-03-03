"""Load and validate seedrank.config.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from seedrank.config.schema import PseoConfig


def load_config(path: str | Path | None = None) -> PseoConfig:
    """Load a pSEO config from a YAML file.

    Args:
        path: Path to seedrank.config.yaml. Defaults to ./seedrank.config.yaml.

    Returns:
        Validated PseoConfig instance.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If the config is invalid.
    """
    if path is None:
        path = Path.cwd() / "seedrank.config.yaml"
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Run 'seedrank init' to create one, or specify a path with --config."
        )

    raw = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Config file must be a YAML mapping, got {type(data).__name__}")

    try:
        return PseoConfig(**data)
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            errors.append(f"  {loc}: {err['msg']}")
        raise ValueError(
            f"Config validation failed ({len(errors)} error{'s' if len(errors) != 1 else ''}):\n"
            + "\n".join(errors)
        ) from e
