from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import csv


# Contract surfaces (engine-owned list; missing files load as empty)
INPUT_TABLES = [
    "company_snapshot",
    "company_observed",
    "structure_map",
    "slot_product_assignment",
    "sales_strategy",
    "scenario_delta",
    # not yet in schema.yml but reserved by architecture; loads as empty if missing
    "flow_policy",
]

REFERENCE_TABLES = [
    "product_bom",
    "market_pricing",
    "system_parameters",
]

OUTPUT_TABLES = [
    "diagnostics",
    "guidance",
    "signal_evidence",
    # optional internal surfaces can be added later without changing IO shape rules
    "throughput",
]


@dataclass(frozen=True)
class ContractInputs:
    """
    Minimal contract inputs.
    Values are L1-cleaned strings (except when tests construct inputs directly).
    """
    input_tables: Dict[str, List[dict]]
    reference_tables: Dict[str, List[dict]]


@dataclass(frozen=True)
class ContractOutputs:
    """
    Minimal contract outputs.
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

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append(_clean_row(r))
        return rows


def _write_csv_rows(path: Path, rows: List[dict]) -> None:
    """
    IO only: write dict rows to CSV.
    Header is union of keys encountered (stable sort).
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Always write a file (even empty) for determinism? For now: write only when rows exist.
    if not rows:
        # Create an empty file with no header to avoid implying schema.
        path.write_text("", encoding="utf-8")
        return

    # Stable header: sorted union of keys
    keys = sorted({k for r in rows for k in r.keys()})

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            out = {k: ("" if r.get(k) is None else str(r.get(k))) for k in keys}
            writer.writerow(out)


def load_contract_inputs(input_dir: Path, reference_dir: Path) -> ContractInputs:
    """
    Loads known external contract surfaces if files exist.
    Missing files are loaded as empty tables.
    """
    input_tables: Dict[str, List[dict]] = {}
    reference_tables: Dict[str, List[dict]] = {}

    for name in INPUT_TABLES:
        input_tables[name] = _read_csv_rows(input_dir / f"{name}.csv")

    for name in REFERENCE_TABLES:
        reference_tables[name] = _read_csv_rows(reference_dir / f"{name}.csv")

    return ContractInputs(input_tables=input_tables, reference_tables=reference_tables)


def write_contract_outputs(outputs: ContractOutputs, output_dir: Path) -> None:
    """
    Writes external output contract surfaces.
    """
    for name, rows in outputs.output_tables.items():
        _write_csv_rows(output_dir / f"{name}.csv", rows)
