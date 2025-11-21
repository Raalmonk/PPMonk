"""Configuration loader utilities for PPMonk."""

from __future__ import annotations

import yaml
from typing import Any


def load_yaml(path: str) -> Any:
    """Load a YAML configuration file."""

    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)
