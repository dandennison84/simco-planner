from __future__ import annotations

from pathlib import Path

from engine.io_csv import ContractInputs, load_contract_inputs, write_contract_outputs
from engine.pipeline import run_pipeline
from engine.schema_loader import load_schema
from engine.validator import validate_table


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    import os

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

    # --- Validate input tables ---
    validated_input_tables = {}
    input_logs = {}

    for name, rows in inputs.input_tables.items():
        result = validate_table(rows, tables_schema.get(name))
        validated_input_tables[name] = result["rows"]
        input_logs[name] = result["log"]

    # --- Validate reference tables ---
    validated_reference_tables = {}
    reference_logs = {}

    for name, rows in inputs.reference_tables.items():
        result = validate_table(rows, tables_schema.get(name))
        validated_reference_tables[name] = result["rows"]
        reference_logs[name] = result["log"]

    # --- ALWAYS print summary (this is the key change) ---
    total_rows = 0
    total_tables = 0

    for name, log in {**input_logs, **reference_logs}.items():
        total_tables += 1
        total_rows += log["rows_read"]

        print(f"[schema] {name}: rows={log['rows_read']} valid={log['rows_valid']}")

        if log["rows_dropped"] > 0:
            print(f"[schema][DROP] {name}: {log['rows_dropped']} row(s) removed")

        # ✅ NEW: print errors (clean + capped)
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

    # --- Rebuild validated inputs ---
    validated_inputs = ContractInputs(
        input_tables=validated_input_tables,
        reference_tables=validated_reference_tables,
    )

    # --- Run pipeline ---
    outputs = run_pipeline(validated_inputs)

    # --- Write outputs ---
    write_contract_outputs(
        outputs=outputs,
        output_dir=output_dir,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())