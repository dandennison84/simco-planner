def validate_table(rows: list[dict], schema: dict | None) -> dict:
    """
    No-op validator.

    L0: data already read
    L1: assumed cleaned upstream
    L2: disabled (no schema)

    Returns same rows + log.
    """

    return {
        "rows": rows,
        "log": {
            "rows_read": len(rows),
            "rows_valid": len(rows),
            "rows_dropped": 0,
            "errors": [],
            "warnings": [],
        },
    }