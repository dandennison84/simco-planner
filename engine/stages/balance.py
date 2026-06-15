from __future__ import annotations

from typing import Dict, Tuple, Any

from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    """
    Normalize keys:
        - None → ""
        - ensure string type
        - trim whitespace

    Ensures consistent joins across stages.
    """
    return ("" if x is None else str(x)).strip()


def _require_float(row: Dict[str, Any], field: str, *, stage: str, row_idx: int | None = None) -> float:
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
    """
    =============================================================================
    Stage: balance

    Purpose:
        Compute net supply/demand for each (company, product, quality).

    Functional view:
        produced_map  = group_sum(production_intent)
        consumed_map  = group_sum(product_bom_consumption)

        balance_plan =
            (produced − consumed)
            → split into (surplus, shortage)

    Inputs:
        production_intent:
            (company, product, quality) → units_produced_per_hour

        product_bom_consumption:
            (company, product, quality) → units_consumed_per_hour

    Output:
        balance_plan:
            Contains:
                - produced
                - consumed
                - net
                - surplus (max(net, 0))
                - shortage (max(-net, 0))

    Notes:
        - Union of keys ensures all products are included
        - Zero production or zero consumption still handled
        - No allocation occurs here (pure accounting stage)
    =============================================================================
    """

    debug_log(state, "[balance] start")

    production_rows = state.get("production_intent", [])
    consumption_rows = state.get("product_bom_consumption", [])

    # ---------------------------------------------------------
    # Aggregate production: group by (company, product, quality)
    # ---------------------------------------------------------
    produced_map: Dict[Tuple[str, str, str], float] = {}

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

    # ---------------------------------------------------------
    # Aggregate consumption: group by same grain
    # ---------------------------------------------------------
    consumed_map: Dict[Tuple[str, str, str], float] = {}

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

    # ---------------------------------------------------------
    # Combine keys (union of produced and consumed)
    # ---------------------------------------------------------
    all_keys = sorted(set(produced_map.keys()) | set(consumed_map.keys()))

    # ---------------------------------------------------------
    # Compute balance per key
    # ---------------------------------------------------------
    balance_plan = []

    for key in all_keys:
        company_key, product_key, quality_level = key

        produced = produced_map.get(key, 0.0)
        consumed = consumed_map.get(key, 0.0)

        # Core balance equation
        net = produced - consumed

        balance_plan.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "quality_level": quality_level,

                "units_produced_per_hour": produced,
                "units_consumed_per_hour": consumed,
                "net_units_per_hour": net,

                # Split into positive / negative flows
                "surplus_units_per_hour": max(net, 0.0),
                "shortage_units_per_hour": max(-net, 0.0),
            }
        )

    # ---------------------------------------------------------
    # Emit result
    # ---------------------------------------------------------
    out = dict(state, balance_plan=balance_plan)
    debug_rows(out, "balance", "balance_plan")

    # ---------------------------------------------------------
    # Invariant: produced - consumed == net
    # ---------------------------------------------------------
    for r in balance_plan:
        produced = r["units_produced_per_hour"]
        consumed = r["units_consumed_per_hour"]
        net = r["net_units_per_hour"]

        if abs((produced - consumed) - net) > 1e-6:
            raise ValueError("[balance:error]\n  reason=balance invariant violated")

    return out