# Requirements

## Purpose

Define what the system must do, how the domain behaves, and what outputs are expected.

This document captures:

- user intent  
- system capabilities  
- domain behavior  
- expected outputs  

All requirements must be:

- explicit  
- testable  
- aligned to system structure  

---

## 1. User Stories

| ID | User | Goal | Reason |
|----|------|------|--------|
| US-001 | Player | Understand company health | Identify issues and risks |
| US-002 | Player | Plan production strategy | Maximize economic outcome |
| US-003 | Player | Simulate scenarios | Evaluate decisions over time |

---

## 2. Use Cases

| ID | Name | Question | Tool |
|----|------|----------|------|
| UC-001 | Map Health | Is my company healthy right now? | Map Health |
| UC-002 | VI Planner | What should I build in steady state? | VI Planner |
| UC-003 | Scenario Runner | What happens if I do X over time? | Scenario Runner |

---

## 3. Core System Requirements

The system must:

- accept structured, valid input data  
- require complete and explicit assignment  
- keep structure independent from assignment  
- resolve pricing per product and quality  
- produce diagnostics and guidance based on system state  
- generate hypothetical scenarios without altering observed data  

---

## 4. Domain Rules (Sim Companies Mechanics)

The engine models the game using deterministic rules.

### Production and Capacity

- Production depends on capacity and modifiers  
- Bottlenecks limit total output  
- Fractional BL must be explicitly represented  

---

### Allocation and Flow

- Assignment defines how capacity is used  
- Production is constrained by system limits  
- Output must remain consistent with available capacity  

---

### Sales and Channels

- Retail is satisfied before exchange  
- Channels distribute output, not produce it  
- Transport represents system pressure, not cost  

---

### Pricing and Inputs

- Pricing is resolved per product and quality level  
- Inputs must meet required quality thresholds  
- All inputs must be explicitly defined  

---

## 5. Expected Outputs

| ID | Scenario | Condition | Expected Result |
|----|----------|----------|-----------------|
| EO-001 | Balanced Production | No bottleneck | All capacity utilized |
| EO-002 | Bottleneck | Limited BL | Production constrained |
| EO-003 | Overproduction | Produced > demand | Excess unsold |
| EO-004 | Retail Priority | Limited retail capacity | Retail satisfied first |
| EO-005 | Invalid Assignment | Missing or incomplete splits | Validation failure |

---

## 6. System Constraints

The system must:

- behave deterministically (same input → same output)  
- operate only on explicit inputs  
- preserve structural consistency across all layers  

---

## 7. Validation Requirements

Validation must ensure:

- inputs conform to schema  
- invalid data is rejected before execution  
- assignment completeness is enforced  
- outputs are internally consistent  

---

## 8. Surface Coverage

| Surface | Role |
|--------|------|
| company_snapshot | observed company state |
| financial_snapshot | observed financial results |
| structure_map | building layout and capacity |
| slot_product_assignment | capacity allocation |
| market_pricing | pricing data |
| product_bom | input relationships |
| system_parameters | configuration |
| diagnostics | system outputs |
| guidance | interpretation layer |
| signal_evidence | diagnostic trace |

---

## Summary

Requirements define:

- what the system must do  
- how the domain behaves  
- what outputs must be produced  

All behavior must be:

- explicit  
- testable  
- deterministic  