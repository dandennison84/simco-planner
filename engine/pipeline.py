from __future__ import annotations

from engine.io_csv import ContractInputs, ContractOutputs


# Channel keys (current convention)
EXCHANGE_KEY = 1
RETAIL_KEY = 2


def _to_float(x: str, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _to_int(x: str, default: int | None = None) -> int | None:
    try:
        return int(x)
    except Exception:
        return default


def _fmt_num(x: float) -> str:
    # Keep CSV comparisons stable: 50 instead of 50.0
    return str(int(x)) if float(x).is_integer() else str(x)


# -------------------------
# Clean layer helpers
# -------------------------
def clean_row(row: dict) -> dict:
    """
    Normalize a raw CSV row into consistent strings:
    - None -> ""
    - everything -> str(...).strip()
    """
    return {k: ("" if v is None else str(v).strip()) for k, v in row.items()}


def clean_table(rows: list[dict]) -> list[dict]:
    """Normalize all rows using clean_row()."""
    return [clean_row(r) for r in rows]


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

    # Load & clean surfaces (CSV values arrive as strings; normalize once)
    company_rows = clean_table(inputs.input_tables.get("company_snapshot", []))
    structure_rows = clean_table(inputs.input_tables.get("structure_map", []))
    assignment_rows = clean_table(inputs.input_tables.get("slot_product_assignment", []))
    bom_rows = clean_table(inputs.reference_tables.get("product_bom", []))

    # Optional EO-004 surface (added during channel_key migration)
    sales_rows = clean_table(inputs.input_tables.get("sales_demand", []))

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

    snapshot_key = company.get("snapshot_key", "")
    product_key = assign.get("product_key", "")

    # --- EO-002: production / bottleneck ---
    labor_available = _to_float(company.get("labor_available", "0"))
    capacity = _to_float(slot.get("capacity", "0"))

    labor_per_unit = 0.0
    for r in bom_rows:
        if r.get("product_key", "") == product_key and r.get("input_product_key", "") == "labor":
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

    # --- EO-004: retail before exchange allocation ---
    retail_demand = 0.0
    exchange_demand = 0.0

    for row in sales_rows:
        # Robust join (strings already stripped by clean_row)
        if row.get("product_key", "") != product_key:
            continue

        # channel_key arrives as string from CSV; normalize once
        channel_key_raw = row.get("channel_key", "")
        channel_key = _to_int(channel_key_raw, default=None)
        if channel_key is None:
            # Skip bad rows deterministically (no crash)
            continue

        demand = _to_float(row.get("demand", "0"))

        if channel_key == RETAIL_KEY:
            retail_demand += demand
        elif channel_key == EXCHANGE_KEY:
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