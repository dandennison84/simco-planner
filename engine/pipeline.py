from __future__ import annotations

from typing import Dict, List, Tuple

from engine.io_csv import ContractInputs, ContractOutputs
from engine.scenario import apply_scenario_delta, resolve_state_identity
from engine.flow_policy import apply_flow_policy
from engine.allocation_policy import apply_allocation_policy


EXCHANGE_KEY = 1
RETAIL_KEY = 2


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _fmt_num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else str(x)


def _group_by(rows: List[dict], key: str) -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = {}
    for r in rows:
        out.setdefault(_k(r.get(key)), []).append(r)
    return out


def _index_by(rows: List[dict], key: str) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for r in rows:
        out[_k(r.get(key))] = r
    return out


# =============================================================================
# Stage: INPUT
# =============================================================================
def stage_input(inputs: ContractInputs) -> Dict[str, List[dict]]:
    state: Dict[str, List[dict]] = {}
    state.update(inputs.input_tables)
    state.update(inputs.reference_tables)
    return state


# =============================================================================
# Stage: SCENARIO RESOLUTION
# =============================================================================
def stage_scenario_resolution(
    state: Dict[str, List[dict]]
) -> Tuple[Dict[str, List[dict]], str]:
    company_snapshot = state.get("company_snapshot", [])
    scenario_delta_rows = state.get("scenario_delta", [])

    patched = apply_scenario_delta(state, scenario_delta_rows)
    state_key, _scenario_key = resolve_state_identity(
        company_snapshot,
        scenario_delta_rows,
    )

    resolved: Dict[str, List[dict]] = {}
    for name, rows in patched.items():
        resolved[name] = [dict(r, state_key=state_key) for r in rows]

    return resolved, state_key


