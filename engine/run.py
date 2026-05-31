from __future__ import annotations

from pathlib import Path
import os
from typing import Dict, List, Tuple, Any

from engine.debug import debug_log, debug_enabled

from engine.io_csv import (
    ContractInputs,
    load_contract_inputs,
    write_contract_outputs,
    ContractOutputs,
)
from engine.pipeline import run_pipeline
from engine.schema_loader import load_schema
from engine.validator import validate_table

def _get_debug_level(validated_inputs: Dict[str, List[dict]]) -> int:
    try:
        rows = validated_inputs.get("system_parameters", [])
        for r in rows:
            if str(r.get("parameter_key")).strip() == "debug.level":
                return int(str(r.get("parameter_value")).strip())
    except Exception:
        pass

    return 0

# =============================================================================
# Paths & Environment
# =============================================================================
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_env() -> str:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return "test"
    return os.getenv("SIMCO_ENV", "runtime")


def _schema_paths(repo_root: Path) -> tuple[Path, Path]:
    schema_dir = repo_root / "schema"
    return (
        schema_dir / "input.yml",
        schema_dir / "reference.yml",
    )


# =============================================================================
# Validation
# =============================================================================
def _validate_tables(
    tables: Dict[str, List[dict]],
    schema_tables: Dict[str, Any],
) -> Tuple[Dict[str, List[dict]], Dict[str, dict]]:
    """
    PURE: table-by-table validation using strict validator.
    """
    validated: Dict[str, List[dict]] = {}
    logs: Dict[str, dict] = {}

    for name, rows in tables.items():
        table_schema = schema_tables.get(name)

        result = validate_table(rows, table_schema)

        validated[name] = result["rows"]
        logs[name] = result

    return validated, logs


def _fail_if_any_errors(logs: Dict[str, dict]) -> None:
    """
    STRICT GATE:
    ANY invalid table → stop execution.
    """
    failures = []

    for table, result in logs.items():
        if not result["valid"]:
            error_count = len(result["log"]["errors"])
            failures.append(f"{table}: {error_count} errors")

    if failures:
        raise ValueError(f"Validation failed: {'; '.join(failures)}")


def _print_schema_summary(
    logs: Dict[str, dict],
    debug_level: int,
) -> None:
    """
    Debug-aware validation summary.

    Level 0:
        no output

    Level 1:
        table summaries only

    Level 2:
        include sample errors
    """

    if debug_level < 1:
        return

    total_tables = 0
    total_rows = 0
    total_errors = 0

    for name, result in sorted(logs.items(), key=lambda x: x[0]):
        log = result["log"]

        rows_read = int(log.get("rows_read", 0))
        rows_valid = int(log.get("rows_valid", 0))
        rows_invalid = int(log.get("rows_invalid", 0))
        errors = log.get("errors", []) or []
        error_count = len(errors)

        total_tables += 1
        total_rows += rows_read
        total_errors += error_count

        # ✅ Level 1 summary
        print(
            f"[validate] {name}: "
            f"read={rows_read} valid={rows_valid} invalid={rows_invalid} errors={error_count}"
        )

        # ✅ Level 2 sample errors
        if debug_level >= 2 and error_count > 0:
            for e in errors[:5]:
                print(
                    f"[validate:{name}] row={e.get('row')} "
                    f"field={e.get('field')} error={e.get('error')}"
                )

            if error_count > 5:
                print(f"[validate:{name}] ... {error_count - 5} more errors")

    print(
        f"[validate] tables={total_tables} rows_read={total_rows} total_errors={total_errors}"
    )

# =============================================================================
# Main
# =============================================================================
def main(env: str | None = None) -> int:
    repo_root = _repo_root()
    env = env or _default_env()

    data_root = repo_root / "data" / env

    input_dir = data_root / "input"
    output_dir = data_root / "output"

    # ✅ GLOBAL reference layer
    reference_dir = repo_root / "data" / "reference"

    # -------------------------------------------------------------------------
    # Load schemas
    # -------------------------------------------------------------------------
    input_schema_path, reference_schema_path = _schema_paths(repo_root)

    input_schema = load_schema(input_schema_path)
    reference_schema = load_schema(reference_schema_path)

    input_tables_schema = input_schema.get("tables", {})
    reference_tables_schema = reference_schema.get("tables", {})

    # -------------------------------------------------------------------------
    # Load contract CSVs (schema-driven)
    # -------------------------------------------------------------------------
    inputs = load_contract_inputs(
        input_dir=input_dir,
        reference_dir=reference_dir,
        input_schema=input_schema,
        reference_schema=reference_schema,
        require_input_files=True,
        require_reference_files=True,
    )

    # -------------------------------------------------------------------------
    # STRICT VALIDATION
    # -------------------------------------------------------------------------
    validated_inputs, logs_in = _validate_tables(
        inputs.input_tables,
        input_tables_schema,
    )

    validated_refs, logs_ref = _validate_tables(
        inputs.reference_tables,
        reference_tables_schema,
    )

    logs = {**logs_in, **logs_ref}

    debug_level = _get_debug_level(validated_inputs)
    _print_schema_summary(logs, debug_level)
    
    _fail_if_any_errors(logs)

    # -------------------------------------------------------------------------
    # Pipeline (ONLY VALID DATA)
    # -------------------------------------------------------------------------
    validated_contract = ContractInputs(
        input_tables=validated_inputs,
        reference_tables=validated_refs,
    )

    outputs: ContractOutputs = run_pipeline(validated_contract)

    # -------------------------------------------------------------------------
    # Write outputs
    # -------------------------------------------------------------------------
    write_contract_outputs(outputs, output_dir=output_dir)

    if debug_level >= 1:
        print(f"[run] wrote outputs to: {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())