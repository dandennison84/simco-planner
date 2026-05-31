from typing import Dict


def _debug_level_from_state(state: Dict[str, object]) -> int:
    try:
        return int(
            state
            .get("_meta", {})
            .get("system_parameters_map", {})
            .get("debug.level", "0")
        )
    except Exception:
        return 0


def debug_enabled(state: Dict[str, object], level: int = 1) -> bool:
    return _debug_level_from_state(state) >= level


def debug_log(state: Dict[str, object], message: str, level: int = 1) -> None:
    if debug_enabled(state, level):
        print(message)


import csv
import io

def debug_rows(state: Dict[str, object], stage: str, table: str) -> None:
    rows = state.get(table, [])

    # ----------------------------------------
    # LEVEL 1: row count
    # ----------------------------------------
    if debug_enabled(state, 1):
        if isinstance(rows, list):
            print(f"[{stage}] {table}: rows={len(rows)}")
        else:
            print(f"[{stage}] {table}: (non-table)")

    # stop if not list
    if not isinstance(rows, list):
        return

    # ----------------------------------------
    # LEVEL 2: sample rows
    # ----------------------------------------
    if debug_enabled(state, 2):
        sample = rows[:5]
        print(f"[{stage}] {table} sample (first 5 rows):")
        for r in sample:
            print(r)

    # ----------------------------------------
    # LEVEL 3: full CSV dump
    # ----------------------------------------
    if debug_enabled(state, 3):
        if not rows:
            print(f"[{stage}] {table}: <empty>")
            return

        # collect all columns across rows (safe)
        cols = sorted({k for r in rows for k in r.keys()})

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=cols)

        writer.writeheader()
        for r in rows:
            writer.writerow(r)

        print(f"[{stage}] {table} CSV START")
        print(buffer.getvalue().strip())
        print(f"[{stage}] {table} CSV END")
