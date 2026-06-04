from typing import Any, Dict, List
from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _require_float(
    row: Dict[str, Any],
    field: str,
    *,
    stage: str,
    row_idx: int | None = None,
    context: str = "",
) -> float:
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
    stage_name = "structure"

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

        if company_key == "" or slot_key == "":
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  row={i}\n"
                f"  field=company_key/slot_key\n"
                f"  context=company_key={company_key}, slot_key={slot_key}\n"
                f"  reason=required fields missing"
            )

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

        slot_context.append({
            "company_key": company_key,
            "slot_key": slot_key,
            "building_key": building_key,
            "building_level": building_level,
            "robots_installed": robots_installed,
        })

    out = dict(state, slot_context=slot_context)
    debug_rows(out, "structure", "slot_context")

    return out