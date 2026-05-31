#!/usr/bin/env python3
from __future__ import annotations

import csv
import shutil
from pathlib import Path
import yaml

import win32com.client as win32


# =============================================================================
# Paths
# =============================================================================
ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_SRC = ROOT / "template" / "Template.xlsm"
TEMPLATE_DST = ROOT / "template" / "PlannerTemplate.xlsm"

REF_DIR = ROOT / "data" / "reference"
UI_CONFIG_PATH = ROOT / "schema" / "ui.yml"


# =============================================================================
# Lookup definitions
# These drive BOTH:
#   - Excel dropdowns (named ranges over names)
#   - Power Query joins (real Excel tables with key + name)
# =============================================================================
LOOKUPS = [
    {
        "sheet_name": "_ref_building",
        "table_name": "ref_building",
        "csv_path": REF_DIR / "building.csv",
        "key_col": "building_key",
        "name_col": "building_name",
        "range_name": "nr_BuildingNames",
    },
    {
        "sheet_name": "_ref_product",
        "table_name": "ref_product",
        "csv_path": REF_DIR / "product.csv",
        "key_col": "product_key",
        "name_col": "product_name",
        "range_name": "nr_ProductNames",
    },
    {
        "sheet_name": "_ref_sales_channel",
        "table_name": "ref_sales_channel",
        "csv_path": REF_DIR / "sales_channel.csv",
        "key_col": "sales_channel_key",
        "name_col": "sales_channel_name",
        "range_name": "nr_SalesChannelNames",
    },
    {
        "sheet_name": "_ref_realm",
        "table_name": "ref_realm",
        "csv_path": REF_DIR / "realm.csv",
        "key_col": "realm_key",
        "name_col": "realm_name",
        "range_name": "nr_RealmNames",
    },
]


# =============================================================================
# UI config
# =============================================================================
def load_ui_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing UI config: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    tables = data.get("tables", {})
    if not isinstance(tables, dict):
        raise ValueError("schema/ui.yml must contain a top-level 'tables' mapping")

    return tables


