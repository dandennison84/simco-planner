#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]


def run_step(label: str, cmd: list[str]) -> None:
    print(f"\n=== {label} ===")
    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode != 0:
        raise SystemExit(f"{label} failed")


def main(argv) -> int:
    python = sys.executable

    steps = [
        ("Build Template", [python, "tools/template/build_template.py"]),
        ("Generate Workbook", [python, "tools/template/generate_workbook.py"]),
        ("Export Inputs", [python, "tools/run/export_inputs.py"]),
    ]

    for label, cmd in steps:
        run_step(label, cmd)

    print("\n✅ All steps completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))