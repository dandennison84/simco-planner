from __future__ import annotations

from pathlib import Path
import os

from engine.io_csv import ContractInputs, load_contract_inputs, write_contract_outputs
from engine.pipeline import run_pipeline
from engine.schema_loader import load_schema
from engine.validator import validate_table


# ------------------------------------------------------------
# PURE: validate a dict of tables
# ------------------------------------------------------------
def _validate_tables(
    tables: dict[str, list[dict]],
    tables_schema: dict,
) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    validated = {}
    logs = {}

    for name, rows in tables.items():
        result = validate_table(rows, tables_schema.get(name))
        validated[name] = result["rows"]
        logs[name] = result["log"]

    return validated, logs


# ------------------------------------------------------------
# SIDE EFFECT: print schema summary
# ------------------------------------------------------------
def _print_schema_summary(logs: dict[str, dict]) -> None:
    total_rows = 0
    total_tables = 0

    for name, log in logs.items():
        total_tables += 1
        total_rows += log["rows_read"]

        print(f"[schema] {name}: rows={log['rows_read']} valid={log['rows_valid']}")

        if log["rows_dropped"] > 0:
            print(f"[schema][DROP] {name}: {log['rows_dropped']} row(s) removed")

        if log["errors"]:
            print(f"[schema][ERROR] {name}: {len(log['errors'])} issue(s)")

            MAX_ERR = 3
            for i, err in enumerate(log["errors"][:MAX_ERR], 1):
                print(
                    f"  {i}. row={err.get('row')} field={err.get('field')} -> {err.get('error')}"
                )

            if len(log["errors"]) > MAX_ERR:
                print(f"  ... {len(log['errors']) - MAX_ERR} more")

    print(f"[engine] tables={total_tables} total_rows={total_rows}")


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    env = os.getenv("SIMCO_ENV", "runtime")
    data_dir = repo_root / "data" / env

    input_dir = data_dir / "input"
    reference_dir = data_dir / "reference"
    output_dir = data_dir / "output"

    schema_path = repo_root / "schema" / "schema.yml"

    # --- Load inputs ---
    inputs = load_contract_inputs(
        input_dir=input_dir,
        reference_dir=reference_dir,
    )

    # --- Load schema ---
    schema = load_schema(schema_path)
    tables_schema = schema.get("tables", {})

    # --- Validate all tables (pure) ---
    validated_input_tables, input_logs = _validate_tables(
        inputs.input_tables, tables_schema
    )

    validated_reference_tables, reference_logs = _validate_tables(
        inputs.reference_tables, tables_schema
    )

    # --- Print summary (side effect boundary) ---
    _print_schema_summary({**input_logs, **reference_logs})

    # --- Rebuild validated inputs (pure) ---
    validated_inputs = ContractInputs(
        input_tables=validated_input_tables,
        reference_tables=validated_reference_tables,
    )

    # --- Run pipeline (pure) ---
    outputs = run_pipeline(validated_inputs)

    # --- Write outputs (side effect) ---
    write_contract_outputs(
        outputs=outputs,
        output_dir=output_dir,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())