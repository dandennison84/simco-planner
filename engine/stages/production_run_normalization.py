from __future__ import annotations

from fractions import Fraction
from functools import reduce
from math import floor, lcm
from typing import Dict, List, Tuple

from engine.debug import debug_log, debug_rows


EPSILON = 1e-6


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _to_float(x, default: float = 0.0) -> float:
    if x is None:
        return default
    s = str(x).strip()
    if s == "":
        return default
    return float(s)


def _to_fraction(x) -> Fraction:
    """
    Convert numeric input to exact Fraction using string form.
    """
    s = str(x).strip()
    if s == "":
        raise ValueError("Cannot convert blank value to Fraction")
    return Fraction(s)


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
                "input_units_per_output": _to_fraction(r.get(qty_col)),
                "output_quality_level": _k(r.get(output_quality_col)) if output_quality_col else "",
                "input_quality_level": _k(r.get(input_quality_col)) if input_quality_col else "",
            }
        )

    return normalized


def _expand_bom_fraction_coefficients(
    output_product_key: str,
    output_quality_level: str,
    bom_by_output_product: Dict[str, List[dict]],
    bom_by_output_exact: Dict[Tuple[str, str], List[dict]],
    path: Tuple[Tuple[str, str], ...] = (),
) -> Dict[Tuple[str, str], Fraction]:
    """
    Recursively compute total BOM coefficients per 1 unit of output.

    Returns:
      {
        (input_product_key, input_quality_level): Fraction(total_units_required_per_one_output)
      }

    Semantics:
      - includes intermediate and terminal consumed products
      - if exact (product_key, quality_level) BOM exists, use it
      - else use generic BOM by product_key
      - input_quality_level defaults to current output_quality_level when blank
    """
    current_node = (output_product_key, output_quality_level)

    if current_node in path:
        raise ValueError(
            f"Cycle detected during production run normalization at product={output_product_key}, quality={output_quality_level}"
        )

    requirements = bom_by_output_exact.get((output_product_key, output_quality_level))
    if requirements is None:
        requirements = bom_by_output_product.get(output_product_key, [])

    # terminal product: no consumed inputs
    if not requirements:
        return {}

    coeffs: Dict[Tuple[str, str], Fraction] = {}

    for req in requirements:
        qty = req.get("input_units_per_output")
        if qty <= 0:
            raise ValueError(
                f"product_bom invalid for output_product_key={output_product_key}: "
                f"input_units_per_output must be > 0"
            )

        input_product_key = _k(req.get("input_product_key"))
        input_quality_level = _k(req.get("input_quality_level")) or output_quality_level

        # always include direct requirement
        key = (input_product_key, input_quality_level)
        coeffs[key] = coeffs.get(key, Fraction(0, 1)) + qty

        # recurse into child BOM if it exists
        child_exact = bom_by_output_exact.get((input_product_key, input_quality_level))
        child_generic = bom_by_output_product.get(input_product_key, [])

        if child_exact is not None or child_generic:
            child_coeffs = _expand_bom_fraction_coefficients(
                input_product_key,
                input_quality_level,
                bom_by_output_product,
                bom_by_output_exact,
                path=path + (current_node,),
            )

            for child_key, child_qty in child_coeffs.items():
                coeffs[child_key] = coeffs.get(child_key, Fraction(0, 1)) + (qty * child_qty)

    return coeffs


def _compute_run_size(coeff_map: Dict[Tuple[str, str], Fraction]) -> int:
    """
    Compute smallest integer run size that makes all recursive input quantities whole.
    """
    denominators = [frac.denominator for frac in coeff_map.values() if frac > 0]
    if not denominators:
        return 1
    return reduce(lcm, denominators)


