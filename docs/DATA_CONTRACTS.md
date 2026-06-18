## DATA CONTRACTS

### Purpose
Define data contract surfaces for the SimCo Planner engine.

Describes:
- input tables
- reference tables
- engine outputs
- grain
- invariants

Contracts (`contracts/*.yml`) are authoritative for:
- structure
- typing
- validation

This doc defines:
- meaning
- grain
- invariants

→ see CONTRACT_SPEC.md

---

# CONTRACT BOUNDARY

data/runtime/input/*.csv  
data/runtime/reference/*.csv  
data/runtime/output/*.csv  

Rules:
- CSV only boundary
- no implicit inputs/outputs
- no hidden state
- outputs fully materialized

---

# CONTRACT MODEL

Contracts define:
- structure
- typing
- keys
- constraints

Rules:
- contracts are source of truth
- engine does not infer schema
- tables must exist in contracts

---

# CONTRACT DISCOVERY

Discovered dynamically from:
- contracts/input
- contracts/reference
- contracts/output

Rules:
- no hardcoded tables
- add tables without code changes

---

# PRODUCT GRAIN

All product-derived tables use:

(company_key, product_key, building_key, quality_level)

Meaning:
- building_key = producing building
- row = product tied to specific building

Rules:
- building_key required
- joins must include building_key
- product identity = (company, product, building, quality)

---

# BUILDING SEMANTICS

Producing building:
- source of production
- used in production_intent, balance_plan, etc.

Retail building:
- used for allocation
- used in retail_plan, retail_allocation_result

Rule:
- do not mix producing vs retail buildings

---

# INPUT TABLES

- company
- map_structure
- production_plan
- clearing_plan
- retail_plan
- override_exchange_prices
- override_retail_prices

---

## retail_plan

Purpose:
- defines retail building types and priority

Behavior:
- lower number = higher priority
- defines building types

Invariants:
- required for retail products
- priority unique per (company, product, quality)
- building_key must be valid

---

# REFERENCE TABLES

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

---

## production_intent

Grain:
(company, product, building, quality)

Fields:
- units_produced_per_hour

Invariants:
- ≥ 0
- full capacity
- abundance applied upstream

---

## product_bom_consumption

Grain:
(company, product, building, quality)

Fields:
- units_consumed_per_hour

Invariants:
- ≥ 0
- BOM-driven
- no routing

---

## balance_plan

Grain:
(company, product, building, quality)

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

## constraint_type

Grain:
(company, product, building, quality)

Values:
- retail_constrained
- supply_constrained
- not_constrained

Meaning:
- retail_constrained → retail cap
- supply_constrained → net < 0
- not_constrained → no issue

---

## clearing_result

Grain:
(company, product, quality, priority, channel)

Fields:
- direction
- allocated_units_per_hour

Invariants:
- ≥ 0
- sequential by priority
- retail capped here

---

## allocation_summary

Grain:
(company, product, quality)

Fields:
- total_units_per_hour
- retail_units_per_hour
- non_retail_units_per_hour
- is_retail_capped

Invariant:
- total = retail + non_retail

---

## retail_allocation_result

Grain:
(company, product, quality, building, priority)

Fields:
- allocated_units_per_hour

Invariants:
- ≥ 0
- sums to retail allocation
- no over-allocation
- respects priority

---

# VIEW: PLAN HEALTH

## view_plan_health

Purpose:
Operational diagnostics per product.

Grain:
(company, product, quality)

Behavior:
- only rows where constraint_type ≠ not_constrained

Outputs:
- required_action
- action_target
- required_change_per_day
- required_change_pct
- required_bl_change

---

## ACTION TRANSLATION

Retail:
required_bl_change =
retail_shortfall ÷ retail_capacity_per_BL

Supply (existing):
required_bl_change =
shortage ÷ (units_produced_per_hour / total_BL)

Supply (no production):
required_bl_change = null

Meaning:
- production not running
- BL cannot be inferred

---

# SYSTEM INVARIANTS

Production:
- ≥ 0
- full capacity

Consumption:
- BOM only

Balance:
- net = produced − consumed

Clearing:
- sequential
- retail capped

Retail allocation:
- distribution only
- reconciles to clearing_result

Determinism:
- same input → same output

Contract:
- no missing fields
- no extra fields
- no implicit logic

---

# PIPELINE

INPUT  
→ VALIDATION  
→ STRUCTURE  
→ PRODUCTION_RESOLUTION  
→ BOM_CONSUMPTION  
→ BALANCE  
→ CLEARING  
→ RETAIL_ALLOCATION  
→ OUTPUT  

---

# SUMMARY

Engine produces:
- product-level flows → clearing_result
- building-level retail flows → retail_allocation_result

All downstream logic:
- consumes outputs only
- does not recompute upstream

Contracts define structure.
Engine executes against contracts.