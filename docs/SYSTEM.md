## System Architecture

### Purpose

Define how the engine works as a complete system:
- what data it consumes
- how that data flows
- where rules are enforced
- what outputs are produced

This document is the single source of truth for understanding system structure and flow.

---

### Overview

The system is a deterministic transformation engine:

Excel (UI)
→ CSV (contract boundary)
→ Engine (Python)
→ CSV outputs
→ Excel (presentation)

The engine never reads Excel directly.

---

### System Model

The engine operates as a layered transformation system:

INPUT
→ VALIDATION
→ SCENARIO RESOLUTION
→ STRUCTURE
→ PRODUCTION_RESOLUTION
→ BOM_CONSUMPTION
→ BALANCE
→ CLEARING
→ ENGINE OUTPUT

---

### Engine Output (L5)

The engine produces fully resolved fact tables:

- production_intent
- product_bom_consumption
- balance_plan
- clearing_result
- clearing_remainder
- allocation_summary

These outputs are:

- deterministic
+ complete (no unresolved imbalance; all imbalance resolved)
- non-interpretive (no diagnostics or guidance)

They serve as the foundation for all downstream tools.

---

### Consumption & Clearing

Consumption and clearing define how production results propagate and resolve.

Consumption:
- derived strictly from BOM
- no routing or priority logic
- global aggregation

consumed[p] = sum(parent production × BOM ratio)

Balance:
net[p] = produced[p] - consumed[p]

net > 0 → surplus  
net < 0 → shortage  

Clearing:

Shortage:
- exchange %
- contract %

Surplus:
- exchange %
- contract %
- retail %
- storage %

All allocations must sum to 1.

- all allocation fractions must be explicitly defined
- no defaults or implicit distribution allowed

---

### Scenario Resolution

- scenario_delta defines explicit field-level modifications
- unspecified fields inherit from baseline

---

### Data Contract

The engine operates only on CSV:

data/{env}/input/
data/{env}/reference/
data/{env}/output/

Rules:
- CSV only
- no implicit inputs

---

### Tables

Inputs:
- company_snapshot
- financial_snapshot
- structure_map
- slot_product_assignment

References:
- product_bom
- market_pricing

Outputs:
- production_intent
- product_bom_consumption
- balance_plan
- clearing_result
- clearing_remainder
- allocation_summary

---

### Execution Flow

run.py:

load_contract_inputs()
→ load_schema()
→ validate_table()
→ run_pipeline()
→ write_contract_outputs()

---

### Design Principles

- no routing logic
- no priority logic
- BOM is authoritative for consumption
- all imbalance resolved via clearing
- deterministic and testable