# Requirements Ledger

## Purpose

Captures all functional, structural, and behavioral requirements of the system.

This is the authoritative source for:
- system behavior
- invariants
- domain rules
- constraints

Rules:
- append-only (do not delete)
- mark inactive instead of removing
- each row is atomic and testable

---

# CORE SYSTEM MODEL

The engine must:

- compute production at full capacity
- compute consumption via BOM explosion
- compute net balance:
  net = produced − consumed
- resolve all imbalance via clearing

Rules:
- no routing
- no prioritization in consumption
- no bottleneck-constrained production

---

# REQUIREMENTS TABLE

| ID | Active | Requirement | Type | Scope | Notes |
|----|--------|-------------|------|-------|-------|

REQ-001 | TRUE | Engine must execute all companies in a single run | Functional | Engine | Required for comparison across scenarios

REQ-002 | TRUE | System must operate deterministically | Invariant | Engine | Same input → same output

REQ-003 | TRUE | System must operate only on explicit inputs | Constraint | Engine | No implicit defaults

REQ-004 | TRUE | All inputs must be validated before execution | Validation | Engine | Fail fast

REQ-005 | TRUE | Contracts define all table structure | Constraint | Contracts | No schema in code

REQ-006 | TRUE | Engine must not infer or correct invalid inputs | Constraint | Engine | Reject only

REQ-007 | TRUE | Production must be computed at full capacity | Functional | Production | No internal constraints

REQ-008 | TRUE | Production must be independent of input availability | Domain Rule | Production | Shortages resolved in clearing

REQ-009 | TRUE | Production must be continuous (not integer constrained) | Domain Rule | Production | Fractional allowed

REQ-010 | TRUE | Production must include abundance as an output modifier | Domain Rule | Production | Applied per (slot, product)

REQ-011 | TRUE | Consumption must be computed via full BOM explosion | Functional | Production | Recursive

REQ-012 | TRUE | BOM graph must be acyclic | Validation | Production | No infinite recursion

REQ-013 | TRUE | Consumption must be globally aggregated | Constraint | Engine | No routing

REQ-014 | TRUE | System must compute net per product × quality × building | Functional | Engine | Uses product grain

REQ-015 | TRUE | All product tables must include building_key | Invariant | Data Model | Required for correctness

REQ-016 | TRUE | Product identity must include building_key | Invariant | Data Model | (company, product, building, quality)

REQ-017 | TRUE | System must produce balance_plan | Functional | Output | Surplus + shortage

REQ-018 | TRUE | Clearing must resolve all imbalance | Functional | Clearing | No partial resolution

REQ-019 | TRUE | Clearing + remainder must equal absolute imbalance | Invariant | Clearing | Conservation

REQ-020 | TRUE | No routing logic is allowed anywhere in the system | Constraint | Engine | Hard invariant

REQ-021 | TRUE | Clearing must distribute via explicit channels only | Domain Rule | Clearing | No implicit behavior

REQ-022 | TRUE | Allocation fractions must sum to 1 per product | Invariant | Clearing | Enforced

REQ-023 | TRUE | Retail allocation must be downstream of clearing | Domain Rule | Retail | No demand generation

REQ-024 | TRUE | Retail allocation must respect building capacity | Invariant | Retail | No over-allocation

REQ-025 | TRUE | Output tables must reflect full resolved state | Invariant | Output | No partial outputs

REQ-026 | TRUE | Output tables must not be empty if inputs imply results | Validation | Output | Except valid no-op

REQ-027 | TRUE | System must fail if required data relationships are missing | Validation | Engine | No silent failure

REQ-028 | TRUE | All structural validation must occur before pipeline | Constraint | Engine | Single validation pass

REQ-029 | TRUE | Each stage must enforce behavioral invariants | Invariant | Engine | No downstream correction

REQ-030 | TRUE | No stage may modify upstream results | Constraint | Engine | No recomputation

REQ-031 | TRUE | Channels must not modify production quantities | Constraint | Clearing | Distribution only

REQ-032 | TRUE | Surplus must be fully dispatched | Domain Rule | Clearing | No leftover

REQ-033 | TRUE | Shortage must be externally sourced | Domain Rule | Clearing | Exchange + contract

REQ-034 | TRUE | Transport must be modeled as economic input only | Domain Rule | Economics | Not capacity constraint

REQ-035 | TRUE | Prices must be defined per product × quality | Domain Rule | Pricing | Required for economics

REQ-036 | TRUE | System must support scenario evaluation | Functional | Engine | No mutation of baseline

---

# PLAN HEALTH REQUIREMENTS

REQ-100 | TRUE | System must generate plan_health view | Functional | Diagnostics | Derived layer

REQ-101 | TRUE | plan_health must include only abnormal rows | Invariant | Diagnostics | constraint_type ≠ not_constrained

REQ-102 | TRUE | plan_health must compute required_bl_change | Functional | Diagnostics | Action translation

REQ-103 | TRUE | BL change must be derived from observed production | Domain Rule | Diagnostics | No inference when absent

REQ-104 | TRUE | supply constraint without production must return null BL | Invariant | Diagnostics | No estimation allowed

REQ-105 | TRUE | plan_health must not recompute engine outputs | Constraint | Diagnostics | Pure interpretation

---

# SYSTEM CONSTRAINTS

- no routing  
- no implicit defaults  
- no hidden behavior  
- no partial allocation  
- no data mutation across stages  

---

# SUMMARY

System behavior is defined by:

- full-capacity production  
- global BOM consumption  
- deterministic balance  
- clearing-based resolution  

All outputs must be:

- explicit  
- deterministic  
- fully resolved  

This ledger is the authoritative source of system behavior.