"""Load workout definitions from YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_spec(path: str | Path) -> dict:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    if not isinstance(spec, dict):
        raise ValueError(f"{path} does not contain a workout mapping.")
    spec.setdefault("name", path.stem.replace("-", " ").replace("_", " ").title())
    return spec
