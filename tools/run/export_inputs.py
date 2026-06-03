from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
import sys


# =============================================================================
# Path Resolution
# =============================================================================
def resolve_workbook_path(argv: Sequence[str]) -> Path:
    if len(argv) > 1:
        return Path(argv[1]).resolve()

    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / "runtime" / "Planner.xlsm").resolve()

def resolve_project_root(script_path: Path) -> Path:
    return script_path.resolve().parents[2]

def resolve_runtime_input_dir(project_root: Path) -> Path:
    return project_root / "data" / "runtime" / "input"


# =============================================================================
# Naming (STRICT CONTRACT)
# =============================================================================
ING_PREFIX = "_ing_"


def is_ingestion_sheet(sheet_name: str) -> bool:
    return sheet_name.startswith(ING_PREFIX)


def sheet_name_to_table_name(sheet_name: str) -> str:
    """
    STRICT CONTRACT:

      _ing_company → company
      _ing_map_structure → map_structure

    NO transformation
    NO camel parsing
    NO guessing
    """
    if not is_ingestion_sheet(sheet_name):
        raise ValueError(f"Not an ingestion sheet: {sheet_name}")

    table_name = sheet_name[len(ING_PREFIX):].strip()

    if not table_name:
        raise ValueError(f"Invalid ingestion sheet name: {sheet_name}")

    return table_name


def sheet_name_to_csv_name(sheet_name: str) -> str:
    table_name = sheet_name_to_table_name(sheet_name)
    return f"{table_name}.csv"


# =============================================================================
# Workbook Discovery
# =============================================================================
def open_workbook(workbook_path: Path) -> pd.ExcelFile:
    return pd.ExcelFile(workbook_path, engine="openpyxl")


def list_ingestion_sheets(excel_file: pd.ExcelFile) -> list[str]:
    return [name for name in excel_file.sheet_names if is_ingestion_sheet(name)]


# =============================================================================
# Sheet Parsing
# =============================================================================
def read_ingestion_sheet(excel_file: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    df = excel_file.parse(sheet_name=sheet_name)
    df = df.dropna(how="all")  # remove Excel noise rows
    return df


# =============================================================================
# CSV Emission
# =============================================================================
def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def clear_existing_csvs(input_dir: Path) -> None:
    """
    Deterministic build:
    remove stale CSVs before writing
    """
    for path in input_dir.glob("*.csv"):
        path.unlink()


def csv_output_path(input_dir: Path, sheet_name: str) -> Path:
    return input_dir / sheet_name_to_csv_name(sheet_name)


def write_csv(df: pd.DataFrame, path: Path) -> Path:
    df.to_csv(path, index=False)
    return path


# =============================================================================
# Ingestion Pipeline
# =============================================================================
def ingest_sheet_to_csv(
    excel_file: pd.ExcelFile,
    sheet_name: str,
    input_dir: Path,
) -> Path:
    df = read_ingestion_sheet(excel_file, sheet_name)
    out_path = csv_output_path(input_dir, sheet_name)
    return write_csv(df, out_path)


def ingest_workbook(
    workbook_path: Path,
    input_dir: Path,
) -> list[Path]:
    excel_file = open_workbook(workbook_path)
    ingestion_sheets = list_ingestion_sheets(excel_file)

    clear_existing_csvs(input_dir)

    return [
        ingest_sheet_to_csv(excel_file, sheet_name, input_dir)
        for sheet_name in ingestion_sheets
    ]


# =============================================================================
# Reporting
# =============================================================================
def print_start(workbook_path: Path) -> None:
    print(f"Reading workbook: {workbook_path}")


def print_no_ingestion_sheets() -> None:
    print("No _ing_ sheets found. Nothing to ingest.")


def print_written(paths: Iterable[Path]) -> None:
    for path in paths:
        print(f"Wrote: {path}")


def print_done() -> None:
    print("Ingestion complete.")


# =============================================================================
# Main
# =============================================================================
def main(argv: Sequence[str]) -> int:
    script_path = Path(__file__).resolve()
    project_root = resolve_project_root(script_path)
    workbook_path = resolve_workbook_path(argv)
    input_dir = ensure_directory(resolve_runtime_input_dir(project_root))

    if not workbook_path.exists():
        print(f"Workbook not found: {workbook_path}")
        return 1

    print_start(workbook_path)

    try:
        written_paths = ingest_workbook(workbook_path, input_dir)
    except Exception as exc:
        print(f"Ingestion failed: {exc}")
        return 1

    if not written_paths:
        print_no_ingestion_sheets()
        return 0

    print_written(written_paths)
    print_done()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))