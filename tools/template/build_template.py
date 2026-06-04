#!/usr/bin/env python3
from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

import win32com.client as win32

from engine.debug import init_debug_state, debug_enabled, debug_log

from engine.contracts import (
    LookupRule,
    all_lookup_rules,
    group_lookup_rules_by_ref_table,
    load_contract_registry,
)

# =============================================================================
# Paths
# =============================================================================

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_SRC = ROOT / "tools" / "template" / "Template.xlsm"
TEMPLATE_DST = ROOT / "template" / "PlannerTemplate.xlsm"

REF_DIR = ROOT / "data" / "reference"
CONTRACTS_DIR = ROOT / "contracts"


# =============================================================================
# Helpers
# =============================================================================

def load_lookup_pairs(path: Path, key_col: str, name_col: str) -> List[Tuple[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            (str(row[key_col]).strip(), str(row[name_col]).strip())
            for row in reader
            if row.get(key_col) is not None and row.get(name_col) is not None
        ]


def _delete_existing_named_item(wb, name: str) -> None:
    try:
        wb.Names.Item(name).Delete()
    except Exception:
        pass

def _get_or_create_sheet(wb, sheet_name: str):
    for ws in wb.Worksheets:
        if ws.Name == sheet_name:
            return ws

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
    rows: List[Tuple[str, str]],
):
    ws = _get_or_create_sheet(wb, sheet_name)
    ws.Visible = 0  # hidden

    # set headers
    ws.Range("A1").Value = key_col
    ws.Range("B1").Value = name_col

    # get or create table (DO NOT delete)
    if ws.ListObjects.Count > 0:
        lo = ws.ListObjects(table_name)
    else:
        lo = ws.ListObjects.Add(
            1,
            ws.Range("A1:B2"),
            None,
            1
        )
        lo.Name = table_name

    # clear existing data body ONLY
    if lo.DataBodyRange is not None:
        lo.DataBodyRange.ClearContents()

    # write new data
    for i, (k, v) in enumerate(rows, start=2):
        ws.Cells(i, 1).Value = k
        ws.Cells(i, 2).Value = v

    # resize table AFTER writing
    last_row = max(2, len(rows) + 1)
    lo.Resize(ws.Range(f"A1:B{last_row}"))

    return ws

def create_name_dropdown_range(
    wb,
    *,
    range_name: str,
    sheet_name: str,
    row_count: int,
) -> None:
    _delete_existing_named_item(wb, range_name)

    last_row = max(2, row_count + 1)
    refers_to = f"='{sheet_name}'!$B$2:$B${last_row}"
    wb.Names.Add(Name=range_name, RefersTo=refers_to)


def apply_validation(ws, table_name: str, column_name: str, range_name: str) -> None:
    try:
        lo = ws.ListObjects(table_name)
    except Exception as e:
        available_tables = [t.Name for t in ws.ListObjects]
        raise RuntimeError(
            f"[template:error]\n"
            f"  worksheet={ws.Name}\n"
            f"  table={table_name}\n"
            f"  reason=table not found\n"
            f"  available_tables={available_tables}"
        ) from e

    available_columns = [lo.ListColumns(i).Name for i in range(1, lo.ListColumns.Count + 1)]

    try:
        target_column = lo.ListColumns(column_name)
    except Exception as e:
        raise RuntimeError(
            f"[template:error]\n"
            f"  worksheet={ws.Name}\n"
            f"  table={table_name}\n"
            f"  column={column_name}\n"
            f"  range={range_name}\n"
            f"  reason=column not found in table\n"
            f"  available_columns={available_columns}"
        ) from e

    target = target_column.DataBodyRange
    if target is None:
        raise RuntimeError(
            f"[template:error]\n"
            f"  worksheet={ws.Name}\n"
            f"  table={table_name}\n"
            f"  column={column_name}\n"
            f"  range={range_name}\n"
            f"  reason=table has no data body range"
        )

    try:
        target.Validation.Delete()
    except Exception:
        pass

    try:
        target.Validation.Add(
            Type=3,
            AlertStyle=1,
            Operator=1,
            Formula1=f"={range_name}",
        )
    except Exception as e:
        raise RuntimeError(
            f"[template:error]\n"
            f"  worksheet={ws.Name}\n"
            f"  table={table_name}\n"
            f"  column={column_name}\n"
            f"  range={range_name}\n"
            f"  reason=failed to add validation"
        ) from e

def _rules_by_ref_table(rules: Tuple[LookupRule, ...]) -> Dict[str, List[LookupRule]]:
    out: Dict[str, List[LookupRule]] = {}
    for rule in rules:
        out.setdefault(rule.ref_table, []).append(rule)
    return out


