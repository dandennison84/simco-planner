# Task Tracking

## Purpose

Track active and completed work items.

Rules:
- One row = one task
- Keep tasks small and testable
- Move tasks between states explicitly

---

## Active Tasks

| ID | Task | Layer | Status | Notes |
|----|------|------|--------|------|
| T-109 | Design user-facing summary sheet (Map Health dashboard) | UI / Excel | ⏳ Pending | Create a consolidated summary view showing only actionable, non-normal conditions with combined signals (flow, role, constraint, allocation) and ratios expressed in daily units to guide building adjustments |

---

## Backlog

| ID | Task | Layer | Notes |
|----|------|------|------|
| T-004 | Add core unit tests | tooling | In Progress | TOOLING.md |
| T-082 | Backfill missing product slopes | data | Pending | derive from in-game tests |
| T-083 | Backfill boom phase multipliers | data | Pending | requires new test data |
| T-099 | Refactor stage helpers into contract-driven inputs | engine | ⏳ Pending | Replace `_k()` and `_require_*` usage with trusted, typed values from io_csv + validator; retain only business-rule invariants |
| T-098 | Add structured comments and improve readability across engine | docs/code | ⏳ Pending | Focus on explaining data flow, invariants, and loop intent for non-imperative readers |

---

## Completed

