from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping
import csv

from engine.contracts import ContractRegistry, TableContract, tables_for_surface
from engine.debug import debug_log, debug_enabled

# =============================================================================
# Contracts
# =============================================================================

@dataclass(frozen=True)
class ContractInputs:
    input_tables: Dict[str, List[dict]]
    reference_tables: Dict[str, List[dict]]

@dataclass(frozen=True)
class ContractOutputs:
    output_tables: Dict[str, List[dict]]


# =============================================================================
# L1 Clean
# =============================================================================

def _clean_value(value: Any) -> str:
    return "" if value is None else str(value).strip()

def _clean_row(row: Mapping[str, Any]) -> Dict[str, str]:
    return {str(k): _clean_value(v) for k, v in row.items()}


# =============================================================================
# CSV Read
# =============================================================================

def _read_csv_rows(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [_clean_row(row) for row in reader]


# =============================================================================
# CSV Write
# =============================================================================

def _write_csv_rows(
    path: Path,
    rows: List[dict],
    *,
    columns: List[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if columns is None:
        columns = list(rows[0].keys()) if rows else []

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


# =============================================================================
# Contract-driven loading
# =============================================================================

def _load_contract_tables(
    directory: Path,
    contracts: Mapping[str, TableContract],
    *,
    require_files: bool,
    debug_state: Dict[str, object] | None = None,
) -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = {}

    for table_name in contracts.keys():
        csv_path = directory / f"{table_name}.csv"

        # ✅ Level 1: show file lookup
        if debug_state and debug_enabled(debug_state, 1):
            debug_log(
                debug_state,
                f"[io] lookup table='{table_name}' path='{csv_path}' exists={csv_path.exists()}",
                level=1,
            )

        if not csv_path.exists():
            if require_files:
                msg = (
                    f"[io:error] missing required CSV\n"
                    f"  table={table_name}\n"
                    f"  expected_path={csv_path}\n"
                    f"  directory={directory}"
                )

                # ✅ Always log BEFORE raising
                if debug_state:
                    debug_log(debug_state, msg, level=1)

                raise FileNotFoundError(msg)

            out[table_name] = []
            continue

        rows_raw = _read_csv_rows(csv_path)

        contract = contracts[table_name]
        allowed_cols = set(contract.fields.keys())

        rows = [
            {k: v for k, v in row.items() if k in allowed_cols}
            for row in rows_raw
        ]

        # ✅ Level 2: row count
        if debug_state and debug_enabled(debug_state, 2):
            debug_log(
                debug_state,
                f"[io] loaded {table_name}: rows={len(rows)}",
                level=2,
            )

        # ✅ Level 3: sample rows
        if debug_state and debug_enabled(debug_state, 3) and rows:
            sample = rows[:3]
            debug_log(
                debug_state,
                f"[io:{table_name}] sample_rows={sample}",
                level=3,
            )

        out[table_name] = rows

    return out

def load_contract_inputs(
    input_dir: Path,
    reference_dir: Path,
    registry: ContractRegistry,
    *,
    require_input_files: bool = True,
    require_reference_files: bool = True,
    debug_state: Dict[str, object] | None = None,
) -> ContractInputs:

    if debug_state and debug_enabled(debug_state, 1):
        debug_log(
            debug_state,
            f"[io] load_contract_inputs\n"
            f"  input_dir={input_dir}\n"
            f"  reference_dir={reference_dir}",
            level=1,
        )

    return ContractInputs(
        input_tables=_load_contract_tables(
            input_dir,
            tables_for_surface(registry, "input"),
            require_files=require_input_files,
            debug_state=debug_state,
        ),
        reference_tables=_load_contract_tables(
            reference_dir,
            tables_for_surface(registry, "reference"),
            require_files=require_reference_files,
            debug_state=debug_state,
        ),
    )

# =============================================================================
# Outputs
# =============================================================================

def write_contract_outputs(
    outputs: ContractOutputs,
    output_dir: Path,
    registry: ContractRegistry,
) -> None:
    output_contracts = tables_for_surface(registry, "output")

    if not output_contracts:
        raise ValueError(
            "[io:error]\n"
            "  reason=no output contracts defined\n"
            "  path=contracts/output\n"
            "  action=add output table contracts before running pipeline"
        )

    for table_name, contract in output_contracts.items():
        rows = outputs.output_tables.get(table_name)

        if rows is None:
            raise ValueError(
                f"[io:error]\n"
                f"  table={table_name}\n"
                f"  reason=output not produced by pipeline\n"
                f"  available_tables={list(outputs.output_tables.keys())}"
            )

        columns = list(contract.fields.keys())

        if not columns:
            raise ValueError(
                f"[io:error]\n"
                f"  table={table_name}\n"
                f"  reason=no columns defined in contract\n"
                f"  action=add fields to contract"
            )

        output_dir.mkdir(parents=True, exist_ok=True)

        _write_csv_rows(
            output_dir / f"{table_name}.csv",
            rows,
            columns=columns,
        )