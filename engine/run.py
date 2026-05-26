from __future__ import annotations

from pathlib import Path

from engine.io_csv import load_contract_inputs, write_contract_outputs
from engine.pipeline import run_pipeline


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    data_dir = repo_root / "data"
    input_dir = data_dir / "input"
    reference_dir = data_dir / "reference"
    output_dir = data_dir / "output"

    inputs = load_contract_inputs(
        input_dir=input_dir,
        reference_dir=reference_dir,
    )

    outputs = run_pipeline(inputs)

    write_contract_outputs(
        outputs=outputs,
        output_dir=output_dir,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())