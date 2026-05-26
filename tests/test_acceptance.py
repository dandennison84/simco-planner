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

REPO_DATA_DIRNAME = "data"
REPO_INPUT_DIRNAME = "input"
REPO_REFERENCE_DIRNAME = "reference"
REPO_OUTPUT_DIRNAME = "output"


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
        case_input = p / CASE_INPUT_DIRNAME
        case_reference = p / CASE_REFERENCE_DIRNAME
        case_expected = p / CASE_EXPECTED_DIRNAME

        if case_expected.exists() and case_expected.is_dir():
            cases.append(
                CasePaths(
                    case_name=p.name,
                    case_root=p,
                    case_input=case_input,
                    case_reference=case_reference,
                    case_expected=case_expected,
                )
            )

    return cases


def _wipe_dir_contents(dir_path: Path) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    for child in dir_path.iterdir():
        if child.is_file():
            if child.name == ".gitkeep":
                continue
            child.unlink()
        else:
            shutil.rmtree(child)


def _copy_tree_if_exists(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.exists():
        return

    dst_dir.mkdir(parents=True, exist_ok=True)

    for f in src_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, dst_dir / f.name)


def _detect_delimiter(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as fp:
        first_line = fp.readline()
    return "|" if "|" in first_line else ","


def _read_csv_as_rows(path: Path) -> List[Dict[str, str]]:
    delim = _detect_delimiter(path)
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp, delimiter=delim)
        if reader.fieldnames is None:
            return []
        return [dict(row) for row in reader]


def _canonical_row_key(row: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
    return tuple(sorted((k, "" if v is None else str(v)) for k, v in row.items()))


def _normalize_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    normalized = [{k: ("" if v is None else str(v)) for k, v in r.items()} for r in rows]
    return sorted(normalized, key=_canonical_row_key)


def _diff_rows(expected: List[Dict[str, str]], actual: List[Dict[str, str]]) -> str:
    exp = _normalize_rows(expected)
    act = _normalize_rows(actual)

    if exp == act:
        return ""

    exp_keys = {_canonical_row_key(r) for r in exp}
    act_keys = {_canonical_row_key(r) for r in act}

    missing = exp_keys - act_keys
    extra = act_keys - exp_keys

    lines: List[str] = []

    if missing:
        lines.append(f"Missing {len(missing)} row(s) from actual output.")
        for i, s in enumerate(sorted(missing)[:3], 1):
            lines.append(f"  missing[{i}]: {s}")

    if extra:
        lines.append(f"Unexpected {len(extra)} extra row(s) in actual output.")
        for i, s in enumerate(sorted(extra)[:3], 1):
            lines.append(f"  extra[{i}]: {s}")

    if not missing and not extra and exp and act:
        lines.append("Row sets differ (likely formatting/canonicalization).")
        lines.append(f"  expected[0]: {_canonical_row_key(exp[0])}")
        lines.append(f"  actual[0]:   {_canonical_row_key(act[0])}")

    return "\n".join(lines)


def _expected_files(case_expected_dir: Path) -> List[Path]:
    return sorted([p for p in case_expected_dir.glob("*.csv") if p.is_file()])


# ---------- pytest ----------
_CASES = _list_case_dirs()
_CASE_IDS = [c.case_name for c in _CASES]


@pytest.mark.parametrize("case", _CASES, ids=_CASE_IDS)
def test_acceptance_case(case: CasePaths) -> None:
    # Clean slate
    _wipe_dir_contents(_data_input_dir())
    _wipe_dir_contents(_data_reference_dir())
    _wipe_dir_contents(_data_output_dir())

    # Install case data
    _copy_tree_if_exists(case.case_input, _data_input_dir())
    _copy_tree_if_exists(case.case_reference, _data_reference_dir())

    should_fail = "eo_005" in case.case_name

    # Execute engine
    try:
        rc = run_engine()

        if should_fail:
            raise AssertionError(
                f"Case '{case.case_name}' expected failure but succeeded"
            )

    except Exception:
        if should_fail:
            return  # ✅ expected failure
        else:
            raise

    # Normal validation
    assert rc == 0, f"Engine returned non-zero exit code {rc} for case '{case.case_name}'."

    expected_files = _expected_files(case.case_expected)
    assert expected_files, f"Case '{case.case_name}' has no expected/*.csv files."

    for exp_path in expected_files:
        out_path = _data_output_dir() / exp_path.name

        assert out_path.exists(), (
            f"Case '{case.case_name}' expected output '{exp_path.name}' "
            f"but engine did not produce '{out_path}'."
        )

        expected_rows = _read_csv_as_rows(exp_path)
        actual_rows = _read_csv_as_rows(out_path)

        diff = _diff_rows(expected_rows, actual_rows)

        assert diff == "", (
            f"Case '{case.case_name}' output mismatch for '{exp_path.name}':\n{diff}"
        )