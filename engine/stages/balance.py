from __future__ import annotations

from typing import Dict, Tuple, Any, List

from engine.debug import debug_log, debug_rows


def _k(x) -> str:
    """
    Normalize keys:
        - None -> ""
        - ensure string type
        - trim whitespace

    Ensures consistent joins across stages.
    """
    return ("" if x is None else str(x)).strip()


def _require_float(
    row: Dict[str, Any],
    field: str,
    *,
    stage: str,
    row_idx: int | None = None,
) -> float:
    """
    Extract required float field with fail-fast validation.
    """
    value = row.get(field, None)

    if value is None or str(value).strip() == "":
        raise ValueError(
            f"[{stage}:error]\n"
            f"  field={field}\n"
            f"  row={row_idx}\n"
            f"  value={value}\n"
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
            f"  reason=invalid float value"
        )


def stage_balance(state: Dict[str, object]) -> Dict[str, object]:
    """
    =============================================================================
    Stage: balance

    Purpose:
        Compute net supply/demand for each (company, product, quality).

    Functional view:
        produced_map  = group_sum(production_intent)
        consumed_map  = group_sum(product_bom_consumption)

        balance_plan =
            (produced - consumed)
            -> split into (surplus, shortage)

        product_flow_classification =
            classify(balance_plan.net_units_per_hour)

        product_role_classification =
            classify product role using:
              - Retail channel presence in clearing_plan
              - units_consumed_per_hour

    Inputs:
        production_intent:
            (company, product, quality) -> units_produced_per_hour

        product_bom_consumption:
            (company, product, quality) -> units_consumed_per_hour

        clearing_plan:
            used to identify products routed to Retail

        channel:
            used to identify which channel_key values are Retail

        product:
            used to map product_key -> producing building_key

    Outputs:
        balance_plan:
            Contains:
                - company_key
                - product_key
                - building_key
                - quality_level
                - units_produced_per_hour
                - units_consumed_per_hour
                - net_units_per_hour
                - surplus_units_per_hour
                - shortage_units_per_hour

        product_flow_classification:
            Contains:
                - company_key
                - product_key
                - building_key
                - quality_level
                - flow_type (surplus / shortage / balanced)

        product_role_classification:
            Contains:
                - company_key
                - product_key
                - building_key
                - quality_level
                - product_role (retail_output / pure_non_retail_output / vi_input)

    Notes:
        - Union of keys ensures all products are included
        - Zero production or zero consumption still handled
        - No allocation occurs here (pure accounting stage)
        - building_key is emitted from product reference so downstream
          views can translate shortages/surpluses into BL requirements
    =============================================================================
    """

    stage_name = "balance"
    debug_log(state, "[balance] start")

    production_rows = state.get("production_intent", [])
    consumption_rows = state.get("product_bom_consumption", [])
    clearing_rows = state.get("clearing_plan", [])
    channel_rows = state.get("channel", [])
    product_rows = state.get("product", [])

    # ---------------------------------------------------------
    # Identify which channel keys are Retail
    # ---------------------------------------------------------
    retail_channel_keys = {
        _k(r.get("channel_key"))
        for r in channel_rows
        if str(r.get("uses_retail_capacity", "")).strip().lower() in {"true", "1", "yes", "y"}
    }

    # ---------------------------------------------------------
    # Identify products routed to Retail
    # Grain: (company, product, quality)
    # ---------------------------------------------------------
    retail_output_keys = {
        (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )
        for r in clearing_rows
        if _k(r.get("channel_key")) in retail_channel_keys
    }

    # ---------------------------------------------------------
    # Product -> producing building map
    # Assumes each product is produced by a single building type
    # ---------------------------------------------------------
    product_to_building: Dict[str, str] = {}

    for i, r in enumerate(product_rows, start=1):
        product_key = _k(r.get("product_key"))
        building_key = _k(r.get("building_key"))

        if product_key == "":
            continue

        if building_key == "":
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  field=building_key\n"
                f"  row={i}\n"
                f"  product_key={product_key}\n"
                f"  value={building_key}\n"
                f"  reason=missing building_key in product reference"
            )

        if product_key in product_to_building and product_to_building[product_key] != building_key:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  field=building_key\n"
                f"  row={i}\n"
                f"  product_key={product_key}\n"
                f"  reason=multiple producing building types found for product"
            )

        product_to_building[product_key] = building_key

    # ---------------------------------------------------------
    # Aggregate production: group by (company, product, quality)
    # ---------------------------------------------------------
    produced_map: Dict[Tuple[str, str, str], float] = {}

    for i, r in enumerate(production_rows, start=1):
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )

        produced_map[key] = produced_map.get(key, 0.0) + _require_float(
            r,
            "units_produced_per_hour",
            stage=stage_name,
            row_idx=i,
        )

    # ---------------------------------------------------------
    # Aggregate consumption: group by same grain
    # ---------------------------------------------------------
    consumed_map: Dict[Tuple[str, str, str], float] = {}

    for i, r in enumerate(consumption_rows, start=1):
        key = (
            _k(r.get("company_key")),
            _k(r.get("product_key")),
            _k(r.get("quality_level")),
        )

        consumed_map[key] = consumed_map.get(key, 0.0) + _require_float(
            r,
            "units_consumed_per_hour",
            stage=stage_name,
            row_idx=i,
        )

    # ---------------------------------------------------------
    # Combine keys (union of produced and consumed)
    # ---------------------------------------------------------
    all_keys = sorted(set(produced_map.keys()) | set(consumed_map.keys()))

    # ---------------------------------------------------------
    # Compute balance per key
    # ---------------------------------------------------------
    balance_plan: List[dict] = []
    product_flow_classification: List[dict] = []
    product_role_classification: List[dict] = []

    for key in all_keys:
        company_key, product_key, quality_level = key

        if product_key not in product_to_building:
            raise ValueError(
                f"[{stage_name}:error]\n"
                f"  field=product_key\n"
                f"  product_key={product_key}\n"
                f"  reason=product not found in product reference or missing building_key"
            )

        building_key = product_to_building[product_key]

        produced = produced_map.get(key, 0.0)
        consumed = consumed_map.get(key, 0.0)

        # Core balance equation
        net = produced - consumed

        surplus = max(net, 0.0)
        shortage = max(-net, 0.0)

        balance_plan.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "building_key": building_key,
                "quality_level": quality_level,
                "units_produced_per_hour": produced,
                "units_consumed_per_hour": consumed,
                "net_units_per_hour": net,
                "surplus_units_per_hour": surplus,
                "shortage_units_per_hour": shortage,
            }
        )

        # -----------------------------------------------------
        # Flow classification
        # -----------------------------------------------------
        if net > 1e-12:
            flow_type = "surplus"
        elif net < -1e-12:
            flow_type = "shortage"
        else:
            flow_type = "balanced"

        product_flow_classification.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "building_key": building_key,
                "quality_level": quality_level,
                "flow_type": flow_type,
            }
        )

        # -----------------------------------------------------
        # Product role classification
        # -----------------------------------------------------
        if key in retail_output_keys:
            product_role = "retail_output"
        elif consumed > 1e-12:
            product_role = "vi_input"
        else:
            product_role = "pure_non_retail_output"

        product_role_classification.append(
            {
                "company_key": company_key,
                "product_key": product_key,
                "building_key": building_key,
                "quality_level": quality_level,
                "product_role": product_role,
            }
        )

    # ---------------------------------------------------------
    # Emit result
    # ---------------------------------------------------------
    out = dict(
        state,
        balance_plan=balance_plan,
        product_flow_classification=product_flow_classification,
        product_role_classification=product_role_classification,
    )

    debug_rows(out, "balance", "balance_plan")
    debug_rows(out, "balance", "product_flow_classification")
    debug_rows(out, "balance", "product_role_classification")

    # ---------------------------------------------------------
    # Invariant: produced - consumed == net
    # ---------------------------------------------------------
    for r in balance_plan:
        produced = r["units_produced_per_hour"]
        consumed = r["units_consumed_per_hour"]
        net = r["net_units_per_hour"]

        if abs((produced - consumed) - net) > 1e-6:
            raise ValueError("[balance:error]\n  reason=balance invariant violated")

    return out