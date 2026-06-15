from typing import Dict


def _k(x) -> str:
    """
    Normalize keys/values:
        - None → ""
        - strip whitespace
        - ensure string type
    """
    return ("" if x is None else str(x)).strip()


def stage_system_parameters(state: Dict[str, object]) -> Dict[str, object]:
    """
    =============================================================================
    Stage: system_parameters

    Purpose:
        Normalize system parameter table into a lookup map and store in _meta.

    Functional view:
        system_parameters_map = map(parameter_key → parameter_value)

        state_out = state_in + {_meta.system_parameters_map}

    Inputs:
        state["system_parameters"]:
            List of parameter rows:
                {parameter_key, parameter_value}

    Output:
        state["_meta"]["system_parameters_map"]:
            Dict[str, str]
                parameter_key → parameter_value

    Notes:
        - This is a pure transformation (no side effects beyond _meta)
        - Missing parameters resolve to "" via normalization
        - Downstream stages treat this as a read-only lookup
    =============================================================================
    """

    # Source table (raw parameter rows)
    rows = state.get("system_parameters", [])

    # Build parameter lookup:
    #   key:   parameter_key (normalized)
    #   value: parameter_value (normalized)
    param_map = {
        _k(r.get("parameter_key")): _k(r.get("parameter_value"))
        for r in rows
    }

    # Update meta container (do not mutate original directly)
    meta = dict(state["_meta"])
    meta["system_parameters_map"] = param_map

    # Return updated state with enriched _meta
    return dict(state, _meta=meta)