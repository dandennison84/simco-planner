from __future__ import annotations

from typing import Dict, Tuple

from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _to_float(x, default: float = 0.0) -> float:
    if x is None:
        return default
    s = str(x).strip()
    if s == "":
        return default
    return float(s)


def stage_balance(state: Dict[str, object]) -> Dict[str, object]:
    """
    Computes net balance from produced vs consumed quantities.

    Inputs:
      - production_intent
      - product_bom_consumption

    Outputs:
      - balance_plan

    Grain:
      (company_key, product_key, quality_level)

    Rules:
      net = produced - consumed
      surplus = max(net, 0)
      shortage = max(-net, 0)
    """
    debug_log(state, "[balance] start")

    production_rows = state.get("production_intent", [])
    consumption_rows = state.get("product_bom_consumption", [])

    produced_map: Dict[Tuple[str, str, str], float] = {}
    consumed_map: Dict[Tuple[str, str, str], float] = {}

    for r in production_rows:
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )
        produced_map[key] = produced_map.get(key, 0.0) + _to_float(r.get("units_produced_per_hour"))

    for r in consumption_rows:
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )
        consumed_map[key] = consumed_map.get(key, 0.0) + _to_float(r.get("units_consumed_per_hour"))

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

    # ---------------------------------------------------------
    # Invariant: net = produced - consumed
    # ---------------------------------------------------------
    for r in balance_plan:
        produced = r["units_produced_per_hour"]
        consumed = r["units_consumed_per_hour"]
        net = r["net_units_per_hour"]

        if abs((produced - consumed) - net) > 1e-6:
            raise ValueError("Balance invariant violated")
        
    return out