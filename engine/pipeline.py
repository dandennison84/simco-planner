from __future__ import annotations

from typing import Dict

from engine.io_csv import ContractInputs, ContractOutputs
from engine.scenario import apply_scenario_delta
from engine.debug import debug_log

from engine.stages.input import stage_input
from engine.stages.system_parameters import stage_system_parameters
from engine.stages.structure import stage_structure
from engine.stages.production_resolution import stage_production_resolution
from engine.stages.product_bom_consumption import stage_product_bom_consumption
from engine.stages.balance import stage_balance
from engine.stages.clearing_allocation import stage_clearing_allocation

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
# PIPELINE
# ============================================================

def run_pipeline(inputs: ContractInputs) -> ContractOutputs:
    state = stage_input(inputs)
    state = stage_scenario_resolution(state)
    state = stage_system_parameters(state)
    state = stage_structure(state)
    state = stage_production_resolution(state)
    state = stage_product_bom_consumption(state)
    state = stage_balance(state)
    state = stage_clearing_allocation(state)

    from pprint import pprint

    return ContractOutputs(
        output_tables={
            "production_intent": state["production_intent"],
            "product_bom_consumption": state["product_bom_consumption"],
            "product_bom_demand_detail": state["product_bom_demand_detail"],
            "balance_plan": state["balance_plan"],
            "clearing_result": state["clearing_result"],
            "allocation_summary": state["allocation_summary"],
        }
    )