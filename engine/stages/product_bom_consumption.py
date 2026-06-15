from __future__ import annotations

from typing import Any, Dict, List, Tuple

from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    """
    Normalize keys:
        - None → ""
        - ensure string type
        - trim whitespace

    Ensures consistent joins across tables.
    """
    return ("" if x is None else str(x)).strip()


def _require_float(
    value: Any,
    *,
    stage: str,
    field: str,
    context: str = "",
) -> float:
    """
    Extract required float value with fail-fast validation.
    """
    if value is None or str(value).strip() == "":
        raise ValueError(
            f"[{stage}:error]\n"
            f"  field={field}\n"
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
            f"  value={value}\n"
            f"  context={context}\n"
            f"  reason=invalid float value"
        )


def _normalize_product_bom_rows(bom_rows: List[dict]) -> List[dict]:
    """
    Normalize BOM rows into canonical schema.

    Functional view:
        normalized_rows = map(raw_rows → normalized_row)

    Handles flexible column naming across different BOM inputs.
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

    # Resolve schema columns (flexible input support)
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
        raise ValueError("[product_bom_consumption:error]\n  reason=invalid product_bom schema")

    normalized: List[dict] = []

    # Map raw rows → normalized BOM rows
    for r in bom_rows:
        normalized.append(
            {
                "output_product_key": _k(r.get(output_product_col)),
                "input_product_key": _k(r.get(input_product_col)),

                # Core quantity (units per 1 output)
                "input_units_per_output": _require_float(
                    r.get(qty_col),
                    stage="product_bom_consumption",
                    field="input_units_per_output",
                    context=f"output_product_key={_k(r.get(output_product_col))}",
                ),

                # Optional quality fields
                "output_quality_level": _k(r.get(output_quality_col)) if output_quality_col else "",
                "input_quality_level": _k(r.get(input_quality_col)) if input_quality_col else "",
            }
        )

    return normalized


def _direct_bom_requirements(
    output_product_key: str,
    output_quality_level: str,
    output_units: float,
    bom_by_output_product: Dict[str, List[dict]],
    bom_by_output_exact: Dict[Tuple[str, str], List[dict]],
) -> List[Tuple[str, str, float]]:
    """
    Resolve immediate (non-recursive) BOM inputs.

    Functional view:
        inputs = map(requirements → (input_product, units_needed))

    NOTE:
        - Direct-only (no recursive expansion)
        - output_units drives required input quantities
    """
    # Prefer exact (product, quality) match
    requirements = bom_by_output_exact.get((output_product_key, output_quality_level))

    if requirements is None:
        # Fallback to generic product-level BOM
        requirements = bom_by_output_product.get(output_product_key, [])

    if not requirements:
        return []

    direct_inputs: List[Tuple[str, str, float]] = []

    for req in requirements:
        qty = req["input_units_per_output"]

        # Validate BOM quantity
        if qty <= 0:
            raise ValueError(
                f"[product_bom_consumption:error]\n"
                f"  field=input_units_per_output\n"
                f"  value={qty}\n"
                f"  context=output_product_key={output_product_key}\n"
                f"  reason=must be > 0"
            )

        input_product_key = _k(req.get("input_product_key"))
        input_quality_level = _k(req.get("input_quality_level")) or output_quality_level

        # Multiply by output quantity
        required_units = output_units * qty

        direct_inputs.append((input_product_key, input_quality_level, required_units))

    return direct_inputs


def stage_product_bom_consumption(state: Dict[str, object]) -> Dict[str, object]:
    """
    =============================================================================
    Stage: product_bom_consumption

    Purpose:
        Calculate intermediate product consumption based on production output.

    Functional view:
        consumption_map =
            map(production_intent → direct_inputs)
            → group by (company, product, quality)
            → sum

        demand_detail =
            map(production_intent → (source → demanded inputs))

    Inputs:
        production_intent   → output products + quantities
        product_bom         → input requirements per product

    Outputs:
        product_bom_consumption:
            (company, product, quality) → total units consumed

        product_bom_demand_detail:
            detailed mapping of:
            (source product → demanded input product)

    Notes:
        - Direct-only BOM (no recursive expansion)
        - Only driven by actual production_intent
        - No phantom products introduced
    =============================================================================
    """

    stage_name = "product_bom_consumption"
    debug_log(state, "[product_bom_consumption] start")

    production_rows = state.get("production_intent", [])
    bom_rows = _normalize_product_bom_rows(state.get("product_bom", []))

    # Aggregated outputs
    consumption_map: Dict[Tuple[str, str, str], float] = {}
    demand_detail_map: Dict[Tuple[str, str, str, str, str], float] = {}

    # ---------------------------------------------------------
    # Build BOM lookup indexes
    # ---------------------------------------------------------
    bom_by_output_product: Dict[str, List[dict]] = {}
    bom_by_output_exact: Dict[Tuple[str, str], List[dict]] = {}

    for r in bom_rows:
        out_pk = _k(r["output_product_key"])
        out_ql = _k(r["output_quality_level"])

        bom_by_output_product.setdefault(out_pk, []).append(r)

        if out_ql != "":
            bom_by_output_exact.setdefault((out_pk, out_ql), []).append(r)

    # ---------------------------------------------------------
    # Core transformation:
    # production → direct inputs → aggregate
    # ---------------------------------------------------------
    for row in production_rows:
        company_key = _k(row.get("company_key"))
        source_product_key = _k(row.get("product_key"))
        source_quality_level = _k(row.get("quality_level"))

        produced_units = _require_float(
            row.get("units_produced_per_hour"),
            stage=stage_name,
            field="units_produced_per_hour",
            context=f"company_key={company_key}, product_key={source_product_key}",
        )

        if produced_units <= 0:
            continue

        # Resolve immediate inputs
        direct_inputs = _direct_bom_requirements(
            source_product_key,
            source_quality_level,
            produced_units,
            bom_by_output_product,
            bom_by_output_exact,
        )

        # Aggregate results
        for demanded_product_key, demanded_quality_level, required_units in direct_inputs:

            # --- total consumption
            agg_key = (company_key, demanded_product_key, demanded_quality_level)
            consumption_map[agg_key] = consumption_map.get(agg_key, 0.0) + required_units

            # --- detailed trace (source → input)
            detail_key = (
                company_key,
                source_product_key,
                source_quality_level,
                demanded_product_key,
                demanded_quality_level,
            )
            demand_detail_map[detail_key] = demand_detail_map.get(detail_key, 0.0) + required_units

    # ---------------------------------------------------------
    # Emit outputs
    # ---------------------------------------------------------
    product_bom_consumption = [
        {
            "company_key": ck,
            "product_key": pk,
            "quality_level": ql,
            "units_consumed_per_hour": units,
        }
        for (ck, pk, ql), units in sorted(consumption_map.items())
    ]

    product_bom_demand_detail = [
        {
            "company_key": ck,
            "source_product_key": spk,
            "source_quality_level": sql,
            "demanded_product_key": dpk,
            "demanded_quality_level": dql,
            "units_consumed_per_hour": units,
        }
        for (ck, spk, sql, dpk, dql), units in sorted(demand_detail_map.items())
    ]

    out = dict(
        state,
        product_bom_consumption=product_bom_consumption,
        product_bom_demand_detail=product_bom_demand_detail,
    )

    debug_rows(out, "product_bom_consumption", "product_bom_consumption")
    debug_rows(out, "product_bom_consumption", "product_bom_demand_detail")

    # ---------------------------------------------------------
    # Invariant: consumption must be non-negative
    # ---------------------------------------------------------
    for r in product_bom_consumption:
        if r["units_consumed_per_hour"] < 0:
            raise ValueError("[product_bom_consumption:error]\n  reason=negative consumption")

    for r in product_bom_demand_detail:
        if r["units_consumed_per_hour"] < 0:
            raise ValueError("[product_bom_consumption:error]\n  reason=negative demand detail")

    return out