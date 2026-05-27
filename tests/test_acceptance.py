from __future__ import annotations

import csv
import os
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
    for p in sorted([x for x in root.iterdir() if x.is_dir()]):
        case_expected = p / CASE_EXPECTED_DIRNAME
        if case_expected.exists():
            cases.append(
                CasePaths(
                    case_name=p.name,
                    case_root=p,
                    case_input=p / CASE_INPUT_DIRNAME,
                    case_reference=p / CASE_REFERENCE_DIRNAME,
                    case_expected=case_expected,
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

    if case.case_input.exists():
        for f in case.case_input.iterdir():
            if f.is_file():
                shutil.copy2(f, _data_input_dir() / f.name)

    if case.case_reference.exists():
        for f in case.case_reference.iterdir():
            if f.is_file():
                shutil.copy2(f, _data_reference_dir() / f.name)


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=",")  # ✅ fixed (no detection)
        if reader.fieldnames is None:
            return []
        return [dict(row) for row in reader]


# ---------- comparison ----------
def _norm_value(v) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if s == "":
        return ""

    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
        return str(f)
    except Exception:
        return s


def _canonical_row(row: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
    return tuple(sorted((k, _norm_value(v)) for k, v in row.items()))


def _normalize(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return sorted(
        [{k: _norm_value(v) for k, v in r.items()} for r in rows],
        key=_canonical_row
    )


def _diff(expected, actual) -> str:
    exp = _normalize(expected)
    act = _normalize(actual)

    if exp == act:
        return ""

    exp_set = {_canonical_row(r) for r in exp}
    act_set = {_canonical_row(r) for r in act}

    missing = exp_set - act_set
    extra = act_set - exp_set

    lines = []

    if missing:
        lines.append(f"Missing {len(missing)} row(s).")
        for i, s in enumerate(sorted(missing)[:MAX_DIFF_ROWS], 1):
            lines.append(f"  missing[{i}]: {s}")

    if extra:
        lines.append(f"Unexpected {len(extra)} row(s).")
        for i, s in enumerate(sorted(extra)[:MAX_DIFF_ROWS], 1):
            lines.append(f"  extra[{i}]: {s}")

    return "\n".join(lines)


# ---------- pytest ----------
_CASES = _list_case_dirs()


@pytest.mark.parametrize("case", _CASES, ids=[c.case_name for c in _CASES])
def test_acceptance_case(case: CasePaths) -> None:
    _install_case(case)

    should_fail = "eo_005" in case.case_name

    prev_env = os.environ.get("SIMCO_ENV")
    os.environ["SIMCO_ENV"] = "test"

    try:
        rc = run_engine()

        if should_fail:
            raise AssertionError(f"Case '{case.case_name}' expected failure but succeeded")

    except Exception:
        if should_fail:
            return
        raise

    finally:
        if prev_env is None:
            os.environ.pop("SIMCO_ENV", None)
        else:
            os.environ["SIMCO_ENV"] = prev_env

    assert rc == 0

    expected_files = sorted(case.case_expected.glob("*.csv"))

    for exp_path in expected_files:
        out_path = _data_output_dir() / exp_path.name

        assert out_path.exists()

        expected = _read_csv(exp_path)
        actual = _read_csv(out_path)

        diff = _diff(expected, actual)
        if diff:
            raise AssertionError(
                f"\n[CASE] {case.case_name}\n[FILE] {exp_path.name}\n{diff}\n"
            )
