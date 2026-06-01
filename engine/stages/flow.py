from typing import Dict, List, Tuple
from engine.flow_plan import apply_flow_plan
from engine.debug import debug_log, debug_rows, debug_enabled


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def stage_flow(state: Dict[str, object]) -> Dict[str, object]:

    debug_log(state, "[flow] start")

    production_rows = state.get("production_intent", [])
    flow_plan_rows = state.get("flow_plan", [])

    debug_log(state, f"[flow] production_intent rows={len(production_rows)}", level=2)
    debug_log(state, f"[flow] flow_plan rows={len(flow_plan_rows)}", level=2)

    if debug_enabled(state, 3):
        debug_rows(state, "flow", "production_intent")
        debug_rows(state, "flow", "flow_plan")

    # ---------------------------------------------------------
    # Group production by company
    # ---------------------------------------------------------
    by_company: Dict[str, List[dict]] = {}

    for r in production_rows:
        ck = _k(r.get("company_key"))
        by_company.setdefault(ck, []).append(r)

    debug_log(state, f"[flow] companies found: {list(by_company.keys())}", level=2)

    flow_allocation: List[dict] = []

    # ---------------------------------------------------------
    # Apply per company
    # ---------------------------------------------------------
    for company_key, rows in by_company.items():

        debug_log(state, f"[flow] --- company={company_key} ---", level=2)
        debug_log(state, f"[flow] production rows={len(rows)}", level=2)

        # show non-zero production sources
        non_zero_sources = [
            (_k(r["product_key"]), _k(r["quality_level"]), r["units_produced_per_hour"])
            for r in rows
            if float(r.get("units_produced_per_hour", 0.0)) > 0
        ]

        debug_log(state, f"[flow] non-zero production sources={non_zero_sources}", level=2)

        # filter flow_plan for this company
        fp_company = [
            r for r in flow_plan_rows
            if _k(r.get("company_key")) == company_key
        ]

        debug_log(state, f"[flow] flow_plan rows for company={len(fp_company)}", level=2)

        # show distinct source keys in flow_plan
        fp_sources = sorted({
            (_k(r["source_product_key"]), _k(r["source_quality_level"]))
            for r in fp_company
        })

        debug_log(state, f"[flow] flow_plan sources={fp_sources}", level=2)

        # match sources between production and flow_plan
        prod_keys = {
            (_k(r["product_key"]), _k(r["quality_level"]))
            for r in rows
            if float(r.get("units_produced_per_hour", 0.0)) > 0
        }

        intersection = sorted(prod_keys & set(fp_sources))

        debug_log(state, f"[flow] matching sources (production ∩ flow_plan)={intersection}", level=2)

        # -----------------------------------------------------
        # Call flow engine
        # -----------------------------------------------------
        alloc = apply_flow_plan(
            rows,
            flow_plan_rows,
            company_key=company_key
        )

        debug_log(state, f"[flow] allocations returned={len(alloc)}", level=2)

        if debug_enabled(state, 3) and alloc:
            debug_rows({"flow_allocation": alloc}, "flow", "flow_allocation_partial")

        flow_allocation.extend(alloc)

    # ---------------------------------------------------------
    # Emit
    # ---------------------------------------------------------
    out = dict(state, flow_allocation=flow_allocation)
    debug_rows(out, "flow", "flow_allocation")

    return out
