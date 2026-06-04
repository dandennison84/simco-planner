from __future__ import annotations

from typing import Any, Dict, List, Tuple
from collections import defaultdict

from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _require_float(
    row: Dict[str, Any],
    field: str,
    *,
    stage: str,
    row_idx: int | None = None,
    context: str = "",
) -> float:
    value = row.get(field, None)

    if value is None or str(value).strip() == "":
        raise ValueError(
            f"[{stage}:error]\n"
            f"  field={field}\n"
            f"  row={row_idx}\n"
            f"  value={value}\n"
            f"  context={context}\n"
            f"  reason=missing float value"
        )

    try:
        return float(value)
    except Exception:
        raise ValueError(
            f"[{stage}:error]\n"
            f"  field={field}\n"
            f"  row={row_idx}\n"
            f"  value={value}\n"
            f"  context={context}\n"
            f"  reason=invalid float value"
        )


def _optional_float(
    row: Dict[str, Any],
    field: str,
    default: float = 0.0,
) -> float:
    value = row.get(field, None)
    if value is None:
        return default
    s = str(value).strip()
    if s == "":
        return default
    return float(s)


def _require_int(
    row: Dict[str, Any],
    field: str,
    *,
    stage: str,
    row_idx: int | None = None,
    context: str = "",
) -> int:
    value = row.get(field, None)

    if value is None or str(value).strip() == "":
        raise ValueError(
            f"[{stage}:error]\n"
            f"  field={field}\n"
            f"  row={row_idx}\n"
            f"  value={value}\n"
            f"  context={context}\n"
            f"  reason=missing int value"
        )

    try:
        return int(value)
    except Exception:
        raise ValueError(
            f"[{stage}:error]\n"
            f"  field={field}\n"
            f"  row={row_idx}\n"
            f"  value={value}\n"
            f"  context={context}\n"
            f"  reason=invalid int value"
        )


