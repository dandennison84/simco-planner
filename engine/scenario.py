from __future__ import annotations

from typing import Dict, List, Tuple


def _parse_target_key(target_key: str) -> Dict[str, str]:
    """
    Parses a serialized key like:
      "slot_key=3"
      "product_key=10,quality_level=2"

    Returns dict[str,str]. No implicit typing here.
    """
    s = ("" if target_key is None else str(target_key)).strip()
    if s == "":
        raise ValueError("scenario_delta.target_key is blank")

    out: Dict[str, str] = {}
    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
    for p in parts:
        if "=" not in p:
            raise ValueError(f"Invalid target_key fragment (missing '='): {p}")
        k, v = p.split("=", 1)
        k = k.strip()
        v = v.strip()
        if k == "" or v == "":
            raise ValueError(f"Invalid target_key fragment: {p}")
        out[k] = v
    return out


def apply_scenario_delta(
    tables: Dict[str, List[dict]],
    scenario_delta_rows: List[dict],
) -> Dict[str, List[dict]]:
    """
    Pure patch application:
    - Only specified fields are overridden.
    - Unspecified fields remain baseline.
    - No add/remove semantics: if a target row doesn't exist -> error.
    - If multiple rows match -> error.
    """
    # deep-ish copy: list + dict copy
    resolved: Dict[str, List[dict]] = {k: [r.copy() for r in v] for k, v in tables.items()}

    if not scenario_delta_rows:
        return resolved

    for d in scenario_delta_rows:
        target_table = d.get("target_table", "")
        target_key = d.get("target_key", "")
        field_name = d.get("field_name", "")
        value = d.get("value", "")

        target_table = ("" if target_table is None else str(target_table)).strip()
        field_name = ("" if field_name is None else str(field_name)).strip()

        if target_table == "":
            raise ValueError("scenario_delta.target_table is blank")
        if field_name == "":
            raise ValueError("scenario_delta.field_name is blank")

        if target_table not in resolved:
            raise ValueError(f"scenario_delta references unknown table: {target_table}")

        key_map = _parse_target_key(str(target_key))

        rows = resolved[target_table]

        matches = []
        for r in rows:
            ok = True
            for k, v in key_map.items():
                rv = r.get(k)
                if ("" if rv is None else str(rv)).strip() != v:
                    ok = False
                    break
            if ok:
                matches.append(r)

        if len(matches) != 1:
            raise ValueError(
                f"scenario_delta match error: table={target_table}, key={key_map}, matches={len(matches)}"
            )

        # Override only the specified field
        matches[0][field_name] = value

    return resolved


def resolve_state_identity(company_snapshot_rows: List[dict], scenario_delta_rows: List[dict]) -> Tuple[str, str]:
    """
    Minimal deterministic identity policy for current engine shape:
    - Requires exactly one snapshot row if scenarios are used.
    - If no scenario_delta: scenario_key = "0" and state_key = snapshot_key
    - If scenario_delta: require exactly one scenario_key across delta rows and one snapshot row
      and state_key = f"{snapshot_key}__{scenario_key}"

    This keeps identity explicit without inventing add/remove semantics.
    """
    if not company_snapshot_rows:
        raise ValueError("company_snapshot is empty; cannot resolve state identity")

    if not scenario_delta_rows:
        snap = str(company_snapshot_rows[0].get("snapshot_key", "")).strip()
        if snap == "":
            raise ValueError("company_snapshot.snapshot_key is missing/blank")
        return snap, "0"

    if len(company_snapshot_rows) != 1:
        raise ValueError("scenario_delta present: engine currently requires exactly one company_snapshot row")

    scenario_keys = {str(r.get("scenario_key", "")).strip() for r in scenario_delta_rows}
    scenario_keys.discard("")
    if len(scenario_keys) != 1:
        raise ValueError(f"scenario_delta must contain exactly one scenario_key for now. Found: {sorted(scenario_keys)}")

    scenario_key = next(iter(scenario_keys))
    snapshot_key = str(company_snapshot_rows[0].get("snapshot_key", "")).strip()
    if snapshot_key == "":
        raise ValueError("company_snapshot.snapshot_key is missing/blank")

    state_key = f"{snapshot_key}__{scenario_key}"
    return state_key, scenario_key