# =============================================================================
# CSV helpers
# =============================================================================
def load_lookup_pairs(path: Path, key_col: str, name_col: str) -> list[tuple[str, str]]:
    """
    Reads canonical reference CSVs (snake_case headers) and returns rows as:
        [(key, name), ...]
    Sorted by name for UI friendliness.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        rows: list[tuple[str, str]] = []
        for record in reader:
            k = (record.get(key_col) or "").strip()
            v = (record.get(name_col) or "").strip()
            if k and v:
                rows.append((k, v))

    return sorted(rows, key=lambda x: x[1])


# =============================================================================
# Excel helpers
# =============================================================================
def _column_letter(n: int) -> str:
    """
    1 -> A, 2 -> B, 27 -> AA
    """
    letters = []
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters.append(chr(65 + rem))
    return "".join(reversed(letters))


def _delete_existing_named_item(wb, name: str) -> None:
    try:
        wb.Names.Item(name).Delete()
    except Exception:
        pass


def _delete_existing_sheet_if_present(wb, sheet_name: str) -> None:
    names = [ws.Name for ws in wb.Worksheets]
    if sheet_name in names:
        wb.Worksheets(sheet_name).Delete()


def create_lookup_sheet_with_table(
    wb,
    *,
    sheet_name: str,
    table_name: str,
    key_col: str,
    name_col: str,
    rows: list[tuple[str, str]],
):
    """
    Creates:
      - worksheet named _ref_*
      - Excel table named ref_* at A1:B{n}
      - headers = snake_case schema names
      - data rows = key + name
    """
    # Remove any stale sheet in the copied workbook (defensive)
    _delete_existing_sheet_if_present(wb, sheet_name)

    ws = wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
    ws.Name = sheet_name

    # headers
    ws.Cells(1, 1).Value = key_col
    ws.Cells(1, 2).Value = name_col

    # data
    for i, (k, v) in enumerate(rows, start=2):
        ws.Cells(i, 1).Value = k
        ws.Cells(i, 2).Value = v

    last_row = max(2, len(rows) + 1)
    table_ref = f"A1:B{last_row}"

    # Remove stale table name if needed (defensive)
    # Table names live workbook-wide
    try:
        existing = wb.Worksheets(sheet_name).ListObjects(table_name)
        existing.Delete()
    except Exception:
        pass

    # Create Excel Table so Power Query can consume via Excel.CurrentWorkbook()
    lo = ws.ListObjects.Add(1, ws.Range(table_ref), None, 1)
    lo.Name = table_name

    # Optional style (safe if available)
    try:
        lo.TableStyle = "TableStyleLight9"
    except Exception:
        pass

    # Hide sheet after creation (Power Query can still read workbook tables)
    # Change to -1 if you want them visible for debugging.
    ws.Visible = 2  # xlSheetVeryHidden

    return ws, len(rows)


def create_name_dropdown_range(
    wb,
    *,
    range_name: str,
    sheet_name: str,
    row_count: int,
):
    """
    Creates workbook-level named range over the NAME column only (column B),
    used for Excel data validation dropdowns.
    """
    _delete_existing_named_item(wb, range_name)

    last_row = max(2, row_count + 1)
    ref_formula = f"={sheet_name}!$B$2:$B${last_row}"
    wb.Names.Add(Name=range_name, RefersTo=ref_formula)


def apply_validation(ws, table_name: str, column_name: str, range_name: str) -> None:
    """
    Applies Excel list validation to one UI column.
    """
    lo = ws.ListObjects(table_name)

    target = None
    for i in range(1, lo.ListColumns.Count + 1):
        col = lo.ListColumns(i)
        if col.Name == column_name:
            target = col.Range
            break

    if target is None:
        raise Exception(f"{column_name} not found in {table_name}")

    try:
        target.Validation.Delete()
    except Exception:
        pass

    # Type=3 => list validation
    target.Validation.Add(3, 1, 1, f"={range_name}")
    target.Validation.InCellDropdown = True


# =============================================================================
# UI lookup mapping
# Keeps only UI wiring here; engine remains schema-driven.
# =============================================================================
LOOKUP_TO_RANGE = {
    "building": "nr_BuildingNames",
    "product": "nr_ProductNames",
    "sales_channel": "nr_SalesChannelNames",
    "realm": "nr_RealmNames",
}


# =============================================================================
# Main
# =============================================================================
def main():
    if not TEMPLATE_SRC.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_SRC}")

    # Deterministic rebuild
    if TEMPLATE_DST.exists():
        TEMPLATE_DST.unlink()

    shutil.copy2(TEMPLATE_SRC, TEMPLATE_DST)

    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False

    wb = xl.Workbooks.Open(str(TEMPLATE_DST))

    try:
        # ---------------------------------------------------------------------
        # STEP 1: Create _ref_* sheets + Excel tables + dropdown named ranges
        # ---------------------------------------------------------------------
        for spec in LOOKUPS:
            rows = load_lookup_pairs(
                spec["csv_path"],
                spec["key_col"],
                spec["name_col"],
            )

            create_lookup_sheet_with_table(
                wb,
                sheet_name=spec["sheet_name"],
                table_name=spec["table_name"],
                key_col=spec["key_col"],
                name_col=spec["name_col"],
                rows=rows,
            )

            create_name_dropdown_range(
                wb,
                range_name=spec["range_name"],
                sheet_name=spec["sheet_name"],
                row_count=len(rows),
            )

        # ---------------------------------------------------------------------
        # STEP 2: Apply UI validations from schema/ui.yml
        # ---------------------------------------------------------------------
        ui_tables = load_ui_config(UI_CONFIG_PATH)
        ws_inputs = wb.Worksheets("Inputs")

        for table_name, table_spec in ui_tables.items():
            rules = table_spec.get("validations", []) or []
            for rule in rules:
                lookup_name = rule["lookup"]
                range_name = LOOKUP_TO_RANGE[lookup_name]

                apply_validation(
                    ws_inputs,
                    table_name,
                    rule["column"],
                    range_name,
                )


        import time

        print("→ Refreshing Power Query...")

        wb.RefreshAll()

        # ✅ Allow Excel to start async queries
        time.sleep(1)

        # ✅ Wait a fixed duration (tune this)
        sleep_seconds = 5   # start with 5–10 depending on data size
        time.sleep(sleep_seconds)

        print("✅ Refresh window complete")
        wb.Save()
        print("✅ PlannerTemplate.xlsm generated successfully")

    finally:
        wb.Close(SaveChanges=True)
        xl.Quit()


if __name__ == "__main__":
    main()