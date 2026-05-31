from __future__ import annotations

from typing import Dict, List


def apply_scenario_delta(
    tables: Dict[str, object],
    scenario_delta_rows: List[dict],
) -> Dict[str, object]:
    """
    Pure copy-only baseline.

    Current behavior:
    - deep-copies table surfaces
    - passes through non-table state unchanged
    - does not yet mutate values from scenario_delta_rows
    """
    resolved: Dict[str, object] = {}

    for k, v in tables.items():
        if isinstance(v, list):
            resolved[k] = [
                r.copy() if isinstance(r, dict) else r
                for r in v
            ]
        else:
            resolved[k] = v

    return resolved