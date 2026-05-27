from pathlib import Path

import pytest

from engine.schema_loader import load_schema
from engine.validator import validate_table


SCHEMA_PATH = Path("schema") / "schema.yml"


@pytest.fixture(scope="module")
def schema():
    return load_schema(SCHEMA_PATH)


@pytest.fixture
def company_snapshot_schema(schema):
    return schema["tables"]["company_snapshot"]


def test_schema_loads_and_has_company_snapshot(schema) -> None:
    cs = schema["tables"].get("company_snapshot")
    assert cs is not None
    assert cs.get("version") == 1


def test_validator_emits_log_and_types_rows(company_snapshot_schema) -> None:
    rows = [
        {
            "snapshot_key": "1",
            "realm_key": "1",
            "structure_map_key": "1",
            "company_level": "10",
            "production_speed_delta": "0.03",
            "sales_speed_delta": "0.02",
        }
    ]

    result = validate_table(rows, company_snapshot_schema)
    log = result["log"]
    out_rows = result["rows"]

    assert log["rows_read"] == 1
    assert log["rows_valid"] == 1
    assert log["rows_dropped"] == 0
    assert log["errors"] == []

    assert len(out_rows) == 1

    r = out_rows[0]
    assert r["snapshot_key"] == 1
    assert r["realm_key"] == 1
    assert r["structure_map_key"] == 1
    assert r["company_level"] == 10
    assert r["production_speed_delta"] == 0.03
    assert r["sales_speed_delta"] == 0.02


def test_validator_rejects_missing_required_fields_and_bad_values(company_snapshot_schema) -> None:
    bad_rows = [
        {
            "snapshot_key": "0",  # invalid: min constraint
            # realm_key missing
            "structure_map_key": "-5",  # invalid
            "company_level": "0",       # invalid
            "production_speed_delta": "not_a_float",
            "sales_speed_delta": "0.02",
        }
    ]

    result = validate_table(bad_rows, company_snapshot_schema)
    log = result["log"]

    assert log["rows_read"] == 1
    assert log["rows_valid"] == 0
    assert log["rows_dropped"] == 1

    # ✅ Stronger assertion: check at least 3 specific issues
    fields_with_errors = {e["field"] for e in log["errors"]}

    assert "snapshot_key" in fields_with_errors
    assert "realm_key" in fields_with_errors
    assert "structure_map_key" in fields_with_errors
    assert "company_level" in fields_with_errors
    assert "production_speed_delta" in fields_with_errors