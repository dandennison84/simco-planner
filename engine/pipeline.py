from __future__ import annotations

from typing import Dict, List, Tuple

from engine.io_csv import ContractInputs, ContractOutputs
from engine.scenario import apply_scenario_delta
from engine.flow_plan import apply_flow_plan
from engine.allocation_policy import apply_allocation_policy
from engine.debug import debug_log, debug_enabled,debug_rows


# =============================================================================
# Helpers
# =============================================================================
def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _fmt_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)

def _overlay_table(
    base_rows: List[dict],
    override_rows: List[dict],
    key_fields: List[str],
) -> List[dict]:
    if not override_rows:
        return list(base_rows)

    override_keys = {
        tuple(_k(row.get(k)) for k in key_fields)
        for row in override_rows
    }

    base_filtered = [
        row
        for row in base_rows
        if tuple(_k(row.get(k)) for k in key_fields) not in override_keys
    ]

    return base_filtered + list(override_rows)


def _resolve_sales_channel_keys(state: Dict[str, object]) -> Tuple[str, str]:
    """
    Resolve exchange / retail channel keys from reference data instead of hardcoding them.
    """
    rows = state.get("sales_channel", [])

    by_name = {
        _k(r.get("sales_channel_name")).lower(): _k(r.get("sales_channel_key"))
        for r in rows
    }

    exchange_key = by_name.get("exchange", "")
    retail_key = by_name.get("retail", "")

    return exchange_key, retail_key


# =============================================================================
# Stage: INPUT
# =============================================================================
def stage_input(inputs: ContractInputs) -> Dict[str, object]:
    state: Dict[str, object] = {}
    state.update(inputs.input_tables)
    state.update(inputs.reference_tables)
    state["_meta"] = {}
    return state


# =============================================================================
# Stage: SYSTEM PARAMETERS
# =============================================================================
def stage_system_parameters(state: Dict[str, object]) -> Dict[str, object]:
    rows = state.get("system_parameters", [])

    param_map = {
        _k(r.get("parameter_key")): _k(r.get("parameter_value"))
        for r in rows
    }

    meta = dict(state.get("_meta", {}))
    meta["system_parameters_map"] = param_map

    out = dict(state, _meta=meta)

    # ✅ Level 1 debug
    count = len(param_map)
    debug_log(out, f"[system_parameters] loaded: count={count}")

    # ✅ Optional: show keys if small (safe + useful)
    if count > 0 and count <= 10:
        keys = ", ".join(sorted(param_map.keys()))
        debug_log(out, f"[system_parameters] keys: {keys}")

    return out


# =============================================================================
# Stage: DEBUG INPUT SUMMARY
# =============================================================================

def stage_debug_input_summary(state: Dict[str, object]) -> Dict[str, object]:
    """
    Debug levels:

    Level 1:
        total table count only

    Level 2:
        individual table row counts
    """

    # ---------------------------------------------------------
    # LEVEL 1: total table count
    # ---------------------------------------------------------
    if debug_enabled(state, 1):
        table_count = sum(
            1
            for name, rows in state.items()
            if not name.startswith("_") and isinstance(rows, list)
        )

        debug_log(state, f"[stage_input] tables loaded: count={table_count}")

    # ---------------------------------------------------------
    # LEVEL 2: per-table row counts
    # ---------------------------------------------------------
    if debug_enabled(state, 2):
        for name, rows in sorted(state.items()):
            if name.startswith("_"):
                continue
            if not isinstance(rows, list):
                continue

            debug_log(state, f"  - {name}: rows={len(rows)}")

    return state

