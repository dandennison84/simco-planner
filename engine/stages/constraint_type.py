from __future__ import annotations

from typing import Any, Dict, List, Tuple

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


def stage_constraint_type(state: Dict[str, object]) -> Dict[str, object]:
    """
    =============================================================================
    Stage: constraint_type

    Purpose:
        Classify the primary constraint driver for each product.

    Functional view:
        constraint_type =
            classify(allocation_summary, balance_plan)

    Inputs:
        allocation_summary:
            - is_retail_capped

        balance_plan:
            - net_units_per_hour

    Output:
        constraint_type:
            - company_key
            - product_key
            - quality_level
            - constraint_type

    Rules:
        - if is_retail_capped = TRUE -> retail_constrained
        - else if net_units_per_hour < 0 -> supply_constrained
        - else -> balanced

    Notes:
        - This is a product-level interpretation layer
        - "balanced" means:
            no retail cap AND no supply shortage
    =============================================================================
    """

    stage_name = "constraint_type"
    debug_log(state, "[constraint_type] start")

    allocation_rows = state.get("allocation_summary", [])
    balance_rows = state.get("balance_plan", [])

    # ---------------------------------------------------------
    # Index balance by product grain
    # ---------------------------------------------------------
    balance_index: Dict[Tuple[str, str, str], dict] = {
        (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        ): r
        for r in balance_rows
    }

    constraint_type_rows: List[dict] = []

    for i, r in enumerate(allocation_rows, start=1):
        company_key = _k(r.get("company_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))

        key = (company_key, product_key, quality_level)

        if key not in balance_index:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  row={i}\n"
                f"  context=company_key={company_key}, product_key={product_key}, quality_level={quality_level}\n"
                f"  reason=missing balance_plan match"
            )

        bal = balance_index[key]

        net = _require_float(
            bal,
            "net_units_per_hour",
            stage=stage_name,
            row_idx=i,
            context=f"company_key={company_key}, product_key={product_key}, quality_level={quality_level}",
        )

        is_retail_capped = bool(r.get("is_retail_capped"))

        if is_retail_capped:
            constraint_value = "retail_constrained"
        elif net < -1e-12:
            constraint_value = "supply_constrained"
        else:
            constraint_value = "not_constrained"

        constraint_type_rows.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "quality_level": quality_level,
                "constraint_type": constraint_value,
            }
        )

    out = dict(state, constraint_type=constraint_type_rows)
    debug_rows(out, "constraint_type", "constraint_type")

    return out