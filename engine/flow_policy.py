from __future__ import annotations

from typing import Dict, List

from engine.allocation_policy import apply_allocation_policy


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
        produced = _to_float_strict(
            r.get("units_produced_per_hour"),
            f"production_intent[{pk},{ql}].units_produced_per_hour",
        )
        prod[(pk, ql)] = produced

    # invariant: no duplicate flow_policy rows
    seen = set()
    for p in flow_policy_rows:
        key = (
            _k(p.get("source_product_key")),
            _k(p.get("target_product_key")),
            _to_int_strict(p.get("priority"), "priority"),
        )
        if key in seen:
            raise ValueError(f"Duplicate flow_policy row: {key}")
        seen.add(key)

    # group policy by source product (quality-agnostic for now)
    grouped: Dict[str, List[Dict]] = {}
    for p in flow_policy_rows:
        spk = _k(p.get("source_product_key"))
        tpk = _k(p.get("target_product_key"))
        if spk == "" or tpk == "":
            raise ValueError("flow_policy missing source_product_key or target_product_key")
        grouped.setdefault(spk, []).append(p)

    allocations: List[Dict] = []

    # deterministic: iterate production in sorted key order
    for (pk, ql), produced in sorted(prod.items(), key=lambda x: (x[0][0], x[0][1])):
        policy = grouped.get(pk, [])
        if not policy:
            continue

        results = apply_allocation_policy(
            produced=produced,
            rows=policy,
            priority_field="priority",
            units_field="allocation_units_per_hour",
            frac_field="allocation_frac",
            priority_label="flow_policy.priority",
            policy_label_fn=lambda row: (
                f"flow_policy[{_k(row.get('source_product_key'))}->{_k(row.get('target_product_key'))}]"
            ),
        )

        for row, allocated in results:
            if allocated == 0:
                continue

            allocations.append(
                {
                    "source_product_key": pk,
                    "source_quality_level": ql,
                    "target_product_key": _k(row.get("target_product_key")),
                    "allocated_units_per_hour": str(allocated),
                }
            )

    return allocations