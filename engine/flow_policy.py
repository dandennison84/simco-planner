from __future__ import annotations

from typing import Dict, List


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


def apply_flow_policy(
    production_intent_rows: List[Dict],
    flow_policy_rows: List[Dict],
) -> List[Dict]:
    """
    Pure routing allocator.

    Input:
      production_intent_rows: [{"product_key", "quality_level", "units_produced_per_hour", ...}, ...]
      flow_policy_rows: [{"source_product_key","target_product_key","priority", ("allocation_frac" xor "allocation_units_per_hour")}, ...]

    Output:
      flow_allocation_rows: [{"source_product_key","target_product_key","allocated_units_per_hour"}, ...]

    Rules:
      - deterministic priority order (ascending priority)
      - allocation_frac applies to INITIAL produced units for that source
      - no implicit fallback: missing required columns => error
      - cannot allocate more than remaining
    """
    if not flow_policy_rows:
        return []

    # index production by (product_key, quality_level)
    prod: Dict[tuple[str, str], float] = {}
    for r in production_intent_rows:
        pk = _k(r.get("product_key"))
        ql = _k(r.get("quality_level"))
        if pk == "" or ql == "":
            raise ValueError("production_intent missing product_key or quality_level")
        produced = _to_float_strict(r.get("units_produced_per_hour"), f"production_intent[{pk},{ql}].units_produced_per_hour")
        prod[(pk, ql)] = produced

    # group policy by (source_product_key, source_quality_level?) -> for now quality-agnostic unless provided
    # If flow_policy includes quality, you can extend later. For now: apply per source_product_key to all qualities.
    grouped: Dict[str, List[Dict]] = {}
    for p in flow_policy_rows:
        spk = _k(p.get("source_product_key"))
        tpk = _k(p.get("target_product_key"))
        if spk == "" or tpk == "":
            raise ValueError("flow_policy missing source_product_key or target_product_key")

        # priority required
        pr = _to_int_strict(p.get("priority"), f"flow_policy[{spk}->{tpk}].priority")

        # allocation shape: xor
        frac_raw = p.get("allocation_frac")
        units_raw = p.get("allocation_units_per_hour")

        has_frac = _k(frac_raw) != ""
        has_units = _k(units_raw) != ""
        if has_frac == has_units:
            raise ValueError(f"flow_policy[{spk}->{tpk}] must provide exactly one of allocation_frac or allocation_units_per_hour")

        grouped.setdefault(spk, []).append(p)

    allocations: List[Dict] = []

    # deterministic: iterate production in sorted key order
    for (pk, ql), produced in sorted(prod.items(), key=lambda x: (x[0][0], x[0][1])):
        policy = grouped.get(pk, [])
        if not policy:
            continue

        remaining = produced

        # deterministic: sort by priority asc, then target_product_key
        policy_sorted = sorted(
            policy,
            key=lambda p: (
                _to_int_strict(p.get("priority"), "priority"),
                _k(p.get("target_product_key")),
            ),
        )

        for p in policy_sorted:
            tpk = _k(p.get("target_product_key"))
            frac_raw = p.get("allocation_frac")
            units_raw = p.get("allocation_units_per_hour")

            if _k(units_raw) != "":
                desired = _to_float_strict(units_raw, f"flow_policy[{pk}->{tpk}].allocation_units_per_hour")
            else:
                frac = _to_float_strict(frac_raw, f"flow_policy[{pk}->{tpk}].allocation_frac")
                if frac < 0 or frac > 1:
                    raise ValueError(f"flow_policy[{pk}->{tpk}].allocation_frac out of [0,1]: {frac}")
                desired = frac * produced

            allocated = desired if desired <= remaining else remaining
            remaining -= allocated

            if allocated != 0:
                allocations.append(
                    {
                        "source_product_key": pk,
                        "source_quality_level": ql,
                        "target_product_key": tpk,
                        "allocated_units_per_hour": str(allocated),
                    }
                )

            if remaining <= 0:
                break

    return allocations