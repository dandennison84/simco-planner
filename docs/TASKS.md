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
| ID | Task | Layer | Notes |
|----|------|------|------|
| T-030 | Rename `/schema` directory to `/contracts` | repo | Update all Python references (`run.py`, `build_template.py`) to new path |
| T-031 | Rename `schema/input.yml` → `contracts/input_tables.yml` | contracts | Update `_schema_paths()` in `run.py` |
| T-032 | Rename `schema/reference.yml` → `contracts/reference_tables.yml` | contracts | Update `_schema_paths()` in `run.py` |
| T-033 | Rename `schema/output.yml` → `contracts/output_tables.yml` | contracts | Update `_schema_paths()` in `run.py` |
| T-034 | Rename `schema/ui.yml` → `contracts/ui_lookups.yml` | contracts | Update `build_template.py` UI config path |
| T-035 | Rename `schema/internal.yml` → `contracts/internal_tables.yml` | contracts | No runtime use yet |
| T-036 | Replace all `type: logical` with `type: boolean` in all contract files | contracts | Align with standard type vocabulary |
| T-037 | Add `kind: table` to all table definitions in input/reference/output contract files | contracts | Top-level per table |
| T-038 | Add `kind: lookup_mapping` to UI contract file (`ui_lookups.yml`) | contracts | Separate behavior vs schema intent |
| T-039 | Add `presence.required` and `presence.non_empty` metadata to required input tables (company, map_structure, production_plan) | contracts | Replace hardcoded logic in run.py |
| T-040 | Add `presence.non_empty` metadata to required output tables (production_intent) | contracts | Replace `_validate_output_non_empty()` |
| T-041 | Remove hardcoded required input table list from `_validate_required_inputs_non_empty()` in `run.py` | engine | Replace with schema-driven presence checks |
| T-042 | Remove hardcoded output non-empty check from `_validate_output_non_empty()` in `run.py` | engine | Replace with schema-driven presence metadata |
| T-043 | Refactor `_schema_paths()` in `run.py` to read from `/contracts/` directory instead of `/schema/` | engine | Maintain current 3-file grouping |
| T-044 | Introduce contract loader that reads all files in `/contracts/` directory instead of fixed filenames | engine | Prepare for future folder split |
| T-045 | Move lookup definitions from `LOOKUPS` constant in `build_template.py` into `ui_lookups.yml` | tooling | Eliminate duplicated config |
| T-046 | Replace `LOOKUP_TO_RANGE` mapping in `build_template.py` with schema-driven mapping from `ui_lookups.yml` | tooling | Ensure Excel validation is config-driven |
| T-047 | Update `build_template.py` to fully derive lookup sheets, tables, and ranges from `ui_lookups.yml` | tooling | Remove hardcoded lookup behavior |
| T-048 | Add validation to ensure all `keys` fields exist in `fields` and are marked `required: true` | validation | Schema sanity check layer |
| T-049 | Add validation to reject unknown field types during schema load (before row validation) | validation | Prevent silent schema errors |
| T-050 | Add meta-validation: ensure `constraints` only applied to numeric fields | validation | Avoid invalid schema usage |
| T-051 | Standardize contract parsing to require `fields` to be a mapping and `keys` to be a list (fail fast) | validation | Already partially implemented, formalize behavior |
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