from typing import Dict


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def stage_system_parameters(state: Dict[str, object]) -> Dict[str, object]:

    rows = state.get("system_parameters", [])

    param_map = {
        _k(r.get("parameter_key")): _k(r.get("parameter_value"))
        for r in rows
    }

    meta = dict(state["_meta"])
    meta["system_parameters_map"] = param_map

    return dict(state, _meta=meta)