def _first_rule_per_ref_table(rules: List[LookupRule]) -> LookupRule:
    return sorted(
        rules,
        key=lambda r: (
            r.excel["sheet_name"],
            r.excel["table_name"],
            r.excel["range_name"],
        ),
    )[0]


# =============================================================================
# Main
# =============================================================================

def main():
    state = init_debug_state(REF_DIR)

    if debug_enabled(state, 1):
        debug_log(state, "[template] building template", level=1)

    if not TEMPLATE_SRC.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_SRC}")

    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    registry = load_contract_registry(CONTRACTS_DIR)

    lookup_rules = all_lookup_rules(registry)
    rules_by_ref = _rules_by_ref_table(lookup_rules)

    if debug_enabled(state, 2):
        debug_log(
            state,
            f"[template] registry summary\n"
            f"  lookup_rules={len(lookup_rules)}\n"
            f"  reference_tables={len(rules_by_ref)}",
            level=2,
        )

    TEMPLATE_DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TEMPLATE_SRC, TEMPLATE_DST)

    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False

    try:
        if debug_enabled(state, 1):
            debug_log(state, f"[template] opening workbook: {TEMPLATE_DST}", level=1)

        wb = excel.Workbooks.Open(str(TEMPLATE_DST))

        if debug_enabled(state, 2):
            sheet_names = [ws.Name for ws in wb.Worksheets]
            debug_log(
                state,
                f"[template] available sheets\n"
                f"  sheets={sheet_names}",
                level=2,
            )

        # ---------------------------------------------------------------------
        # Build lookup sheets
        # ---------------------------------------------------------------------
        for ref_table, rules in sorted(rules_by_ref.items()):
            if debug_enabled(state, 1):
                debug_log(state, f"[template] loading lookup: {ref_table}", level=1)

            rule = _first_rule_per_ref_table(rules)

            csv_path = REF_DIR / f"{ref_table}.csv"
            pairs = load_lookup_pairs(
                csv_path,
                rule.ref_key_field,
                rule.ref_label_field,
            )

            if debug_enabled(state, 2):
                debug_log(
                    state,
                    f"[template] lookup\n"
                    f"  table={ref_table}\n"
                    f"  rows={len(pairs)}",
                    level=2,
                )

            if debug_enabled(state, 3) and pairs:
                debug_log(
                    state,
                    f"[template:{ref_table}] sample\n" +
                    "\n".join(
                        f"  key={k}  name={v}"
                        for k, v in pairs[:5]
                    ),
                    level=3,
                )

            create_lookup_sheet_with_table(
                wb,
                sheet_name=rule.excel["sheet_name"],
                table_name=rule.excel["table_name"],
                key_col=rule.ref_key_field,
                name_col=rule.ref_label_field,
                rows=pairs,
            )

            if debug_enabled(state, 2):
                debug_log(
                    state,
                    f"[template] created sheet\n"
                    f"  sheet_name={rule.excel['sheet_name']}\n"
                    f"  table_name={rule.excel['table_name']}",
                    level=2,
                )

            create_name_dropdown_range(
                wb,
                range_name=rule.excel["range_name"],
                sheet_name=rule.excel["sheet_name"],
                row_count=len(pairs),
            )

            if debug_enabled(state, 2):
                debug_log(
                    state,
                    f"[template] created range\n"
                    f"  range_name={rule.excel['range_name']}\n"
                    f"  rows={len(pairs)}",
                    level=2,
                )

        # ---------------------------------------------------------------------
        # Apply validations (✅ FIXED — Inputs sheet only)
        # ---------------------------------------------------------------------
        ws = wb.Worksheets("Inputs")

        for rule in lookup_rules:
            if debug_enabled(state, 2):
                debug_log(
                    state,
                    f"[template] apply validation\n"
                    f"  ui_table={rule.ui_table}\n"
                    f"  column={rule.ui_column}\n"
                    f"  ref_table={rule.ref_table}",
                    level=2,
                )

            apply_validation(
                ws,
                table_name=rule.ui_table,
                column_name=rule.ui_column,
                range_name=rule.excel["range_name"],
            )

        wb.Save()
        wb.Close(SaveChanges=True)

        if debug_enabled(state, 1):
            debug_log(state, "[template] build complete", level=1)

    finally:
        excel.Quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import os
        level = int(os.getenv("SIMCO_DEBUG", "0"))

        print(str(e).strip())
        print("")
        print("Tip: Run with higher debug level for more detail")
        print("     Example: SIMCO_DEBUG=2 python -m tools.template.build_template")
        print("=" * 60 + "\n")

        if level >= 3:
            raise

        raise SystemExit(1)