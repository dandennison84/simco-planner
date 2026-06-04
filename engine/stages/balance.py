from __future__ import annotations

from typing import Dict, Tuple, Any

from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _require_float(row: Dict[str, Any], field: str, *, stage: str, row_idx: int | None = None) -> float:
    value = row.get(field, None)

    if value is None or str(value).strip() == "":
        raise ValueError(
            f"[{stage}:error]\n"
            f"  field={field}\n"
            f"  row={row_idx}\n"
            f"  value={value}\n"
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
            f"  reason=invalid float value"
        )


def stage_balance(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[balance] start")

    production_rows = state.get("production_intent", [])
    consumption_rows = state.get("product_bom_consumption", [])

    produced_map: Dict[Tuple[str, str, str], float] = {}
    consumed_map: Dict[Tuple[str, str, str], float] = {}

    for i, r in enumerate(production_rows, start=1):
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )

        produced_map[key] = produced_map.get(key, 0.0) + _require_float(
            r,
            "units_produced_per_hour",
            stage="balance",
            row_idx=i,
        )

    for i, r in enumerate(consumption_rows, start=1):
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )

        consumed_map[key] = consumed_map.get(key, 0.0) + _require_float(
            r,
            "units_consumed_per_hour",
            stage="balance",
            row_idx=i,
        )

    all_keys = sorted(set(produced_map.keys()) | set(consumed_map.keys()))

    balance_plan = []
    for key in all_keys:
        company_key, product_key, quality_level = key
        produced = produced_map.get(key, 0.0)
        consumed = consumed_map.get(key, 0.0)
        net = produced - consumed

        balance_plan.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "quality_level": quality_level,
                "units_produced_per_hour": produced,
                "units_consumed_per_hour": consumed,
                "net_units_per_hour": net,
                "surplus_units_per_hour": max(net, 0.0),
                "shortage_units_per_hour": max(-net, 0.0),
            }
        )

    out = dict(state, balance_plan=balance_plan)
    debug_rows(out, "balance", "balance_plan")

    for r in balance_plan:
        produced = r["units_produced_per_hour"]
        consumed = r["units_consumed_per_hour"]
        net = r["net_units_per_hour"]

        if abs((produced - consumed) - net) > 1e-6:
            raise ValueError("[balance:error]\n  reason=balance invariant violated")

    return out