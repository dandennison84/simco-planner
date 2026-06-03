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
| T-004 | Add core unit tests | tooling | In Progress | TOOLING.md |
| T-025 | Add product BOM demand detail trace table | L4 (BOM Consumption) | Emit source-to-demand relationships for recursive BOM to support debugging and matrix/pivot analysis; include (company, source_product, demanded_product, quality, units) |

---

## Backlog

| ID | Task | Layer | Notes |
|----|------|------|------|
| T-005 | Functional coding audit | All | ARCHITECTURE, DECISIONS |

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