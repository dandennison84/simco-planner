from __future__ import annotations
from typing import Any


def _coerce(value: str, target_type: str) -> tuple[bool, Any, str]:
    if target_type == "string":
        return True, "" if value is None else str(value), ""

    if value is None or str(value).strip() == "":
        return False, None, "missing value"

    raw = str(value).strip()

    if target_type == "int":
        try:
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


def validate_table(rows: list[dict], schema: dict | None) -> dict:
    log = {
        "rows_read": len(rows),
        "rows_valid": 0,
        "rows_dropped": 0,
        "errors": [],
        "warnings": [],
    }

    if not schema:
        log["rows_valid"] = len(rows)
        return {"rows": rows, "log": log}

    fields = schema.get("fields", {})

    required_fields = {k for k, v in fields.items() if v.get("required")}
    unique_fields = {k for k, v in fields.items() if v.get("unique")}

    seen_unique: dict[str, set] = {k: set() for k in unique_fields}

    validated_rows: list[dict] = []

    for idx, row in enumerate(rows, start=1):
        row_errors = []
        typed_row: dict[str, Any] = {}

        # ----- Required field presence -----
        for col in required_fields:
            if col not in row:
                row_errors.append({
                    "row": idx,
                    "field": col,
                    "error": "missing required field",
                })

        # ----- Field processing -----
        for col, spec in fields.items():
            target_type = spec.get("type", "string")
            required = spec.get("required", False)
            constraints = spec.get("constraints") or {}

            raw_value = row.get(col, "")

            ok, coerced, err = _coerce(raw_value, target_type)

            if not ok:
                if required:
                    row_errors.append({
                        "row": idx,
                        "field": col,
                        "error": err,
                    })
                continue

            # Constraints
            if isinstance(coerced, (int, float)):
                if "min" in constraints and coerced < constraints["min"]:
                    row_errors.append({
                        "row": idx,
                        "field": col,
                        "error": f"value {coerced} < min {constraints['min']}",
                    })

                if "max" in constraints and coerced > constraints["max"]:
                    row_errors.append({
                        "row": idx,
                        "field": col,
                        "error": f"value {coerced} > max {constraints['max']}",
                    })

            typed_row[col] = coerced

        # ----- Unique constraints -----
        for col in unique_fields:
            if col in typed_row:
                val = typed_row[col]
                if val in seen_unique[col]:
                    row_errors.append({
                        "row": idx,
                        "field": col,
                        "error": "duplicate value (unique constraint)",
                    })
                else:
                    seen_unique[col].add(val)

        # ----- If errors, drop row -----
        if row_errors:
            log["rows_dropped"] += 1
            log["errors"].extend(row_errors)
            continue

        # ----- Extra column warnings -----
        extra_cols = set(row) - set(fields)
        for col in extra_cols:
            log["warnings"].append({
                "row": idx,
                "field": col,
                "warning": "extra column not in schema",
            })

        validated_rows.append(typed_row)
        log["rows_valid"] += 1

    return {"rows": validated_rows, "log": log}