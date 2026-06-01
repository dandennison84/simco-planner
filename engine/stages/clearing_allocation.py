from __future__ import annotations

from typing import Dict, List, Tuple

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

    for bal in balance_rows:
        company_key = _k(bal.get("company_key"))
        product_key = _k(bal.get("product_key"))
        quality_level = _k(bal.get("quality_level"))
        net = _to_float(bal.get("net_units_per_hour"))

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
            if direction == "sink" and bool(ch.get("uses_retail_capacity")):
                cap = retail_capacity_map.get((company_key, product_key, quality_level), 0.0)
                used = allocated_so_far.get(channel_key, 0.0)
                cap_left = max(0.0, cap - used)
                desired = min(desired, cap_left)

            allocated = min(desired, remaining)

            if allocated <= 0:
                continue

            remaining -= allocated
            allocated_so_far[channel_key] = allocated_so_far.get(channel_key, 0.0) + allocated

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

    out = dict(
        state,
        clearing_result=clearing_result,
        clearing_remainder=clearing_remainder,
    )
    debug_rows(out, "clearing_allocation", "clearing_result")
    debug_rows(out, "clearing_allocation", "clearing_remainder")
    return out