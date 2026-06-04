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
| 7 | ✅ |  |  | Contracts | Engine must not define or infer table structure | Prevents drift between contracts and runtime behavior | Contract-first architecture enforcement | All structure comes from contracts |
| 8 | ✅ |  |  | Contracts | Engine must not hardcode table presence or requiredness | Enables adding new tables without code changes | Contract metadata enforcement | Replaces hardcoded checks in run.py |
| 9 | ✅ |  |  | Contracts | All table validation behavior must be derived from contracts | Prevents duplication of validation logic | Schema-driven validation layer | Includes required/non-empty semantics |
| 10 | ✅ |  |  | Contracts | Contract definitions must be complete and self-sufficient | Partial schema definitions create ambiguity and require defensive logic | Contract validation discipline | Fields, types, constraints, keys all required |
| 11 | ✅ |  |  | Contracts | Contract files must be explicitly typed | Prevents ambiguous parsing and interpretation | Contract parser enforcement | Uses `kind: table`, `kind: lookup_mapping` |
| 12 | ✅ |  |  | Contracts | Engine must dynamically discover contract definitions | Prevents static schema loading and enables extensibility | Contract discovery logic | No reliance on fixed filenames |
| 13 | ✅ |  |  | Tooling | UI behavior must be fully derived from contract definitions | Prevents duplication between YAML and code | Template builder design | Eliminates hardcoded LOOKUPS |

---

## Principles

- These rules are **never optional**
- These rules are **not decisions** — they are invariants
- These rules apply wherever Signals, Facts, or Evidence exist
- Contract enforcement must be systemic and cannot rely on implementation discipline alone
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

---

## Contract Invariants

The following invariants govern contract-driven behavior:

### Structure Ownership
- All table structure must be defined in contract files
- Engine must not infer structure from data
- Engine must not define schema internally

### Validation Ownership
- All structural validation rules must originate from contracts
- Engine must not duplicate validation logic present in contracts
- Required/non-empty semantics must be defined in contract metadata

### Discovery
- All contract definitions must be dynamically discovered
- Engine must not depend on fixed schema filenames
- Adding new contract files must not require engine changes

### Completeness
- Contract definitions must be complete
- All fields must have explicit types
- All keys must reference valid fields
- No partial or implicit schema definitions allowed

### Separation of Concerns
- Contracts define structure and validation
- Engine executes transformations only
- Tooling (UI) derives behavior from contracts, not code