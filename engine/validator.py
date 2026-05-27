from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _coerce(value: Any, target_type: str) -> Tuple[bool, Any, str]:
    """
    Pure coercion helper.
    Returns: (ok, coerced_value, error_message)
    """
    t = (target_type or "string").strip().lower()

    if t == "string":
        return True, "" if value is None else str(value), ""

    # treat empty/blank as missing for non-string targets
    if value is None or str(value).strip() == "":
        return False, None, "missing value"

    raw = str(value).strip()

    if t == "int":
        try:
            if "." in raw:
                return False, None, "not an int"
            return True, int(raw), ""
        except Exception:
            return False, None, "not an int"

    if t == "float":
        try:
            return True, float(raw), ""
        except Exception:
            return False, None, "not a float"

    return False, None, f"unknown type '{target_type}'"


def validate_table(rows: List[Dict[str, Any]], schema: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    L2 Validation: schema-based typing + constraints.

    IMPORTANT:
    - This function is PURE: it does not raise for row-level validation failures.
    - It returns {rows, log}.
    - Execution policy ("fail fast if any errors") is enforced by run.py.
    """
    log: Dict[str, Any] = {
        "rows_read": len(rows),
        "rows_valid": 0,
        "rows_dropped": 0,
        "errors": [],
        "warnings": [],
    }

    # No schema = pass-through (still pure)
    if not schema:
        log["rows_valid"] = len(rows)
        return {"rows": rows, "log": log}

    fields: Dict[str, Dict[str, Any]] = schema.get("fields", {}) or {}
    if not isinstance(fields, dict):
        raise ValueError("Schema table 'fields' must be a mapping")

    required_fields = {k for k, v in fields.items() if (v or {}).get("required")}
    unique_fields = {k for k, v in fields.items() if (v or {}).get("unique")}

    seen_unique: Dict[str, set] = {k: set() for k in unique_fields}

    validated_rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows, start=1):
        row_errors: List[Dict[str, Any]] = []
        typed_row: Dict[str, Any] = {}

        # ----- Required field presence -----
        for col in required_fields:
            if col not in row:
                row_errors.append({"row": idx, "field": col, "error": "missing required field"})

        # ----- Field processing -----
        for col, spec in fields.items():
            spec = spec or {}
            target_type = spec.get("type", "string")
            required = bool(spec.get("required", False))
            constraints = spec.get("constraints") or {}

            raw_value = row.get(col, "")

            ok, coerced, err = _coerce(raw_value, target_type)
            if not ok:
                if required:
                    row_errors.append({"row": idx, "field": col, "error": err})
                continue

            # Constraints for numeric types
            if isinstance(coerced, (int, float)):
                if "min" in constraints and coerced < constraints["min"]:
                    row_errors.append({"row": idx, "field": col, "error": f"value {coerced} < min {constraints['min']}"})
                if "max" in constraints and coerced > constraints["max"]:
                    row_errors.append({"row": idx, "field": col, "error": f"value {coerced} > max {constraints['max']}"})

            typed_row[col] = coerced

        # ----- Unique constraints -----
        for col in unique_fields:
            if col in typed_row:
                val = typed_row[col]
                if val in seen_unique[col]:
                    row_errors.append({"row": idx, "field": col, "error": "duplicate value (unique constraint)"})
                else:
                    seen_unique[col].add(val)

        # ----- Extra column warnings -----
        extra_cols = set(row) - set(fields)
        for col in extra_cols:
            log["warnings"].append({"row": idx, "field": col, "warning": "extra column not in schema"})

        # ----- Drop invalid row (pure result) -----
        if row_errors:
            log["rows_dropped"] += 1
            log["errors"].extend(row_errors)
            continue

        validated_rows.append(typed_row)
        log["rows_valid"] += 1

    return {"rows": validated_rows, "log": log}
