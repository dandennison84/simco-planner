from __future__ import annotations

from engine.io_csv import ContractInputs, ContractOutputs


def _to_float(x: str, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _fmt_num(x: float) -> str:
    # Avoid "50.0" vs "50" mismatches in CSV comparisons.
    return str(int(x)) if float(x).is_integer() else str(x)


def run_pipeline(inputs: ContractInputs) -> ContractOutputs:
    # Load required surfaces (strings from CSV)
    company_rows = inputs.input_tables.get("company_snapshot", [])
    structure_rows = inputs.input_tables.get("structure_map", [])
    assignment_rows = inputs.input_tables.get("slot_product_assignment", [])
    bom_rows = inputs.reference_tables.get("product_bom", [])

    diagnostics_rows = []

    # Minimal EO-002: single snapshot, single slot, single assignment.
    if company_rows and structure_rows and assignment_rows:
        company = company_rows[0]
        slot = structure_rows[0]
        assign = assignment_rows[0]

        snapshot_key = company["snapshot_key"]
        labor_available = _to_float(company.get("labor_available", "0"))

        product_key = assign["product_key"]
        capacity = _to_float(slot.get("capacity", "0"))

        # Find labor requirement per unit from product_bom
        labor_per_unit = 0.0
        for r in bom_rows:
            if r.get("product_key") == product_key and r.get("input_product_key") == "labor":
                labor_per_unit = _to_float(r.get("input_quantity", "0"))
                break

        if labor_per_unit > 0:
            produced = min(capacity, labor_available / labor_per_unit)
            bottleneck = "labor" if produced < capacity else "none"
        else:
            produced = capacity
            bottleneck = "none"

        diagnostics_rows.append(
            {
                "snapshot_key": snapshot_key,
                "product_key": product_key,
                "produced_quantity": _fmt_num(produced),
                "bottleneck": bottleneck,
            }
        )

    return ContractOutputs(
        output_tables={
            "diagnostics": diagnostics_rows,
            "guidance": [],
            "signal_evidence": [],
        }
    )