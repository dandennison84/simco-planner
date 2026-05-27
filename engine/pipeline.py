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


def run_pipeline(inputs: ContractInputs) -> ContractOutputs:
    """
    Minimal pipeline behavior to support early acceptance tests.

    Supported behaviors:
    - EO-002: bottleneck cap (labor constraint via product_bom)
      Emits diagnostics schema:
        snapshot_key, product_key, produced_quantity, bottleneck

    - EO-004: retail priority allocation (retail before exchange) when sales_demand exists
      Expects sales_demand channel_key.
      Emits diagnostics schema:
        snapshot_key, product_key, produced_quantity, retail_quantity, exchange_quantity

    - EO-005: invalid assignment (fail-fast)
      slot_product_assignment split_fraction must sum to 1 per slot_key
    """

    company_rows = inputs.input_tables.get("company_snapshot", [])
    structure_rows = inputs.input_tables.get("structure_map", [])
    assignment_rows = inputs.input_tables.get("slot_product_assignment", [])
    bom_rows = inputs.reference_tables.get("product_bom", [])
    sales_rows = inputs.input_tables.get("sales_demand", [])

    # Guard: minimal data required
    if not (company_rows and structure_rows and assignment_rows):
        return ContractOutputs(
            output_tables={
                "diagnostics": [],
                "guidance": [],
                "signal_evidence": [],
            }
        )

    # ------------------------------------------------------------
    # EO-005: validate assignment splits (fail-fast)
    # ------------------------------------------------------------
    # Sum split_fraction per slot_key must equal 1.0 (within epsilon)
    slot_totals: dict[str, float] = {}
    for row in assignment_rows:
        slot_key = row.get("slot_key", "")
        frac = _to_float(row.get("split_fraction", "0"))
        slot_totals[slot_key] = slot_totals.get(slot_key, 0.0) + frac

    eps = 1e-6
    for slot_key, total in slot_totals.items():
        if abs(total - 1.0) > eps:
            raise ValueError(f"invalid split_fraction total for slot_key={slot_key}: {total}")

    # ------------------------------------------------------------
    # Current simplified model: single snapshot, single slot, first assignment row
    # ------------------------------------------------------------
    company = company_rows[0]
    slot = structure_rows[0]
    assign = assignment_rows[0]

    snapshot_key = company.get("snapshot_key", "")
    product_key = assign.get("product_key", "")

    labor_available = _to_float(company.get("labor_available", "0"))
    capacity = _to_float(slot.get("capacity", "0"))

    # ------------------------------------------------------------
    # EO-002: bottleneck calculation (capacity-based)
    # ------------------------------------------------------------

    # For now: only capacity exists (no input or retail constraints yet)
    constraints = {
        "capacity": capacity,
    }

    # Select bottleneck as argmin
    bottleneck = min(constraints, key=constraints.get)
    produced = constraints[bottleneck]

    diagnostics_rows: list[dict] = []

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

    # ------------------------------------------------------------
    # EO-004: retail before exchange allocation
    # ------------------------------------------------------------
    retail_demand = 0.0
    exchange_demand = 0.0

    for row in sales_rows:
        if row.get("product_key", "") != product_key:
            continue

        # Primary path: channel_key
        channel_key_raw = row.get("channel_key", "")
        channel_key = _to_int(channel_key_raw, default=None)

        # Optional fallback path (during migration): channel string
        if channel_key is None:
            channel = row.get("channel", "")
            if channel == "retail":
                channel_key = RETAIL_KEY
            elif channel == "exchange":
                channel_key = EXCHANGE_KEY
            else:
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