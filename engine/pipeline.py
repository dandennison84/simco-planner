from __future__ import annotations

from typing import Dict, List, Tuple

from engine.io_csv import ContractInputs, ContractOutputs
from engine.scenario import apply_scenario_delta
from engine.debug import debug_log, debug_rows
from engine.stages.input import stage_input
from engine.stages.system_parameters import stage_system_parameters
from engine.stages.structure import stage_structure
from engine.stages.production_allocation import stage_production_allocation


# ============================================================
# Helpers
# ============================================================

def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _to_float(x, default: float = 0.0) -> float:
    if x is None:
        return default
    s = str(x).strip()
    if s == "":
        return default
    return float(s)


def _to_int(x, default: int = 0) -> int:
    if x is None:
        return default
    s = str(x).strip()
    if s == "":
        return default
    return int(s)


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
                "input_units_per_output": _to_float(r.get(qty_col)),
                "output_quality_level": _k(r.get(output_quality_col)) if output_quality_col else "",
                "input_quality_level": _k(r.get(input_quality_col)) if input_quality_col else "",
            }
        )

    return normalized


# ============================================================
# Stage: SCENARIO
# ============================================================

def stage_scenario_resolution(state: Dict[str, object]) -> Dict[str, object]:
    scenario_delta_rows = state.get("scenario_delta", [])
    if not scenario_delta_rows:
        return state
    debug_log(state, "[scenario_resolution] start")
    return apply_scenario_delta(state, scenario_delta_rows)


# ============================================================
# Stage: PRODUCT BOM CONSUMPTION
# ============================================================

def stage_product_bom_consumption(state: Dict[str, object]) -> Dict[str, object]:
    """
    Computes direct BOM consumption implied by unconstrained production_intent.

    Inputs:
      - production_intent
      - product_bom

    Output:
      - product_bom_consumption

    Grain:
      (company_key, product_key, quality_level)

    Rules:
      - consumption = sum(units_produced_per_hour * input_units_per_output)
      - if BOM row specifies output_quality_level, it only matches that output QL
      - if BOM row specifies input_quality_level, that becomes the consumption QL
      - otherwise input consumption QL defaults to produced row quality_level
    """
    debug_log(state, "[product_bom_consumption] start")

    production_rows = state.get("production_intent", [])
    bom_rows = _normalize_product_bom_rows(state.get("product_bom", []))

    consumption_map: Dict[Tuple[str, str, str], float] = {}

    # index BOM by output product (+ optional exact QL)
    bom_by_output_product: Dict[str, List[dict]] = {}
    bom_by_output_exact: Dict[Tuple[str, str], List[dict]] = {}

    for r in bom_rows:
        out_pk = _k(r["output_product_key"])
        out_ql = _k(r["output_quality_level"])

        bom_by_output_product.setdefault(out_pk, []).append(r)
        if out_ql != "":
            bom_by_output_exact.setdefault((out_pk, out_ql), []).append(r)

    for row in production_rows:
        company_key = _k(row.get("company_key"))
        output_product_key = _k(row.get("product_key"))
        output_quality_level = _k(row.get("quality_level"))
        produced_units = _to_float(row.get("units_produced_per_hour"))

        requirements = bom_by_output_exact.get((output_product_key, output_quality_level))
        if requirements is None:
            requirements = bom_by_output_product.get(output_product_key, [])

        for req in requirements:
            qty = _to_float(req.get("input_units_per_output"))
            if qty <= 0:
                raise ValueError(
                    f"product_bom invalid for output_product_key={output_product_key}: "
                    f"input_units_per_output must be > 0"
                )

            input_product_key = _k(req.get("input_product_key"))
            input_quality_level = _k(req.get("input_quality_level")) or output_quality_level

            key = (company_key, input_product_key, input_quality_level)
            consumption_map[key] = consumption_map.get(key, 0.0) + (produced_units * qty)

    product_bom_consumption = [
        {
            "company_key": company_key,
            "product_key": product_key,
            "quality_level": quality_level,
            "units_consumed_per_hour": units,
        }
        for (company_key, product_key, quality_level), units in sorted(consumption_map.items())
    ]

    out = dict(state, product_bom_consumption=product_bom_consumption)
    debug_rows(out, "product_bom_consumption", "product_bom_consumption")
    return out


# ============================================================
# Stage: BALANCE
# ============================================================

def stage_balance(state: Dict[str, object]) -> Dict[str, object]:
    """
    Computes net balance from produced vs consumed quantities.

    Inputs:
      - production_intent
      - product_bom_consumption

    Outputs:
      - balance_plan

    Grain:
      (company_key, product_key, quality_level)

    Rules:
      net = produced - consumed
      surplus = max(net, 0)
      shortage = max(-net, 0)
    """
    debug_log(state, "[balance] start")

    production_rows = state.get("production_intent", [])
    consumption_rows = state.get("product_bom_consumption", [])

    produced_map: Dict[Tuple[str, str, str], float] = {}
    consumed_map: Dict[Tuple[str, str, str], float] = {}

    for r in production_rows:
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )
        produced_map[key] = produced_map.get(key, 0.0) + _to_float(r.get("units_produced_per_hour"))

    for r in consumption_rows:
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )
        consumed_map[key] = consumed_map.get(key, 0.0) + _to_float(r.get("units_consumed_per_hour"))

    all_keys = sorted(set(produced_map.keys()) | set(consumed_map.keys()))

    balance_plan = []
    for key in all_keys:
        company_key, product_key, quality_level = key
        produced = produced_map.get(key, 0.0)
        consumed = consumed_map.get(key, 0.0)
        net = produced - consumed

        balance_plan.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "quality_level": quality_level,
                "units_produced_per_hour": produced,
                "units_consumed_per_hour": consumed,
                "net_units_per_hour": net,
                "surplus_units_per_hour": max(net, 0.0),
                "shortage_units_per_hour": max(-net, 0.0),
            }
        )

    out = dict(state, balance_plan=balance_plan)
    debug_rows(out, "balance", "balance_plan")
    return out


