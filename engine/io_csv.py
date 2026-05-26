from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class ContractInputs:
    """
    Minimal contract inputs.

    This is intentionally permissive at bootstrap time:
    - we load files if present
    - we do not enforce schema yet
    - schema enforcement comes with tests and validation rules
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


def _read_csv_rows(path: Path) -> List[dict]:
    import csv

    if not path.exists():
        return []

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def _write_csv_rows(path: Path, rows: List[dict]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)

    # If no rows, we still write headers if possible; otherwise write empty file.
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

    Naming is semantic + snake_case and matches DATA_CONTRACTS.md.
    Missing files load as empty tables.
    """
    input_names = [
        "company_snapshot",
        "financial_snapshot",
        "structure_map",
        "slot_product_assignment",
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