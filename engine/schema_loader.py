from pathlib import Path
import yaml


def load_schema(path: Path) -> dict:
    if not path.exists():
        return {"tables": {}}

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return {"tables": {}}

    return data