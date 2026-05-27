from __future__ import annotations

from engine.io_csv import ContractInputs, ContractOutputs

# Channel keys
EXCHANGE_KEY = 1
RETAIL_KEY = 2


def _to_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _to_int(x, default: int | None = None) -> int | None:
    try:
        return int(x)
    except Exception:
        return default


def _fmt_num(x: float) -> str:
    # Stable CSV formatting: 50 instead of 50.0
    return str(int(x)) if float(x).is_integer() else str(x)


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _group_by(rows: list[dict], key: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(_k(r.get(key)), []).append(r)
    return out


def _index_by(rows: list[dict], key: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for r in rows:
        out[_k(r.get(key))] = r
    return out


def _validate_split_fractions(assignment_rows: list[dict]) -> None:
    # EO-005: sum split_fraction per slot_key must equal 1
    totals: dict[str, float] = {}
    for r in assignment_rows:
        slot_key = _k(r.get("slot_key"))
        frac = _to_float(r.get("split_fraction", "0"))
        totals[slot_key] = totals.get(slot_key, 0.0) + frac

    for slot_key, total in totals.items():
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"invalid split_fraction total for slot_key={slot_key}: {total}")


def _capacity_by_product(structure_rows: list[dict], assignment_rows: list[dict]) -> dict[str, float]:
    """
    Production capacity is derived from:
      structure_map(slot_key -> capacity)
      slot_product_assignment(slot_key -> product_key, split_fraction)
    Output:
      product_key -> summed capacity
    """
    structure_by_slot = _index_by(structure_rows, "slot_key")
    assigns_by_slot = _group_by(assignment_rows, "slot_key")

    cap_by_product: dict[str, float] = {}

    for slot_key, assigns in assigns_by_slot.items():
        slot = structure_by_slot.get(slot_key)
        if not slot:
            continue

        slot_capacity = _to_float(slot.get("capacity", "0"))

        for a in assigns:
            product_key = _k(a.get("product_key"))
            split_fraction = _to_float(a.get("split_fraction", "0"))
            cap = slot_capacity * split_fraction
            cap_by_product[product_key] = cap_by_product.get(product_key, 0.0) + cap

    return cap_by_product


def _demand_by_product(sales_rows: list[dict]) -> dict[str, tuple[float, float]]:
    """
    sales_demand rows are expected to contain:
      product_key, channel_key, demand
    Output:
      product_key -> (retail_demand, exchange_demand)
    """
    demand: dict[str, tuple[float, float]] = {}

    for r in sales_rows:
        product_key = _k(r.get("product_key"))
        channel_key = _to_int(r.get("channel_key", ""), None)
        qty = _to_float(r.get("demand", "0"))

        retail, exchange = demand.get(product_key, (0.0, 0.0))

        if channel_key == RETAIL_KEY:
            retail += qty
        elif channel_key == EXCHANGE_KEY:
            exchange += qty

        demand[product_key] = (retail, exchange)

    return demand


def _throughput_from_constraints(constraints: dict[str, float]) -> tuple[str, float]:
    """
    Pure bottleneck selection:
      produced = min(constraints)
      bottleneck = argmin(constraints)
    """
    bottleneck = min(constraints, key=constraints.get)
    return bottleneck, constraints[bottleneck]


def _allocate_retail_first(produced: float, retail_demand: float, exchange_demand: float) -> tuple[float, float]:
    retail_qty = min(produced, retail_demand)
    remaining = produced - retail_qty
    exchange_qty = min(remaining, exchange_demand)
    return retail_qty, exchange_qty


def run_pipeline(inputs: ContractInputs) -> ContractOutputs:
    company_rows = inputs.input_tables.get("company_snapshot", [])
    structure_rows = inputs.input_tables.get("structure_map", [])
    assignment_rows = inputs.input_tables.get("slot_product_assignment", [])
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

    # EO-005
    _validate_split_fractions(assignment_rows)

    # Current scope: first scenario row only (until multi-snapshot refactor)
    company = company_rows[0]
    snapshot_key = _k(company.get("snapshot_key"))

    # Capacity by product (structure + assignment)
    cap_by_product = _capacity_by_product(structure_rows, assignment_rows)

    # If no sales_demand: EO-002 schema
    if not sales_rows:
        diagnostics_rows: list[dict] = []
        for product_key, capacity in cap_by_product.items():
            constraints = {"capacity": capacity}
            bottleneck, produced = _throughput_from_constraints(constraints)

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

    # sales_demand present: EO-004 schema
    demand = _demand_by_product(sales_rows)

    diagnostics_rows = []
    for product_key, capacity in cap_by_product.items():
        # For now, only capacity constrains production (input constraints come later)
        constraints = {"capacity": capacity}
        bottleneck, produced = _throughput_from_constraints(constraints)

        retail_demand, exchange_demand = demand.get(product_key, (0.0, 0.0))
        retail_qty, exchange_qty = _allocate_retail_first(produced, retail_demand, exchange_demand)

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