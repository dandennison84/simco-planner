from __future__ import annotations

from engine.io_csv import ContractInputs, ContractOutputs


def _to_float(x: str, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _fmt_num(x: float) -> str:
    # Keep CSV comparisons stable: 50 instead of 50.0
    return str(int(x)) if float(x).is_integer() else str(x)


def run_pipeline(inputs: ContractInputs) -> ContractOutputs:
    """
    Minimal pipeline behavior to support early acceptance tests.

    Supported behaviors:
    - EO-002: bottleneck cap (labor constraint via product_bom)
      Emits diagnostics schema:
        snapshot_key, product_key, produced_quantity, bottleneck

    - EO-004: retail priority allocation (retail before exchange) when sales_demand exists
      Emits diagnostics schema:
        snapshot_key, product_key, produced_quantity, retail_quantity, exchange_quantity
    """
    company_rows = inputs.input_tables.get("company_snapshot", [])
    structure_rows = inputs.input_tables.get("structure_map", [])
    assignment_rows = inputs.input_tables.get("slot_product_assignment", [])
    bom_rows = inputs.reference_tables.get("product_bom", [])

    # Optional EO-004 input (not part of core contracts yet, but used for acceptance)
    sales_rows = inputs.input_tables.get("sales_demand", [])

    diagnostics_rows: list[dict] = []

    # Minimal: single snapshot, single slot, single assignment.
    if not (company_rows and structure_rows and assignment_rows):
        return ContractOutputs(
            output_tables={
                "diagnostics": [],
                "guidance": [],
                "signal_evidence": [],
            }
        )

    company = company_rows[0]
    slot = structure_rows[0]
    assign = assignment_rows[0]

    snapshot_key = company["snapshot_key"]
    product_key = assign["product_key"]

    labor_available = _to_float(company.get("labor_available", "0"))
    capacity = _to_float(slot.get("capacity", "0"))

    # EO-002: find labor requirement per unit from product_bom
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

    # If no sales_demand provided, emit EO-002 schema (do NOT add extra columns)
    if not sales_rows:
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

    # EO-004: retail before exchange allocation
    retail_demand = 0.0
    exchange_demand = 0.0

    for row in sales_rows:
        if row.get("product_key") != product_key:
            continue

        channel = row.get("channel", "")
        demand = _to_float(row.get("demand", "0"))

        if channel == "retail":
            retail_demand += demand
        elif channel == "exchange":
            exchange_demand += demand

    retail_qty = min(produced, retail_demand)
    remaining = produced - retail_qty
    exchange_qty = min(remaining, exchange_demand)

    diagnostics_rows.append(
        {
            "snapshot_key": snapshot_key,
            "product_key": product_key,
            "produced_quantity": _fmt_num(produced),
            "retail_quantity": _fmt_num(retail_qty),
            "exchange_quantity": _fmt_num(exchange_qty),
        }
    )

    return ContractOutputs(
        output_tables={
            "diagnostics": diagnostics_rows,
            "guidance": [],
            "signal_evidence": [],
        }
    )