| ID | Task | Layer | Notes |
|----|------|------|------|
| T-001 | Add core documentation | docs | In Progress | ARCHITECTURE, DECISIONS |
| T-002 | Define tooling document | tooling | In Progress | TOOLING.md |
| T-003 | Define git workflow | tooling | In Progress | GIT_WORKFLOW.md |
| T-010 | Create engine skeleton | engine | minimal pipeline |
| T-011 | Define data folder structure | data | input/output |
| T-013 | Documentation alignment with engine contract | docs | In Progress | README, SYSTEM, DATA_CONTRACTS |
| T-012 | Build first staging layer | L2 | typing + validation |
| T-018 | Formalize full-capacity production model with clearing-based imbalance resolution | L3–L5 | Production independent of inputs; shortages resolved via clearing |
| T-024 | Implement centralized structural validation boundary in run.py | Engine | Ensure schema validation, typing, required table checks, and key constraints are fully enforced |
| T-023 | Implement logical data completeness validation | Engine | Fail when required relationships are missing despite schema validity |
| T-021 | Implement empty table validation logic | Engine | Distinguish valid no-op runs from missing required outputs |
| T-020 | Enforce strict clearing completeness | L5 (Clearing) | Fail if any imbalance remains |
| T-014 | Implement multi-level BOM explosion with cycle detection | L4 (BOM Consumption) | Recursive expansion; full upstream consumption |
| T-016 | Implement BOM input rounding and production run consistency | L3–L4 | Integer input consumption; introduce production runs |
| T-019 | Implement BOM cycle detection in validation layer | Validation | Detect cycles in product_bom graph and fail execution |
| T-022 | Enforce explicit retail channel behavior | L5 (Clearing) | Retail allocation only when clearing_plan includes retail channel |
| T-025 | Add product BOM demand detail trace table | L4 (BOM Consumption) | Emit source-to-demand relationships for recursive BOM to support debugging and matrix/pivot analysis; include (company, source_product, demanded_product, quality, units) |
| T-026 | Refactor template creation process | Engine / UX Layer | Standardize and modularize generation of input/output Excel templates; eliminate duplication, enforce schema-driven structure, and align with naming conventions and table contracts |
| T-031 | Create `/contracts/input/`, `/contracts/reference/`, `/contracts/output/`, `/contracts/ui/`, `/contracts/internal/`, `/contracts/schema/` directories | contracts |  | Establish canonical contract directory structure |
| T-035 | Rename `schema/ui.yml` → `/contracts/ui/lookups.yaml` | contracts |  | Convert to canonical `kind: lookup_mapping` format |
| T-032 | Split `schema/input.yml` into per-table files under `/contracts/input/` | contracts |  | One file per table (company.yaml, map_structure.yaml, etc.) |
| T-033 | Split `schema/reference.yml` into per-table files under `/contracts/reference/` | contracts |  | One file per table (building.yaml, product.yaml, etc.) |
| T-034 | Split `schema/output.yml` into per-table files under `/contracts/output/` | contracts |  | One file per table (production_intent.yaml, etc.) |
| T-036 | Remove `schema/internal.yml`; create `/contracts/internal/` directory placeholder | contracts |  | No tables defined yet |
| T-037 | Add required top-level metadata to all table contracts (`kind`, `table`, `surface`, `presence`) | contracts |  | Conform to CONTRACT_SPEC.md |
| T-038 | Replace all `type: logical` with `type: boolean` in all contract files | contracts |  | Align with standard vocabulary |
| T-030 | Rename `/schema` directory to `/contracts` | repo |  | Update all Python references (`run.py`, `build_template.py`) |
| T-039 | Add `presence.required` and `presence.non_empty` metadata to input tables (company, map_structure, production_plan) | contracts |  | Replace hardcoded logic in run.py |
| T-040 | Add `presence.non_empty` metadata to required output tables (production_intent) | contracts |  | Replace `_validate_output_non_empty()` |
| T-041 | Refactor `_schema_paths()` in `run.py` to remove fixed file references and support directory-based loading | engine |  | No more input.yml/reference.yml/output.yml |
| T-042 | Implement contract discovery: load all `*.yaml` files under `/contracts/**` | engine |  | Build registry by (surface, table) |
| T-043 | Update `load_contract_inputs()` to use contract registry instead of grouped schema documents | engine |  | Fully contract-driven loading |
| T-044 | Remove hardcoded required input table list from `_validate_required_inputs_non_empty()` | engine |  | Use `presence.required` instead |
| T-045 | Remove hardcoded output non-empty logic from `_validate_output_non_empty()` | engine |  | Use `presence.non_empty` instead |
| T-046 | Replace `LOOKUPS` constant in `build_template.py` with contract-driven lookup parsing | tooling |  | Use `/contracts/ui/lookups.yaml` |
| T-047 | Replace `LOOKUP_TO_RANGE` mapping in `build_template.py` with contract-derived values | tooling |  | Eliminate duplicated mapping |
| T-048 | Update `build_template.py` to generate sheets, tables, and ranges entirely from lookup contracts | tooling |  | Fully contract-driven UI |
| T-049 | Add schema meta-validation: ensure all `keys` exist in `fields` and are `required: true` | validation |  | Contract integrity check |
| T-050 | Add validation to reject unknown field types during contract load | validation |  | Prevent silent schema errors |
| T-051 | Add validation: `constraints` allowed only for numeric types | validation |  | Prevent invalid schema usage |
| T-052 | Enforce contract parsing rules: `fields` must be mapping, `keys` must be list | validation |  | Fail fast on invalid contracts |
| T-053 | Enforce filename convention: `<table>.yaml` must match `table:` field | validation |  | Prevent identity drift |
| T-054 | Create `/contracts/schema/` directory for contract meta-schemas | contracts |  | Holds JSON schema definitions for contract validation |
| T-055 | Define `table.schema.json` to validate all `kind: table` contracts | contracts |  | Enforce top-level fields, field structure, keys consistency |
| T-056 | Define `lookup.schema.json` to validate `kind: lookup_mapping` contracts | contracts |  | Enforce lookup mapping structure |
| T-057 | Integrate schema validation step before contract loading | validation |  | Validate contract YAML against meta-schema before runtime |
| T-058 | Replace linear production speed with inverse scaling | engine | Update `prod_speed` in production_resolution to `1 / (1 - mod)` |
| T-059 | Add `economic_phase_key` to company schema | contracts | Add column and mark as `required: true` |
| T-060 | Load company → economic_phase mapping | engine | Build `company_key → economic_phase_key` lookup |
| T-061 | Load building phase multipliers | engine | Build `building_key → recession/boom multipliers` map |
| T-062 | Apply phase multiplier to production | engine | Multiply production by building-level phase multiplier |
| T-063 | Normalize Normal phase behavior | engine | Ensure phase key = 1 → multiplier = `1.0` |
| T-066 | Validate company phase key integrity | validation | Ensure all `economic_phase_key` values exist in reference table |
| T-067 | Validate production vs game (BL=1 test) | validation | Power BL=1 at 4% → 2673.90 expected |
| T-068 | Validate production aggregation behavior | validation | Ensure BL scaling remains consistent post-change |
| T-069 | Validate recession vs boom production | validation | Recession increases output, boom decreases output |
| T-072 | Refactor BOM consumption to direct-only inputs | engine | ✅ Complete | Removed recursive expansion, fixed double-counting |
| T-074 | Replace retail sales speed with inverse scaling | engine | Pending | Use `1 / (1 - sales_speed_delta)` |
| T-075 | Add retail_quality_model table | data | Pending | product_key × building_key slope |
| T-076 | Add retail_phase_multiplier table | data | Pending | product_key × phase multiplier |
| T-077 | Integrate QL slope into retail calc | engine | Pending | `1 + slope × QL` |
| T-078 | Integrate phase multiplier into retail calc | engine | Pending | product-level phase |
| T-079 | Validate Oranges vs Orange Juice retail behavior | validation | Pending | ensure slopes differ correctly |
| T-080 | Validate Fashion products (Dresses, Necklaces) | validation | Pending | confirm higher QL slopes |
| T-081 | Validate recession vs normal retail outputs | validation | Pending | confirm phase multipliers |
| T-070 | Validate retail behavior under phase | validation | Retail allocation should shift with phase multiplier |
| T-073 | Validate BOM consumption vs production (Power net sanity) | validation | ⏳ Pending | Expect Power consumption < production for company 1 |
| T-064 | Replace linear sales speed with inverse scaling | engine | Update retail capacity to use `1 / (1 - sales_speed_delta)` |
| T-065 | Apply phase multiplier to retail throughput | engine | Multiply retail capacity by phase multiplier |
| T-090 | Validate balance_plan net flow correctness | validation | ⏳ Pending | Production − consumption − retail demand must reconcile per product |
| T-091 | Validate Power net sanity across full pipeline | validation | ⏳ Pending | Ensure Power surplus from production persists after clearing |
| T-092 | Validate clearing_result retail allocation | validation | ⏳ Pending | Retail should consume up to capacity, then overflow to exchange |
| T-093 | Validate clearing priority ordering | validation | ⏳ Pending | Retail → Contract → Exchange must be enforced correctly |
| T-094 | Validate no double-counting between BOM and clearing | validation | ⏳ Pending | Ensure intermediate goods not consumed twice |
| T-095 | Validate channel allocation consistency | validation | ⏳ Pending | Sum(retail + contract + exchange) = available supply |
| T-096 | Validate phase impact propagates through clearing | validation | ⏳ Pending | Demand shifts should move allocation mix, not just totals |
| T-097 | Validate negative/overdraw conditions | validation | ⏳ Pending | No product should allocate beyond available supply |
| T-071 | Ensure phase multiplier applied once | engine | Prevent duplicate application across stages |
| T-084 | Review and update documentation for core engine physics | docs | Pending | Update production, BOM, and retail sections to reflect new formulas and table structures |
| T-100 | Add retail_bottleneck_detail output | engine | ⏳ Pending | Expose building-level capacity usage (allocated vs capacity) to identify which retail buildings are constraining sales |
| T-101 | Add product_flow_classification output | engine | ⏳ Pending | Classify each product as surplus / shortage / balanced using balance_plan.net_units_per_hour |
| T-107 | Standardize _out_* Power Query outputs (joins, naming, column order) | UI / Power Query | ⏳ Pending | Ensure all _out_* queries enrich IDs with names, include company_display, and enforce consistent column ordering via final Table.SelectColumns |
| T-108 | Add product_role_classification output | engine | ⏳ Pending | Classify each product as retail_output, pure_non_retail_output, or vi_input using clearing_plan Retail channel presence and balance_plan.units_consumed_per_hour |
| T-106 | Add company_display field across all _out queries | UI / Power Query | ⏳ Pending | Join company table and expose company_name, realm_name, snapshot_date, plus composite company_display for consistent, readable multi-company output |
T-102 | Add retail_unused_capacity output | engine | ⏳ Pending | Compute unused retail capacity per building using bottleneck detail (capacity - allocated)
| T-005 | Functional coding audit | All | ARCHITECTURE, DECISIONS |
| T-103 | Add allocation ratios to allocation_summary (M layer) | UI / Power Query | ⏳ Pending | Compute retail_pct and non_retail_pct in view layer from allocation_summary (no engine stage) |
T-104 | Add retail_priority_path output | engine | ⏳ Pending | Surface retail_plan priority ordering per product for debugging allocation cascade
T-105 | Add constraint_type output | engine | ⏳ Pending | Classify constraint driver per product (retail_constrained, supply_constrained, not_constrained) using allocation_summary and balance_plan

---

## Status Values

- Backlog
- In Progress
- Blocked
- Complete

---

## Summary

Tasks track execution work.
They must remain small, explicit, and testable.