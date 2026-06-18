# Task Tracking

## Purpose

Track execution work items.

Rules:
- One row = one task
- Tasks must be small, isolated, and testable
- Status must be explicit and current

---

## Status Values

- Backlog
- In Progress
- Blocked
- Complete

---

## Active Tasks

| ID | Task | Layer | Status | Notes |
|----|------|------|--------|------|
| T-110 | Add product_cost_basis output | engine | Backlog | Compute direct production cost per unit |
| T-111 | Add product_cost_rollup output | engine | Backlog | Recursive cost rollup |
| T-112 | Add product_revenue model | engine | Backlog | Revenue from retail + exchange |
| T-113 | Add product_profitability output | engine | Backlog | Profit and margin outputs |
| T-114 | Add view_plan_economics | UI | Backlog | User-facing economics summary |
| T-115 | Add profit_allocation_summary | engine | Backlog | Retail vs non-retail profit |
| T-116 | Add economic_action_signals | engine | Backlog | Expand/reduce classification |
| T-099 | Refactor stage helpers into contract-driven inputs | engine | Backlog | Remove helper parsing functions |
| T-098 | Improve engine readability and comments | docs/code | Backlog | Focus on invariants and flow |
| T-100 | Add retail_bottleneck_detail output | engine | Backlog | Identify retail constraints |
| T-101 | Add product_flow_classification | engine | Backlog | surplus / shortage / balanced |
| T-102 | Add retail_unused_capacity | engine | Backlog | capacity - allocated |
| T-103 | Add allocation ratios to allocation_summary | UI | Backlog | retail_pct, non_retail_pct |
| T-104 | Add retail_priority_path | engine | Backlog | debug allocation cascade |
| T-105 | Add constraint_type | engine | Backlog | classify constraints |
| T-106 | Add company_display in outputs | UI | Backlog | improve readability |
| T-107 | Standardize _out_* queries | UI | Backlog | consistent naming + ordering |
| T-108 | Add product_role_classification | engine | Backlog | retail_output, etc. |
| T-109 | Design Map Health dashboard | UI | Backlog | consolidated signals view |
| T-118 | Fix input reader to exclude disabled rows | engine | Complete | Already implemented |
| T-119 | Add abundance mechanics | engine | Complete | Implemented in production stage |

---

## Backlog

| ID | Task | Layer | Status | Notes |
|----|------|------|--------|------|
| T-004 | Add core unit tests | tooling | In Progress | Testing framework integration |
| T-082 | Backfill product slopes | data | Backlog | derive from game data |
| T-083 | Backfill boom multipliers | data | Backlog | requires test data |
| T-074 | Replace retail speed with inverse scaling | engine | Backlog | align with production speed |
| T-075 | Add retail_quality_model table | data | Backlog | slope per product |
| T-076 | Add retail_phase_multiplier | data | Backlog | phase impact |
| T-077 | Integrate QL slope | engine | Backlog | use slope × QL |
| T-078 | Integrate retail phase multiplier | engine | Backlog | product-level effect |

---

## Completed

| ID | Task | Layer | Status | Notes |
|----|------|------|--------|------|
| T-001 | Add core documentation | docs | Complete | |
| T-002 | Define tooling document | tooling | Complete | |
| T-003 | Define git workflow | tooling | Complete | |
| T-010 | Create engine skeleton | engine | Complete | |
| T-011 | Define data folders | data | Complete | |
| T-013 | Align documentation with contracts | docs | Complete | |
| T-012 | Build first staging layer | engine | Complete | |
| T-018 | Implement full-capacity production | engine | Complete | |
| T-024 | Central validation boundary | engine | Complete | |
| T-023 | Data completeness validation | engine | Complete | |
| T-021 | Empty table validation | engine | Complete | |
| T-020 | Clearing completeness enforcement | engine | Complete | |
| T-014 | Multi-level BOM explosion | engine | Complete | |
| T-019 | BOM cycle detection | validation | Complete | |
| T-022 | Retail channel enforcement | clearing | Complete | |
| T-025 | BOM demand trace table | engine | Complete | |
| T-030 | Rename schema → contracts | repo | Complete | |
| T-041 | Contract discovery system | engine | Complete | |
| T-043 | Contract-driven input loading | engine | Complete | |
| T-045 | Output validation via contracts | engine | Complete | |
| T-052 | Contract validation rules | validation | Complete | |
| T-062 | Phase multiplier applied to production | engine | Complete | |
| T-071 | Prevent duplicate phase application | engine | Complete | |
| T-072 | Direct BOM consumption refactor | engine | Complete | |
| T-058 | Production speed inverse scaling | engine | Complete | |
| T-117 | Align documentation with building_key propagation and plan_health output | docs | Complete | Updating schemas, constraint_type, and plan_health docs |

---

## Summary

Tasks track execution work.

They must remain:
- small
- explicit
- testable

Tasks represent implementation steps, not system behavior.