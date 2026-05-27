# System Architecture

## Purpose

Define how the engine works as a complete system:

- what data it consumes  
- how that data flows  
- where rules are enforced  
- what outputs are produced  

This document is the **single source of truth for understanding system structure and flow**.

---

## Overview

The system is a deterministic transformation engine:

Excel (UI)  
→ CSV (contract boundary)  
→ Engine (Python)  
→ CSV outputs  
→ Excel (presentation)

The engine never reads Excel directly.

---

## System Model

The engine operates as a layered transformation system:

INPUT
(company_snapshot, structure_map, assignment, scenario_delta, flow_policy)
        ↓
VALIDATION
(schema + invariants)
        ↓
SCENARIO RESOLUTION
(baseline + scenario_delta → resolved state)
        ↓
STRUCTURE
(building capacity & topology)
        ↓
ALLOCATION
(slot → product × quality split)
        ↓
FLOW POLICY
(internal routing + sourcing intent)
        ↓
THROUGHPUT
(quantity resolution)
        ↓
ECONOMICS
(value applied to flow)
        ↓
DIAGNOSTICS
(facts → signals → guidance)
        ↓
OUTPUT

---

## Flow Policy

Flow policy defines how produced resources are used internally.

- it controls routing between products
- it defines sourcing behavior (make vs buy)
- it determines priority of consumption

Flow policy does not modify structure, assignment, or production.
It only affects how output is allocated before throughput resolution.

---

## Scenario Resolution

Scenarios are defined as a baseline snapshot combined with a set of deltas.

- scenario_delta defines explicit field-level modifications
- only specified fields are updated
- all other values are inherited from the baseline

This produces a resolved state used for execution.

The pipeline operates only on resolved state and does not distinguish between baseline and scenario inputs.

---

## Data Contract

### Contract Boundary

The engine operates only on CSV files:

```
data/{env}/input/
data/{env}/reference/
data/{env}/output/
```

Rules:

- CSV is the only interface  
- No direct Excel reads  
- All inputs must be explicit and inspectable  
- No implicit or hidden inputs  

---

### Table Surfaces

#### Inputs
- company_snapshot  
- financial_snapshot  
- structure_map  
- slot_product_assignment  
- sales_demand  

#### References
- product_bom  
- market_pricing  

#### System
- system_parameters  

#### Outputs
- diagnostics  
- guidance  
- signal_evidence  

---

### File Rules

- One file per table  
- File name must match table name exactly  
- Headers must match schema exactly  
- No extra or implicit columns  
- Input tables contain no system metadata  

---

## Execution Flow

The engine runs as a single deterministic process:

```
run.py:
    load_contract_inputs()
    → load_schema()
    → validate_table()
    → run_pipeline()
    → write_contract_outputs()
```

---

## Layer Model

### L0 — Raw
- Reads CSV exactly as provided  
- No interpretation  

---

### L1 — Clean
- Trims whitespace  
- Normalizes structure  
- No logical changes  

---

### L2 — Validation
- Applies schema rules  
- Enforces structure and constraints  
- Rejects invalid data  

---

### Pipeline

- Executes all business logic  
- Assumes valid inputs  
- Does not perform cleaning or validation  

---

## Validation Model

### Schema

Defined in:

```
schema/schema.yml
```

Schema:

- defines structure  
- enforces typing and constraints  

Schema does NOT:

- define business logic  
- mutate data  

---

### Validator

- enforces schema rules  
- rejects invalid data  
- guarantees correctness before pipeline execution  

---

## Responsibilities

| Layer | Responsibility |
|------|---------------|
| User (Excel) | provides input values |
| CSV | transports data |
| Schema | defines structure |
| Validator | enforces correctness |
| Pipeline | executes business logic |
| Integration (Excel) | presents outputs |

---

## Observability

Every engine run must report:

- tables processed  
- rows read per table  

Rules:

- the engine must never run silently  
- all behavior must be observable  

---

## Design Principles

- Observed data is authoritative  
- All behavior is explicit  
- No implicit inference or correction  
- Outputs are fully resolved  
- System behavior is deterministic and testable  

---

## Summary

The system is:

- a deterministic transformation engine  
- driven by explicit data contracts  
- executed as a staged pipeline  

It guarantees:

- no hidden logic  
- no silent data mutation  
- full traceability of results  