# =============================================================================
# Stage: STRUCTURE
# Minimal slice: requires explicit "capacity" per slot.
# =============================================================================
def stage_structure(state: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    structure_rows = state.get("structure_map", [])
    if not structure_rows:
        return dict(state, slot_capacity=[])

    if "capacity" not in structure_rows[0]:
        raise NotImplementedError(
            "STRUCTURE stage: building mechanics-based capacity is not implemented. "
            "Provide structure_map.capacity for now (explicit)."
        )

    slot_capacity = []
    for r in structure_rows:
        slot_key = _k(r.get("slot_key"))
        cap_raw = _k(r.get("capacity"))

        if slot_key == "" or cap_raw == "":
            raise ValueError(
                "structure_map requires slot_key and capacity for current STRUCTURE stage"
            )

        try:
            cap = float(cap_raw)
        except Exception:
            raise ValueError(
                f"structure_map.capacity must be numeric. "
                f"slot_key={slot_key}, capacity={cap_raw!r}"
            )

        slot_capacity.append(
            {
                "slot_key": slot_key,
                "capacity_per_hour": cap,
                "state_key": _k(r.get("state_key")),
            }
        )

    return dict(state, slot_capacity=slot_capacity)


# =============================================================================
# Stage: ALLOCATION
# Produces: production_intent at grain (product_key, quality_level)
# =============================================================================
def stage_allocation(state: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    assigns = state.get("slot_product_assignment", [])
    slot_capacity_rows = state.get("slot_capacity", [])

    cap_by_slot = {
        _k(r.get("slot_key")): float(r.get("capacity_per_hour"))
        for r in slot_capacity_rows
    }

    # Validate split integrity
    totals: Dict[str, float] = {}
    for r in assigns:
        slot = _k(r.get("slot_key"))
        frac_raw = _k(r.get("split_fraction"))

        if slot == "" or frac_raw == "":
            raise ValueError(
                "slot_product_assignment requires slot_key and split_fraction"
            )

        try:
            frac = float(frac_raw)
        except Exception:
            raise ValueError(
                f"split_fraction must be numeric. "
                f"slot_key={slot}, split_fraction={frac_raw!r}"
            )

        totals[slot] = totals.get(slot, 0.0) + frac

    for slot, total in totals.items():
        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"Split integrity violated: sum(split_fraction) != 1 "
                f"for slot_key={slot}. total={total}"
            )

    # Build production intent
    prod: Dict[Tuple[str, str], float] = {}
    for r in assigns:
        slot = _k(r.get("slot_key"))
        product = _k(r.get("product_key"))
        ql = _k(r.get("quality_level", "0"))
        frac = float(_k(r.get("split_fraction")))

        if slot not in cap_by_slot:
            raise ValueError(
                f"slot_product_assignment references unknown slot_key={slot} "
                f"(no capacity found)"
            )

        units = cap_by_slot[slot] * frac
        key = (product, ql)
        prod[key] = prod.get(key, 0.0) + units

    state_key = (
        _k(state.get("company_snapshot", [{}])[0].get("state_key"))
        if state.get("company_snapshot")
        else ""
    )

    production_intent = [
        {
            "product_key": pk,
            "quality_level": ql,
            "units_produced_per_hour": v,
            "state_key": state_key,
        }
        for (pk, ql), v in sorted(prod.items(), key=lambda x: (x[0][0], x[0][1]))
    ]

    return dict(state, production_intent=production_intent)


# =============================================================================
# Stage: FLOW POLICY
# =============================================================================
def stage_flow_policy(state: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    production_intent = state.get("production_intent", [])
    flow_policy_rows = state.get("flow_policy", [])

    flow_alloc = apply_flow_policy(production_intent, flow_policy_rows)
    return dict(state, flow_allocation=flow_alloc)


# =============================================================================
# Stage: THROUGHPUT
# throughput = produced - routed_out + routed_in
# =============================================================================
def stage_throughput(state: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    production_intent = state.get("production_intent", [])
    flow_alloc = state.get("flow_allocation", [])

    out_map: Dict[Tuple[str, str], float] = {}
    in_map: Dict[Tuple[str, str], float] = {}

    for r in flow_alloc:
        spk = _k(r.get("source_product_key"))
        sql = _k(r.get("source_quality_level", "0"))
        tpk = _k(r.get("target_product_key"))
        amt = float(_k(r.get("allocated_units_per_hour", "0")) or "0")

        out_map[(spk, sql)] = out_map.get((spk, sql), 0.0) + amt
        in_map[(tpk, sql)] = in_map.get((tpk, sql), 0.0) + amt

    throughput = []
    for r in production_intent:
        pk = _k(r.get("product_key"))
        ql = _k(r.get("quality_level"))
        produced = float(r.get("units_produced_per_hour"))
        routed_out = out_map.get((pk, ql), 0.0)
        routed_in = in_map.get((pk, ql), 0.0)
        available = produced - routed_out + routed_in

        throughput.append(
            {
                "product_key": pk,
                "quality_level": ql,
                "units_produced_per_hour": produced,
                "units_routed_out_per_hour": routed_out,
                "units_routed_in_per_hour": routed_in,
                "units_available_per_hour": available,
                "state_key": _k(r.get("state_key")),
            }
        )

    return dict(state, throughput=throughput)


# =============================================================================
# Stage: SALES
# Produces: sales_allocation
# =============================================================================
def stage_sales(state: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    company_rows = state.get("company_snapshot", [])
    throughput = state.get("throughput", [])
    sales_rows = state.get("sales_strategy", [])

    snapshot_key = _k(company_rows[0].get("snapshot_key")) if company_rows else ""

    # invariant: no duplicate sales_strategy rows
    seen = set()
    for s in sales_rows:
        key = (
            _k(s.get("snapshot_key")),
            _k(s.get("product_key")),
            _k(s.get("quality_level")),
            _k(s.get("sales_channel_key")),
        )
        if key in seen:
            raise ValueError(f"Duplicate sales_strategy row: {key}")
        seen.add(key)

    sales_allocation: List[dict] = []

    for r in throughput:
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))
        state_key = _k(r.get("state_key"))

        produced_raw = r.get("units_available_per_hour")
        try:
            produced = float(produced_raw)
        except Exception:
            raise ValueError(
                f"Invalid throughput.units_available_per_hour "
                f"for product_key={product_key}, quality_level={quality_level}: "
                f"{produced_raw!r}"
            )

        strategy_rows = [
            s
            for s in sales_rows
            if _k(s.get("snapshot_key")) == snapshot_key
            and _k(s.get("product_key")) == product_key
            and _k(s.get("quality_level")) == quality_level
        ]

        results = apply_allocation_policy(
            produced=produced,
            rows=strategy_rows,
            priority_field="priority",
            units_field="allocation_units_per_hour",
            frac_field="allocation_frac",
            priority_label="sales_strategy.priority",
            policy_label_fn=lambda row: (
                f"sales_strategy[{_k(row.get('snapshot_key'))},{_k(row.get('product_key'))},{_k(row.get('quality_level'))},{_k(row.get('sales_channel_key'))}]"
            ),
        )

        for row, allocated in results:
            channel = _k(row.get("sales_channel_key"))
            if channel not in {str(RETAIL_KEY), str(EXCHANGE_KEY)}:
                raise ValueError(f"Unknown sales_channel_key: {channel}")

            if allocated == 0:
                continue

            sales_allocation.append(
                {
                    "snapshot_key": snapshot_key,
                    "product_key": product_key,
                    "quality_level": quality_level,
                    "sales_channel_key": channel,
                    "allocated_units_per_hour": float(allocated),
                    "state_key": state_key,
                }
            )

    return dict(state, sales_allocation=sales_allocation)


# =============================================================================
# Stage: ECONOMICS (stub)
# =============================================================================
def stage_economics(state: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    return state


# =============================================================================
# Stage: DIAGNOSTICS
# Read-only projection from throughput + sales_allocation
# =============================================================================
def stage_diagnostics(state: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
    company_rows = state.get("company_snapshot", [])
    throughput = state.get("throughput", [])
    sales_allocation = state.get("sales_allocation", [])

    snapshot_key = _k(company_rows[0].get("snapshot_key")) if company_rows else ""

    sales_by_product_ql: Dict[Tuple[str, str], Dict[str, float]] = {}
    for r in sales_allocation:
        pk = _k(r.get("product_key"))
        ql = _k(r.get("quality_level"))
        ch = _k(r.get("sales_channel_key"))
        qty = float(r.get("allocated_units_per_hour", 0.0))

        sales_by_product_ql.setdefault(
            (pk, ql),
            {
                str(RETAIL_KEY): 0.0,
                str(EXCHANGE_KEY): 0.0,
            },
        )
        sales_by_product_ql[(pk, ql)][ch] = sales_by_product_ql[(pk, ql)].get(ch, 0.0) + qty

    diagnostics = []

    for r in throughput:
        pk = _k(r.get("product_key"))
        ql = _k(r.get("quality_level"))
        produced = float(r.get("units_available_per_hour"))

        retail_qty = sales_by_product_ql.get((pk, ql), {}).get(str(RETAIL_KEY), 0.0)
        exchange_qty = sales_by_product_ql.get((pk, ql), {}).get(str(EXCHANGE_KEY), 0.0)

        diagnostics.append(
            {
                "snapshot_key": snapshot_key,
                "product_key": pk,
                "produced_quantity": _fmt_num(produced),
                "retail_quantity": _fmt_num(retail_qty),
                "exchange_quantity": _fmt_num(exchange_qty),
                "bottleneck": "capacity",
            }
        )

    if not diagnostics and snapshot_key != "":
        diagnostics = [
            {
                "snapshot_key": snapshot_key,
                "product_key": "",
                "produced_quantity": "0",
                "retail_quantity": "0",
                "exchange_quantity": "0",
                "bottleneck": "capacity",
            }
        ]

    return dict(state, diagnostics=diagnostics)


# =============================================================================
# MAIN PIPELINE
# =============================================================================
def run_pipeline(inputs: ContractInputs) -> ContractOutputs:
    state = stage_input(inputs)
    state, _state_key = stage_scenario_resolution(state)
    state = stage_structure(state)
    state = stage_allocation(state)
    state = stage_flow_policy(state)
    state = stage_throughput(state)
    state = stage_sales(state)
    state = stage_economics(state)
    state = stage_diagnostics(state)

    output_tables: Dict[str, List[dict]] = {
        "diagnostics": state.get("diagnostics", []),
        "guidance": state.get("guidance", []),
        "signal_evidence": state.get("signal_evidence", []),
        "throughput": state.get("throughput", []),
    }

    return ContractOutputs(output_tables=output_tables)