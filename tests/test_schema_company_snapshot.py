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


def test_validator_emits_log_and_passes_through_rows_when_noop() -> None:
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
    assert log["warnings"] == []

    # no-op validator should pass rows through unchanged
    assert result["rows"] == rows


def test_validator_currently_does_not_enforce_required_fields_or_constraints() -> None:
    """
    This test documents the CURRENT behavior: validator is no-op.
    Once you implement enforcement, replace this test with real negative tests.
    """
    schema = load_schema(Path("schema") / "schema.yml")
    cs_schema = _table_schema(schema, "company_snapshot")

    # missing required fields + invalid values
    bad_rows = [
        {
            "snapshot_key": "0",  # would violate min:1 once enforced
            # realm_key missing
            "structure_map_key": "-5",  # would violate min:1 once enforced
            "company_level": "0",  # would violate min:1 once enforced
            "production_speed_delta": "not_a_float",  # would violate float typing once enforced
            "sales_speed_delta": "0.02",
        }
    ]

    result = validate_table(bad_rows, cs_schema)

    # current no-op behavior: still reports no errors
    assert result["log"]["errors"] == []
    assert result["log"]["rows_valid"] == 1