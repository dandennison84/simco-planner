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


def debug_rows(state: Dict[str, object], stage: str, table: str) -> None:
    if not debug_enabled(state, 1):
        return

    rows = state.get(table, [])
    if isinstance(rows, list):
        print(f"[{stage}] {table}: rows={len(rows)}")
    else:
        print(f"[{stage}] {table}: (non-table)")