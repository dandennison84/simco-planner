from __future__ import annotations

from pathlib import Path
import os
from typing import Dict, List, Tuple, Any

from engine.debug import debug_log, debug_enabled, init_debug_state
from engine.io_csv import (
    ContractInputs,
    ContractOutputs,
    load_contract_inputs,
    write_contract_outputs,
)
from engine.pipeline import run_pipeline
from engine.validator import validate_table, debug_validate_result
from engine.contracts import (
    load_contract_registry,
    required_non_empty_table_names,
    table_contract_to_schema,
    tables_for_surface,
)

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


def _contracts_root(repo_root: Path) -> Path:
    return repo_root / "contracts"


# =============================================================================
# Validation
# =============================================================================

def _validate_tables(
    tables: Dict[str, List[dict]],
    contracts: Dict[str, Any],
) -> Tuple[Dict[str, List[dict]], Dict[str, dict]]:
    validated: Dict[str, List[dict]] = {}
    logs: Dict[str, dict] = {}

    for table_name, rows in tables.items():
        contract = contracts[table_name]
        result = validate_table(rows, table_contract_to_schema(contract))
        validated[table_name] = result["rows"]
        logs[table_name] = result["log"]

    return validated, logs


def _fail_if_any_errors(logs: Dict[str, dict]) -> None:
    failures: List[str] = []
    for table_name, log in logs.items():
        errors = log.get("errors", [])
        if errors:
            failures.append(f"{table_name}: {len(errors)} errors")
    if failures:
        raise SystemExit("FATAL: validation failed\n" + "\n".join(failures))


def _validate_required_tables_non_empty(
    validated_tables: Dict[str, List[dict]],
    contracts: Dict[str, Any],
) -> None:
    required_non_empty = required_non_empty_table_names(contracts)
    missing = [name for name in required_non_empty if not validated_tables.get(name)]
    if missing:
        raise SystemExit(
            "FATAL: required non-empty tables are empty: " + ", ".join(sorted(missing))
        )


# =============================================================================
# Optional debug helpers
# =============================================================================

def _build_debug_state(
    validated_inputs: Dict[str, List[dict]],
    validated_refs: Dict[str, List[dict]],
) -> Dict[str, object]:
    return {
        "input_tables": validated_inputs,
        "reference_tables": validated_refs,
    }


def _log_validation_summary(state: Dict[str, object], logs: Dict[str, dict]) -> None:
    if not logs:
        return

    for table_name, log in sorted(logs.items()):
        debug_validate_result(
            state,
            table_name,
            {"log": log},
        )

# =============================================================================
# Main
# =============================================================================

def main(env: str | None = None) -> int:
    repo_root = _repo_root()
    env = env or _default_env()

    runtime_dir = repo_root / "data" / env

    input_dir = runtime_dir / "input"
    output_dir = runtime_dir / "output"
    reference_dir = repo_root / "data" / "reference"

    # ✅ Initialize debug correctly
    state = init_debug_state(reference_dir)

    if debug_enabled(state, 1):
        debug_log(
            state,
            f"[run] paths\n"
            f"  input_dir={input_dir}\n"
            f"  reference_dir={reference_dir}\n"
            f"  output_dir={output_dir}",
            level=1,
        )

    contracts_root = _contracts_root(repo_root)
    registry = load_contract_registry(contracts_root)

    input_contracts = dict(tables_for_surface(registry, "input"))
    ref_contracts = dict(tables_for_surface(registry, "reference"))
    output_contracts = dict(tables_for_surface(registry, "output"))

    if debug_enabled(state, 2):
        debug_log(
            state,
            f"[run] registry\n"
            f"  input_tables={list(input_contracts.keys())}\n"
            f"  reference_tables={list(ref_contracts.keys())}\n"
            f"  output_tables={list(output_contracts.keys())}",
            level=2,
        )

    # ✅ Pass debug state through IO
    loaded = load_contract_inputs(
        input_dir=input_dir,
        reference_dir=reference_dir,
        registry=registry,
        require_input_files=True,
        require_reference_files=True,
        debug_state=state,   # ✅ FIX
    )

    # ✅ Validate inputs
    validated_inputs, input_logs = _validate_tables(loaded.input_tables, input_contracts)
    validated_refs, ref_logs = _validate_tables(loaded.reference_tables, ref_contracts)

    # ✅ Build debug state BEFORE logging
    state = state | _build_debug_state(validated_inputs, validated_refs)

    # ✅ LOG FIRST (this was missing)
    _log_validation_summary(state, input_logs)
    _log_validation_summary(state, ref_logs)

    # ✅ THEN fail
    _fail_if_any_errors(input_logs)
    _fail_if_any_errors(ref_logs)

    _validate_required_tables_non_empty(validated_inputs, input_contracts)
    _validate_required_tables_non_empty(validated_refs, ref_contracts)

    if debug_enabled(state, 1):
        debug_log(state, "[run] running pipeline", level=1)

    outputs = run_pipeline(
        ContractInputs(
            input_tables=validated_inputs,
            reference_tables=validated_refs,
        )
    )    
    
    if debug_enabled(state, 2):
        debug_log(
            state,
            f"[run] pipeline outputs\n"
            f"  tables={list(outputs.output_tables.keys())}",
            level=2,
        )

    write_contract_outputs(outputs, output_dir, registry)

    if debug_enabled(state, 1):
        debug_log(state, "[run] complete", level=1)

    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        import os
        level = int(os.getenv("SIMCO_DEBUG", "0"))

        print(str(e).strip())
        print("")
        print("Tip: Run with higher debug level for more detail")
        print("     Example: SIMCO_DEBUG=2 python -m engine.run")
        print("=" * 60 + "\n")

        if level >= 3:
            raise

        raise SystemExit(1)