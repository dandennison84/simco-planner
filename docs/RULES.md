# Engine Rules Registry

### Purpose

Define non-negotiable behavioral invariants of the engine that cannot be cleanly expressed as architectural or governance decisions.

These rules govern:

- evaluation correctness  
- diagnostic integrity  
- signal behavior  
- evidence preservation  

They are:

- independent of implementation  
- always-on constraints  
- enforced through pipeline design, testing, and structural discipline  

---

## Rule Status Legend

| Status | Meaning |
|-------|--------|
| ✅ Active | Current invariant |
| ❌ Superseded | No longer valid (retained for history) |
| ⚠️ Partial | Not fully implemented yet |

---

## Rules Table

| RuleId | Status | Supersedes | ReplacedBy | Domain | Rule | Rationale | Enforcement | Notes |
|--------|--------|-----------|------------|--------|------|-----------|-------------|-------|
| 1 | ✅ |  |  | Signals | Signals must be derived only from fact surfaces | Prevents dependence on unstable intermediate data | Signal layer design | Ensures composability |
| 2 | ✅ |  |  | Signals | Signals must preserve full evaluation grain | Prevents loss of context and incorrect aggregation | Schema + evaluation logic | All context keys required |
| 3 | ✅ |  |  | Evidence | Signals must include Evidence preserving causal row identity | Enables traceability and diagnostics | Signal generation | Evidence captured pre-aggregation |
| 4 | ✅ |  |  | Signals | Suppression must operate at full signal grain | Prevents cross-context suppression errors | Signal engine logic | No partial matching |
| 5 | ✅ |  |  | Signals | Signals must not implicitly aggregate or deduplicate rows | Preserves event-level correctness | Query design discipline | Explicit collapse only |
| 6 | ✅ |  |  | Evidence | Evidence represents row-level causality and must not be interpreted as entity counts | Prevents misinterpretation of diagnostics | Diagnostics layer discipline | Distinguish row vs entity counts |

---

## Principles

- These rules are **never optional**
- These rules are **not decisions** — they are invariants
- These rules apply wherever Signals, Facts, or Evidence exist
- These rules must be enforced by:
  - schema design  
  - pipeline structure  
  - testing  
  - code review discipline  

---

## Summary

This registry ensures:

- signal correctness  
- causal traceability  
- deterministic diagnostics  
- preservation of evaluation grain  

These rules protect the integrity of the diagnostic system.

---

## Input Validation Invariants

These invariants define correctness requirements for input tables.

They are enforced during validation before pipeline execution.

### Scenario Delta (scenario_delta)

- Overrides must apply only to explicitly specified fields
- All unspecified fields must retain their baseline values
- Overrides must resolve to a valid state after application

### Flow Policy (vi_flow_policy)

- Flow policy must not modify structure or assignment data
- Flow policy must only affect resource routing and sourcing
- Flow policy must operate on resolved production outputs

---

### Sales Strategy (`sales_strategy`)

The following invariants must hold for all rows:

- Exactly one of the following must be provided:
  - `allocation_frac`
  - `allocation_units_per_hour`

- Both fields must not be populated simultaneously

- `allocation_frac` must be within [0, 1]

- `allocation_units_per_hour` must be non-negative

---

### Channel Constraints

- If `sales_channel_key` represents Contract:
  - `contract_discount_frac` must be provided

- If `sales_channel_key` represents non-Contract:
  - `contract_discount_frac` must be null or zero

---

### Structural Constraints

- Each row represents a clearing intent at grain:
  - snapshot_key × product_key × quality_level × sales_channel_key

- Multiple rows per product are allowed

- Duplicate rows with identical keys are not allowed

---

### Temporal Normalization

- All allocation quantities must be stored in hourly units

- User-facing daily inputs must be normalized prior to ingestion

## No Routing

The system must not implement:

- routing
- path-based allocation
- priority-based consumption

All consumption must be:

- BOM-driven
- aggregate
- global

All imbalance must be resolved via clearing only.