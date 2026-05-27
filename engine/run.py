from __future__ import annotations

from pathlib import Path
import os
from typing import Dict, List, Tuple, Any

from engine.io_csv import ContractInputs, load_contract_inputs, write_contract_outputs, ContractOutputs
from engine.pipeline import run_pipeline
from engine.schema_loader import load_schema
from engine.validator import validate_table


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_env() -> str:
    # If running under pytest, default to test environment for acceptance harness
    if os.getenv("PYTEST_CURRENT_TEST"):
        return "test"
    return os.getenv("SIMCO_ENV", "runtime")


def _schema_path(repo_root: Path) -> Path:
    # Your tests reference Path("schema") / "schema.yml"
    # Keep consistent with that layout.
    return repo_root / "schema" / "schema.yml"


def _validate_tables(
    tables: Dict[str, List[dict]],
    schema_tables: Dict[str, Any],
) -> Tuple[Dict[str, List[dict]], Dict[str, dict]]:
    """
    Pure: validate a dict of tables using schema definitions when available.
    Returns: (validated_tables, logs_by_table)
    """
    validated: Dict[str, List[dict]] = {}
    logs: Dict[str, dict] = {}

    for name, rows in tables.items():
        table_schema = schema_tables.get(name)
        result = validate_table(rows, table_schema)
        validated[name] = result["rows"]
        logs[name] = result["log"]

    return validated, logs


def _fail_if_any_errors(logs: Dict[str, dict]) -> None:
    """
    Enforces strict validation policy:
    - any validation errors in any table => stop execution.
    """
    all_errors = []
    for table, log in logs.items():
        errs = log.get("errors") or []
        if errs:
            all_errors.append((table, errs))

    if all_errors:
        # Build a compact deterministic message
        parts = []
        for table, errs in all_errors:
            parts.append(f"{table}: {len(errs)} errors")
        summary = "; ".join(parts)
        raise ValueError(f"Validation failed: {summary}")


def _print_schema_summary(logs: Dict[str, dict]) -> None:
    """
    SIDE EFFECT: print schema validation summary (observability).
    """
    total_rows = 0
    total_tables = 0
    total_dropped = 0

    for name, log in sorted(logs.items(), key=lambda x: x[0]):
        total_tables += 1
        rows_read = int(log.get("rows_read", 0))
        rows_valid = int(log.get("rows_valid", 0))
        rows_dropped = int(log.get("rows_dropped", 0))
        total_rows += rows_read
        total_dropped += rows_dropped
        print(f"[validate] {name}: read={rows_read} valid={rows_valid} dropped={rows_dropped}")

    print(f"[validate] tables={total_tables} rows_read={total_rows} rows_dropped={total_dropped}")


def main(env: str | None = None) -> int:
    repo_root = _repo_root()
    env = env or _default_env()

    data_root = repo_root / "data" / env
    input_dir = data_root / "input"
    reference_dir = data_root / "reference"
    output_dir = data_root / "output"

    schema = load_schema(_schema_path(repo_root))
    schema_tables = schema.get("tables", {}) or {}

    inputs = load_contract_inputs(input_dir=input_dir, reference_dir=reference_dir)

    # Validate input + reference with schema when available
    validated_inputs, logs_in = _validate_tables(inputs.input_tables, schema_tables)
    validated_refs, logs_ref = _validate_tables(inputs.reference_tables, schema_tables)

    # Merge logs for summary + strict fail
    logs = {**logs_in, **logs_ref}
    _print_schema_summary(logs)
    _fail_if_any_errors(logs)

    validated_contract = ContractInputs(input_tables=validated_inputs, reference_tables=validated_refs)

    outputs: ContractOutputs = run_pipeline(validated_contract)

    write_contract_outputs(outputs, output_dir=output_dir)

    print(f"[run] wrote outputs to: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())