from __future__ import annotations

from typing import Dict, List, Tuple

from engine.io_csv import ContractInputs, ContractOutputs
from engine.scenario import apply_scenario_delta
from engine.flow_plan import apply_flow_plan
from engine.allocation_policy import apply_allocation_policy
from engine.debug import debug_log, debug_rows

def _normalize_product_bom_rows(bom_rows: List[dict]) -> List[dict]:
    """
    Normalize product_bom rows into a canonical shape.

    Expected canonical fields:
      - output_product_key
      - input_product_key
      - input_units_per_output
      - output_quality_level (optional)
      - input_quality_level (optional)

    This is intentionally tolerant of several likely column names so the
    validator / transform layer does not hardcode one BOM header convention yet.
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

    normalized = []
    for r in bom_rows:
        normalized.append(
            {
                "output_product_key": _k(r.get(output_product_col)),
                "input_product_key": _k(r.get(input_product_col)),
                "input_units_per_output": float(r.get(qty_col)),
                "output_quality_level": _k(r.get(output_quality_col)) if output_quality_col else None,
                "input_quality_level": _k(r.get(input_quality_col)) if input_quality_col else None,
            }
        )

    return normalized

# ============================================================
# Helpers (keep minimal here — move later)
# ============================================================

def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _fmt_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


# ============================================================
# Stage: INPUT
# ============================================================

def stage_input(inputs: ContractInputs) -> Dict[str, object]:
    state: Dict[str, object] = {}
    state.update(inputs.input_tables)
    state.update(inputs.reference_tables)
    state["_meta"] = {}
    return state


# ============================================================
# Stage: SYSTEM PARAMETERS
# ============================================================

def stage_system_parameters(state: Dict[str, object]) -> Dict[str, object]:
    rows = state.get("system_parameters", [])

    param_map = {
        _k(r.get("parameter_key")): _k(r.get("parameter_value"))
        for r in rows
    }

    meta = dict(state.get("_meta", {}))
    meta["system_parameters_map"] = param_map

    return dict(state, _meta=meta)


# ============================================================
# Stage: SCENARIO
# ============================================================

def stage_scenario_resolution(state: Dict[str, object]) -> Dict[str, object]:
    scenario_delta_rows = state.get("scenario_delta", [])
    return apply_scenario_delta(state, scenario_delta_rows)


# ============================================================
# Stage: STRUCTURE
# ============================================================

def stage_structure(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[structure] start")

    rows = state.get("map_structure", [])

    slot_context = [
        {
            "company_key": _k(r["company_key"]),
            "slot_key": _k(r["slot_key"]),
            "building_key": _k(r["building_key"]),
            "building_level": float(r["building_level"]),
            "robots_installed": r["robots_installed"],
        }
        for r in rows
    ]

    out = dict(state, slot_context=slot_context)
    debug_rows(out, "structure", "slot_context")
    return out


# ============================================================
# Stage: ALLOCATION
# ============================================================

def stage_allocation(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[allocation] start")

    assigns = state.get("production_plan", [])
    slot_ctx = state.get("slot_context", [])
    products = state.get("product", [])

    slot_index = {
        (_k(r["company_key"]), _k(r["slot_key"])): r
        for r in slot_ctx
    }

    product_index = {
        _k(r["product_key"]): r
        for r in products
    }

    produced = {}

    for r in assigns:
        ck = _k(r["company_key"])
        sk = _k(r["slot_key"])
        pk = _k(r["product_key"])
        ql = _k(r["quality_level"])
        frac = float(r["production_split_fraction"])

        slot = slot_index[(ck, sk)]
        prod = product_index[pk]

        units = float(slot["building_level"]) * float(prod["baseline_output_per_hour"]) * frac

        key = (ck, pk, ql)
        produced[key] = produced.get(key, 0.0) + units

    production_intent = [
        {
            "company_key": ck,
            "product_key": pk,
            "quality_level": ql,
            "units_produced_per_hour": units,
        }
        for (ck, pk, ql), units in produced.items()
    ]

    out = dict(state, production_intent=production_intent)
    debug_rows(out, "allocation", "production_intent")
    return out


# ============================================================
# Stage: FLOW PLAN (single-pass, correct for now)
# ============================================================

def stage_flow_plan(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[flow_plan] start")

    production_intent = state.get("production_intent", [])
    flow_plan_rows = state.get("flow_plan", [])

    grouped = {}
    for r in production_intent:
        grouped.setdefault(_k(r["company_key"]), []).append(r)

    flow_allocation = []

    for company_key, rows in grouped.items():
        alloc = apply_flow_plan(rows, flow_plan_rows, company_key=company_key)
        flow_allocation.extend(alloc)

    out = dict(state, flow_allocation=flow_allocation)
    debug_rows(out, "flow_plan", "flow_allocation")
    return out

def stage_transform(state: Dict[str, object]) -> Dict[str, object]:
    """
    Minimal BOM-backed transform stage.

    INTERPRETATION:
      - production_intent = capacity per product/QL
      - flow_allocation   = routed internal inputs
      - transformed_output = feasible output after BOM input limits

    RULES:
      - If a product has no BOM rows, output = capacity
      - If a product has BOM rows, output is limited by inbound routed inputs:
            min( capacity,
                 inbound[input_1] / qty_1,
                 inbound[input_2] / qty_2, ... )

    IMPORTANT:
      - This is intentionally minimal and single-pass.
      - It does not yet close the full multi-hop manufacturing loop by itself.
    """
    debug_log(state, "[transform] start")

    capacity_rows = state.get("production_intent", [])
    flow_rows = state.get("flow_allocation", [])
    bom_rows = _normalize_product_bom_rows(state.get("product_bom", []))

    # ---------------------------------------------------------
    # Index capacity by (company, product, ql)
    # ---------------------------------------------------------
    capacity_map: Dict[Tuple[str, str, str], float] = {}
    for r in capacity_rows:
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )
        capacity_map[key] = capacity_map.get(key, 0.0) + float(r.get("units_produced_per_hour", 0.0))

    # ---------------------------------------------------------
    # Index inbound flows by target (company, product, ql, input_product, input_ql)
    # ---------------------------------------------------------
    inbound_by_target_input: Dict[Tuple[str, str, str, str, str], float] = {}
    for r in flow_rows:
        company_key = _k(r.get("company_key"))
        input_product_key = _k(r.get("source_product_key"))
        input_quality_level = _k(r.get("source_quality_level"))
        target_product_key = _k(r.get("target_product_key"))
        target_quality_level = _k(r.get("target_quality_level"))
        amt = float(r.get("allocated_units_per_hour", 0.0))

        key = (
            company_key,
            target_product_key,
            target_quality_level,
            input_product_key,
            input_quality_level,
        )
        inbound_by_target_input[key] = inbound_by_target_input.get(key, 0.0) + amt

    # ---------------------------------------------------------
    # Group BOM by target product(+optional ql)
    # ---------------------------------------------------------
    bom_by_target_exact: Dict[Tuple[str, str], List[dict]] = {}
    bom_by_target_product: Dict[str, List[dict]] = {}

    for r in bom_rows:
        out_pk = r["output_product_key"]
        out_ql = r["output_quality_level"]
        bom_by_target_product.setdefault(out_pk, []).append(r)
        if out_ql is not None and out_ql != "":
            bom_by_target_exact.setdefault((out_pk, out_ql), []).append(r)

    # ---------------------------------------------------------
    # Compute feasible transformed output
    # ---------------------------------------------------------
    transformed_output = []

    for (company_key, product_key, quality_level), capacity in sorted(capacity_map.items()):
        # Prefer exact target-Q L BOM if available, else product-only BOM
        requirements = bom_by_target_exact.get((product_key, quality_level))
        if requirements is None:
            requirements = bom_by_target_product.get(product_key, [])

        # No BOM inputs => raw / source product => output is just capacity
        if not requirements:
            feasible = capacity
        else:
            candidates = []

            for req in requirements:
                input_product_key = req["input_product_key"]
                input_quality_level = req["input_quality_level"]
                qty = float(req["input_units_per_output"])

                if qty <= 0:
                    raise ValueError(
                        f"product_bom invalid for output {product_key}: input_units_per_output must be > 0"
                    )

                # If BOM specifies input quality, use it; otherwise sum all inbound QL for that input product
                if input_quality_level is not None and input_quality_level != "":
                    inbound = inbound_by_target_input.get(
                        (company_key, product_key, quality_level, input_product_key, input_quality_level),
                        0.0,
                    )
                else:
                    inbound = 0.0
                    for (ck, tpk, tql, ipk, iql), amt in inbound_by_target_input.items():
                        if ck == company_key and tpk == product_key and tql == quality_level and ipk == input_product_key:
                            inbound += amt

                candidates.append(inbound / qty)

            feasible_from_inputs = min(candidates) if candidates else capacity
            feasible = min(capacity, feasible_from_inputs)

        transformed_output.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "quality_level": quality_level,
                "units_transformed_per_hour": max(0.0, feasible),
            }
        )

    out = dict(state, transformed_output=transformed_output)
    debug_rows(out, "transform", "transformed_output")
    return out

# ============================================================
# Stage: THROUGHPUT
# ============================================================

from typing import Dict, Tuple

def stage_transform(state: Dict[str, object]) -> Dict[str, object]:

    debug_log(state, "[transform] start")

    production_rows = state.get("production_intent", [])
    flow_rows = state.get("flow_allocation", [])
    bom_rows = _normalize_product_bom_rows(state.get("product_bom", []))

    # ---------------------------------------------------------
    # 1. Build total available supply map
    #    (production + inbound flow)
    # ---------------------------------------------------------
    available_supply: Dict[Tuple[str, str, str], float] = {}

    # Base production
    for r in production_rows:
        key = (
            _k(r["company_key"]),
            _k(r["product_key"]),
            _k(r["quality_level"]),
        )
        available_supply[key] = available_supply.get(key, 0.0) + float(r["units_produced_per_hour"])

    # Add inbound flow
    for r in flow_rows:
        key = (
            _k(r["company_key"]),
            _k(r["target_product_key"]),
            _k(r["target_quality_level"]),
        )
        available_supply[key] = available_supply.get(key, 0.0) + float(r["allocated_units_per_hour"])

    # ---------------------------------------------------------
    # 2. Group BOM by output product (+ optional QL)
    # ---------------------------------------------------------
    bom_by_product = {}

    for r in bom_rows:
        pk = r["output_product_key"]
        ql = r["output_quality_level"]

        key = (pk, ql) if ql else (pk, None)
        bom_by_product.setdefault(key, []).append(r)

    # ---------------------------------------------------------
    # 3. Compute transformed output
    # ---------------------------------------------------------
    transformed_output = []

    for (company_key, product_key, quality_level), capacity in sorted(available_supply.items()):

        # Get BOM requirements
        requirements = (
            bom_by_product.get((product_key, quality_level))
            or bom_by_product.get((product_key, None))
            or []
        )

        # ✅ Keep only real constraints
        requirements = [
            r for r in requirements
            if r["input_units_per_output"] > 0
        ]

        # -----------------------------------------------------
        # SOURCE PRODUCTS (no BOM constraints)
        # -----------------------------------------------------
        if not requirements:
            feasible = capacity

        # -----------------------------------------------------
        # TRANSFORM PRODUCTS
        # -----------------------------------------------------
        else:
            limits = []

            for req in requirements:
                input_pk = req["input_product_key"]
                input_ql = req["input_quality_level"]
                qty = req["input_units_per_output"]

                # ✅ total available input = supply map (NOT inbound-only)
                available_input = 0.0

                for (ck, pk, ql), amt in available_supply.items():
                    if ck != company_key:
                        continue
                    if pk != input_pk:
                        continue

                    # respect QL if specified
                    if input_ql and ql != input_ql:
                        continue

                    available_input += amt

                limits.append(available_input / qty)

            feasible = min(capacity, min(limits))

        transformed_output.append({
            "company_key": company_key,
            "product_key": product_key,
            "quality_level": quality_level,
            "units_transformed_per_hour": max(0.0, feasible),
        })

    out = dict(state, transformed_output=transformed_output)
    debug_rows(out, "transform", "transformed_output")
    return out

def stage_throughput(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[throughput] start")

    # ✅ Use transformed output (post-BOM production)
    produced_rows = state.get("transformed_output", [])
    flow_rows = state.get("flow_allocation", [])

    # ---------------------------------------------------------
    # Track routed OUT only (inputs being consumed)
    # ---------------------------------------------------------
    out_map: Dict[Tuple[str, str, str], float] = {}

    for r in flow_rows:
        key = (
            _k(r.get("company_key")),
            _k(r.get("source_product_key")),
            _k(r.get("source_quality_level")),
        )

        out_map[key] = out_map.get(key, 0.0) + float(r.get("allocated_units_per_hour", 0.0))

    # ---------------------------------------------------------
    # Compute throughput
    # ---------------------------------------------------------
    throughput = []

    for r in produced_rows:
        company_key = _k(r.get("company_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))

        produced = float(r.get("units_transformed_per_hour", 0.0))

        routed_out = out_map.get((company_key, product_key, quality_level), 0.0)

        # ✅ Remaining after internal consumption
        available = max(0.0, produced - routed_out)

        throughput.append({
            "company_key": company_key,
            "product_key": product_key,
            "quality_level": quality_level,

            "units_produced_per_hour": produced,
            "units_routed_out_per_hour": routed_out,
            "units_available_per_hour": available,
        })

    out = dict(state, throughput=throughput)
    debug_rows(out, "throughput", "throughput")
    return out
# ============================================================
# Stage: SALES
# ============================================================

def stage_sales(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[sales] start")

    throughput = state.get("throughput", [])
    sales_rows = state.get("sales_plan", [])

    sales_alloc = []

    for r in throughput:
        ck = _k(r["company_key"])
        pk = _k(r["product_key"])
        ql = _k(r["quality_level"])
        available = float(r["units_available_per_hour"])

        rows = [
            s for s in sales_rows
            if _k(s["company_key"]) == ck
            and _k(s["product_key"]) == pk
            and _k(s["quality_level"]) == ql
        ]

        results = apply_allocation_policy(
            produced=available,
            rows=rows,
            priority_field="priority",
            units_field="allocation_units_per_hour",
            frac_field="allocation_frac",
        )

        for row, amt in results:
            if amt > 0:
                sales_alloc.append({
                    "company_key": ck,
                    "product_key": pk,
                    "quality_level": ql,
                    "sales_channel_key": _k(row["sales_channel_key"]),
                    "allocated_units_per_hour": float(amt),
                })

    out = dict(state, sales_allocation=sales_alloc)
    debug_rows(out, "sales", "sales_allocation")
    return out


# ============================================================
# Stage: STORAGE
# ============================================================

def stage_storage(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[storage] start")

    throughput = state.get("throughput", [])
    sales = state.get("sales_allocation", [])

    sold_map = {}

    for r in sales:
        key = (_k(r["company_key"]), _k(r["product_key"]), _k(r["quality_level"]))
        sold_map[key] = sold_map.get(key, 0) + float(r["allocated_units_per_hour"])

    storage = []

    for r in throughput:
        key = (_k(r["company_key"]), _k(r["product_key"]), _k(r["quality_level"]))

        available = float(r["units_available_per_hour"])
        sold = sold_map.get(key, 0)

        storage.append({
            "company_key": key[0],
            "product_key": key[1],
            "quality_level": key[2],
            "units_stored_per_hour": max(0.0, available - sold),
        })

    out = dict(state, storage_state=storage)
    debug_rows(out, "storage", "storage_state")
    return out


# ============================================================
# Stage: DIAGNOSTICS
# ============================================================

def stage_diagnostics(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[diagnostics] start")

    throughput = state.get("throughput", [])
    storage = state.get("storage_state", [])

    storage_map = {
        (_k(r["company_key"]), _k(r["product_key"]), _k(r["quality_level"])):
        float(r["units_stored_per_hour"])
        for r in storage
    }

    diagnostics = []

    for r in throughput:
        ck = _k(r["company_key"])
        pk = _k(r["product_key"])
        ql = _k(r["quality_level"])
        available = float(r["units_available_per_hour"])

        stored = storage_map.get((ck, pk, ql), 0.0)

        diagnostics.append({
            "company_key": ck,
            "product_key": pk,
            "quality_level": ql,
            "available": _fmt_num(available),
            "stored": _fmt_num(stored),
            "is_oversupplied": stored > 0,
        })

    out = dict(state, diagnostics=diagnostics)
    debug_rows(out, "diagnostics", "diagnostics")
    return out


# ============================================================
# PIPELINE
# ============================================================

def run_pipeline(inputs: ContractInputs) -> ContractOutputs:

    state = stage_input(inputs)

    state = stage_scenario_resolution(state)
    state = stage_system_parameters(state)

    state = stage_structure(state)
    state = stage_allocation(state)
    state = stage_flow_plan(state)
    state = stage_transform(state)
    state = stage_throughput(state)
    state = stage_sales(state)
    state = stage_storage(state)
    state = stage_diagnostics(state)

    return ContractOutputs(output_tables={
        "diagnostics": state["diagnostics"],
        "throughput": state["throughput"],
    })