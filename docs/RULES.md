# Engine Rules Registry

## Purpose

Define non-negotiable behavioral invariants of the engine.

These rules govern:
- evaluation correctness
- diagnostic integrity
- signal behavior
- evidence preservation

They are:
- independent of implementation
- always-on constraints
- enforced via structure, pipeline, and validation

---

## Rule Status Legend

| Status | Meaning |
|--------|--------|
| ✅ Active | Current invariant |
| ❌ Superseded | No longer valid |
| ⚠️ Partial | Not fully implemented |

---

## Rules Table

| RuleId | Status | Supersedes | ReplacedBy | Domain | Rule | Rationale | Enforcement | Notes |
|--------|--------|-----------|------------|--------|------|-----------|-------------|-------|
| 1 | ✅ | | | Signals | Signals must be derived only from fact surfaces | Prevents unstable dependencies | Signal layer design | |
| 2 | ✅ | | | Signals | Signals must preserve full evaluation grain | Prevents incorrect aggregation | Schema + logic | |
| 3 | ✅ | | | Evidence | Signals must include row-level evidence | Enables traceability | Signal generation | |
| 4 | ✅ | | | Signals | Suppression must operate at full grain | Prevents cross-context errors | Signal logic | |
| 5 | ✅ | | | Signals | Signals must not implicitly aggregate | Preserves correctness | Query design | |
| 6 | ✅ | | | Evidence | Evidence must represent row-level causality | Prevents misinterpretation | Diagnostics discipline | |

| 7 | ✅ | | | Contracts | Engine must not define schema | Prevents drift | Contract-first enforcement | |
| 8 | ✅ | | | Contracts | Engine must not hardcode table presence | Enables extensibility | Contract metadata | |
| 9 | ✅ | | | Contracts | Validation must be contract-driven | Prevents duplication | Validator layer | |
| 10 | ✅ | | | Contracts | Contracts must be complete | Avoid ambiguity | Validation discipline | |
| 11 | ✅ | | | Contracts | Contracts must declare kind | Prevents ambiguity | Parser | |
| 12 | ✅ | | | Contracts | Contracts must be dynamically discovered | Enables extensibility | Loader | |
| 13 | ✅ | | | Tooling | UI logic must be contract-driven | Prevents duplication | Template builder | |

---

## Product Grain Invariants

- All product-level tables must include building_key
- Product identity is:

  (company, product, building, quality)

- No joins may occur on product without building_key
- Aggregation must occur only after slot-level computation

---

## Pipeline Invariants

- Each stage consumes validated input and produces valid output
- No stage may modify upstream results
- No stage may recompute prior transformations
- All stage outputs must be deterministic

---

## Production and Flow Rules

- Production is computed at full capacity
- Production is independent of input availability
- Production must not be bottleneck-constrained
- Consumption is globally aggregated via BOM
- No routing or path-based allocation is allowed
- All imbalance is resolved via clearing

---

## Clearing Rules

- Clearing must resolve all imbalance
- Allocation must be explicit
- Allocation fractions must sum to 1
- Channels distribute only (do not modify production)
- Retail capacity is applied only in clearing/allocation layers

---

## Diagnostics Rules

- Diagnostics must not modify engine outputs
- Diagnostics must use only fact surfaces
- Diagnostics must preserve evaluation grain
- Diagnostics must not infer missing values

---

## Plan Health Rules

- plan_health must operate only on abnormal rows
- plan_health must not recompute production or balance
- BL translation must use observed production only
- No BL inference when production is missing

---

## Input Validation Invariants

### Structural

- All inputs must match contract schema
- All keys must be valid
- No duplicate key rows

---

### Scenario Behavior

- Overrides must apply only to explicit fields
- Unspecified fields retain baseline values
- Result must be valid after application

---

### Temporal

- All rates must be normalized to hourly units
- Daily inputs must be converted before ingestion

---

## No Routing

The system must not implement:

- routing
- path-based allocation
- priority-based consumption

All flows must be:
- aggregate
- global
- deterministic

All imbalance is resolved via clearing.

---

## Contract Invariants

### Structure

- All structure defined in contracts
- Engine must not infer schema
- No schema in code

---

### Validation

- All validation rules defined in contracts
- No duplication in engine
- Required/non-empty defined in metadata

---

### Discovery

- Contracts dynamically loaded
- No fixed filenames
- Adding contracts requires no code change

---

### Completeness

- All fields explicitly defined
- All keys valid
- No partial schemas

---

## Principles

- Rules are never optional
- Rules are enforced systemically
- Rules are not decisions — they are invariants

---

## Summary

These rules ensure:

- deterministic execution
- full traceability
- schema-driven behavior
- correct diagnostics

They protect the integrity of the system.