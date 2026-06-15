from typing import Any, Dict, List
from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    """
    Normalize keys:
        - None → ""
        - convert to string
        - strip whitespace

    Ensures consistent join keys across all stages.
    """
    return ("" if x is None else str(x)).strip()


def _require_float(
    row: Dict[str, Any],
    field: str,
    *,
    stage: str,
    row_idx: int | None = None,
    context: str = "",
) -> float:
    """
    Extract required float field with fail-fast validation.
    """
    value = row.get(field, None)

    if value is None or str(value).strip() == "":
        raise ValueError(
            f"[{stage}:error]\n"
            f"  field={field}\n"
            f"  row={row_idx}\n"
            f"  value={value}\n"
            f"  context={context}\n"
            f"  reason=missing float value"
        )

    try:
        return float(value)
    except Exception:
        raise ValueError(
            f"[{stage}:error]\n"
            f"  field={field}\n"
            f"  row={row_idx}\n"
            f"  value={value}\n"
            f"  context={context}\n"
            f"  reason=invalid float value"
        )


def _require_bool(
    row: Dict[str, Any],
    field: str,
    *,
    stage: str,
    row_idx: int | None = None,
    context: str = "",
) -> bool:
    """
    Extract required boolean with normalization.

    Accepts:
        true/false, 1/0, yes/no, y/n
    """
    value = row.get(field, None)

    if value is None or str(value).strip() == "":
        raise ValueError(
            f"[{stage}:error]\n"
            f"  field={field}\n"
            f"  row={row_idx}\n"
            f"  value={value}\n"
            f"  context={context}\n"
            f"  reason=missing boolean value"
        )

    s = str(value).strip().lower()

    if s in {"true", "1", "yes", "y"}:
        return True
    if s in {"false", "0", "no", "n"}:
        return False

    raise ValueError(
        f"[{stage}:error]\n"
        f"  field={field}\n"
        f"  row={row_idx}\n"
        f"  value={value}\n"
        f"  context={context}\n"
        f"  reason=invalid boolean value"
    )


def stage_structure(state: Dict[str, object]) -> Dict[str, object]:
    """
    =============================================================================
    Stage: structure

    Purpose:
        Convert raw map structure into normalized slot-level context.

    Functional view:
        slot_context = map(map_structure_rows → normalized_slot)

    Inputs:
        map_structure:
            raw slot configuration with:
                - company_key
                - slot_key
                - building_key
                - building_level
                - robots_installed

    Output:
        slot_context:
            normalized per-slot records used by downstream stages
            (joins + production rely on this)

    Notes:
        - Pure transformation (no aggregation, no cross-row dependency)
        - Each row is validated independently (fail fast)
        - Acts as "typed + normalized layer" for map inputs
    =============================================================================
    """

    stage_name = "structure"
    debug_log(state, "[structure] start")

    rows = state.get("map_structure", [])

    # ---------------------------------------------------------
    # Empty input guard
    # ---------------------------------------------------------
    if not rows:
        out = dict(state, slot_context=[])
        debug_rows(out, "structure", "slot_context")
        return out

    slot_context: List[dict] = []

    # ---------------------------------------------------------
    # Core transformation: row → normalized slot record
    # ---------------------------------------------------------
    for i, r in enumerate(rows, start=1):

        # --- Normalize identifiers
        company_key = _k(r.get("company_key"))
        slot_key = _k(r.get("slot_key"))
        building_key = _k(r.get("building_key"))

        # --- Validate required keys
        if company_key == "" or slot_key == "":
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  row={i}\n"
                f"  field=company_key/slot_key\n"
                f"  context=company_key={company_key}, slot_key={slot_key}\n"
                f"  reason=required fields missing"
            )

        # --- Extract typed fields (fail fast)
        building_level = _require_float(
            r,
            "building_level",
            stage=stage_name,
            row_idx=i,
            context=f"company_key={company_key}, slot_key={slot_key}",
        )

        robots_installed = _require_bool(
            r,
            "robots_installed",
            stage=stage_name,
            row_idx=i,
            context=f"company_key={company_key}, slot_key={slot_key}",
        )

        # --- Emit normalized row
        slot_context.append({
            "company_key": company_key,
            "slot_key": slot_key,
            "building_key": building_key,
            "building_level": building_level,
            "robots_installed": robots_installed,
        })

    # ---------------------------------------------------------
    # Emit result into state
    # ---------------------------------------------------------
    out = dict(state, slot_context=slot_context)
    debug_rows(out, "structure", "slot_context")

    return out