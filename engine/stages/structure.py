from typing import Dict, List
from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def stage_structure(state: Dict[str, object]) -> Dict[str, object]:
    """
    STRUCTURE STAGE

    Input:
      - map_structure

    Output:
      - slot_context

    Grain:
      (company_key, slot_key)

    Purpose:
      Normalize building + slot information for production allocation.
    """

    debug_log(state, "[structure] start")

    rows = state.get("map_structure", [])

    if not rows:
        out = dict(state, slot_context=[])
        debug_rows(out, "structure", "slot_context")
        return out

    slot_context: List[dict] = []

    for i, r in enumerate(rows, start=1):
        company_key = _k(r.get("company_key"))
        slot_key = _k(r.get("slot_key"))
        building_key = _k(r.get("building_key"))
        building_level = r.get("building_level")
        robots_installed = r.get("robots_installed")

        # ✅ Required fields
        if company_key == "" or slot_key == "":
            raise ValueError(
                f"map_structure row {i}: company_key and slot_key are required"
            )

        if building_level is None:
            raise ValueError(
                f"map_structure row {i}: building_level is required"
            )

        slot_context.append({
            "company_key": company_key,
            "slot_key": slot_key,
            "building_key": building_key,
            "building_level": float(building_level),
            "robots_installed": robots_installed,
        })

    out = dict(state, slot_context=slot_context)
    debug_rows(out, "structure", "slot_context")

    return out