from pathlib import Path
import yaml


def load_schema(path: Path) -> dict:
    """
    Pure schema loader.

    Guarantees:
    - Always returns a dict
    - Always contains "tables" key
    - Never returns None
    """

    if not path.exists():
        return {"tables": {}}

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Normalize empty / None
    if not data:
        return {"tables": {}}

    # Ensure contract shape
    if "tables" not in data or data["tables"] is None:
        data["tables"] = {}

    return data