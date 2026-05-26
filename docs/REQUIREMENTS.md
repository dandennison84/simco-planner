# Requirements

## Purpose

Define what the system must do, how the domain behaves, and what outputs are expected.

This document captures:
- user intent
- system capabilities
- domain rules
- expected outputs

All requirements must be:
- testable
- explicit
- table-driven


---

## 1. User Stories

Describe why the system exists.

| ID | User | Goal | Reason |
|----|------|------|--------|
| US-001 | Player | Understand company health | Identify issues and risks |
| US-002 | Player | Plan production strategy | Maximize economic outcome |
| US-003 | Player | Simulate scenarios | Evaluate decisions over time |


---

## 2. Use Cases

Each use case represents a question the system must answer.

| ID | Name | Question | Tool |
|----|------|----------|------|
| UC-001 | Map Health | Is my company healthy right now? | Map Health |
| UC-002 | VI Planner | What should I build in steady state? | VI Planner |
| UC-003 | Scenario Runner | What happens if I do X over time? | Scenario Runner |


---

## 3. Functional Requirements

| ID | Requirement | Surface | Grain | Validation |
|----|------------|---------|-------|-----------|
| FR-001 | Inputs must be validated and typed | company_snapshot, financial_snapshot | snapshot_key | Reject invalid rows |
| FR-002 | Assignment must fully define slot usage | slot_product_assignment | slot_key | Split fractions sum to 1 |
| FR-003 | Structure must not encode assignment | structure_map | structure_key + slot_key | No product fields allowed |
| FR-004 | Pricing must be resolved per product + quality | market_pricing | product_key + quality_level | All required rows present |
| FR-005 | Diagnostics must derive only from upstream data | diagnostics | snapshot_key + signal_code | No recomputation |
| FR-006 | Optimization must produce candidate scenarios only | diagnostics | snapshot_key | No mutation of base data |
| FR-007 | Guidance must not prescribe actions | guidance | snapshot_key + signal_code | Signals-only derivation |

---

## 4. Domain Rules (Sim Companies Mechanics)

| ID | Rule | Surface | Grain | Validation |
|----|------|---------|-------|-----------|
| DR-001 | All capacity must be explicitly assigned | slot_product_assignment | slot_key | All slots present |
| DR-002 | Production depends on capacity and modifiers | company_snapshot, structure_map | snapshot_key, slot_key | Deterministic calculation |
| DR-003 | Retail is satisfied before exchange | diagnostics | snapshot_key + product_key | Ordering enforced |
| DR-004 | Bottleneck determines production | diagnostics | snapshot_key + product_key | Output capped |
| DR-005 | Fractional BL must be explicit | slot_product_assignment | slot_key | No implicit rounding |
| DR-006 | Pricing must meet required quality floor | market_pricing | product_key + quality_level | No invalid substitution |
| DR-007 | Transport is a diagnostic signal only | diagnostics | snapshot_key + signal_code | No economic impact |

---

## 5. Calculation Rules (Formulas)

| ID | Calculation | Surface | Grain | Validation |
|----|-------------|---------|-------|-----------|
| CR-001 | Production = capacity × modifiers | diagnostics | snapshot_key + slot_key | Deterministic |
| CR-002 | Sold ≤ Produced | diagnostics | snapshot_key + product_key | Constraint holds |
| CR-003 | Profit = revenue - cost | financial_snapshot | snapshot_key | Reconciliation |
| CR-004 | Cost includes all inputs | diagnostics | snapshot_key + product_key | No omission |
| CR-005 | Allocation sums to 1 | slot_product_assignment | slot_key | Sum = 1 |

---

## 6. Expected Outputs

| ID | Scenario | Surface | Input Condition | Expected Output |
|----|----------|---------|----------------|-----------------|
| EO-001 | Balanced Production | diagnostics | No bottleneck | All capacity utilized |
| EO-002 | Bottleneck | diagnostics | Limited BL | Production capped |
| EO-003 | Overproduction | diagnostics | Produced > demand | Excess unsold |
| EO-004 | Retail Priority | diagnostics | Limited retail | Retail first |
| EO-005 | Invalid Assignment | slot_product_assignment | Missing split | Validation failure |

---

## 7. Constraints

System-wide rules that must always hold.

| ID | Constraint | Description |
|----|-----------|------------|
| C-001 | Determinism | Same input → same output |
| C-002 | No Implicit Logic | All behavior must be explicit |
| C-003 | Grain Integrity | No unintended row expansion |
| C-004 | Separation | Layers must not override upstream results |

---

## 8. Validation Rules

Define how correctness is verified.

| ID | Rule | Method |
|----|------|--------|
| VR-001 | Output matches expected | Table comparison |
| VR-002 | No unit loss | Reconciliation check |
| VR-003 | Assignment complete | Constraint validation |
| VR-004 | Signals deterministic | Repeat evaluation |

---

## 9. Surface Coverage

| Surface | Covered By |
|--------|------------|
| company_snapshot | FR-001, CR-001 |
| financial_snapshot | FR-001, CR-003 |
| structure_map | FR-003, DR-002 |
| slot_product_assignment | FR-002, DR-001, CR-005 |
| market_pricing | FR-004, DR-006 |
| product_bom | DR-002 |
| system_parameters | FR-001 |
| diagnostics | FR-005, DR-003, DR-004, CR-001 |
| guidance | FR-007 |
| signal_evidence | FR-005 |

---

## Summary

Requirements define:
- what the system must do
- how the domain behaves
- what outputs are expected

All requirements must be:
- explicit
- testable
- aligned to system layers