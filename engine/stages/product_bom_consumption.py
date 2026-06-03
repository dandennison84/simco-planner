from __future__ import annotations

from typing import Dict, List, Tuple

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


def _normalize_product_bom_rows(bom_rows: List[dict]) -> List[dict]:
    """
    Normalize product_bom rows into a canonical shape.

    Canonical fields:
      - output_product_key
      - input_product_key
      - input_units_per_output
      - output_quality_level (optional)
      - input_quality_level (optional)
    """
    if not bom_rows:
        return []

    cols = list(bom_rows[0].keys())

    def pick(candidates: List[str]) -> str | None:
        present = set(cols)
        for c in candidates:
            if c in present:
                return c
        return None

    output_product_col = pick([
        "output_product_key",
        "produced_product_key",
        "target_product_key",
        "product_key",
    ])
    input_product_col = pick([
        "input_product_key",
        "component_product_key",
        "material_product_key",
        "source_product_key",
    ])
    qty_col = pick([
        "input_units_per_output",
        "units_per_output",
        "bom_quantity",
        "quantity",
        "input_quantity",
    ])
    output_quality_col = pick([
        "output_quality_level",
        "produced_quality_level",
        "target_quality_level",
        "quality_level",
    ])
    input_quality_col = pick([
        "input_quality_level",
        "component_quality_level",
        "material_quality_level",
        "source_quality_level",
    ])

    if output_product_col is None or input_product_col is None or qty_col is None:
        raise ValueError(
            "product_bom must contain recognizable output_product, input_product, and quantity columns"
        )

    normalized: List[dict] = []
    for r in bom_rows:
        normalized.append(
            {
                "output_product_key": _k(r.get(output_product_col)),
                "input_product_key": _k(r.get(input_product_col)),
                "input_units_per_output": _to_float(r.get(qty_col)),
                "output_quality_level": _k(r.get(output_quality_col)) if output_quality_col else "",
                "input_quality_level": _k(r.get(input_quality_col)) if input_quality_col else "",
            }
        )

    return normalized


def stage_product_bom_consumption(state: Dict[str, object]) -> Dict[str, object]:
    """
    Computes direct BOM consumption implied by unconstrained production_intent.

    Inputs:
      - production_intent
      - product_bom

    Output:
      - product_bom_consumption

    Grain:
      (company_key, product_key, quality_level)

    Rules:
      - consumption = sum(units_produced_per_hour * input_units_per_output)
      - if BOM row specifies output_quality_level, it only matches that output QL
      - if BOM row specifies input_quality_level, that becomes the consumption QL
      - otherwise input consumption QL defaults to produced row quality_level
    """
    debug_log(state, "[product_bom_consumption] start")

    production_rows = state.get("production_intent", [])
    bom_rows = _normalize_product_bom_rows(state.get("product_bom", []))

    consumption_map: Dict[Tuple[str, str, str], float] = {}

    # index BOM by output product (+ optional exact QL)
    bom_by_output_product: Dict[str, List[dict]] = {}
    bom_by_output_exact: Dict[Tuple[str, str], List[dict]] = {}

    for r in bom_rows:
        out_pk = _k(r["output_product_key"])
        out_ql = _k(r["output_quality_level"])

        bom_by_output_product.setdefault(out_pk, []).append(r)
        if out_ql != "":
            bom_by_output_exact.setdefault((out_pk, out_ql), []).append(r)

    for row in production_rows:
        company_key = _k(row.get("company_key"))
        output_product_key = _k(row.get("product_key"))
        output_quality_level = _k(row.get("quality_level"))
        produced_units = _to_float(row.get("units_produced_per_hour"))

        requirements = bom_by_output_exact.get((output_product_key, output_quality_level))
        if requirements is None:
            requirements = bom_by_output_product.get(output_product_key, [])

        for req in requirements:
            qty = _to_float(req.get("input_units_per_output"))
            if qty <= 0:
                raise ValueError(
                    f"product_bom invalid for output_product_key={output_product_key}: "
                    f"input_units_per_output must be > 0"
                )

            input_product_key = _k(req.get("input_product_key"))
            input_quality_level = _k(req.get("input_quality_level")) or output_quality_level

            key = (company_key, input_product_key, input_quality_level)
            consumption_map[key] = consumption_map.get(key, 0.0) + (produced_units * qty)

    product_bom_consumption = [
        {
            "company_key": company_key,
            "product_key": product_key,
            "quality_level": quality_level,
            "units_consumed_per_hour": units,
        }
        for (company_key, product_key, quality_level), units in sorted(consumption_map.items())
    ]

    out = dict(state, product_bom_consumption=product_bom_consumption)
    debug_rows(out, "product_bom_consumption", "product_bom_consumption")

    # ---------------------------------------------------------
    # Invariant: consumption must be non-negative
    # ---------------------------------------------------------
    for r in product_bom_consumption:
        if r["units_consumed_per_hour"] < 0:
            raise ValueError("Negative consumption detected")

    return out