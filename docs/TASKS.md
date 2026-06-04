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

---

## Backlog

| ID | Task | Layer | Notes |
|----|------|------|------|
| T-005 | Functional coding audit | All | ARCHITECTURE, DECISIONS |
| T-004 | Add core unit tests | tooling | In Progress | TOOLING.md |

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