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


def apply_flow_plan(
    production_intent_rows: List[Dict],
    flow_plan_rows: List[Dict],
    *,
    company_key: str,
) -> List[Dict]:
    """
    Internal routing allocator (VI-only).

    Input:
      production_intent_rows:
        [{company_key, product_key, quality_level, units_produced_per_hour}, ...]

      flow_plan_rows:
        [{company_key, source_product_key, source_quality_level,
          target_product_key, target_quality_level,
          allocation_priority,
          (allocation_units_per_hour xor allocation_frac)}, ...]

    Output:
      flow_allocation_rows:
        [{company_key, source_product_key, source_quality_level,
          target_product_key, target_quality_level,
          allocated_units_per_hour}, ...]

    Rules:
      - grouped by (company, source product, source QL)
      - allocation is sequential by allocation_priority
      - allocation_frac applies to SOURCE AVAILABLE (via allocation_policy)
      - cannot exceed available units
      - strict validation (no silent fallbacks)
    """

    if not flow_plan_rows:
        return []

    # ---------------------------------------------------------
    # Filter flow_plan to this company only
    # ---------------------------------------------------------
    flow_plan_rows = [
        r for r in flow_plan_rows
        if _k(r.get("company_key")) == company_key
    ]

    if not flow_plan_rows:
        return []

    # ---------------------------------------------------------
    # Index production by (product_key, quality_level)
    # ---------------------------------------------------------
    prod: Dict[tuple[str, str], float] = {}

    for r in production_intent_rows:
        pk = _k(r.get("product_key"))
        ql = _k(r.get("quality_level"))

        if pk == "" or ql == "":
            raise ValueError("production_intent missing product_key or quality_level")

        produced = _to_float_strict(
            r.get("units_produced_per_hour"),
            f"production_intent[{company_key},{pk},{ql}].units_produced_per_hour",
        )

        prod[(pk, ql)] = produced

    # ---------------------------------------------------------
    # Validate duplicates
    # ---------------------------------------------------------
    seen = set()
    for p in flow_plan_rows:
        key = (
            _k(p.get("source_product_key")),
            _k(p.get("source_quality_level")),
            _to_int_strict(p.get("allocation_priority"), "allocation_priority"),
        )
        if key in seen:
            raise ValueError(f"Duplicate flow_plan row: {key}")
        seen.add(key)

    # ---------------------------------------------------------
    # Group policy by (source_product_key, source_quality_level)
    # ---------------------------------------------------------
    grouped: Dict[tuple[str, str], List[Dict]] = {}

    for p in flow_plan_rows:
        spk = _k(p.get("source_product_key"))
        sql = _k(p.get("source_quality_level"))

        if spk == "" or sql == "":
            raise ValueError("flow_plan missing source_product_key or source_quality_level")

        grouped.setdefault((spk, sql), []).append(p)

    allocations: List[Dict] = []

    # ---------------------------------------------------------
    # Deterministic iteration
    # ---------------------------------------------------------
    for (pk, ql), produced in sorted(prod.items(), key=lambda x: (x[0][0], x[0][1])):
        policy = grouped.get((pk, ql), [])
        if not policy:
            continue

        results = apply_allocation_policy(
            produced=produced,
            rows=policy,
            priority_field="allocation_priority",
            units_field="allocation_units_per_hour",
            frac_field="allocation_frac",
            priority_label="flow_plan.allocation_priority",
            policy_label_fn=lambda row: (
                f"flow_plan[{company_key}:{_k(row.get('source_product_key'))}@{_k(row.get('source_quality_level'))}"
                f"->{_k(row.get('target_product_key'))}@{_k(row.get('target_quality_level'))}]"
            ),
        )

        for row, allocated in results:
            if allocated == 0:
                continue

            allocations.append(
                {
                    "company_key": company_key,
                    "source_product_key": pk,
                    "source_quality_level": ql,
                    "target_product_key": _k(row.get("target_product_key")),
                    "target_quality_level": _k(row.get("target_quality_level")),
                    "allocated_units_per_hour": float(allocated),
                }
            )

    return allocations