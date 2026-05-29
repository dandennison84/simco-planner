from __future__ import annotations

from typing import Callable, Dict, List, Tuple


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _to_float_strict(x, label: str) -> float:
    try:
        return float(str(x).strip())
    except Exception:
        raise ValueError(f"{label}: cannot parse float from {x!r}")


def _to_int_strict(x, label: str) -> int:
    try:
        return int(str(x).strip())
    except Exception:
        raise ValueError(f"{label}: cannot parse int from {x!r}")


def apply_allocation_policy(
    *,
    produced: float,
    rows: List[Dict],
    priority_field: str = "priority",
    units_field: str = "allocation_units_per_hour",
    frac_field: str = "allocation_frac",
    priority_label: str = "priority",
    policy_label_fn: Callable[[Dict], str] | None = None,
) -> List[Tuple[Dict, float]]:
    """
    Generic deterministic allocation engine.

    Returns:
      List of tuples:
        (original_row, allocated_units)

    Rules:
    - rows are processed in ascending priority
    - exactly one of units_field / frac_field must be populated
    - frac is applied to INITIAL produced amount
    - allocation cannot exceed remaining
    - no fallback behavior
    """

    policy_label_fn = policy_label_fn or (lambda r: "policy")

    # explicit priority ordering
    ordered = sorted(
        rows,
        key=lambda r: _to_int_strict(r.get(priority_field), priority_label),
    )

    remaining = produced
    out: List[Tuple[Dict, float]] = []

    for row in ordered:
        units_raw = _k(row.get(units_field))
        frac_raw = _k(row.get(frac_field))

        has_units = units_raw != ""
        has_frac = frac_raw != ""

        if has_units == has_frac:
            raise ValueError(
                f"{policy_label_fn(row)} must provide exactly one of "
                f"{units_field} or {frac_field}"
            )

        if has_units:
            desired = _to_float_strict(
                units_raw,
                f"{policy_label_fn(row)}.{units_field}",
            )
        else:
            frac = _to_float_strict(
                frac_raw,
                f"{policy_label_fn(row)}.{frac_field}",
            )
            if frac < 0 or frac > 1:
                raise ValueError(
                    f"{policy_label_fn(row)}.{frac_field} out of [0,1]: {frac}"
                )
            desired = frac * produced

        allocated = min(desired, remaining)
        remaining -= allocated

        out.append((row, allocated))

        if remaining <= 0:
            break

    return out