def _build_retail_capacity_map(state: Dict[str, object]) -> Dict[Tuple[str, str, str], float]:
    company_rows = state.get("company", [])
    retail_rows = state.get("retail_prices", [])

    company_index = {
        _k(r.get("company_key")): (
            _k(r.get("realm_key")),
            _optional_float(r, "sales_speed_delta", 0.0),
        )
        for r in company_rows
    }

    retail_index = {
        (
            _k(r.get("realm_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        ): _optional_float(r, "baseline_retail_units", 0.0)
        for r in retail_rows
    }

    capacity_map: Dict[Tuple[str, str, str], float] = {}

    for company_key, (realm_key, delta) in company_index.items():
        for (rk, pk, ql), base in retail_index.items():
            if rk == realm_key:
                capacity_map[(company_key, pk, ql)] = base * (1.0 + delta)

    return capacity_map


def stage_clearing_allocation(state: Dict[str, object]) -> Dict[str, object]:
    stage_name = "clearing_allocation"

    debug_log(state, "[clearing_allocation] start")

    balance_rows = state.get("balance_plan", [])
    clearing_rows = state.get("clearing_plan", [])
    channel_rows = state.get("channel", [])

    channel_index = {
        _k(r.get("channel_key")): r
        for r in channel_rows
    }

    retail_capacity_map = _build_retail_capacity_map(state)

    # group clearing rows by product grain
    clearing_by_product: Dict[Tuple[str, str, str], List[dict]] = {}
    for r in clearing_rows:
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )
        clearing_by_product.setdefault(key, []).append(r)

    clearing_result: List[dict] = []
    allocation_summary: List[dict] = []

    for bal_idx, bal in enumerate(balance_rows, start=1):
        company_key = _k(bal.get("company_key"))
        product_key = _k(bal.get("product_key"))
        quality_level = _k(bal.get("quality_level"))

        net = _require_float(
            bal,
            "net_units_per_hour",
            stage=stage_name,
            row_idx=bal_idx,
            context=f"company_key={company_key}, product_key={product_key}, quality_level={quality_level}",
        )

        total_initial = abs(net)
        retail_alloc = 0.0
        non_retail_alloc = 0.0

        if abs(net) <= 1e-12:
            continue

        direction = "sink" if net > 0 else "source"
        remaining = abs(net)

        rules = clearing_by_product.get((company_key, product_key, quality_level), [])
        if not rules:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  context=company_key={company_key}, product_key={product_key}, quality_level={quality_level}\n"
                f"  reason=no clearing rules for non-zero balance\n"
                f"  remaining={remaining}"
            )

        declared_channel_keys = {_k(r.get("channel_key")) for r in rules}

        priorities = [
            _require_int(
                r,
                "priority",
                stage=stage_name,
                context=f"company_key={company_key}, product_key={product_key}, quality_level={quality_level}",
            )
            for r in rules
        ]

        if len(priorities) != len(set(priorities)):
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  context=company_key={company_key}, product_key={product_key}, quality_level={quality_level}\n"
                f"  reason=priority must be unique within clearing_plan"
            )

        rules_sorted = sorted(
            rules,
            key=lambda r: _require_int(
                r,
                "priority",
                stage=stage_name,
                context=f"company_key={company_key}, product_key={product_key}, quality_level={quality_level}",
            ),
        )

        allocated_so_far: Dict[str, float] = {}

        for rule_idx, r in enumerate(rules_sorted, start=1):
            priority = _require_int(
                r,
                "priority",
                stage=stage_name,
                row_idx=rule_idx,
                context=f"company_key={company_key}, product_key={product_key}, quality_level={quality_level}",
            )
            channel_key = _k(r.get("channel_key"))

            if channel_key not in channel_index:
                raise ValueError(
                    f"[{stage_name}:error]\n"
                    f"  row={rule_idx}\n"
                    f"  field=channel_key\n"
                    f"  value={channel_key}\n"
                    f"  context=company_key={company_key}, product_key={product_key}, quality_level={quality_level}, priority={priority}\n"
                    f"  reason=unknown channel_key"
                )

            if channel_key not in declared_channel_keys:
                raise ValueError(
                    f"[{stage_name}:error]\n"
                    f"  row={rule_idx}\n"
                    f"  field=channel_key\n"
                    f"  value={channel_key}\n"
                    f"  context=company_key={company_key}, product_key={product_key}, quality_level={quality_level}, priority={priority}\n"
                    f"  reason=channel used outside clearing_plan"
                )

            ch = channel_index[channel_key]
            can_source = bool(ch.get("can_source"))
            can_sink = bool(ch.get("can_sink"))
            is_retail = bool(ch.get("uses_retail_capacity"))

            # direction filter
            if direction == "source" and not can_source:
                continue
            if direction == "sink" and not can_sink:
                continue

            units = r.get("allocation_units_per_hour")
            frac = r.get("allocation_frac")

            units_val = str(units).strip() if units is not None else ""
            frac_val  = str(frac).strip() if frac is not None else ""

            units_num = float(units_val) if units_val != "" else 0.0
            frac_num  = float(frac_val) if frac_val != "" else 0.0

            has_units = units_val != "" and units_num > 0.0
            has_frac  = frac_val != "" and frac_num > 0.0            

            if has_units == has_frac:
                raise ValueError(
                    f"[{stage_name}:error]\n"
                    f"  row={rule_idx}\n"
                    f"  context=company_key={company_key}, product_key={product_key}, quality_level={quality_level}, priority={priority}\n"
                    f"  reason=row must define exactly one of allocation_units_per_hour or allocation_frac"
                )

            if has_units:
                desired = _require_float(
                    r,
                    "allocation_units_per_hour",
                    stage=stage_name,
                    row_idx=rule_idx,
                    context=f"company_key={company_key}, product_key={product_key}, quality_level={quality_level}, priority={priority}",
                )
            else:
                desired = _require_float(
                    r,
                    "allocation_frac",
                    stage=stage_name,
                    row_idx=rule_idx,
                    context=f"company_key={company_key}, product_key={product_key}, quality_level={quality_level}, priority={priority}",
                ) * remaining

            if desired <= 0:
                continue

            # retail capacity applies only to sink channels that use retail capacity
            if direction == "sink" and is_retail:
                cap = retail_capacity_map.get((company_key, product_key, quality_level), 0.0)
                used = allocated_so_far.get(channel_key, 0.0)
                cap_left = max(0.0, cap - used)
                desired = min(desired, cap_left)

            allocated = min(desired, remaining)

            if allocated <= 0:
                continue

            remaining -= allocated
            allocated_so_far[channel_key] = allocated_so_far.get(channel_key, 0.0) + allocated

            if is_retail:
                retail_alloc += allocated
            else:
                non_retail_alloc += allocated

            clearing_result.append(
                {
                    "company_key": company_key,
                    "product_key": product_key,
                    "quality_level": quality_level,
                    "priority": priority,
                    "channel_key": channel_key,
                    "direction": direction,
                    "allocated_units_per_hour": allocated,
                }
            )

            if remaining <= 1e-12:
                break

        if remaining > 1e-12:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  context=company_key={company_key}, product_key={product_key}, quality_level={quality_level}\n"
                f"  reason=incomplete clearing\n"
                f"  remaining={remaining}"
            )

        capped = retail_alloc < total_initial and retail_alloc > 0

        allocation_summary.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "quality_level": quality_level,
                "total_units_per_hour": total_initial,
                "retail_units_per_hour": retail_alloc,
                "non_retail_units_per_hour": non_retail_alloc,
                "is_retail_capped": capped,
            }
        )

        debug_log(
            state,
            f"[check] company={company_key} product={product_key} "
            f"total={round(total_initial, 4)} "
            f"retail={round(retail_alloc, 4)} "
            f"contract={round(non_retail_alloc, 4)} "
            f"capped={capped}",
            level=2,
        )

    out = dict(
        state,
        clearing_result=clearing_result,
        allocation_summary=allocation_summary,
    )

    debug_rows(out, "clearing_allocation", "clearing_result")

    # ---------------------------------------------------------
    # Invariant: allocations must match net
    # ---------------------------------------------------------
    alloc_sum = defaultdict(float)

    for r in clearing_result:
        key = (
            r["company_key"],
            r["product_key"],
            r["quality_level"],
        )
        alloc_sum[key] += r["allocated_units_per_hour"]

    for bal_idx, r in enumerate(balance_rows, start=1):
        key = (
            _k(r["company_key"]),
            _k(r["product_key"]),
            _k(r["quality_level"]),
        )

        expected = abs(
            _require_float(
                r,
                "net_units_per_hour",
                stage=stage_name,
                row_idx=bal_idx,
                context=f"company_key={key[0]}, product_key={key[1]}, quality_level={key[2]}",
            )
        )
        actual = alloc_sum.get(key, 0.0)

        if abs(actual - expected) > 1e-6:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  context=company_key={key[0]}, product_key={key[1]}, quality_level={key[2]}\n"
                f"  reason=clearing invariant violated\n"
                f"  expected={expected}\n"
                f"  actual={actual}"
            )

    return out