def stage_production_run_normalization(state: Dict[str, object]) -> Dict[str, object]:
    """
    Normalize raw capacity-based production_intent into executable whole-run production.

    Inputs:
      - production_intent   (raw capacity-driven output from production_resolution)
      - product_bom

    Outputs:
      - production_intent   (normalized executable output)
      - production_capacity (internal/debug surface with pre-normalized output)

    Grain:
      (company_key, product_key, quality_level)

    Rules:
      - production_resolution remains full-capacity and independent of inputs
      - run normalization rounds down to the nearest complete production run
      - run size is determined by recursive BOM denominators
      - normalized production must never exceed raw capacity
    """
    debug_log(state, "[production_run_normalization] start")

    raw_production_rows = state.get("production_intent", [])
    bom_rows = _normalize_product_bom_rows(state.get("product_bom", []))

    # Index BOM by output product (+ optional exact QL)
    bom_by_output_product: Dict[str, List[dict]] = {}
    bom_by_output_exact: Dict[Tuple[str, str], List[dict]] = {}

    for r in bom_rows:
        out_pk = _k(r["output_product_key"])
        out_ql = _k(r["output_quality_level"])

        bom_by_output_product.setdefault(out_pk, []).append(r)
        if out_ql != "":
            bom_by_output_exact.setdefault((out_pk, out_ql), []).append(r)

    run_size_cache: Dict[Tuple[str, str], int] = {}
    coeff_map_cache: Dict[Tuple[str, str], Dict[Tuple[str, str], Fraction]] = {}

    production_capacity: List[dict] = []
    normalized_production_intent: List[dict] = []

    for row in raw_production_rows:
        company_key = _k(row.get("company_key"))
        product_key = _k(row.get("product_key"))
        quality_level = _k(row.get("quality_level"))
        raw_units = _to_float(row.get("units_produced_per_hour"))

        coeff_key = (product_key, quality_level)

        if coeff_key not in run_size_cache:
            coeff_map = _expand_bom_fraction_coefficients(
                output_product_key=product_key,
                output_quality_level=quality_level,
                bom_by_output_product=bom_by_output_product,
                bom_by_output_exact=bom_by_output_exact,
            )
            coeff_map_cache[coeff_key] = coeff_map
            run_size_cache[coeff_key] = _compute_run_size(coeff_map)

        run_size = run_size_cache[coeff_key]
        coeff_map = coeff_map_cache[coeff_key]

        if raw_units <= 0:
            normalized_units = 0
        else:
            runs = floor(raw_units / run_size)
            normalized_units = runs * run_size

        production_capacity.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "quality_level": quality_level,
                "units_produced_per_hour": raw_units,
            }
        )

        normalized_production_intent.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "quality_level": quality_level,
                "units_produced_per_hour": normalized_units,
            }
        )

    out = dict(
        state,
        production_capacity=production_capacity,
        production_intent=normalized_production_intent,
    )

    debug_rows(out, "production_run_normalization", "production_capacity")
    debug_rows(out, "production_run_normalization", "production_intent")

    # ---------------------------------------------------------
    # Invariants
    # ---------------------------------------------------------
    for raw_row, norm_row in zip(production_capacity, normalized_production_intent):
        raw_units = _to_float(raw_row["units_produced_per_hour"])
        normalized_units = _to_float(norm_row["units_produced_per_hour"])
        product_key = _k(norm_row["product_key"])
        quality_level = _k(norm_row["quality_level"])

        if normalized_units < -EPSILON:
            raise ValueError("Normalized production cannot be negative")

        if normalized_units - raw_units > EPSILON:
            raise ValueError("Normalized production cannot exceed raw capacity")

        run_size = run_size_cache[(product_key, quality_level)]
        if run_size > 0 and normalized_units > EPSILON:
            multiple = normalized_units / run_size
            if abs(multiple - round(multiple)) > EPSILON:
                raise ValueError(
                    f"Normalized production is not a whole run multiple for product={product_key}, quality={quality_level}"
                )

        coeff_map = coeff_map_cache[(product_key, quality_level)]

        for (input_product_key, input_quality_level), coeff in coeff_map.items():
            required_units = Fraction(str(norm_row["units_produced_per_hour"])) * coeff
            if required_units.denominator != 1:
                raise ValueError(
                    f"Normalized production still implies fractional input consumption "
                    f"for output product={product_key}, quality={quality_level}, "
                    f"input product={input_product_key}, input quality={input_quality_level}, "
                    f"required={required_units}"
                )

    return out