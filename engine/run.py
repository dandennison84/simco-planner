from __future__ import annotations

from pathlib import Path
import os
from typing import Dict, List, Tuple, Any
from collections import defaultdict

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


# =============================================================================
# Helpers
# =============================================================================

def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


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
        schema_dir / "output.yml",
    )


# =============================================================================
# Validation
# =============================================================================

def _validate_tables(
    tables: Dict[str, List[dict]],
    schema_tables: Dict[str, Any],
) -> Tuple[Dict[str, List[dict]], Dict[str, dict]]:
    validated: Dict[str, List[dict]] = {}
    logs: Dict[str, dict] = {}

    for name, rows in tables.items():
        table_schema = schema_tables.get(name)
        result = validate_table(rows, table_schema)

        validated[name] = result["rows"]
        logs[name] = result

    return validated, logs

def _fail_if_any_errors(logs):
    failures = []

    for table, result in logs.items():
        errors = result.get("log", {}).get("errors", [])

        if errors:
            # ✅ GROUP errors
            field_summary = defaultdict(int)

            for err in errors:
                key = (err.get("field"), err.get("error"))
                field_summary[key] += 1

            summary_lines = [
                f"{field} → {msg} ({count} rows)"
                for (field, msg), count in sorted(field_summary.items())
            ]

            # ✅ SAMPLE rows only (NOT all)
            examples = []
            for err in errors[:6]:
                examples.append(
                    f"row {err.get('row')} field '{err.get('field')}': {err.get('error')}"
                )

            failures.append(
                f"{table}: {len(errors)} errors\n\n"
                f"FIELD SUMMARY:\n"
                + "\n".join(summary_lines)
                + "\n\nEXAMPLES:\n"
                + "\n".join(examples)
            )

    if failures:
        message = (
            "\n" + "="*60 +
            "\nVALIDATION FAILED — PIPELINE HALTED\n" +
            "="*60 + "\n\n" +
            "\n\n".join(failures)
        )

        raise SystemExit(message)

def _validate_logical_completeness(
    inputs: Dict[str, List[dict]],
    refs: Dict[str, List[dict]],
) -> None:
    """
    Enforce cross-table logical requirements (REQ-090).
    Fail fast if required relationships are missing.
    """

    # Example: every product in production_plan must exist in product reference
    production = inputs.get("production_plan", [])
    products = refs.get("product", [])

    product_index = {r.get("product_key") for r in products}

    missing_products = [
        r.get("product_key")
        for r in production
        if r.get("product_key") not in product_index
    ]

    if missing_products:
        raise SystemExit(
            f"FATAL: production_plan references unknown products: {sorted(set(missing_products))}"
        )
    
def _validate_empty_table_semantics(
    inputs: Dict[str, List[dict]],
) -> None:
    """
    Enforce empty-table rules (REQ-088).
    """

    production = inputs.get("production_plan", [])
    company_rows = inputs.get("company", [])

    # Example rule:
    # If production_plan exists, company must exist
    if production and not company_rows:
        raise SystemExit(
            "FATAL: production_plan provided but company table is empty"
        )

def _validate_required_inputs_non_empty(
    validated_inputs: Dict[str, List[dict]],
) -> None:
    required_inputs = [
        "company",
        "map_structure",
        "production_plan",
    ]

    for name in required_inputs:
        if not validated_inputs.get(name):
            raise SystemExit(f"FATAL: required input '{name}' is empty")

def _validate_output_non_empty(validated_outputs: Dict[str, List[dict]]):
    # Optional rule: important outputs must not be empty
    # Example:
    if not validated_outputs.get("production_intent"):
        raise SystemExit("FATAL: production_intent is empty")
        
def _validate_bom_cycles(state: Dict[str, object]) -> None:
    """
    Detect cycles in product_bom using DFS.

    Raises ValueError if any cycle is found.
    """

    bom_rows = state.get("product_bom", [])

    # Build adjacency list
    graph: Dict[str, List[str]] = {}

    for r in bom_rows:
        output_product = str(r.get("product_key")).strip()
        input_product = str(r.get("input_product_key")).strip()

        if output_product == "" or input_product == "":
            continue

        graph.setdefault(output_product, []).append(input_product)

    visited: set[str] = set()
    stack: set[str] = set()

    def dfs(node: str):
        if node in stack:
            raise ValueError(f"BOM cycle detected at product={node}")

        if node in visited:
            return

        stack.add(node)

        for neighbor in graph.get(node, []):
            dfs(neighbor)

        stack.remove(node)
        visited.add(node)

    # Check all nodes
    for node in graph:
        if node not in visited:
            dfs(node)

# =============================================================================
# Build debug-aware state (KEY FIX)
# =============================================================================

def _build_debug_state(
    validated_inputs: Dict[str, List[dict]],
    validated_refs: Dict[str, List[dict]],
) -> Dict[str, object]:
    """
    Build minimal state ONLY for debug usage (not pipeline mutation)
    """

    state: Dict[str, object] = {
        **validated_inputs,
        **validated_refs,
        "_meta": {},
    }

    # Populate system_parameters into _meta
    rows = state.get("system_parameters", [])

    param_map = {
        _k(r.get("parameter_key")): _k(r.get("parameter_value"))
        for r in rows
    }

    state["_meta"]["system_parameters_map"] = param_map

    return state


