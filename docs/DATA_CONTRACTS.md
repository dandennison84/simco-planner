## DATA CONTRACTS

### Purpose

Define the data contract surfaces for the SimCo Planner engine.

This document describes:
- input tables
- reference tables
- engine output tables
- table grain
- invariants

The contract definitions (contracts/*.yml) are the authoritative definition of structure, typing, and validation behavior.

This document defines meaning, grain, and invariants only.

For contract structure:
→ see CONTRACT_SPEC.md

---

# Contract Boundary

The engine contract boundary is:

data/runtime/input/*.csv  
data/runtime/reference/*.csv  
data/runtime/output/*.csv  

### Rules

- CSV is the only contract boundary
- No implicit inputs or outputs
- No hidden state
- All outputs must be fully materialized

---

# Contract Model

All table surfaces are defined through external contract files.

Contracts define:
- structure
- typing
- keys
- constraints

Rules:

- Contracts are the single source of truth
- Engine must not infer schema
- All tables must exist in contracts before use

---

# Contract Discovery

Contracts are dynamically discovered from:

- contracts/input
- contracts/reference
- contracts/output

Rules:

- No hardcoded table definitions
- Adding a contract does not require code changes

---

# INPUT TABLES

User-controlled surfaces.

### Tables

- company
- map_structure
- production_plan
- clearing_plan
- retail_plan
- override_exchange_prices
- override_retail_prices

---

## retail_plan

### Purpose

Defines which retail building types are used for each product and in what priority order.

### Grain

company_key | product_key | quality_level | building_key

### Behavior

- Lower priority number executes first
- Defines building *types*, not specific instances
- Drives downstream retail allocation

### Invariants

- Must exist for any product routed to Retail
- Priorities must be unique per (company, product, quality)
- building_key must exist on the map
- building_key must be valid for product

---

# REFERENCE TABLES

System-controlled domain surfaces.

### Tables

- building
- building_category
- building_bom
- product
- product_bom
- exchange_prices
- retail_prices
- retail_product_building
- retail_quality_model
- retail_phase_multiplier
- channel
- realm
- economic_role
- economic_phase
- seasons
- system_parameters

---

# ENGINE OUTPUT TABLES

Resolved, deterministic fact tables.

---

## production_intent

Grain:
company_key | product_key | quality_level

Fields:
- units_produced_per_hour

Invariants:
- ≥ 0
- Full capacity only

---

## product_bom_consumption

Grain:
company_key | product_key | quality_level

Fields:
- units_consumed_per_hour

Invariants:
- ≥ 0
- BOM-derived only
- No routing

---

## balance_plan

Grain:
company_key | product_key | quality_level

Fields:
- units_produced_per_hour
- units_consumed_per_hour
- net_units_per_hour
- surplus_units_per_hour
- shortage_units_per_hour

Invariants:
- net = produced − consumed
- surplus = max(net, 0)
- shortage = max(-net, 0)

---

## clearing_result

Grain:
company_key | product_key | quality_level | priority | channel_key

Meaning:
Product-level routing across channels.

Fields:
- direction
- allocated_units_per_hour

Invariants:
- allocated ≥ 0
- Sequential by priority
- Uses remaining quantity
- Retail is capped here, not distributed

---

## allocation_summary

Grain:
company_key | product_key | quality_level

Fields:
- total_units_per_hour
- retail_units_per_hour
- non_retail_units_per_hour
- is_retail_capped

Invariants:
- retail + non_retail = total

---

## retail_allocation_result

Grain:
company_key | product_key | quality_level | building_key | priority

Meaning:
Building-level allocation of Retail channel output.

Fields:
- allocated_units_per_hour

Behavior:
- Distributes cleared retail demand
- Uses retail_plan priority cascade
- Applies building capacity constraints

Invariants:
- allocated ≥ 0
- Sum(building allocations) = clearing_result retail
- No over-allocation
- Honors priority order

---

# SYSTEM INVARIANTS

## Production
- ≥ 0
- Full capacity only

## Consumption
- Strictly BOM-driven

## Balance
- net = produced − consumed

## Clearing
- allocated + remainder = abs(net)
- Sequential by priority

## Retail Allocation
- Operates only on Retail channel
- Distributes — does not calculate demand
- Fully reconciles to clearing_result

## Determinism
- Same inputs → same outputs

## Contract Enforcement
- No missing fields
- No extra fields
- No implicit behavior

---

# PIPELINE

INPUT  
→ VALIDATION  
→ STRUCTURE  
→ PRODUCTION_RESOLUTION  
→ BOM_CONSUMPTION  
→ BALANCE  
→ CLEARING (product-level routing + retail capacity cap)  
→ RETAIL_ALLOCATION (building-level distribution)  
→ OUTPUT  

---

# SUMMARY

The engine produces:

- product-level flows (clearing_result)
- building-level retail flows (retail_allocation_result)

All downstream logic must build on these outputs.

Contracts define all structure.  
The engine executes strictly against contracts.