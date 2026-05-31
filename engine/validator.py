from __future__ import annotations

from typing import Any, Dict, List, Tuple

from engine.debug import debug_log

def debug_validate_result(
    state: Dict[str, object],
    table_name: str,
    result: Dict[str, Any],
) -> None:
    """
    Debug wrapper for validate_table output.

    Level 1:
      - prints row counts summary

    Level 2:
      - prints first few errors (if any)

    Does NOT mutate result.
    """

    log = result.get("log", {})

    rows_read = log.get("rows_read", 0)
    rows_valid = log.get("rows_valid", 0)
    rows_invalid = log.get("rows_invalid", 0)
    errors = log.get("errors", [])

    # ✅ Level 1 summary
    debug_log(
        state,
        f"[validate] {table_name}: read={rows_read} valid={rows_valid} invalid={rows_invalid}",
        level=1
    )

    # ✅ Level 2 detail (first few errors only)
    if errors:
        sample = errors[:5]
        for e in sample:
            debug_log(
                state,
                f"[validate:{table_name}] row={e.get('row')} field={e.get('field')} error={e.get('error')}",
                level=2
            )

        if len(errors) > 5:
            debug_log(
                state,
                f"[validate:{table_name}] ... {len(errors) - 5} more errors",
                level=2
            )

# =============================================================================
# Coercion
# =============================================================================
def _coerce(value: Any, target_type: str) -> Tuple[bool, Any, str]:
    """
    Pure coercion helper.

    Returns:
        (ok, coerced_value, error_message)

    Notes:
    - string: None -> ""
    - non-string blank values are treated as missing
    - no implicit cleanup beyond type coercion
    """
    t = (target_type or "string").strip().lower()

    if t == "string":
        return True, "" if value is None else str(value), ""

    if value is None:
        return False, None, "missing value"

    raw = str(value).strip()

    if raw == "":
        return False, None, "missing value"

    if t == "int":
        try:
            # Reject float-like strings for ints
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

    if t == "logical":
        lowered = raw.lower()

        if lowered in {"true", "1", "yes", "y"}:
            return True, True, ""

        if lowered in {"false", "0", "no", "n"}:
            return True, False, ""

        return False, None, "not a logical"

    return False, None, f"unknown type '{target_type}'"


# =============================================================================
# Schema helpers
# =============================================================================
def _get_fields(schema: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    if not schema:
        return {}

    fields = schema.get("fields", {}) or {}
    if not isinstance(fields, dict):
        raise ValueError("Schema table 'fields' must be a mapping")

    return fields


def _get_keys(schema: Dict[str, Any] | None) -> List[str]:
    if not schema:
        return []

    keys = schema.get("keys", []) or []
    if not isinstance(keys, list):
        raise ValueError("Schema table 'keys' must be a list")

    return keys


def _get_required_fields(fields: Dict[str, Dict[str, Any]]) -> List[str]:
    return [name for name, spec in fields.items() if bool((spec or {}).get("required", False))]


def _get_unique_fields(fields: Dict[str, Dict[str, Any]]) -> List[str]:
    return [name for name, spec in fields.items() if bool((spec or {}).get("unique", False))]


# =============================================================================
# Validation
# =============================================================================
def validate_table(rows: List[Dict[str, Any]], schema: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Strict, pure table validator.

    Contract:
    - No side effects
    - No row dropping
    - No partial "valid subset" behavior
    - Returns rows ONLY when the full table is valid

    Returns:
        {
          "rows": typed_rows_if_valid_else_empty,
          "log": {
              "rows_read": int,
              "rows_valid": int,
              "rows_invalid": int,
              "errors": [...],
              "warnings": [...]
          },
          "valid": bool
        }

    Strictness:
    - any extra column -> error
    - any missing schema column -> error
    - any row-level type/constraint/key violation -> table invalid
    """
    log: Dict[str, Any] = {
        "rows_read": len(rows),
        "rows_valid": 0,
        "rows_invalid": 0,
        "errors": [],
        "warnings": [],
    }

    # No schema = pass-through, but still deterministic
    if not schema:
        return {
            "rows": rows,
            "log": {
                **log,
                "rows_valid": len(rows),
                "rows_invalid": 0,
            },
            "valid": True,
        }

    fields = _get_fields(schema)
    keys = _get_keys(schema)
    required_fields = _get_required_fields(fields)
    unique_fields = _get_unique_fields(fields)

    schema_columns = list(fields.keys())
    schema_column_set = set(schema_columns)

    seen_unique: Dict[str, set] = {col: set() for col in unique_fields}
    seen_keys: set[tuple[Any, ...]] = set()

    typed_rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows, start=1):
        row_errors: List[Dict[str, Any]] = []
        typed_row: Dict[str, Any] = {}

        row_column_set = set(row.keys())

        # ---------------------------------------------------------------------
        # Strict shape validation
        # ---------------------------------------------------------------------
        missing_columns = [col for col in schema_columns if col not in row_column_set]
        extra_columns = [col for col in row_column_set if col not in schema_column_set]

        for col in missing_columns:
            row_errors.append({
                "row": idx,
                "field": col,
                "error": "missing schema column",
            })

        for col in extra_columns:
            row_errors.append({
                "row": idx,
                "field": col,
                "error": "unexpected column",
            })

        # ---------------------------------------------------------------------
        # Field typing + constraints
        # ---------------------------------------------------------------------
        for col, spec in fields.items():
            spec = spec or {}
            target_type = spec.get("type", "string")
            required = bool(spec.get("required", False))
            constraints = spec.get("constraints", {}) or {}

            raw_value = row.get(col, None)

            ok, coerced, err = _coerce(raw_value, target_type)

            if not ok:
                if required:
                    row_errors.append({
                        "row": idx,
                        "field": col,
                        "error": err,
                    })
                else:
                    # optional field missing/blank -> keep as None
                    typed_row[col] = None
                continue

            # Numeric constraints
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

        # ---------------------------------------------------------------------
        # Single-field uniqueness
        # ---------------------------------------------------------------------
        for col in unique_fields:
            val = typed_row.get(col, None)

            if val is None:
                continue

            if val in seen_unique[col]:
                row_errors.append({
                    "row": idx,
                    "field": col,
                    "error": "duplicate value (unique constraint)",
                })
            else:
                seen_unique[col].add(val)

        # ---------------------------------------------------------------------
        # Composite key uniqueness
        # ---------------------------------------------------------------------
        if keys:
            key_tuple = tuple(typed_row.get(k, None) for k in keys)

            # If any key member is missing/null, that is already invalid
            # through required/type validation if schema is correct.
            if None not in key_tuple:
                if key_tuple in seen_keys:
                    row_errors.append({
                        "row": idx,
                        "field": "keys",
                        "error": f"duplicate key {key_tuple}",
                    })
                else:
                    seen_keys.add(key_tuple)

        # ---------------------------------------------------------------------
        # Finalize row result
        # ---------------------------------------------------------------------
        if row_errors:
            log["rows_invalid"] += 1
            log["errors"].extend(row_errors)
        else:
            log["rows_valid"] += 1

        typed_rows.append(typed_row)

    valid = len(log["errors"]) == 0

    return {
        "rows": typed_rows if valid else [],
        "log": log,
        "valid": valid,
    }