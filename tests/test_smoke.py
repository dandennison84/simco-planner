from __future__ import annotations

from pathlib import Path

from engine.io_csv import load_contract_inputs
from engine.pipeline import run_pipeline


def test_pipeline_runs_and_emits_contract_outputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "data"

    inputs = load_contract_inputs(
        input_dir=data_dir / "input",
        reference_dir=data_dir / "reference",
    )

    outputs = run_pipeline(inputs)

    assert "diagnostics" in outputs.output_tables
    assert "guidance" in outputs.output_tables
    assert "signal_evidence" in outputs.output_tables