from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from engine.run import main as run_engine


# ---------- config ----------

CASES_DIRNAME = "cases"
CASE_INPUT_DIRNAME = "input"
CASE_REFERENCE_DIRNAME = "reference"
CASE_EXPECTED_DIRNAME = "expected"

REPO_DATA_DIRNAME = Path("data") / "test"
REPO_INPUT_DIRNAME = "input"
REPO_REFERENCE_DIRNAME = "reference"
REPO_OUTPUT_DIRNAME = "output"

MAX_DIFF_ROWS = 3


# ---------- helpers ----------

@dataclass(frozen=True)
class CasePaths:
    case_name: str
    case_root: Path
    case_input: Path
    case_reference: Path
    case_expected: Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _tests_root() -> Path:
    return Path(__file__).resolve().parent


def _cases_root() -> Path:
    return _tests_root() / CASES_DIRNAME


def _data_root() -> Path:
    return _repo_root() / REPO_DATA_DIRNAME


def _data_input_dir() -> Path:
    return _data_root() / REPO_INPUT_DIRNAME


def _data_reference_dir() -> Path:
    return _data_root() / REPO_REFERENCE_DIRNAME


def _data_output_dir() -> Path:
    return _data_root() / REPO_OUTPUT_DIRNAME


def _list_case_dirs() -> List[CasePaths]:
    root = _cases_root()
    if not root.exists():
        return []

    cases: List[CasePaths] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue

        cases.append(
            CasePaths(
                case_name=p.name,
                case_root=p,
                case_input=p / CASE_INPUT_DIRNAME,
                case_reference=p / CASE_REFERENCE_DIRNAME,
                case_expected=p / CASE_EXPECTED_DIRNAME,
            )
        )
    return cases


# ---------- IO helpers ----------

def _wipe_dir_contents(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_file():
            if child.name != ".gitkeep":
                child.unlink()
        else:
            shutil.rmtree(child)


def _install_case(case: CasePaths) -> None:
    _wipe_dir_contents(_data_input_dir())
    _wipe_dir_contents(_data_reference_dir())
    _wipe_dir_contents(_data_output_dir())

    # copy input + reference files
    for src_dir, dst_dir in [
        (case.case_input, _data_input_dir()),
        (case.case_reference, _data_reference_dir()),
    ]:
        if not src_dir.exists():
            continue
        for f in src_dir.glob("*.csv"):
            shutil.copy(f, dst_dir / f.name)


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]


# ---------- normalization ----------

def _norm_value(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _canonical_row(row: Dict[str, str], keys: List[str]) -> Tuple[Tuple[str, str], ...]:
    # ✅ only normalize expected keys
    return tuple(sorted((k, _norm_value(row.get(k))) for k in keys))


def _normalize(rows: List[Dict[str, str]], keys: List[str]) -> List[Tuple]:
    return sorted(
        [_canonical_row(r, keys) for r in rows],
        key=lambda x: x
    )


def _diff(expected, actual, keys) -> str:
    exp = _normalize(expected, keys)
    act = _normalize(actual, keys)

    missing = [r for r in exp if r not in act]
    extra = [r for r in act if r not in exp]

    lines = []

    if missing:
        lines.append(f"Missing {len(missing)} row(s).")
        for i, r in enumerate(missing[:MAX_DIFF_ROWS], 1):
            lines.append(f"  missing[{i}]: {r}")

    if extra:
        lines.append(f"Unexpected {len(extra)} row(s).")
        for i, r in enumerate(extra[:MAX_DIFF_ROWS], 1):
            lines.append(f"  extra[{i}]: {r}")

    return "\n".join(lines)


# ---------- pytest ----------

_CASES = _list_case_dirs()


@pytest.mark.parametrize("case", _CASES, ids=[c.case_name for c in _CASES])
def test_acceptance_case(case: CasePaths) -> None:
    _install_case(case)

    # run engine
    should_fail = case.case_name.startswith("eo_005")

    if should_fail:
        with pytest.raises(ValueError):
            run_engine()
        return
    else:
        run_engine()

    # compare outputs
    expected_dir = case.case_expected
    actual_dir = _data_output_dir()

    for expected_file in sorted(expected_dir.glob("*.csv")):
        actual_file = actual_dir / expected_file.name

        expected_rows = _read_csv(expected_file)
        actual_rows = _read_csv(actual_file)

        if not expected_rows and not actual_rows:
            continue

        # ✅ Extract expected schema (CRITICAL CHANGE)
        expected_keys = list(expected_rows[0].keys())

        diff = _diff(expected_rows, actual_rows, expected_keys)

        if diff:
            raise AssertionError(
                f"\n[CASE] {case.case_name}\n"
                f"[FILE] {expected_file.name}\n"
                f"{diff}"
            )