# =============================================================================
# Validation Debug Output (NOW USES debug.py)
# =============================================================================

def _log_validation_summary(state: Dict[str, object], logs: Dict[str, dict]) -> None:
    if not debug_enabled(state, 1):
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

        debug_log(
            state,
            f"[validate] {name}: read={rows_read} valid={rows_valid} invalid={rows_invalid} errors={error_count}",
            level=1,
        )

        if debug_enabled(state, 2) and error_count > 0:
            for e in errors[:5]:
                debug_log(
                    state,
                    f"[validate:{name}] row={e.get('row')} "
                    f"field={e.get('field')} error={e.get('error')}",
                    level=2,
                )

            if error_count > 5:
                debug_log(
                    state,
                    f"[validate:{name}] ... {error_count - 5} more errors",
                    level=2,
                )

    debug_log(
        state,
        f"[validate] tables={total_tables} rows_read={total_rows} total_errors={total_errors}",
        level=1,
    )


# =============================================================================
# Optional: dump loaded data at debug level 3 (VERY USEFUL)
# =============================================================================

def _debug_loaded_tables(state: Dict[str, object]) -> None:
    if not debug_enabled(state, 3):
        return

    debug_log(state, "[debug] input tables loaded:", level=3)

    for name, rows in state.items():
        if name == "_meta":
            continue

        if isinstance(rows, list):
            debug_log(state, f"[debug] {name}: rows={len(rows)}", level=3)
            if rows:
                debug_log(state, f"[debug] {name} sample={rows[:3]}", level=3)


# =============================================================================
# Main
# =============================================================================

def main(env: str | None = None) -> int:
    repo_root = _repo_root()
    env = env or _default_env()

    data_root = repo_root / "data" / env

    input_dir = data_root / "input"
    output_dir = data_root / "output"

    reference_dir = repo_root / "data" / "reference"

    # ---------------------------------------------------------
    # Load schemas
    # ---------------------------------------------------------
    input_schema_path, reference_schema_path, output_schema_path = _schema_paths(repo_root)

    input_schema = load_schema(input_schema_path)
    reference_schema = load_schema(reference_schema_path)
    output_schema = load_schema(output_schema_path)

    input_tables_schema = input_schema.get("tables", {})
    reference_tables_schema = reference_schema.get("tables", {})
    output_tables_schema = output_schema.get("tables", {})

    # ---------------------------------------------------------
    # Load CSVs
    # ---------------------------------------------------------
    inputs = load_contract_inputs(
        input_dir=input_dir,
        reference_dir=reference_dir,
        input_schema=input_schema,
        reference_schema=reference_schema,
        require_input_files=True,
        require_reference_files=True,
    )

    # ---------------------------------------------------------
    # Validate
    # ---------------------------------------------------------
    validated_inputs, logs_in = _validate_tables(
        inputs.input_tables,
        input_tables_schema,
    )

    validated_refs, logs_ref = _validate_tables(
        inputs.reference_tables,
        reference_tables_schema,
    )

    logs = {**logs_in, **logs_ref}

    # ---------------------------------------------------------
    # Build debug state (CRITICAL)
    # ---------------------------------------------------------
    debug_state = _build_debug_state(validated_inputs, validated_refs)

    _log_validation_summary(debug_state, logs)

    _fail_if_any_errors(logs)

    # ---------------------------------------------------------
    # Structural validation boundary complete
    # From this point forward, data is guaranteed valid
    # ---------------------------------------------------------

    _validate_required_inputs_non_empty(validated_inputs)
    _validate_logical_completeness(validated_inputs, validated_refs)
    _validate_empty_table_semantics(validated_inputs)
    _validate_bom_cycles(validated_inputs)

    _debug_loaded_tables(debug_state)

    # ---------------------------------------------------------
    # Run pipeline
    # ---------------------------------------------------------
    validated_contract = ContractInputs(
        input_tables=validated_inputs,
        reference_tables=validated_refs,
    )

    outputs: ContractOutputs = run_pipeline(validated_contract)

    validated_outputs, logs_out = _validate_tables(
        outputs.output_tables,
        output_tables_schema,
    )

    _fail_if_any_errors(logs_out)

    schema_output_names = set(output_tables_schema.keys())
    actual_output_names = set(validated_outputs.keys())

    missing = schema_output_names - actual_output_names

    if missing:
        raise SystemExit(
            f"FATAL: missing required output tables: {sorted(missing)}"
        )

    _validate_output_non_empty(validated_outputs)

    # ---------------------------------------------------------
    # Write outputs
    # ---------------------------------------------------------
    write_contract_outputs(
        ContractOutputs(validated_outputs),
        output_dir=output_dir,
        output_schema=output_schema,
    )

    if debug_enabled(debug_state, 1):
        debug_log(debug_state, f"[run] wrote outputs to: {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())