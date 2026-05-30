#!/usr/bin/env python3
from __future__ import annotations

import csv
import shutil
from pathlib import Path

import win32com.client as win32


# =============================================================================
# Paths
# =============================================================================
ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_SRC = ROOT / "template" / "Template.xlsm"
TEMPLATE_DST = ROOT / "template" / "PlannerTemplate.xlsm"

REF_DIR = ROOT / "data" / "reference"


# =============================================================================
# Lookup definitions (NAME ONLY)
# =============================================================================
LOOKUPS = [
    {
        "sheet": "_ref_Building",
        "csv": REF_DIR / "building.csv",
        "col": "Building Name",
        "range": "nr_BuildingNames",
    },
    {
        "sheet": "_ref_Product",
        "csv": REF_DIR / "product.csv",
        "col": "Product Name",
        "range": "nr_ProductNames",
    },
    {
        "sheet": "_ref_SalesChannel",
        "csv": REF_DIR / "sales_channel.csv",
        "col": "Sales Channel Name",
        "range": "nr_SalesChannelNames",
    },
    {
        "sheet": "_ref_Realm",
        "csv": REF_DIR / "realm.csv",
        "col": "Realm Name",
        "range": "nr_RealmNames",
    },
]


# =============================================================================
# Validation targets
# =============================================================================
VALIDATIONS = [
    ("tblCompany", "Realm Name", "nr_RealmNames"),
    ("tblMapStructure", "Building Name", "nr_BuildingNames"),
    ("tblProductionPlan", "Product Name", "nr_ProductNames"),
    ("tblSalesPlan", "Product Name", "nr_ProductNames"),
    ("tblSalesPlan", "Sales Channel", "nr_SalesChannelNames"),
    ("tblOverrideExchangePrices", "Realm Name", "nr_RealmNames"),
    ("tblOverrideExchangePrices", "Product Name", "nr_ProductNames"),
    ("tblOverrideRetailPrices", "Realm Name", "nr_RealmNames"),
    ("tblOverrideRetailPrices", "Product Name", "nr_ProductNames"),
]


# =============================================================================
# Helpers
# =============================================================================
def load_names(path: Path, col: str):
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV: {path}")

    values = []
    with path.open(encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            v = (r.get(col) or "").strip()
            if v:
                values.append(v)

    return sorted(set(values))


def delete_ref_sheets(wb):
    for ws in wb.Worksheets:
        name = ws.Name
        if name.startswith("_ref_"):
            ws.Delete()


def create_lookup_sheet(wb, name, header, values):
    ws = wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count))
    ws.Name = name

    # header
    ws.Cells(1, 1).Value = header

    # values
    for i, v in enumerate(values, start=2):
        ws.Cells(i, 1).Value = v

    # hide
    ws.Visible = 2  # xlSheetVeryHidden

    return ws, len(values)


def create_named_range(wb, name, sheet, count):
    last_row = max(2, count + 1)

    # ✅ Correct Excel formula (no leading quote wrapping needed here)
    ref_formula = f"={sheet}!$A$2:$A${last_row}"

    # Delete if exists
    try:
        wb.Names.Item(name).Delete()
    except:
        pass

    # ✅ Add correctly formatted formula
    wb.Names.Add(Name=name, RefersTo=ref_formula)


def apply_validation(ws, table_name, column_name, range_name):
    lo = ws.ListObjects(table_name)

    target = None
    for i in range(1, lo.ListColumns.Count + 1):
        col = lo.ListColumns(i)
        if col.Name == column_name:
            target = target = col.Range
            break

    if target is None:
        raise Exception(f"Column {column_name} not found in {table_name}")

    try:
        target.Validation.Delete()
    except:
        pass

    target.Validation.Add(3, 1, 1, f"={range_name}")

    target.Validation.InCellDropdown = True


# =============================================================================
# Main
# =============================================================================
def main():
    if not TEMPLATE_SRC.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_SRC}")

    # ---------------------------------------------------------
    # Step 1: COPY template (never overwrite source)
    # ---------------------------------------------------------
    shutil.copy2(TEMPLATE_SRC, TEMPLATE_DST)

    xl = win32.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False

    wb = xl.Workbooks.Open(str(TEMPLATE_DST))

    try:
        # -----------------------------------------------------
        # Step 2: REMOVE existing _ref_* sheets
        # -----------------------------------------------------
        delete_ref_sheets(wb)

        # -----------------------------------------------------
        # Step 3–5: CREATE lookup sheets + named ranges
        # -----------------------------------------------------
        for spec in LOOKUPS:
            values = load_names(spec["csv"], spec["col"])

            ws, count = create_lookup_sheet(
                wb,
                spec["sheet"],
                spec["col"],
                values
            )

            create_named_range(
                wb,
                spec["range"],
                spec["sheet"],
                count
            )

        # -----------------------------------------------------
        # Step 6: APPLY validation
        # -----------------------------------------------------
        ws_inputs = wb.Worksheets("Inputs")

        for table, col, rng in VALIDATIONS:
            apply_validation(ws_inputs, table, col, rng)

        wb.Save()

        print("✅ PlannerTemplate.xlsm generated successfully")

    finally:
        wb.Close(SaveChanges=True)
        xl.Quit()


if __name__ == "__main__":
    main()