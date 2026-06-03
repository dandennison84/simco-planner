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
ROOT = Path(__file__).resolve().parents[2]

TEMPLATE_SRC = ROOT / "tools" / "template" / "Template.xlsm"
TEMPLATE_DST = ROOT / "template" / "PlannerTemplate.xlsm"

REF_DIR = ROOT / "data" / "reference"
UI_CONFIG_PATH = ROOT / "schema" / "ui.yml"


# =============================================================================
# Lookup definitions
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
        "sheet_name": "_ref_realm",
        "table_name": "ref_realm",
        "csv_path": REF_DIR / "realm.csv",
        "key_col": "realm_key",
        "name_col": "realm_name",
        "range_name": "nr_RealmNames",
    },
    {
        "sheet_name": "_ref_channel",
        "table_name": "ref_channel",
        "csv_path": REF_DIR / "channel.csv",
        "key_col": "channel_key",
        "name_col": "channel_name",
        "range_name": "nr_ChannelNames",
    },
]


# =============================================================================
# Helpers
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


def load_lookup_pairs(path: Path, key_col: str, name_col: str) -> list[tuple[str, str]]:
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
# Excel helpers (SAFE VERSION)
# =============================================================================
def _delete_existing_named_item(wb, name: str) -> None:
    try:
        wb.Names.Item(name).Delete()
    except Exception:
        pass


def _get_or_create_sheet(wb, sheet_name: str):
    names = [ws.Name for ws in wb.Worksheets]

    if sheet_name in names:
        ws = wb.Worksheets(sheet_name)

        # ✅ Clear only contents, do NOT delete sheet
        try:
            ws.Cells.ClearContents()
        except Exception:
            pass

    else:
        ws = wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
        ws.Name = sheet_name

    return ws


def create_lookup_sheet_with_table(
    wb,
    *,
    sheet_name: str,
    table_name: str,
    key_col: str,
    name_col: str,
    rows: list[tuple[str, str]],
):
    # ✅ Get or reset sheet (NO deletion)
    ws = _get_or_create_sheet(wb, sheet_name)

    # headers
    ws.Cells(1, 1).Value = key_col
    ws.Cells(1, 2).Value = name_col

    # data
    for i, (k, v) in enumerate(rows, start=2):
        ws.Cells(i, 1).Value = k
        ws.Cells(i, 2).Value = v

    last_row = max(2, len(rows) + 1)
    table_ref = f"A1:B{last_row}"

    # ✅ Delete TABLE only (safe)
    try:
        existing = ws.ListObjects(table_name)
        existing.Delete()
    except Exception:
        pass

    # Create table
    lo = ws.ListObjects.Add(1, ws.Range(table_ref), None, 1)
    lo.Name = table_name

    try:
        lo.TableStyle = "TableStyleLight9"
    except Exception:
        pass

    ws.Visible = 2  # VeryHidden

    return ws, len(rows)


def create_name_dropdown_range(
    wb,
    *,
    range_name: str,
    sheet_name: str,
    row_count: int,
):
    _delete_existing_named_item(wb, range_name)

    last_row = max(2, row_count + 1)
    ref_formula = f"={sheet_name}!$B$2:$B${last_row}"
    wb.Names.Add(Name=range_name, RefersTo=ref_formula)


def apply_validation(ws, table_name: str, column_name: str, range_name: str) -> None:
    lo = ws.ListObjects(table_name)
    target = lo.ListColumns(column_name).Range

    try:
        target.Validation.Delete()
    except Exception:
        pass

    target.Validation.Add(3, 1, 1, f"={range_name}")
    target.Validation.InCellDropdown = True


LOOKUP_TO_RANGE = {
    "building": "nr_BuildingNames",
    "product": "nr_ProductNames",
    "channel": "nr_ChannelNames",
    "realm": "nr_RealmNames",
}


# =============================================================================
# Main
# =============================================================================
def main():
    if not TEMPLATE_SRC.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_SRC}")

    if TEMPLATE_DST.exists():
        TEMPLATE_DST.unlink()

    shutil.copy2(TEMPLATE_SRC, TEMPLATE_DST)

    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False

    wb = xl.Workbooks.Open(str(TEMPLATE_DST))

    try:
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

        ui_tables = load_ui_config(UI_CONFIG_PATH)
        ws_inputs = wb.Worksheets("Inputs")

        for table_name, table_spec in ui_tables.items():
            for rule in table_spec.get("validations", []):
                apply_validation(
                    ws_inputs,
                    table_name,
                    rule["column"],
                    LOOKUP_TO_RANGE[rule["lookup"]],
                )

        import time

        print("→ Refreshing Power Query...")
        wb.RefreshAll()

        time.sleep(5)

        wb.Save()
        print("✅ PlannerTemplate.xlsm generated successfully")

    finally:
        wb.Close(SaveChanges=True)
        xl.Quit()


if __name__ == "__main__":
    main()