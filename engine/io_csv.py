from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping
import csv

"""
I/O boundary only.

This module:
- reads CSVs into normalized row structures
- writes schema-driven outputs

This module does NOT:
- validate schema
- enforce constraints
- enforce logical relationships
"""

# =============================================================================
# Contracts
# =============================================================================
@dataclass(frozen=True)
class ContractInputs:
    """
    External engine inputs at the CSV contract boundary.

    All rows are L1-cleaned strings:
    - None -> ""
    - everything else -> str(...).strip()

    Typing/constraints are enforced later by the validator.
    """
    input_tables: Dict[str, List[dict]]
    reference_tables: Dict[str, List[dict]]


@dataclass(frozen=True)
class ContractOutputs:
    """
    External engine outputs at the CSV contract boundary.
    """
    output_tables: Dict[str, List[dict]]


# =============================================================================
# L1 Clean
# =============================================================================
def _clean_value(value: Any) -> str:
    """
    Pure value normalizer for contract reads.

    Rules:
    - None -> ""
    - everything else -> stripped string
    """
    return "" if value is None else str(value).strip()


def _clean_row(row: Mapping[str, Any]) -> Dict[str, str]:
    """
    Pure row normalizer.
    Preserves keys exactly as provided by CSV headers.
    """
    return {str(k): _clean_value(v) for k, v in row.items()}


# =============================================================================
# CSV Read / Write (I/O only)
# =============================================================================
def _read_csv_rows(path: Path) -> List[dict]:
    """
    Read CSV rows as dictionaries and apply L1 clean exactly once.

    Missing file behavior is handled by the caller.
    """
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [_clean_row(row) for row in reader]


def _write_csv_rows(
    path: Path,
    rows: List[dict],
    *,
    columns: List[str] | None = None,
) -> None:
    """
    Write dict rows to CSV.

    Rules:
    - always creates parent directories
    - if columns are provided, they are the schema source of truth
    - if rows is empty and columns are provided, writes header-only CSV
    - if rows is empty and columns are not provided, writes empty file
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if columns is not None:
        keys = list(columns)
    else:
        keys = sorted({k for row in rows for k in row.keys()})

    if not keys:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            if all(row.get(k) in (None, "") for k in keys):
                continue
            writer.writerow({k: "" if row.get(k) is None else str(row.get(k)) for k in keys})

# =============================================================================
# Schema-driven table discovery
# =============================================================================
def _table_names_from_schema(schema_doc: Dict[str, Any]) -> List[str]:
    """
    Extract table names from a loaded schema document.

    Expected shape:
      {
        "tables": {
          "table_name": {...},
          ...
        }
      }

    Raises:
      ValueError if schema shape is invalid.
    """
    if not isinstance(schema_doc, dict):
        raise ValueError("Schema document must be a mapping")

    tables = schema_doc.get("tables", {})
    if not isinstance(tables, dict):
        raise ValueError("Schema document 'tables' must be a mapping")

    return list(tables.keys())


# =============================================================================
# Contract loading
# =============================================================================
def _load_contract_tables(
    directory: Path,
    schema_doc: Dict[str, Any],
    *,
    require_files: bool = True,
) -> Dict[str, List[dict]]:
    """
    Load exactly the tables defined by the schema from the given directory.

    Strict behavior:
    - if require_files=True, every schema-defined CSV must exist
    - if require_files=False, missing files load as empty tables

    This function does NOT validate schema, types, or constraints.
    It only loads the contract surfaces defined by schema.
    """
    table_names = _table_names_from_schema(schema_doc)

    tables: Dict[str, List[dict]] = {}

    for name in table_names:
        path = directory / f"{name}.csv"

        if not path.exists():
            if require_files:
                raise FileNotFoundError(f"Required contract file not found: {path}")
            tables[name] = []
            continue

        tables[name] = _read_csv_rows(path)

    return tables


def load_contract_inputs(
    input_dir: Path,
    reference_dir: Path,
    input_schema: Dict[str, Any],
    reference_schema: Dict[str, Any],
    *,
    require_input_files: bool = True,
    require_reference_files: bool = True,
) -> ContractInputs:
    """
    Load external input/reference CSV contract surfaces using schema as the
    single source of truth.

    No directory scanning.
    No hardcoded table lists.
    No validation here.

    This is the CSV contract boundary:
      CSV -> raw cleaned rows
    """
    input_tables = _load_contract_tables(
        input_dir,
        input_schema,
        require_files=require_input_files,
    )

    reference_tables = _load_contract_tables(
        reference_dir,
        reference_schema,
        require_files=require_reference_files,
    )

    return ContractInputs(
        input_tables=input_tables,
        reference_tables=reference_tables,
    )


# =============================================================================
# Output writing
# =============================================================================
def write_contract_outputs(
    outputs: ContractOutputs,
    output_dir: Path,
    output_schema: Dict[str, Any],
) -> None:
    """
    Write output contract surfaces using output schema as the
    source of truth for column order and empty-table headers.
    """
    schema_tables = output_schema.get("tables", {})

    for name, rows in outputs.output_tables.items():
        table_schema = schema_tables.get(name, {})
        fields = table_schema.get("fields", {})
        columns = list(fields.keys())

        _write_csv_rows(
            output_dir / f"{name}.csv",
            rows,
            columns=columns,
        )