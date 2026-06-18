# Roadmap

## Purpose

Define system evolution in terms of **capability milestones**, not features.

Tracks:
- what is being built
- in what order
- what defines completion of each stage

---

# PHASES

| Phase | Name | Goal | Status |
|------|------|------|--------|
| 1 | Foundation | Contracts, architecture, and governance | ✅ In Progress |
| 2 | Engine Core | Deterministic production → BOM → balance → clearing pipeline | ✅ In Progress |
| 3 | Engine Completion | Full contract alignment + product-grain propagation | ⏳ Pending |
| 4 | Diagnostics Layer | Derived facts, classifications, constraint detection | ⏳ Pending |
| 5 | Map Health | Actionable diagnostics and BL translation (view_plan_health) | ⏳ Pending |
| 6 | VI Planner | Steady-state planning system | ⏳ Pending |
| 7 | Scenario Runner | Time-based simulation | ⏳ Pending |
| 8 | Polish | UI, performance, validation, completeness | ⏳ Pending |

---

# PHASE 1 — FOUNDATION

Goal:
Establish system structure and rules

Includes:
- contract architecture
- decisions log
- naming conventions
- tooling setup
- git workflow

Exit criteria:
- all system structure defined
- no logic embedded in docs or tooling
- contract-first discipline established

---

# PHASE 2 — ENGINE CORE

Goal:
Build deterministic transformation pipeline

Pipeline:

INPUT  
→ VALIDATION  
→ STRUCTURE  
→ PRODUCTION_RESOLUTION  
→ BOM_CONSUMPTION  
→ BALANCE  
→ CLEARING  
→ RETAIL_ALLOCATION  
→ OUTPUT  

Capabilities:
- full-capacity production
- recursive BOM consumption
- global balance
- clearing-based resolution
- retail allocation

Constraints:
- no routing
- no bottleneck-based production
- no implicit allocation

Exit criteria:
- deterministic outputs
- all core invariants enforced
- no upstream recomputation

---

# PHASE 3 — ENGINE COMPLETION

Goal:
Finalize engine correctness and schema alignment

Includes:
- contract-driven schema enforcement
- building_key propagation across all product tables
- product grain standardization
- constraint_type normalization
- abundance integration
- output contract completeness

Exit criteria:
- no contract/engine drift
- all product-grain tables aligned
- all invariants enforced via contracts or stages
- engine produces fully resolved fact tables

---

# PHASE 4 — DIAGNOSTICS LAYER

Goal:
Translate engine outputs into structured facts

Includes:
- product_role classification
- flow classification
- constraint detection (constraint_type)
- aggregation consistency

Rules:
- diagnostics must not modify engine outputs
- diagnostics must operate on fact surfaces only

Exit criteria:
- all derived facts reproducible from outputs
- no duplication of engine logic

---

# PHASE 5 — MAP HEALTH

Goal:
Provide actionable interpretation of system state

Primary output:
- view_plan_health

Capabilities:
- filter abnormal products
- classify constraint type
- compute required actions
- compute BL adjustments

Rules:
- no recomputation of engine values
- BL derived from observed production only
- no inference when production missing

Exit criteria:
- produces actionable, deterministic diagnostics
- aligns with engine outputs exactly

---

# PHASE 6 — VI PLANNER

Goal:
Design steady-state production systems

Capabilities:
- define target production levels
- evaluate required inputs and costs
- identify constraint requirements
- support vertical integration planning

Rules:
- must reuse engine outputs
- must not duplicate production logic

---

# PHASE 7 — SCENARIO RUNNER

Goal:
Model system evolution over time

Capabilities:
- apply scenario deltas
- evolve state over discrete time steps
- simulate investments and transitions

Rules:
- baseline remains immutable
- all changes applied via scenario_delta

---

# PHASE 8 — POLISH

Goal:
Finalize system usability and completeness

Includes:
- UI integration (Excel / Power BI)
- performance improvements
- validation completeness
- edge-case handling
- documentation alignment

---

# RULES

- Phases represent capability, not features
- Do not skip phases
- Each phase must be testable before moving forward
- Later phases must not backfill earlier ones

---

# SUMMARY

System evolves in layers:

1. Engine (truth)
2. Diagnostics (facts)
3. Health (interpretation)
4. Planner (design)
5. Scenarios (time)

Each layer:
- consumes prior results
- does not recompute upstream logic

The roadmap defines capability maturity, not implementation tasks.