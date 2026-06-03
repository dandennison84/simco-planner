# DATA CONTRACTS

## Purpose

Define the data contract surfaces for the SimCo Planner engine.

This document describes:

- input tables
- reference tables
- engine output tables
- table grain
- invariants

The schema (`schema/*.yml`) is the authoritative definition of structure and types.  
This document defines meaning, grain, and invariants.

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

# INPUT TABLES

Defined in: schema/input.yml

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

Defined in: schema/reference.yml

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

# ENGINE OUTPUT TABLES

Defined in: schema/output.yml

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

All diagnostics and guidance must be built on top of these tables.