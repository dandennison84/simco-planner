from __future__ import annotations

from typing import Any


def _coerce(value: str, target_type: str) -> tuple[bool, Any, str]:
    """
    Returns (ok, coerced_value, error_message).
    Input values are expected to be strings (post-clean).
    """
    if target_type == "string":
        return True, "" if value is None else str(value), ""

    if value is None or str(value).strip() == "":
        return False, None, "missing value"

    raw = str(value).strip()

    if target_type == "int":
        try:
            # disallow floats like "1.2" for int
            if "." in raw:
                return False, None, "not an int"
            return True, int(raw), ""
        except Exception:
            return False, None, "not an int"

    if target_type == "float":
        try:
            return True, float(raw), ""
        except Exception:
            return False, None, "not a float"

    return False, None, f"unknown type '{target_type}'"


def _get_fields(schema: dict | None) -> dict:
    if not schema:
        return {}
    return schema.get("fields", {}) or {}


def validate_table(rows: list[dict], schema: dict | None) -> dict:
    """
    Schema-driven validator + typer.

    - If schema is None: no-op pass-through (current bootstrap behavior).
    - If schema exists: enforce required fields, types, constraints, unique.

    Returns:
      {
        "rows": <validated_and_typed_rows>,
        "log": {
          "rows_read": int,
          "rows_valid": int,
          "rows_dropped": int,
          "errors": [ ... ],
          "warnings": [ ... ],
        }
      }
    """
    log = {
        "rows_read": len(rows),
        "rows_valid": 0,
        "rows_dropped": 0,
        "errors": [],
        "warnings": [],
    }

    # No schema => pass-through (matches your current no-op behavior) 【2-da2939】
    if not schema:
        log["rows_valid"] = len(rows)
        return {"rows": rows, "log": log}

    fields = _get_fields(schema)

    # Determine required fields and unique fields
    required_fields = [name for name, spec in fields.items() if spec.get("required") is True]
    unique_fields = [name for name, spec in fields.items() if spec.get("unique") is True]

    seen_unique: dict[str, set] = {name: set() for name in unique_fields}

    validated_rows: list[dict] = []

    for idx, row in enumerate(rows, start=1):
        row_errors: list[dict] = []
        typed_row: dict[str, Any] = {}

        # Missing required fields (column not present at all)
        for col in required_fields:
            if col not in row:
                row_errors.append(
                    {
                        "row": idx,
                        "field": col,
                        "error": "missing required field",
                    }
                )

        # Coerce + per-field constraints
        for col, spec in fields.items():
            target_type = spec.get("type", "string")
            raw_value = row.get(col, "")

            ok, coerced, err = _coerce(raw_value, target_type)
            if not ok:
                if spec.get("required") is True:
                    row_errors.append({"row": idx, "field": col, "error": err})
                # if not required and missing/bad, just omit typed value
                continue

            # constraints: min/max for numeric
            constraints = spec.get("constraints") or {}
            if isinstance(coerced, (int, float)):
                if "min" in constraints and coerced < constraints["min"]:
                    row_errors.append(
                        {
                            "row": idx,
                            "field": col,
                            "error": f"value {coerced} < min {constraints['min']}",
                        }
                    )
                if "max" in constraints and coerced > constraints["max"]:
                    row_errors.append(
                        {
                            "row": idx,
                            "field": col,
                            "error": f"value {coerced} > max {constraints['max']}",
                        }
                    )

            typed_row[col] = coerced

        # Unique checks (only if row is otherwise valid enough to have the field)
        for col in unique_fields:
            if col in typed_row:
                v = typed_row[col]
                if v in seen_unique[col]:
                    row_errors.append(
                        {
                            "row": idx,
                            "field": col,
                            "error": "duplicate value (unique constraint)",
                        }
                    )
                else:
                    seen_unique[col].add(v)

        if row_errors:
            log["rows_dropped"] += 1
            log["errors"].extend(row_errors)
            continue

        # Warn on extra columns not in schema (non-fatal)
        for col in row.keys():
            if col not in fields:
                log["warnings"].append(
                    {
                        "row": idx,
                        "field": col,
                        "warning": "extra column not in schema",
                    }
                )

        validated_rows.append(typed_row)
        log["rows_valid"] += 1

    return {"rows": validated_rows, "log": log}