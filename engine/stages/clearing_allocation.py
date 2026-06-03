from __future__ import annotations

from typing import Dict, List, Tuple
from collections import defaultdict


from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    return ("" if x is None else str(x)).strip()


def _to_float(x, default: float = 0.0) -> float:
    if x is None:
        return default
    s = str(x).strip()
    if s == "":
        return default
    return float(s)


def _to_int(x, default: int = 0) -> int:
    if x is None:
        return default
    s = str(x).strip()
    if s == "":
        return default
    return int(s)

def _build_retail_capacity_map(state):
    company_rows = state.get("company", [])
    retail_rows = state.get("retail_prices", [])

    company_index = {
        _k(r.get("company_key")): (
            _k(r.get("realm_key")),
            _to_float(r.get("sales_speed_delta"))
        )
        for r in company_rows
    }

    retail_index = {
        (
            _k(r.get("realm_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level"))
        ): _to_float(r.get("baseline_retail_units"))
        for r in retail_rows
    }

    capacity_map = {}

    for company_key, (realm_key, delta) in company_index.items():
        for (rk, pk, ql), base in retail_index.items():
            if rk == realm_key:
                capacity_map[(company_key, pk, ql)] = base * (1.0 + delta)

    return capacity_map
    
def stage_clearing_allocation(state: Dict[str, object]) -> Dict[str, object]:
    """
    Sequential waterfall allocation for surplus / shortage.

    Inputs:
      - balance_plan
      - clearing_plan
      - channel
      - company
      - retail_prices

    Outputs:
      - clearing_result
      - clearing_remainder

    Grain:
      clearing_result:
        (company_key, product_key, quality_level, priority, channel_key)

      clearing_remainder:
        (company_key, product_key, quality_level)

    Rules:
      - if net > 0: only channels with can_sink = TRUE may receive allocation
      - if net < 0: only channels with can_source = TRUE may receive allocation
      - rows processed in ascending unique priority
      - each row must define exactly one of:
            allocation_units_per_hour
            allocation_frac
      - allocation_frac is applied to REMAINING
      - if channel uses retail capacity:
            cap = baseline_retail_units * (1 + sales_speed_delta)
      - remainder is emitted explicitly
    """
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
    clearing_remainder: List[dict] = []
    allocation_summary: List[dict] = []

    for bal in balance_rows:
        company_key = _k(bal.get("company_key"))
        product_key = _k(bal.get("product_key"))
        quality_level = _k(bal.get("quality_level"))
        net = _to_float(bal.get("net_units_per_hour"))

        total_initial = abs(net)
        retail_alloc = 0.0
        contract_alloc = 0.0

        if abs(net) <= 1e-12:
            continue

        direction = "sink" if net > 0 else "source"
        remaining = abs(net)

        rules = clearing_by_product.get((company_key, product_key, quality_level), [])
        if not rules:
            clearing_remainder.append(
                {
                    "company_key": company_key,
                    "product_key": product_key,
                    "quality_level": quality_level,
                    "direction": direction,
                    "remaining_units_per_hour": remaining,
                }
            )
            continue

        # validate unique priorities within product
        priorities = [_to_int(r.get("priority")) for r in rules]
        if len(priorities) != len(set(priorities)):
            raise ValueError(
                f"clearing_plan priority must be unique for company={company_key}, product={product_key}, quality={quality_level}"
            )

        rules_sorted = sorted(rules, key=lambda r: _to_int(r.get("priority")))

        # track channel usage within this product for cap enforcement
        allocated_so_far: Dict[str, float] = {}

        for r in rules_sorted:
            priority = _to_int(r.get("priority"))
            channel_key = _k(r.get("channel_key"))

            if channel_key not in channel_index:
                raise ValueError(
                    f"clearing_plan references unknown channel_key={channel_key}"
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

            has_units = units is not None and str(units).strip() != ""
            has_frac = frac is not None and str(frac).strip() != ""

            if has_units == has_frac:
                raise ValueError(
                    f"clearing_plan row must define exactly one of allocation_units_per_hour or allocation_frac "
                    f"(company={company_key}, product={product_key}, quality={quality_level}, priority={priority})"
                )

            if has_units:
                desired = _to_float(units)
            else:
                desired = _to_float(frac) * remaining

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

            # semantic tracking for debug summary (no hardcoded channel ids)
            if is_retail:
                retail_alloc += allocated
            else:
                contract_alloc += allocated

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
            clearing_remainder.append(
                {
                    "company_key": company_key,
                    "product_key": product_key,
                    "quality_level": quality_level,
                    "direction": direction,
                    "remaining_units_per_hour": remaining,
                }
            )

        # debug summary (level 2)
        if total_initial > 0:
            capped = retail_alloc < total_initial and retail_alloc > 0

            allocation_summary.append({
                "company_key": company_key,
                "product_key": product_key,
                "quality_level": quality_level,
                "total_units_per_hour": total_initial,
                "retail_units_per_hour": retail_alloc,
                "non_retail_units_per_hour": contract_alloc,
                "is_retail_capped": retail_alloc < total_initial and retail_alloc > 0,
            })            

            debug_log(
                state,
                f"[check] company={company_key} product={product_key} "
                f"total={round(total_initial,4)} "
                f"retail={round(retail_alloc,4)} "
                f"contract={round(contract_alloc,4)} "
                f"capped={capped}",
                level=2,
            )

    if not clearing_remainder:
        clearing_remainder = [{
            "company_key": None,
            "product_key": None,
            "quality_level": None,
            "direction": None,
            "remaining_units_per_hour": None,
        }]

    out = dict(
        state,
        clearing_result=clearing_result,
        clearing_remainder=clearing_remainder,
        allocation_summary=allocation_summary,
    )

    debug_rows(out, "clearing_allocation", "clearing_result")
    debug_rows(out, "clearing_allocation", "clearing_remainder")

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

    for r in balance_rows:
        key = (
            _k(r["company_key"]),
            _k(r["product_key"]),
            _k(r["quality_level"]),
        )

        expected = abs(_to_float(r["net_units_per_hour"]))
        actual = alloc_sum.get(key, 0.0)

        remainder = 0.0
        for rr in clearing_remainder:
            rr_key = (
                _k(rr.get("company_key")),
                _k(rr.get("product_key")),
                _k(rr.get("quality_level")),
            )
            if rr_key == key:
                remainder += _to_float(rr.get("remaining_units_per_hour"))

        if abs((actual + remainder) - expected) > 1e-6:
            raise ValueError(f"Clearing invariant violated for {key}")

    for r in clearing_result:
        if _to_float(r["allocated_units_per_hour"]) < 0:
            raise ValueError("Negative clearing allocation detected")
    
    return out