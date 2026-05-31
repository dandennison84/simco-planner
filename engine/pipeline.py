from __future__ import annotations

from typing import Dict, List, Tuple

from engine.io_csv import ContractInputs, ContractOutputs
from engine.scenario import apply_scenario_delta
from engine.flow_policy import apply_flow_policy
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
# Grain: (company_key, map_structure_key, slot_key)
# =============================================================================
def stage_structure(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[structure] start")

    structure_rows = state.get("map_structure", [])
    company_rows = state.get("company", [])

    if not structure_rows:
        out = dict(state, slot_context=[])
        debug_rows(out, "structure", "slot_context")
        return out

    company_by_map = {
        _k(r.get("map_structure_key")): _k(r.get("company_key"))
        for r in company_rows
    }

    slot_context = []

    for r in structure_rows:
        map_key = _k(r.get("map_structure_key"))
        slot_key = _k(r.get("slot_key"))
        building_key = _k(r.get("building_key"))
        building_level = r.get("building_level")
        robots_installed = r.get("robots_installed")

        if map_key == "" or slot_key == "":
            raise ValueError("map_structure requires map_structure_key and slot_key")

        company_key = company_by_map.get(map_key, "")
        if company_key == "":
            raise ValueError(f"No company found for map_structure_key={map_key}")

        slot_context.append({
            "company_key": company_key,
            "map_structure_key": map_key,
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

    slot_by_map_slot = {
        (_k(r.get("map_structure_key")), _k(r.get("slot_key"))): r
        for r in slot_context_rows
    }

    product_by_key = {
        _k(r.get("product_key")): r
        for r in product_rows
    }

    totals: Dict[Tuple[str, str], float] = {}

    for r in assigns:
        map_key = _k(r.get("map_structure_key"))
        slot = _k(r.get("slot_key"))
        frac = float(r.get("production_split_fraction"))

        totals[(map_key, slot)] = totals.get((map_key, slot), 0.0) + frac

    for (map_key, slot), total in totals.items():
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"Split must equal 1 for map_structure_key={map_key}, slot={slot}, total={total}"
            )

    produced: Dict[Tuple[str, str, str], float] = {}

    for r in assigns:
        map_key = _k(r.get("map_structure_key"))
        slot = _k(r.get("slot_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))
        split_frac = float(r.get("production_split_fraction"))

        slot_key = (map_key, slot)
        if slot_key not in slot_by_map_slot:
            raise ValueError(f"No slot context for map_structure_key={map_key}, slot={slot}")

        slot_ctx = slot_by_map_slot[slot_key]

        if product_key not in product_by_key:
            raise ValueError(f"Missing product_key={product_key}")

        product = product_by_key[product_key]

        slot_building_key = _k(slot_ctx.get("building_key"))
        product_building_key = _k(product.get("building_key"))
        if slot_building_key != "" and product_building_key != "" and slot_building_key != product_building_key:
            raise ValueError(
                f"Product/building mismatch: map_structure_key={map_key}, slot={slot}, "
                f"slot building_key={slot_building_key}, product building_key={product_building_key}"
            )

        building_level = float(slot_ctx.get("building_level"))
        baseline_output_per_hour = float(product.get("baseline_output_per_hour"))

        units = building_level * baseline_output_per_hour * split_frac

        company_key = _k(slot_ctx.get("company_key"))

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
# Stage: FLOW POLICY
# Applies per company to avoid cross-company contamination
# =============================================================================
def stage_flow_policy(state: Dict[str, object]) -> Dict[str, object]:
    debug_log(state, "[flow_policy] start")

    production_intent = state.get("production_intent", [])
    flow_policy_rows = state.get("flow_policy", [])

    grouped: Dict[str, List[dict]] = {}
    for r in production_intent:
        grouped.setdefault(_k(r.get("company_key")), []).append(r)

    flow_allocation: List[dict] = []

    for company_key, rows in grouped.items():
        alloc = apply_flow_policy(rows, flow_policy_rows)

        flow_allocation.extend([
            dict(r, company_key=company_key)
            for r in alloc
        ])

    out = dict(state, flow_allocation=flow_allocation)
    debug_rows(out, "flow_policy", "flow_allocation")
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
        amt = float(_k(r.get("allocated_units_per_hour", "0")) or "0")

        out_map[(company_key, source_product_key, source_quality_level)] = \
            out_map.get((company_key, source_product_key, source_quality_level), 0.0) + amt

        in_map[(company_key, target_product_key, source_quality_level)] = \
            in_map.get((company_key, target_product_key, source_quality_level), 0.0) + amt

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

    exchange_key, retail_key = _resolve_sales_channel_keys(state)

    sales_by_product: Dict[Tuple[str, str, str], Dict[str, float]] = {}

    for r in sales_allocation:
        company_key = _k(r.get("company_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))
        channel_key = _k(r.get("sales_channel_key"))
        qty = float(r.get("allocated_units_per_hour", 0.0))

        sales_by_product.setdefault(
            (company_key, product_key, quality_level),
            {
                retail_key: 0.0,
                exchange_key: 0.0,
            },
        )
        sales_by_product[(company_key, product_key, quality_level)][channel_key] = \
            sales_by_product[(company_key, product_key, quality_level)].get(channel_key, 0.0) + qty

    diagnostics = []

    for r in throughput:
        company_key = _k(r.get("company_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))
        available = float(r.get("units_available_per_hour"))

        retail_qty = sales_by_product.get(
            (company_key, product_key, quality_level), {}
        ).get(retail_key, 0.0)

        exchange_qty = sales_by_product.get(
            (company_key, product_key, quality_level), {}
        ).get(exchange_key, 0.0)

        diagnostics.append({
            "company_key": company_key,
            "product_key": product_key,
            "produced_quantity": _fmt_num(available),
            "retail_quantity": _fmt_num(retail_qty),
            "exchange_quantity": _fmt_num(exchange_qty),
            "bottleneck": "capacity",
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
    state = stage_flow_policy(state)
    state = stage_throughput(state)
    state = stage_sales(state)
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