# =============================================================================
# Stage: PRICING OVERLAY
# =============================================================================
def stage_pricing_overlay(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[pricing_overlay] start")

    exchange_final = _overlay_table(
        state.get("exchange_prices", []),
        state.get("override_exchange_prices", []),
        ["realm_key", "product_key", "quality_level"],
    )

    retail_final = _overlay_table(
        state.get("retail_prices", []),
        state.get("override_retail_prices", []),
        ["realm_key", "product_key", "quality_level"],
    )

    out = dict(
        state,
        exchange_prices_final=exchange_final,
        retail_prices_final=retail_final,
    )

    debug_rows(out, "pricing_overlay", "exchange_prices_final")
    debug_rows(out, "pricing_overlay", "retail_prices_final")

    return out


# =============================================================================
# Stage: SCENARIO RESOLUTION
# =============================================================================
def stage_scenario_resolution(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[scenario_resolution] start")

    scenario_delta_rows = state.get("scenario_delta", [])
    patched = apply_scenario_delta(state, scenario_delta_rows)

    debug_log(
        state,
        f"[scenario_resolution] scenario_delta rows={len(scenario_delta_rows)}"
    )

    return patched


# =============================================================================
# Stage: STRUCTURE
# Derive normalized slot context from map_structure + company
#
# Grain: (company_key, slot_key)
# =============================================================================
def stage_structure(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[structure] start")

    structure_rows = state.get("map_structure", [])

    if not structure_rows:
        out = dict(state, slot_context=[])
        debug_rows(out, "structure", "slot_context")
        return out

    slot_context = []

    for r in structure_rows:
        company_key = _k(r.get("company_key"))
        slot_key = _k(r.get("slot_key"))
        building_key = _k(r.get("building_key"))
        building_level = r.get("building_level")
        robots_installed = r.get("robots_installed")

        if company_key == "" or slot_key == "":
            raise ValueError("map_structure requires company_key and slot_key")

        slot_context.append({
            "company_key": company_key,
            "slot_key": slot_key,
            "building_key": building_key,
            "building_level": float(building_level),
            "robots_installed": robots_installed,
        })

    out = dict(state, slot_context=slot_context)
    debug_rows(out, "structure", "slot_context")
    return out


# =============================================================================
# Stage: ALLOCATION
# Derive production directly from:
#   building_level * baseline_output_per_hour * production_split_fraction
#
# Grain output: (company_key, product_key, quality_level)
# =============================================================================
def stage_allocation(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[allocation] start")

    assigns = state.get("production_plan", [])
    slot_context_rows = state.get("slot_context", [])
    product_rows = state.get("product", [])

    slot_by_company_slot = {
        (_k(r.get("company_key")), _k(r.get("slot_key"))): r
        for r in slot_context_rows
    }

    product_by_key = {
        _k(r.get("product_key")): r
        for r in product_rows
    }

    # ---------------------------------------------------------
    # Validate splits sum to 1 per slot
    # ---------------------------------------------------------
    totals: Dict[Tuple[str, str], float] = {}

    for r in assigns:
        company_key = _k(r.get("company_key"))
        slot = _k(r.get("slot_key"))
        frac = float(r.get("production_split_fraction"))

        totals[(company_key, slot)] = totals.get((company_key, slot), 0.0) + frac

    for (company_key, slot), total in totals.items():
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"Split must equal 1 for company_key={company_key}, slot={slot}, total={total}"
            )

    # ---------------------------------------------------------
    # Compute production
    # ---------------------------------------------------------
    produced: Dict[Tuple[str, str, str], float] = {}

    for r in assigns:
        company_key = _k(r.get("company_key"))
        slot = _k(r.get("slot_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))
        split_frac = float(r.get("production_split_fraction"))

        slot_key = (company_key, slot)
        if slot_key not in slot_by_company_slot:
            raise ValueError(f"No slot context for company_key={company_key}, slot={slot}")

        slot_ctx = slot_by_company_slot[slot_key]

        if product_key not in product_by_key:
            raise ValueError(f"Missing product_key={product_key}")

        product = product_by_key[product_key]

        # building match
        slot_building_key = _k(slot_ctx.get("building_key"))
        product_building_key = _k(product.get("building_key"))

        if (
            slot_building_key != ""
            and product_building_key != ""
            and slot_building_key != product_building_key
        ):
            raise ValueError(
                f"Product/building mismatch: company_key={company_key}, slot={slot}, "
                f"slot building_key={slot_building_key}, product building_key={product_building_key}"
            )

        building_level = float(slot_ctx.get("building_level"))
        baseline_output_per_hour = float(product.get("baseline_output_per_hour"))

        units = building_level * baseline_output_per_hour * split_frac

        grain = (company_key, product_key, quality_level)
        produced[grain] = produced.get(grain, 0.0) + units

    production_intent = [
        {
            "company_key": company_key,
            "product_key": product_key,
            "quality_level": quality_level,
            "units_produced_per_hour": units,
        }
        for (company_key, product_key, quality_level), units in sorted(produced.items())
    ]

    out = dict(state, production_intent=production_intent)
    debug_rows(out, "allocation", "production_intent")
    return out

# =============================================================================
# Stage: FLOW PLAN
# Applies per company to avoid cross-company contamination
# =============================================================================
def stage_flow_plan(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[flow_plan] start")

    production_intent = state.get("production_intent", [])
    flow_plan_rows = state.get("flow_plan", [])

    grouped: Dict[str, List[dict]] = {}
    for r in production_intent:
        grouped.setdefault(_k(r.get("company_key")), []).append(r)

    flow_allocation: List[dict] = []

    for company_key, rows in grouped.items():
        alloc = apply_flow_plan(rows, flow_plan_rows, company_key=company_key)

        flow_allocation.extend(alloc)

    out = dict(state, flow_allocation=flow_allocation)
    debug_rows(out, "flow_plan", "flow_allocation")
    return out

# =============================================================================
# Stage: THROUGHPUT
# throughput = produced - routed_out + routed_in
#
# Grain: (company_key, product_key, quality_level)
# =============================================================================
def stage_throughput(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[throughput] start")

    production_intent = state.get("production_intent", [])
    flow_alloc = state.get("flow_allocation", [])

    out_map: Dict[Tuple[str, str, str], float] = {}
    in_map: Dict[Tuple[str, str, str], float] = {}

    for r in flow_alloc:
        company_key = _k(r.get("company_key"))
        source_product_key = _k(r.get("source_product_key"))
        source_quality_level = _k(r.get("source_quality_level", "0"))
        target_product_key = _k(r.get("target_product_key"))
        target_quality_level = _k(r.get("target_quality_level"))
        amt = float(_k(r.get("allocated_units_per_hour", "0")) or "0")

        out_map[(company_key, source_product_key, source_quality_level)] = \
            out_map.get((company_key, source_product_key, source_quality_level), 0.0) + amt

        in_map[(company_key, target_product_key, target_quality_level)] = \
            in_map.get((company_key, target_product_key, target_quality_level), 0.0) + amt

    throughput = []

    for r in production_intent:
        company_key = _k(r.get("company_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))
        produced = float(r.get("units_produced_per_hour"))

        routed_out = out_map.get((company_key, product_key, quality_level), 0.0)
        routed_in = in_map.get((company_key, product_key, quality_level), 0.0)
        available = produced - routed_out + routed_in

        throughput.append({
            "company_key": company_key,
            "product_key": product_key,
            "quality_level": quality_level,
            "units_produced_per_hour": produced,
            "units_routed_out_per_hour": routed_out,
            "units_routed_in_per_hour": routed_in,
            "units_available_per_hour": available,
        })

    out = dict(state, throughput=throughput)
    debug_rows(out, "throughput", "throughput")
    return out


# =============================================================================
# Stage: SALES
# Grain input/output per company
# =============================================================================
def stage_sales(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[sales] start")

    throughput = state.get("throughput", [])
    sales_rows = state.get("sales_plan", [])

    sales_allocation = []

    for r in throughput:
        company_key = _k(r.get("company_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))
        available = float(r.get("units_available_per_hour"))

        strategy_rows = [
            s for s in sales_rows
            if _k(s.get("company_key")) == company_key
            and _k(s.get("product_key")) == product_key
            and _k(s.get("quality_level")) == quality_level
        ]

        results = apply_allocation_policy(
            produced=available,
            rows=strategy_rows,
            priority_field="priority",
            units_field="allocation_units_per_hour",
            frac_field="allocation_frac",
            priority_label="sales_plan.priority",
            policy_label_fn=lambda row: (
                f"sales_plan[{company_key},{product_key},{quality_level},{_k(row.get('sales_channel_key'))}]"
            ),
        )

        for row, allocated in results:
            if allocated == 0:
                continue

            sales_allocation.append({
                "company_key": company_key,
                "product_key": product_key,
                "quality_level": quality_level,
                "sales_channel_key": _k(row.get("sales_channel_key")),
                "allocated_units_per_hour": float(allocated),
            })

    out = dict(state, sales_allocation=sales_allocation)
    debug_rows(out, "sales", "sales_allocation")
    return out

# =============================================================================
# Stage: STORAGE
# =============================================================================
def stage_storage(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[storage] start")

    throughput = state.get("throughput", [])
    sales = state.get("sales_allocation", [])

    sold_map: Dict[tuple[str, str, str], float] = {}

    for r in sales:
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )
        sold_map[key] = sold_map.get(key, 0.0) + float(r.get("allocated_units_per_hour"))

    storage_state = []

    for r in throughput:
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )

        available = float(r.get("units_available_per_hour"))
        sold = sold_map.get(key, 0.0)

        storage_state.append({
            "company_key": key[0],
            "product_key": key[1],
            "quality_level": key[2],
            "units_stored_per_hour": max(0.0, available - sold),
        })

    out = dict(state, storage_state=storage_state)
    debug_rows(out, "storage", "storage_state")
    return out

# =============================================================================
# Stage: ECONOMICS (stub)
# =============================================================================
def stage_economics(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[economics] start")
    debug_log(state, "[economics] stub - no calculations applied")
    return state


# =============================================================================
# Stage: DIAGNOSTICS
# Grain: (company_key, product_key, quality_level)
# =============================================================================
def stage_diagnostics(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[diagnostics] start")

    throughput = state.get("throughput", [])
    sales_allocation = state.get("sales_allocation", [])
    storage = state.get("storage_state", [])

    exchange_key, retail_key = _resolve_sales_channel_keys(state)

    # ---------------------------------------------------------
    # BUILD SALES MAP
    # ---------------------------------------------------------
    sales_by_product: Dict[Tuple[str, str, str], Dict[str, float]] = {}

    for r in sales_allocation:
        company_key = _k(r.get("company_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))
        channel_key = _k(r.get("sales_channel_key"))
        qty = float(r.get("allocated_units_per_hour", 0.0))

        key = (company_key, product_key, quality_level)

        if key not in sales_by_product:
            sales_by_product[key] = {
                retail_key: 0.0,
                exchange_key: 0.0,
            }

        sales_by_product[key][channel_key] = (
            sales_by_product[key].get(channel_key, 0.0) + qty
        )

    # ---------------------------------------------------------
    # BUILD STORAGE MAP
    # ---------------------------------------------------------
    storage_map: Dict[Tuple[str, str, str], float] = {}

    for r in storage:
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )

        storage_map[key] = float(r.get("units_stored_per_hour", 0.0))

    # ---------------------------------------------------------
    # BUILD DIAGNOSTICS
    # ---------------------------------------------------------
    diagnostics = []

    for r in throughput:
        company_key = _k(r.get("company_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))

        available = float(r.get("units_available_per_hour"))

        key = (company_key, product_key, quality_level)

        retail_qty = sales_by_product.get(key, {}).get(retail_key, 0.0)
        exchange_qty = sales_by_product.get(key, {}).get(exchange_key, 0.0)
        stored_qty = storage_map.get(key, 0.0)

        diagnostics.append({
            "company_key": company_key,
            "product_key": product_key,
            "quality_level": quality_level,

            # NOTE: this is AVAILABLE, not raw produced
            "available_quantity": _fmt_num(available),

            "retail_quantity": _fmt_num(retail_qty),
            "exchange_quantity": _fmt_num(exchange_qty),
            "stored_quantity": _fmt_num(stored_qty),

            "bottleneck": "capacity",  # placeholder (next phase)
        })

    out = dict(state, diagnostics=diagnostics)
    debug_rows(out, "diagnostics", "diagnostics")
    return out


# =============================================================================
# MAIN PIPELINE
# =============================================================================
def run_pipeline(inputs: ContractInputs) -> ContractOutputs:
    state = stage_input(inputs)

    debug_log(state, "[pipeline] start")

    state = stage_scenario_resolution(state)
    state = stage_system_parameters(state)
    state = stage_debug_input_summary(state)
    state = stage_pricing_overlay(state)

    state = stage_structure(state)
    state = stage_allocation(state)
    state = stage_flow_plan(state)
    state = stage_throughput(state)
    state = stage_sales(state)
    state = stage_storage(state)
    state = stage_economics(state)
    state = stage_diagnostics(state)

    outputs = ContractOutputs(output_tables={
        "diagnostics": state.get("diagnostics", []),
        "guidance": state.get("guidance", []),
        "signal_evidence": state.get("signal_evidence", []),
        "throughput": state.get("throughput", []),
    })

    debug_log(state, "[pipeline] complete")

    return outputs