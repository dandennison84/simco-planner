from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import csv


@dataclass(frozen=True)
class ContractInputs:
    """
    Minimal contract inputs.

    Behavior:
    - load known surfaces if files exist
    - L1 clean at ingestion (trim values; preserve keys)
    - schema enforcement happens later (validator layer)
    """
    input_tables: Dict[str, List[dict]]
    reference_tables: Dict[str, List[dict]]


@dataclass(frozen=True)
class ContractOutputs:
    """
    Minimal contract outputs.

    At bootstrap time we always emit output files (even if empty),
    to prove the end-to-end contract.
    """
    output_tables: Dict[str, List[dict]]


def _clean_row(row: dict) -> dict:
    """
    L1 Clean:
    - None -> ""
    - everything -> str(...).strip()
    Note: keys are preserved as-is; schema matching is exact on keys.
    """
    return {k: ("" if v is None else str(v).strip()) for k, v in row.items()}


def _read_csv_rows(path: Path) -> List[dict]:
    """
    IO only: read raw CSV rows into dicts.
    Cleaning is applied exactly once (via _clean_row) during read.
    """
    if not path.exists():
        return []

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)  # comma-delimited by default
        if reader.fieldnames is None:
            return []
        return [_clean_row(row) for row in reader]


def _write_csv_rows(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_contract_inputs(input_dir: Path, reference_dir: Path) -> ContractInputs:
    """
    Loads known external contract surfaces if files exist.

    Naming is snake_case and matches DATA_CONTRACTS.md.
    Missing files load as empty tables.
    """
    input_names = [
        "company_snapshot",
        "financial_snapshot",
        "structure_map",
        "slot_product_assignment",
        "sales_demand",
    ]

    reference_names = [
        "market_pricing",
        "product_bom",
        "system_parameters",
    ]

    input_tables = {name: _read_csv_rows(input_dir / f"{name}.csv") for name in input_names}
    reference_tables = {name: _read_csv_rows(reference_dir / f"{name}.csv") for name in reference_names}

    return ContractInputs(
        input_tables=input_tables,
        reference_tables=reference_tables,
    )


def write_contract_outputs(outputs: ContractOutputs, output_dir: Path) -> None:
    """
    Writes external output contract surfaces.

    At bootstrap time, we always emit the files for discoverability.
    """
    for name, rows in outputs.output_tables.items():
        _write_csv_rows(output_dir / f"{name}.csv", rows)
