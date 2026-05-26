from __future__ import annotations

from pathlib import Path

from engine.io_csv import load_contract_inputs
from engine.pipeline import run_pipeline


def test_pipeline_runs_and_emits_contract_outputs() -> None:
    from engine.pipeline import run_pipeline
    from engine.io_csv import ContractInputs

    inputs = ContractInputs(
        input_tables={
            "company_snapshot": [{"snapshot_key": "s1", "labor_available": "100"}],
            "structure_map": [{"structure_key": "plant_1", "slot_key": "slot_1", "capacity": "100"}],
            "slot_product_assignment": [
                {"slot_key": "slot_1", "product_key": "apple", "quality_level": "q1", "split_fraction": "1.0"}
            ],
            "financial_snapshot": [],
            "sales_demand": [],
        },
        reference_tables={
            "product_bom": [{"product_key": "apple", "input_product_key": "labor", "input_quantity": "2"}],
            "market_pricing": [],
            "system_parameters": [],
        },
    )

    outputs = run_pipeline(inputs)

    assert "diagnostics" in outputs.output_tables