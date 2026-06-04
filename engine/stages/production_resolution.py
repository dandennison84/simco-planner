from typing import Dict, List, Tuple, Any
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

    if value is None or value == "":
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
    PRODUCTION RESOLUTION STAGE

    Inputs:
      - slot_context
      - production_plan
      - product

    Output:
      - production_intent

    Meaning:
        Raw capacity-based production before run normalization.

    Grain:
      (company_key, product_key, quality_level)

    Rules:
      - Each slot must have splits that sum to 1.0
      - Product must match building
      - Output = BL * baseline_output * split
    """
    stage_name = "production_resolution"

    debug_log(state, "[production resolution] start")

    slot_rows = state.get("slot_context", [])
    plan_rows = state.get("production_plan", [])
    product_rows = state.get("product", [])
    company_rows = state.get("company", [])
    building_rows = state.get("building", [])    

    building_phase_multiplier = {
        _k(r["building_key"]): {
            "recession": float(r.get("recession_output_multiplier", 1.0)),
            "boom": float(r.get("boom_output_multiplier", 1.0)),
        }
        for r in building_rows
    }
    # ---------------------------------------------------------
    # Build lookup indexes
    # ---------------------------------------------------------
    slot_index = {
        (_k(r["company_key"]), _k(r["slot_key"])): r
        for r in slot_rows
    }

    product_index = {
        _k(r["product_key"]): r
        for r in product_rows
    }

    company_index = {
        _k(r["company_key"]): _require_float(
            r,
            "production_speed_delta",
            stage=stage_name,
            context=f"company_key={_k(r.get('company_key'))}",
        )
        for r in company_rows    
    }

    company_phase = {
        _k(r["company_key"]): _k(r["economic_phase_key"])
        for r in company_rows
    }

    # ---------------------------------------------------------
    # Validate splits per slot
    # ---------------------------------------------------------
    split_totals: Dict[Tuple[str, str], float] = {}

    for i, r in enumerate(plan_rows, start=1):
        if not r.get("enabled", True):
            continue

        ck = _k(r.get("company_key"))
        sk = _k(r.get("slot_key"))

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
                f"  field=production_split_frac\n"
                f"  context=company_key={ck}, slot_key={sk}\n"
                f"  reason=slot splits must equal 1.0\n"
                f"  value={total}"
            )

    # ---------------------------------------------------------
    # Compute production
    # ---------------------------------------------------------
    produced: Dict[Tuple[str, str, str], float] = {}

    for i, r in enumerate(plan_rows, start=1):
        if not r.get("enabled", True):
            continue

        ck = _k(r.get("company_key"))
        sk = _k(r.get("slot_key"))
        pk = _k(r.get("product_key"))
        ql = _k(r.get("quality_level"))

        frac = _require_float(
            r,
            "production_split_frac",
            stage=stage_name,
            row_idx=i,
            context=f"company_key={ck}, slot_key={sk}, product_key={pk}, quality_level={ql}",
        )

        # Validate slot exists
        if (ck, sk) not in slot_index:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  row={i}\n"
                f"  context=company_key={ck}, slot_key={sk}\n"
                f"  reason=no slot_context match"
            )

        slot = slot_index[(ck, sk)]

        # Validate product exists
        if pk not in product_index:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  row={i}\n"
                f"  field=product_key\n"
                f"  value={pk}\n"
                f"  reason=product_key not found in product"
            )

        product = product_index[pk]

        # Validate building compatibility
        slot_building = _k(slot.get("building_key"))
        product_building = _k(product.get("building_key"))

        if product_building and slot_building != product_building:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  row={i}\n"
                f"  reason=product/building mismatch\n"
                f"  company_key={ck}\n"
                f"  slot_key={sk}\n"
                f"  slot_building={slot_building}\n"
                f"  product_building={product_building}"
            )

        building_level = _require_float(
            slot,
            "building_level",
            stage=stage_name,
            row_idx=i,
            context=f"company_key={ck}, slot_key={sk}",
        )

        baseline_output = _require_float(
            product,
            "baseline_output_per_hour",
            stage=stage_name,
            row_idx=i,
            context=f"product_key={pk}",
        )

        bk = _k(slot.get("building_key"))
        phase = company_phase.get(ck, "1")

        if bk not in building_phase_multiplier:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  row={i}\n"
                f"  field=building_key\n"
                f"  value={bk}\n"
                f"  reason=no building phase multiplier found"
            )

        bm = building_phase_multiplier[bk]

        if phase == "1":
            phase_multiplier = 1.0
        elif phase == "2":
            phase_multiplier = bm["recession"]
        elif phase == "3":
            phase_multiplier = bm["boom"]
        else:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  row={i}\n"
                f"  field=economic_phase_key\n"
                f"  value={phase}\n"
                f"  reason=unknown phase"
            )
        
        mod = company_index.get(ck, 0.0)
        prod_speed = 1.0 / (1.0 - mod)

        units = (
            building_level
            * baseline_output
            * phase_multiplier
            * prod_speed
            * frac
        )

        key = (ck, pk, ql)
        produced[key] = produced.get(key, 0.0) + units

    # ---------------------------------------------------------
    # Emit production_intent
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
    # Invariant: production must be non-negative
    # ---------------------------------------------------------
    for r in production_intent:
        if r["units_produced_per_hour"] < 0:
            raise ValueError("[production_resolution:error]\n  reason=negative production detected")

    return out