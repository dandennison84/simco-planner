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


def _expand_bom_requirements(
    output_product_key: str,
    output_quality_level: str,
    output_units: float,
    bom_by_output_product: Dict[str, List[dict]],
    bom_by_output_exact: Dict[Tuple[str, str], List[dict]],
    path: Tuple[Tuple[str, str], ...] = (),
) -> List[Tuple[str, str, float]]:
    """
    Recursively expand BOM requirements across all levels.

    Returns a flat list of:
      (input_product_key, input_quality_level, required_units)

    Rules:
      - if exact (product_key, quality_level) BOM exists, use it
      - else use generic BOM by product_key
      - input_quality_level defaults to current output_quality_level when blank
      - intermediate and lower-level demand are both emitted
    """

    current_node = (output_product_key, output_quality_level)

    if current_node in path:
        raise ValueError(
            f"Cycle detected during BOM expansion at product={output_product_key}, quality={output_quality_level}"
        )

    requirements = bom_by_output_exact.get((output_product_key, output_quality_level))
    if requirements is None:
        requirements = bom_by_output_product.get(output_product_key, [])

    # terminal product: no further consumed inputs
    if not requirements:
        return []

    expanded: List[Tuple[str, str, float]] = []

    for req in requirements:
        qty = _to_float(req.get("input_units_per_output"))
        if qty <= 0:
            raise ValueError(
                f"product_bom invalid for output_product_key={output_product_key}: "
                f"input_units_per_output must be > 0"
            )

        input_product_key = _k(req.get("input_product_key"))
        input_quality_level = _k(req.get("input_quality_level")) or output_quality_level
        required_units = output_units * qty

        # ALWAYS emit this level
        expanded.append((input_product_key, input_quality_level, required_units))

        child_exact = bom_by_output_exact.get((input_product_key, input_quality_level))
        child_generic = bom_by_output_product.get(input_product_key, [])

        if child_exact is not None or child_generic:
            expanded.extend(
                _expand_bom_requirements(
                    input_product_key,
                    input_quality_level,
                    required_units,
                    bom_by_output_product,
                    bom_by_output_exact,
                    path=path + (current_node,),
                )
            )

    return expanded


def stage_product_bom_consumption(state: Dict[str, object]) -> Dict[str, object]:
    """
    Computes fully expanded BOM consumption implied by production_intent.

    Inputs:
      - production_intent
      - product_bom

    Outputs:
      - product_bom_consumption
      - product_bom_demand_detail

    Grain:
      product_bom_consumption:
        (company_key, product_key, quality_level)

      product_bom_demand_detail:
        (company_key, source_product_key, source_quality_level,
         demanded_product_key, demanded_quality_level)

    Rules:
      - consumption is recursively expanded across all BOM levels
      - if BOM row specifies output_quality_level, it only matches that output QL
      - if BOM row specifies input_quality_level, that becomes the input QL
      - otherwise input consumption QL defaults to produced row quality_level
      - product_bom_consumption is aggregated total recursive demand
      - product_bom_demand_detail preserves source → demand relationships
    """
    debug_log(state, "[product_bom_consumption] start")

    production_rows = state.get("production_intent", [])
    bom_rows = _normalize_product_bom_rows(state.get("product_bom", []))

    consumption_map: Dict[Tuple[str, str, str], float] = {}
    demand_detail_map: Dict[Tuple[str, str, str, str, str], float] = {}

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
        source_product_key = _k(row.get("product_key"))
        source_quality_level = _k(row.get("quality_level"))
        produced_units = _to_float(row.get("units_produced_per_hour"))

        if produced_units <= 0:
            continue

        expanded_inputs = _expand_bom_requirements(
            output_product_key=source_product_key,
            output_quality_level=source_quality_level,
            output_units=produced_units,
            bom_by_output_product=bom_by_output_product,
            bom_by_output_exact=bom_by_output_exact,
        )

        for demanded_product_key, demanded_quality_level, required_units in expanded_inputs:
            # Aggregated recursive demand
            agg_key = (company_key, demanded_product_key, demanded_quality_level)
            consumption_map[agg_key] = consumption_map.get(agg_key, 0.0) + required_units

            # Source → demand trace
            detail_key = (
                company_key,
                source_product_key,
                source_quality_level,
                demanded_product_key,
                demanded_quality_level,
            )
            demand_detail_map[detail_key] = (
                demand_detail_map.get(detail_key, 0.0) + required_units
            )

    product_bom_consumption = [
        {
            "company_key": company_key,
            "product_key": product_key,
            "quality_level": quality_level,
            "units_consumed_per_hour": units,
        }
        for (company_key, product_key, quality_level), units in sorted(consumption_map.items())
    ]

    product_bom_demand_detail = [
        {
            "company_key": company_key,
            "source_product_key": source_product_key,
            "source_quality_level": source_quality_level,
            "demanded_product_key": demanded_product_key,
            "demanded_quality_level": demanded_quality_level,
            "units_consumed_per_hour": units,
        }
        for (
            company_key,
            source_product_key,
            source_quality_level,
            demanded_product_key,
            demanded_quality_level,
        ), units in sorted(demand_detail_map.items())
    ]

    out = dict(
        state,
        product_bom_consumption=product_bom_consumption,
        product_bom_demand_detail=product_bom_demand_detail,
    )

    debug_rows(out, "product_bom_consumption", "product_bom_consumption")
    debug_rows(out, "product_bom_consumption", "product_bom_demand_detail")

    # ---------------------------------------------------------
    # Invariants
    # ---------------------------------------------------------
    for r in product_bom_consumption:
        if r["units_consumed_per_hour"] < 0:
            raise ValueError("Negative consumption detected")

    for r in product_bom_demand_detail:
        if r["units_consumed_per_hour"] < 0:
            raise ValueError("Negative demand detail detected")

    return out