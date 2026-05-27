from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import yaml


def load_schema(path: Path) -> Dict[str, Any]:
    """
    Pure schema loader.
    Reads schema YAML and returns a dict.
    No validation logic here; this is L0/L1 shape only.
    """
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path}")

    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Schema must be a mapping at root. Got: {type(data)}")

    # normalize minimal expected keys
    if "tables" not in data or data["tables"] is None:
        data["tables"] = {}

    if not isinstance(data["tables"], dict):
        raise ValueError("Schema['tables'] must be a mapping")

    return data