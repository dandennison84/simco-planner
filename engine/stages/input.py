from typing import Dict
from engine.io_csv import ContractInputs


def stage_input(inputs: ContractInputs) -> Dict[str, object]:
    """
    =============================================================================
    Stage: input

    Purpose:
        Initialize engine state by loading all external data.

    Functional view:
        state = merge(input_tables, reference_tables) + _meta

    Inputs:
        inputs.input_tables      → user-provided data (scenario-specific)
        inputs.reference_tables  → static reference data (lookup tables)

    Output:
        state: Dict[str, object]
            - contains all input + reference tables
            - includes empty "_meta" container for downstream use

    Notes:
        - No transformation occurs here (pure load + merge)
        - Later stages assume all required tables are present
    =============================================================================
    """

    # Core state container passed through all stages
    state: Dict[str, object] = {}

    # Merge user inputs (scenario data)
    state.update(inputs.input_tables)

    # Merge reference data (lookup tables, constants)
    state.update(inputs.reference_tables)

    # Reserved namespace for diagnostics, flags, and runtime metadata
    state["_meta"] = {}

    return state