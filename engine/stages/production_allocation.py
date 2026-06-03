from typing import Dict, List, Tuple
from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()

def stage_production_allocation(state: Dict[str, object]) -> Dict[str, object]:
    """
    PRODUCTION ALLOCATION STAGE

    Inputs:
      - slot_context
      - production_plan
      - product

    Output:
      - production_intent

    Grain:
      (company_key, product_key, quality_level)

    Rules:
      - Each slot must have splits that sum to 1.0
      - Product must match building
      - Output = BL * baseline_output * split
    """

    debug_log(state, "[production allocation] start")

    slot_rows = state.get("slot_context", [])
    plan_rows = state.get("production_plan", [])
    product_rows = state.get("product", [])
    company_rows = state.get("company", [])

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
        _k(r["company_key"]): float(r.get("production_speed_delta", 0.0))
        for r in company_rows
    }

    # ---------------------------------------------------------
    # Validate splits per slot
    # ---------------------------------------------------------
    split_totals: Dict[Tuple[str, str], float] = {}

    for r in plan_rows:
        if not r.get("enabled", True):
            continue

        ck = _k(r.get("company_key"))
        sk = _k(r.get("slot_key"))
        frac = float(r.get("production_split_fraction"))

        key = (ck, sk)
        split_totals[key] = split_totals.get(key, 0.0) + frac

    for (ck, sk), total in split_totals.items():
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"production_plan split must equal 1.0 for company={ck}, slot={sk}, got {total}"
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
        frac = float(r.get("production_split_fraction"))

        # Validate slot exists
        if (ck, sk) not in slot_index:
            raise ValueError(
                f"production_plan row {i}: no slot_context for company={ck}, slot={sk}"
            )

        slot = slot_index[(ck, sk)]

        # Validate product exists
        if pk not in product_index:
            raise ValueError(
                f"production_plan row {i}: product_key={pk} not found in product"
            )

        product = product_index[pk]

        # Validate building compatibility
        slot_building = _k(slot.get("building_key"))
        product_building = _k(product.get("building_key"))

        if product_building and slot_building != product_building:
            raise ValueError(
                f"production_plan row {i}: product/building mismatch "
                f"(company={ck}, slot={sk}, slot_building={slot_building}, product_building={product_building})"
            )

        building_level = float(slot.get("building_level"))
        baseline_output = float(product.get("baseline_output_per_hour"))

        prod_speed = 1.0 + company_index.get(ck, 0.0)
        units = building_level * baseline_output * prod_speed * frac

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
    debug_rows(out, "production_allocation", "production_intent")

    return out