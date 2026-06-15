from typing import Dict, List, Tuple, Any
from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    """
    Normalize keys:
        - None → ""
        - ensure string
        - trim whitespace

    Used to enforce consistent join keys across all tables.
    """
    return ("" if x is None else str(x)).strip()


def _require_float(
    row: Dict[str, Any],
    field: str,
    *,
    stage: str,
    row_idx: int | None = None,
    context: str = "",
) -> float:
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


def stage_production_resolution(state: Dict[str, object]) -> Dict[str, object]:
    """
    =============================================================================
    Stage: production_resolution

    Purpose:
        Resolve hourly production per product from slot configuration.

    Functional view:
        production_intent =
            map(plan_rows → per-slot production)
            → group by (company, product, quality)
            → sum

    Inputs:
        slot_context      → building + BL per slot
        production_plan   → slot → product splits
        product           → baseline output per product
        company           → production speed modifier + phase
        building          → phase output multipliers

    Output:
        production_intent:
            (company_key, product_key, quality_level) → units/hour

    Core formula:
        units =
            building_level
            × baseline_output
            × phase_multiplier
            × production_speed
            × split_fraction

    Invariants:
        - Split fractions per slot must sum to 1.0
        - Products must be valid for building
        - Output must be non-negative
    =============================================================================
    """

    stage_name = "production_resolution"
    debug_log(state, "[production resolution] start")

    slot_rows = state.get("slot_context", [])
    plan_rows = state.get("production_plan", [])
    product_rows = state.get("product", [])
    company_rows = state.get("company", [])
    building_rows = state.get("building", [])

    # ---------------------------------------------------------
    # Build lookup indexes (normalize for fast joins)
    # ---------------------------------------------------------

    slot_index = {
        (_k(r["company_key"]), _k(r["slot_key"])): r
        for r in slot_rows
    }

    product_index = {
        _k(r["product_key"]): r
        for r in product_rows
    }

    # Company → production speed modifier
    company_index = {
        _k(r["company_key"]): _require_float(
            r,
            "production_speed_delta",
            stage=stage_name,
            context=f"company_key={_k(r.get('company_key'))}",
        )
        for r in company_rows
    }

    # Company → economic phase
    company_phase = {
        _k(r["company_key"]): _k(r["economic_phase_key"])
        for r in company_rows
    }

    # Building → phase multipliers
    building_phase_multiplier = {
        _k(r["building_key"]): {
            "recession": float(r.get("recession_output_multiplier", 1.0)),
            "boom": float(r.get("boom_output_multiplier", 1.0)),
        }
        for r in building_rows
    }

    # ---------------------------------------------------------
    # Validate: split fractions sum to 1.0 per slot
    # ---------------------------------------------------------
    split_totals: Dict[Tuple[str, str], float] = {}

    for i, r in enumerate(plan_rows, start=1):
        if not r.get("enabled", True):
            continue

        ck = _k(r["company_key"])
        sk = _k(r["slot_key"])

        frac = _require_float(
            r,
            "production_split_frac",
            stage=stage_name,
            row_idx=i,
            context=f"company_key={ck}, slot_key={sk}",
        )

        key = (ck, sk)
        split_totals[key] = split_totals.get(key, 0.0) + frac

    for (ck, sk), total in split_totals.items():
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  context=company_key={ck}, slot_key={sk}\n"
                f"  reason=slot splits must equal 1.0\n"
                f"  value={total}"
            )

    # ---------------------------------------------------------
    # Compute production (core fold over plan rows)
    # ---------------------------------------------------------
    produced: Dict[Tuple[str, str, str], float] = {}

    for i, r in enumerate(plan_rows, start=1):
        if not r.get("enabled", True):
            continue

        ck = _k(r["company_key"])
        sk = _k(r["slot_key"])
        pk = _k(r["product_key"])
        ql = _k(r["quality_level"])

        frac = _require_float(
            r,
            "production_split_frac",
            stage=stage_name,
            row_idx=i,
            context=f"company_key={ck}, slot_key={sk}, product_key={pk}, quality_level={ql}",
        )

        # --- Resolve slot and product (join)
        if (ck, sk) not in slot_index:
            raise ValueError(f"[{stage_name}:error] missing slot_context match")

        slot = slot_index[(ck, sk)]

        if pk not in product_index:
            raise ValueError(f"[{stage_name}:error] product_key not found")

        product = product_index[pk]

        # --- Validate building compatibility
        slot_building = _k(slot.get("building_key"))
        product_building = _k(product.get("building_key"))

        if product_building and slot_building != product_building:
            raise ValueError(f"[{stage_name}:error] product/building mismatch")

        # --- Core inputs
        building_level = _require_float(slot, "building_level", stage=stage_name)
        baseline_output = _require_float(product, "baseline_output_per_hour", stage=stage_name)

        # --- Phase multiplier
        bk = _k(slot.get("building_key"))
        phase = company_phase.get(ck, "1")

        bm = building_phase_multiplier[bk]

        if phase == "1":
            phase_multiplier = 1.0
        elif phase == "2":
            phase_multiplier = bm["recession"]
        elif phase == "3":
            phase_multiplier = bm["boom"]
        else:
            raise ValueError(f"[{stage_name}:error] unknown phase")

        # --- Production speed (inverse scaling)
        mod = company_index.get(ck, 0.0)
        prod_speed = 1.0 / (1.0 - mod)

        # --- Final production formula
        units = (
            building_level
            * baseline_output
            * phase_multiplier
            * prod_speed
            * frac
        )

        # --- Aggregate (group-by + sum)
        key = (ck, pk, ql)
        produced[key] = produced.get(key, 0.0) + units

    # ---------------------------------------------------------
    # Emit result
    # ---------------------------------------------------------
    production_intent: List[dict] = [
        {
            "company_key": ck,
            "product_key": pk,
            "quality_level": ql,
            "units_produced_per_hour": units,
        }
        for (ck, pk, ql), units in sorted(produced.items())
    ]

    out = dict(state, production_intent=production_intent)
    debug_rows(out, "production_resolution", "production_intent")

    # ---------------------------------------------------------
    # Invariant: no negative production
    # ---------------------------------------------------------
    for r in production_intent:
        if r["units_produced_per_hour"] < 0:
            raise ValueError("[production_resolution:error] negative production detected")

    return out