from typing import Dict
from engine.io_csv import ContractInputs


def stage_input(inputs: ContractInputs) -> Dict[str, object]:
    """
    INPUT STAGE

    Merges:
      - input tables
      - reference tables

    Initializes:
      - _meta container
    """

    state: Dict[str, object] = {}

    # input + reference
    state.update(inputs.input_tables)
    state.update(inputs.reference_tables)

    # meta container
    state["_meta"] = {}

    return state