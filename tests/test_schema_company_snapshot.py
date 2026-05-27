from pathlib import Path

from engine.schema_loader import load_schema
from engine.validator import validate_table


def _table_schema(schema: dict, table_name: str) -> dict | None:
    return (schema or {}).get("tables", {}).get(table_name)


def test_schema_loads_and_has_company_snapshot() -> None:
    schema = load_schema(Path("schema") / "schema.yml")
    cs = _table_schema(schema, "company_snapshot")
    assert cs is not None
    assert cs.get("version") == 1


def test_validator_emits_log_and_types_rows() -> None:
    schema = load_schema(Path("schema") / "schema.yml")
    cs_schema = _table_schema(schema, "company_snapshot")

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

    result = validate_table(rows, cs_schema)

    assert "rows" in result
    assert "log" in result

    log = result["log"]
    assert log["rows_read"] == 1
    assert log["rows_valid"] == 1
    assert log["rows_dropped"] == 0
    assert log["errors"] == []

    out_rows = result["rows"]
    assert len(out_rows) == 1

    r = out_rows[0]
    # typed expectations
    assert r["snapshot_key"] == 1
    assert r["realm_key"] == 1
    assert r["structure_map_key"] == 1
    assert r["company_level"] == 10
    assert r["production_speed_delta"] == 0.03
    assert r["sales_speed_delta"] == 0.02


def test_validator_rejects_missing_required_fields_and_bad_values() -> None:
    schema = load_schema(Path("schema") / "schema.yml")
    cs_schema = _table_schema(schema, "company_snapshot")

    bad_rows = [
        {
            "snapshot_key": "0",  # violates min: 1
            # realm_key missing
            "structure_map_key": "-5",  # violates min: 1
            "company_level": "0",  # violates min: 1
            "production_speed_delta": "not_a_float",  # type error
            "sales_speed_delta": "0.02",
        }
    ]

    result = validate_table(bad_rows, cs_schema)
    log = result["log"]

    assert log["rows_read"] == 1
    assert log["rows_valid"] == 0
    assert log["rows_dropped"] == 1
    assert len(log["errors"]) > 0