# ============================================================
# Stage: CLEARING ALLOCATION
# ============================================================

def stage_clearing_allocation(state: Dict[str, object]) -> Dict[str, object]:
    """
    Allocates surplus / shortage across channels according to clearing_plan priority.

    Inputs:
      - balance_plan
      - clearing_plan
      - channel

    Outputs:
      - clearing_result
      - clearing_remainder

    Grain:
      clearing_result:
        (company_key, product_key, quality_level, priority, channel_key)

      clearing_remainder:
        (company_key, product_key, quality_level)

    Rules:
      - if net > 0: only channels with can_sink = TRUE may receive allocation
      - if net < 0: only channels with can_source = TRUE may receive allocation
      - rows processed in ascending priority
      - if multiple valid rows share the same priority, allocation is split evenly
      - no weights yet
      - caps can be added later; currently unlimited
      - remainder is emitted explicitly
    """
    debug_log(state, "[clearing_allocation] start")

    balance_rows = state.get("balance_plan", [])
    clearing_rows = state.get("clearing_plan", [])
    channel_rows = state.get("channel", [])

    # ---------------------------------------------------------
    # Channel domain
    # ---------------------------------------------------------
    channel_index = {
        _k(r.get("channel_key")): r
        for r in channel_rows
    }

    # ---------------------------------------------------------
    # Group clearing rows by product grain
    # ---------------------------------------------------------
    clearing_by_product: Dict[Tuple[str, str, str], List[dict]] = {}

    for r in clearing_rows:
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )
        clearing_by_product.setdefault(key, []).append(r)

    # ---------------------------------------------------------
    # Allocate
    # ---------------------------------------------------------
    clearing_result: List[dict] = []
    clearing_remainder: List[dict] = []

    for bal in balance_rows:
        company_key = _k(bal.get("company_key"))
        product_key = _k(bal.get("product_key"))
        quality_level = _k(bal.get("quality_level"))
        net = _to_float(bal.get("net_units_per_hour"))

        if abs(net) <= 1e-12:
            continue

        direction = "sink" if net > 0 else "source"
        remaining = abs(net)

        rules = clearing_by_product.get((company_key, product_key, quality_level), [])
        if not rules:
            clearing_remainder.append(
                {
                    "company_key": company_key,
                    "product_key": product_key,
                    "quality_level": quality_level,
                    "direction": direction,
                    "remaining_units_per_hour": remaining,
                }
            )
            continue

        # sort by priority
        rules_sorted = sorted(rules, key=lambda r: _to_int(r.get("priority")))

        # group by priority
        priority_groups: Dict[int, List[dict]] = {}
        for r in rules_sorted:
            p = _to_int(r.get("priority"))
            priority_groups.setdefault(p, []).append(r)

        for priority in sorted(priority_groups.keys()):
            tier_rows = priority_groups[priority]

            valid_rows: List[dict] = []
            for r in tier_rows:
                channel_key = _k(r.get("channel_key"))
                if channel_key not in channel_index:
                    raise ValueError(
                        f"clearing_plan references unknown channel_key={channel_key}"
                    )

                ch = channel_index[channel_key]
                can_source = bool(ch.get("can_source"))
                can_sink = bool(ch.get("can_sink"))

                if direction == "source" and can_source:
                    valid_rows.append(r)
                elif direction == "sink" and can_sink:
                    valid_rows.append(r)

            if not valid_rows:
                continue

            # split evenly across valid rows within the tier
            share = remaining / float(len(valid_rows))

            for r in valid_rows:
                channel_key = _k(r.get("channel_key"))

                if share <= 0:
                    continue

                clearing_result.append(
                    {
                        "company_key": company_key,
                        "product_key": product_key,
                        "quality_level": quality_level,
                        "priority": priority,
                        "channel_key": channel_key,
                        "direction": direction,
                        "allocated_units_per_hour": share,
                    }
                )

            remaining = 0.0
            break

        if remaining > 1e-12:
            clearing_remainder.append(
                {
                    "company_key": company_key,
                    "product_key": product_key,
                    "quality_level": quality_level,
                    "direction": direction,
                    "remaining_units_per_hour": remaining,
                }
            )

    out = dict(
        state,
        clearing_result=clearing_result,
        clearing_remainder=clearing_remainder,
    )
    debug_rows(out, "clearing_allocation", "clearing_result")
    debug_rows(out, "clearing_allocation", "clearing_remainder")
    return out


# ============================================================
# PIPELINE
# ============================================================

def run_pipeline(inputs: ContractInputs) -> ContractOutputs:
    state = stage_input(inputs)
    state = stage_scenario_resolution(state)
    state = stage_system_parameters(state)
    state = stage_structure(state)
    state = stage_production_allocation(state)
    state = stage_product_bom_consumption(state)
    state = stage_balance(state)
    state = stage_clearing_allocation(state)

    return ContractOutputs(
        output_tables={
            "production_intent": state["production_intent"],
            "product_bom_consumption": state["product_bom_consumption"],
            "balance_plan": state["balance_plan"],
            "clearing_result": state["clearing_result"],
            "clearing_remainder": state["clearing_remainder"],
        }
    )