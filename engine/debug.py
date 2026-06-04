from typing import Dict


import os

import os

from pathlib import Path
import csv


def init_debug_state(reference_dir: Path) -> Dict[str, object]:
    """
    Initialize debug state from system_parameters.csv

    This is the ONLY entry point for debug initialization.
    """

    system_parameters_map: Dict[str, str] = {}

    path = reference_dir / "system_parameters.csv"

    if path.exists():
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = str(row.get("parameter_key", "")).strip()
                    value = str(row.get("parameter_value", "")).strip()
                    if key:
                        system_parameters_map[key] = value
        except Exception:
            # fail silently → debug defaults to 0
            pass

    return {
        "_meta": {
            "system_parameters_map": system_parameters_map
        }
    }

def _debug_level_from_state(state: Dict[str, object]) -> int:
    """
    Resolution order:

    1. SIMCO_DEBUG env (for early failures + override)
    2. system_parameters_map["debug.level"]
    3. fallback = 0
    """

    # ✅ 1. ALWAYS allow env override (required for early failures)
    env = os.getenv("SIMCO_DEBUG")
    if env is not None:
        try:
            return int(env)
        except Exception:
            return 0

    # ✅ 2. Normal data-driven config (after load)
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
