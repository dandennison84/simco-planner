from __future__ import annotations

from engine.io_csv import ContractInputs
from engine.pipeline import run_pipeline


def test_pipeline_runs_and_emits_contract_outputs() -> None:
    inputs = ContractInputs(
        input_tables={
            "company_snapshot": [
                {
                    "snapshot_key": "1",
                    "realm_key": "1",
                    "structure_map_key": "1",
                    "company_level": "10",
                    "production_speed_delta": "0",
                    "sales_speed_delta": "0",
                }
            ],
            "structure_map": [
                {
                    "structure_map_key": "1",
                    "slot_key": "slot_1",
                    "capacity": "100",
                }
            ],
            "slot_product_assignment": [
                {
                    "slot_key": "slot_1",
                    "product_key": "apple",
                    "split_fraction": "1.0",
                }
            ],
            "financial_snapshot": [],
            "sales_demand": [],
        },
        reference_tables={
            "product_bom": [],
            "market_pricing": [],
            "system_parameters": [],
        },
    )

    outputs = run_pipeline(inputs)

    # ✅ contract exists
    assert "diagnostics" in outputs.output_tables

    diagnostics = outputs.output_tables["diagnostics"]

    # ✅ at least one row produced
    assert len(diagnostics) == 1

    row = diagnostics[0]

    # ✅ required output fields exist
    assert "snapshot_key" in row
    assert "product_key" in row
    assert "produced_quantity" in row
    assert "bottleneck" in row

    # ✅ expected values (capacity-only bottleneck case)
    assert row["snapshot_key"] == "1"
    assert row["product_key"] == "apple"
    assert row["produced_quantity"] == "100"
    assert row["bottleneck"] == "capacity"