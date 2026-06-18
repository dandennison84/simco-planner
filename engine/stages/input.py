from typing import Dict, Any

from engine.io_csv import ContractInputs


# -----------------------------------------------------
# Helper: normalize enabled flag
# -----------------------------------------------------
def _is_enabled(val: Any) -> bool:
    """
    Normalize enabled flag from Excel/CSV.

    Accepts:
        TRUE, true, 1, yes, y

    Anything else = disabled
    """
    if val is None:
        return True  # default: enabled

    s = str(val).strip().lower()
    return s in {"true", "1", "yes", "y"}


# -----------------------------------------------------
# Helper: filter rows by enabled column (if present)
# -----------------------------------------------------
def _filter_enabled_rows(table: Any, *, table_name: str) -> Any:
    """
    Filters rows in a table if an 'enabled' column exists.

    Assumes table is List[Dict].

    Behavior:
        - If no 'enabled' column → returns table unchanged
        - If present → keeps only enabled rows
    """
    if not isinstance(table, list) or len(table) == 0:
        return table

    first_row = table[0]

    # -----------------------------------------------------
    # Detect enabled column (case-insensitive, no guessing)
    # -----------------------------------------------------
    enabled_col = None
    for col in first_row.keys():
        if str(col).strip().lower() == "enabled":
            enabled_col = col
            break

    # Debug: show actual column names
    print(f"[input:debug] table={table_name} columns={list(first_row.keys())}")

    # No enabled column → no filtering
    if enabled_col is None:
        print(f"[input:debug] table={table_name} no enabled column, skipping filter")
        return table

    # -----------------------------------------------------
    # Apply filtering
    # -----------------------------------------------------
    before_count = len(table)

    filtered = [
        row for row in table
        if _is_enabled(row.get(enabled_col))
    ]

    after_count = len(filtered)

    print(
        f"[input:debug] table={table_name} enabled_col={enabled_col} "
        f"before={before_count} after={after_count}"
    )

    return filtered


# -----------------------------------------------------
# Stage: input
# -----------------------------------------------------
def stage_input(inputs: ContractInputs) -> Dict[str, object]:
    state: Dict[str, object] = {}

    state.update(inputs.input_tables)
    state.update(inputs.reference_tables)

    state["_meta"] = {}

    return state