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


def _optional_bool(row: Dict[str, Any], field: str, default: bool = True) -> bool:
    value = row.get(field, None)
    if value is None:
        return default

    s = str(value).strip().lower()
    if s == "":
        return default
    if s in {"true", "1", "yes", "y"}:
        return True
    if s in {"false", "0", "no", "n"}:
        return False

    return default


def stage_retail_allocation(state: Dict[str, object]) -> Dict[str, object]:
    """
    Building-level retail allocation.

    Input:
      - clearing_result (product-level Retail allocations only)
      - retail_plan
      - retail_prices
      - retail_phase_multiplier
      - retail_quality_model
      - retail_product_building
      - map_structure
      - company
      - channel

    Output:
      - retail_allocation_result

    Meaning:
      Expand cleared retail product demand into prioritized building types.

    Grain:
      (company_key, product_key, quality_level, building_key, priority)

    Rule:
      Clearing decides TOTAL retail demand.
      This stage only DISTRIBUTES that demand across building types by priority.
    """
    stage_name = "retail_allocation"

    debug_log(state, "[retail_allocation] start")

    company_rows = state.get("company", [])
    retail_rows = state.get("retail_prices", [])
    phase_rows = state.get("retail_phase_multiplier", [])
    quality_rows = state.get("retail_quality_model", [])
    retail_plan_rows = state.get("retail_plan", [])
    retail_product_building_rows = state.get("retail_product_building", [])
    map_structure_rows = state.get("map_structure", [])
    clearing_rows = state.get("clearing_result", [])
    channel_rows = state.get("channel", [])

    # ---------------------------------------------------------
    # Company settings
    # ---------------------------------------------------------
    company_index = {
        _k(r.get("company_key")): {
            "realm_key": _k(r.get("realm_key")),
            "sales_speed_delta": _optional_float(r, "sales_speed_delta", 0.0),
            "economic_phase_key": _k(r.get("economic_phase_key")),
        }
        for r in company_rows
    }

    # ---------------------------------------------------------
    # Baseline retail units
    # Key: (realm_key, product_key, quality_level)
    # ---------------------------------------------------------
    retail_index = {
        (
            _k(r.get("realm_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        ): _optional_float(r, "baseline_retail_units", 0.0)
        for r in retail_rows
    }

    # ---------------------------------------------------------
    # Product-level phase multiplier
    # Key: (product_key, economic_phase_key)
    # ---------------------------------------------------------
    phase_index = {
        (
            _k(r.get("product_key")),
            _k(r.get("economic_phase_key")),
        ): _optional_float(r, "phase_multiplier", 1.0)
        for r in phase_rows
    }

    # ---------------------------------------------------------
    # QL slope
    # Key: (product_key, building_key)
    # ---------------------------------------------------------
    quality_index = {
        (
            _k(r.get("product_key")),
            _k(r.get("building_key")),
        ): _optional_float(r, "ql_slope", 0.0)
        for r in quality_rows
    }

    # ---------------------------------------------------------
    # Valid product/building retail combinations
    # product_key -> set(building_key)
    # ---------------------------------------------------------
    retail_product_building_index: Dict[str, set[str]] = {}
    for r in retail_product_building_rows:
        product_key = _k(r.get("product_key"))
        building_key = _k(r.get("building_key"))
        retail_product_building_index.setdefault(product_key, set()).add(building_key)

    # ---------------------------------------------------------
    # Retail channels
    # ---------------------------------------------------------
    retail_channel_keys = {
        _k(r.get("channel_key"))
        for r in channel_rows
        if str(r.get("uses_retail_capacity", "")).strip().lower() in {"true", "1", "yes", "y"}
    }

    # ---------------------------------------------------------
    # Group retail_plan by (company, product, quality)
    # ---------------------------------------------------------
    retail_plan_by_key: Dict[Tuple[str, str, str], List[dict]] = {}

    for i, r in enumerate(retail_plan_rows, start=1):
        company_key = _k(r.get("company_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))
        building_key = _k(r.get("building_key"))

        priority = _require_int(
            r,
            "priority",
            stage=stage_name,
            row_idx=i,
            context=f"company_key={company_key}, product_key={product_key}, quality_level={quality_level}, building_key={building_key}",
        )

        key = (company_key, product_key, quality_level)
        retail_plan_by_key.setdefault(key, []).append(
            {
                "building_key": building_key,
                "priority": priority,
            }
        )

    for key, rows in retail_plan_by_key.items():
        priorities = [r["priority"] for r in rows]

        if len(priorities) != len(set(priorities)):
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  context=company_key={key[0]}, product_key={key[1]}, quality_level={key[2]}\n"
                f"  reason=retail_plan priorities must be unique"
            )

        retail_plan_by_key[key] = sorted(rows, key=lambda r: r["priority"])

    # ---------------------------------------------------------
    # Total building level by (company_key, building_key)
    # ---------------------------------------------------------
    building_level_by_company_building: Dict[Tuple[str, str], float] = {}

    for i, r in enumerate(map_structure_rows, start=1):
        if not _optional_bool(r, "enabled", True):
            continue

        company_key = _k(r.get("company_key"))
        building_key = _k(r.get("building_key"))

        if company_key == "" or building_key == "":
            continue

        building_level = _require_float(
            r,
            "building_level",
            stage=stage_name,
            row_idx=i,
            context=f"company_key={company_key}, building_key={building_key}",
        )

        key = (company_key, building_key)
        building_level_by_company_building[key] = (
            building_level_by_company_building.get(key, 0.0) + building_level
        )

    # ---------------------------------------------------------
    # Aggregate product-level retail demand from clearing_result
    # Key: (company_key, product_key, quality_level)
    # ---------------------------------------------------------
    retail_demand_by_key: Dict[Tuple[str, str, str], float] = defaultdict(float)

    for i, r in enumerate(clearing_rows, start=1):
        if _k(r.get("channel_key")) not in retail_channel_keys:
            continue
        if _k(r.get("direction")) != "sink":
            continue

        company_key = _k(r.get("company_key"))
        product_key = _k(r.get("product_key"))
        quality_level = _k(r.get("quality_level"))

        allocated_units = _require_float(
            r,
            "allocated_units_per_hour",
            stage=stage_name,
            row_idx=i,
            context=f"company_key={company_key}, product_key={product_key}, quality_level={quality_level}",
        )

        key = (company_key, product_key, quality_level)
        retail_demand_by_key[key] += allocated_units

    # ---------------------------------------------------------
    # Allocate retail demand across building priorities
    # ---------------------------------------------------------
    retail_allocation_result: List[dict] = {}
    retail_allocation_result = []
    retail_bottleneck_detail: List[dict] = {}
    retail_bottleneck_detail = []

    building_level_alloc_sum: Dict[Tuple[str, str, str], float] = defaultdict(float)

    for key, product_level_alloc in retail_demand_by_key.items():
        company_key, product_key, quality_level = key

        if product_level_alloc <= 0:
            continue

        if key not in retail_plan_by_key:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  context=company_key={company_key}, product_key={product_key}, quality_level={quality_level}\n"
                f"  reason=missing retail_plan for active retail allocation"
            )

        if company_key not in company_index:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  field=company_key\n"
                f"  value={company_key}\n"
                f"  reason=company not found"
            )

        company = company_index[company_key]
        realm_key = company["realm_key"]
        sales_speed_delta = company["sales_speed_delta"]
        economic_phase_key = company["economic_phase_key"]

        if sales_speed_delta >= 1.0:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  field=sales_speed_delta\n"
                f"  company_key={company_key}\n"
                f"  value={sales_speed_delta}\n"
                f"  reason=sales_speed_delta must be < 1.0"
            )

        sales_factor = 1.0 / (1.0 - sales_speed_delta)

        retail_key = (realm_key, product_key, quality_level)
        if retail_key not in retail_index:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  field=retail_prices\n"
                f"  company_key={company_key}\n"
                f"  product_key={product_key}\n"
                f"  quality_level={quality_level}\n"
                f"  realm_key={realm_key}\n"
                f"  reason=missing retail_prices entry"
            )

        base_retail_units = retail_index[retail_key]

        if economic_phase_key == "1":
            phase_factor = 1.0
        else:
            phase_key = (product_key, economic_phase_key)
            if phase_key not in phase_index:
                raise ValueError(
                    f"[{stage_name}:error]\n"
                    f"  field=phase_multiplier\n"
                    f"  company_key={company_key}\n"
                    f"  product_key={product_key}\n"
                    f"  economic_phase_key={economic_phase_key}\n"
                    f"  reason=missing retail_phase_multiplier entry"
                )
            phase_factor = phase_index[phase_key]

        remaining = product_level_alloc
        plan_rows = retail_plan_by_key[key]

        for plan in plan_rows:
            building_key = plan["building_key"]
            priority = plan["priority"]

            allowed_buildings = retail_product_building_index.get(product_key, set())
            if building_key not in allowed_buildings:
                raise ValueError(
                    f"[{stage_name}:error]\n"
                    f"  field=retail_product_building\n"
                    f"  product_key={product_key}\n"
                    f"  building_key={building_key}\n"
                    f"  reason=retail_plan building is not valid for product"
                )

            quality_key = (product_key, building_key)
            if quality_key not in quality_index:
                raise ValueError(
                    f"[{stage_name}:error]\n"
                    f"  field=ql_slope\n"
                    f"  product_key={product_key}\n"
                    f"  building_key={building_key}\n"
                    f"  reason=missing retail_quality_model entry"
                )

            ql_slope = quality_index[quality_key]
            ql_value = float(quality_level)
            quality_factor = 1.0 + (ql_slope * ql_value)

            total_building_level = building_level_by_company_building.get((company_key, building_key), 0.0)

            if total_building_level <= 0:
                continue

            capacity = (
                total_building_level
                * base_retail_units
                * sales_factor
                * phase_factor
                * quality_factor
            )

            allocated = min(remaining, capacity)

            if allocated <= 0:
                continue

            remaining -= allocated
            building_level_alloc_sum[key] += allocated

            # ---------------------------------------------------------
            # Record building-level allocation
            # ---------------------------------------------------------

            retail_allocation_result.append(
                {
                    "company_key": company_key,
                    "product_key": product_key,
                    "quality_level": quality_level,
                    "building_key": building_key,
                    "priority": priority,
                    "allocated_units_per_hour": allocated,
                }
            )

            # ---------------------------------------------------------
            # Record bottleneck detail (capacity utilization)
            # This uses the same computed capacity used for allocation.
            # Invariant:
            #   0 <= capacity_used_pct <= 1 (unless upstream capacity bug exists)
            # ---------------------------------------------------------

            if capacity > 0:
                capacity_used_pct = allocated / capacity
            else:
                capacity_used_pct = 0.0

            retail_bottleneck_detail.append(
                {
                    "company_key": company_key,
                    "product_key": product_key,
                    "quality_level": quality_level,
                    "building_key": building_key,
                    "allocated_units_per_hour": allocated,
                    "capacity_units_per_hour": capacity,
                    "capacity_used_pct": capacity_used_pct,
                }
            )            

            if remaining <= 1e-12:
                break

        if remaining > 1e-6:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  context=company_key={company_key}, product_key={product_key}, quality_level={quality_level}\n"
                f"  reason=retail allocation exceeded building capacity\n"
                f"  unallocated_units_per_hour={remaining}"
            )

    out = dict(
        state,
        retail_allocation_result=retail_allocation_result,
        retail_bottleneck_detail=retail_bottleneck_detail,
    )

    debug_rows(out, "retail_allocation", "retail_allocation_result")
    debug_rows(out, "retail_allocation", "retail_bottleneck_detail")

    # ---------------------------------------------------------
    # Invariant: building allocations must sum back to retail clearing amount
    # ---------------------------------------------------------
    for key, expected in retail_demand_by_key.items():
        actual = building_level_alloc_sum.get(key, 0.0)

        if abs(actual - expected) > 1e-6:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  context=company_key={key[0]}, product_key={key[1]}, quality_level={key[2]}\n"
                f"  reason=retail allocation invariant violated\n"
                f"  expected={expected}\n"
                f"  actual={actual}"
            )

    return out