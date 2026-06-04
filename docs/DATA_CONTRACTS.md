# DATA CONTRACTS

## Purpose

Define the data contract surfaces for the SimCo Planner engine.

This document describes:

- input tables
- reference tables
- engine output tables
- table grain
- invariants

The contract definitions (`contracts/*.yml`) are the authoritative definition of structure, typing, and validation behavior. 
This document defines meaning, grain, and invariants.

For contract structure, typing, and validation rules, see `CONTRACT_SPEC.md`.

This document defines meaning, grain, and invariants only.

---

## Contract Boundary

The engine contract boundary is:

data/runtime/input/*.csv  
data/runtime/reference/*.csv  
data/runtime/output/*.csv  

Rules:

- CSV is the only contract boundary
- No implicit inputs or outputs
- No hidden state
- All outputs must be fully materialized

---

## Contract Model

All table surfaces are defined through external contract files.

Contracts define:
- table presence
- column structure
- data types
- constraints
- identity keys
- validation behavior

Rules:

- Contracts are the single source of truth for all table structure
- The engine must not hardcode table definitions or validation rules
- All tables must be explicitly defined in contracts before use
- Contract files must be complete (no partial schema definitions)
- Engine logic must not infer structure from CSV data
- Contract files must explicitly declare their type using `kind`

Contract types:

- `kind: table` → defines CSV table structure
- `kind: lookup_mapping` → defines UI lookup behavior

---

## Contract Discovery

The engine must dynamically discover contract definitions.

Rules:

- Contract files must be read from the contracts directory
- Engine must not rely on fixed filenames
- Adding a new contract must not require code changes
- All contract files within a category must be loaded and merged

Categories:

- contracts/input
- contracts/reference
- contracts/output
- contracts/ui
- contracts/internal

---

# INPUT TABLES

Defined in: contracts/input_tables.yml

User-controlled surfaces.

Tables:
- company
- map_structure
- production_plan
- clearing_plan
- override_exchange_prices
- override_retail_prices

---

# REFERENCE TABLES

Defined in: contracts/reference_tables.yml

System-controlled domain surfaces.

Tables:
- building
- building_category
- building_bom
- product
- product_bom
- exchange_prices
- retail_prices
- retail_product_building
- channel
- realm
- economic_role
- economic_phase
- seasons
- system_parameters

---

# UI CONTRACTS

Defined in: contracts/ui_lookups.yml

UI contracts define lookup and validation behavior for Excel surfaces.

Rules:

- UI behavior must be fully contract-driven
- Lookup mappings must not be duplicated in code
- UI contracts do not define engine data structure
- UI contracts must reference reference tables for lookup sources
- UI logic must not modify or reinterpret engine data

---

# ENGINE OUTPUT TABLES

Defined in: contracts/output_tables.yml

These are resolved, deterministic fact tables.  
They are NOT diagnostics or guidance.

---

## production_intent

Grain:
company_key | product_key | quality_level

Fields:
company_key  
product_key  
quality_level  
units_produced_per_hour  

Invariants:
- units_produced_per_hour ≥ 0
- Production is computed at full capacity
- No bottleneck constraints applied

---

## product_bom_consumption

Grain:
company_key | product_key | quality_level

Fields:
company_key  
product_key  
quality_level  
units_consumed_per_hour  

Invariants:
- units_consumed_per_hour ≥ 0
- Consumption derived strictly from BOM
- No routing or priority logic
- Globally aggregated

---

## balance_plan

Grain:
company_key | product_key | quality_level

Fields:
company_key  
product_key  
quality_level  
units_produced_per_hour  
units_consumed_per_hour  
net_units_per_hour  
surplus_units_per_hour  
shortage_units_per_hour  

Invariants:
- net_units_per_hour = produced - consumed
- surplus = max(net, 0)
- shortage = max(-net, 0)
- Exactly one of surplus or shortage is non-zero

---

## clearing_result

Grain:
company_key | product_key | quality_level | priority | channel_key

Fields:
company_key  
product_key  
quality_level  
priority  
channel_key  
direction  
allocated_units_per_hour  

Invariants:
- allocated_units_per_hour ≥ 0
- Direction determines allowed channels
- Allocation applied sequentially by priority
- Allocation operates on remaining quantity

---

## clearing_remainder

Grain:
company_key | product_key | quality_level

Fields:
company_key  
product_key  
quality_level  
direction  
remaining_units_per_hour  

Invariants:
- remaining_units_per_hour ≥ 0
- Represents unresolved imbalance

---

## allocation_summary

Grain:
company_key | product_key | quality_level

Fields:
company_key  
product_key  
quality_level  
total_units_per_hour  
retail_units_per_hour  
non_retail_units_per_hour  
is_retail_capped  

Invariants:
- total ≥ 0
- retail ≥ 0
- non_retail ≥ 0
- retail + non_retail = total

---

# SYSTEM INVARIANTS

Production:
- Production ≥ 0
- Full capacity only

Consumption:
- BOM-driven only
- No routing

Balance:
- net = produced - consumed

Clearing:
- allocated + remainder = abs(net)
- No negative allocations
- Sequential priority logic

Determinism:
- Same inputs → same outputs
- No implicit behavior

Contract Enforcement:
- All tables must conform exactly to contract definitions
- Extra or missing columns must fail validation
- All required fields must be present and valid
- All key and uniqueness constraints must be enforced
- Required/non-empty table semantics must be defined in contracts
- Engine must perform no structural inference or correction

---

# SUMMARY

Pipeline:

INPUT  
→ VALIDATION  
→ STRUCTURE  
→ PRODUCTION_RESOLUTION  
→ BOM_CONSUMPTION  
→ BALANCE  
→ CLEARING  
→ ENGINE OUTPUT  

Outputs represent the complete resolved system state.

All diagnostics and guidance must be built on top of these tables.All diagnostics and guidance must be built on top of these tables engine executes strictly against these contracts.

Contracts define all data structure and validation behavior.  
