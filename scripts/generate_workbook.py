#!/usr/bin/env python3
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# Configuration
# =============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

TEMPLATE_DIR = PROJECT_ROOT / "template"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
DATA_RUNTIME_DIR = PROJECT_ROOT / "data" / "runtime"
INPUT_DIR = DATA_RUNTIME_DIR / "input"
OUTPUT_DIR = DATA_RUNTIME_DIR / "output"

TEMPLATE_FILE = TEMPLATE_DIR / "PlannerTemplate.xlsm"
RUNTIME_FILE = RUNTIME_DIR / "Planner.xlsm"

# User-editable ListObjects to clear in the generated workbook.
# Keep these aligned with your actual Excel table names.
TABLES_TO_CLEAR = {
    "Inputs": [
        #"tblCompany",
        #"tblMapStructure",
        #"tblProductionPlan",
        #"tblSalesPlan",
        #"tblOverrideExchangePrices",
        #"tblOverrideRetailPrices"
    ],
    "Outputs": [
        # Add your output tables here once finalized, for example:
        # "tblDiagnostics",
        # "tblKpiSummary",
        # "tblThroughput",
    ],
}

GENERATED_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
META_WRITES = [
    # Safe no-op if sheet/cell doesn't exist
    ("Help", "B2", f"Generated: {GENERATED_UTC}"),
]


# =============================================================================
# Helpers
# =============================================================================
def ensure_dirs() -> None:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}")
    raise SystemExit(code)


def copy_template(src: Path, dst: Path) -> None:
    if not src.exists():
        fail(f"Template workbook not found: {src}")
    shutil.copy2(src, dst)


def clear_listobject_keep_one_blank_row(lo) -> None:
    """
    Clear a ListObject while preserving:
    - headers
    - table style / formatting
    - one blank data row for user entry

    This relies on Excel COM and works with .xlsx / .xlsm / .xlsb.
    """
    # Ensure at least one data row exists
    if lo.ListRows.Count == 0:
        lo.ListRows.Add()

    # Clear the first data row contents only (keep formatting)
    if lo.DataBodyRange is not None:
        first_row = lo.DataBodyRange.Rows(1)
        first_row.ClearContents()

    # Delete all rows after the first
    while lo.ListRows.Count > 1:
        lo.ListRows(lo.ListRows.Count).Delete()


def reset_workbook_xlsm(path: Path) -> None:
    """
    Windows-only path using installed Excel via COM automation.
    Preserves VBA, buttons, shapes, Power Query, and .xlsm format.
    """
    try:
        import win32com.client as win32  # pywin32
    except Exception:
        fail(
            "This script requires Excel + pywin32 on Windows to modify .xlsm files. "
            "Install pywin32 with: pip install pywin32"
        )

    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.EnableEvents = False
    xl.ScreenUpdating = False

    wb = None
    try:
        wb = xl.Workbooks.Open(str(path), UpdateLinks=0, ReadOnly=False)

        for sheet_name, table_names in TABLES_TO_CLEAR.items():
            try:
                ws = wb.Worksheets(sheet_name)
            except Exception:
                continue

            for table_name in table_names:
                try:
                    lo = ws.ListObjects(table_name)
                except Exception:
                    # Table doesn't exist in the template yet; skip safely
                    continue
                clear_listobject_keep_one_blank_row(lo)

        # Optional metadata writes
        for sheet_name, cell_addr, value in META_WRITES:
            try:
                wb.Worksheets(sheet_name).Range(cell_addr).Value = value
            except Exception:
                pass

        wb.Save()

    finally:
        if wb is not None:
            wb.Close(SaveChanges=True)
        xl.Quit()


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    ensure_dirs()
    copy_template(TEMPLATE_FILE, RUNTIME_FILE)
    reset_workbook_xlsm(RUNTIME_FILE)

    print(f"Generated workbook: {RUNTIME_FILE}")
    print(f"Ensured runtime directories:")
    print(f"  input:  {INPUT_DIR}")
    print(f"  output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()