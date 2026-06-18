## System Architecture

### Purpose

Define how the engine operates as a complete system:
- what data it consumes
- how data flows
- where rules are enforced
- what outputs are produced

This document is the authoritative definition of system structure and flow.

---

## Overview

The system is a deterministic transformation engine:

Excel (UI)  
→ CSV (contract boundary)  
→ Engine (Python)  
→ CSV outputs  
→ Excel (presentation)  

Rules:
- Engine does not read Excel directly
- CSV is the only contract boundary

---

## System Model

The engine operates as a staged pipeline:

INPUT  
→ VALIDATION  
→ SCENARIO RESOLUTION  
→ STRUCTURE  
→ PRODUCTION_RESOLUTION  
→ BOM_CONSUMPTION  
→ BALANCE  
→ CLEARING  
→ RETAIL_ALLOCATION  
→ ENGINE OUTPUT  

---

## Product Grain

All product-level tables use:

(company_key, product_key, building_key, quality_level)

Meaning:
- building_key = producing building
- all production and consumption are tied to building-level output

Rules:
- no product joins without building_key
- aggregation occurs after slot-level computation

---

## Engine Output

The engine produces deterministic fact tables:

- production_intent  
- product_bom_consumption  
- balance_plan  
- clearing_result  
- allocation_summary  
- retail_allocation_result  

Properties:

- deterministic  
- complete (all imbalance resolved)  
- non-interpretive (no diagnostics or guidance)

These outputs are the foundation for all downstream layers.

---

## Production

Production is computed at full capacity.

Rules:
- independent of input availability
- no bottleneck constraints
- continuous (fractional rates allowed)
- abundance applied per (slot, product)

Formula (conceptual):

units =
building_level  
× base_output  
× production_speed  
× phase_modifier  
× split_fraction  
× abundance  

---

## Consumption (BOM)

Consumption is derived strictly from the BOM.

Rules:
- recursive across all levels
- globally aggregated
- no routing or prioritization

Definition:

consumed[p] = Σ(parent production × BOM ratio)

---

## Balance

Net production:

net[p] = produced[p] − consumed[p]

Interpretation:

- net > 0 → surplus  
- net < 0 → shortage  

Output:
- balance_plan

---

## Clearing

Clearing resolves all imbalance.

Shortage channels:
- exchange  
- contract  

Surplus channels:
- exchange  
- contract  
- retail  
- storage  

Rules:
- all allocation fractions must be explicitly defined
- fractions must sum to 1
- no implicit allocation
- channels distribute only (do not modify production)

---

## Retail Allocation

Retail allocation distributes cleared retail quantities across buildings.

Rules:
- occurs after clearing
- uses retail_plan priorities
- respects building capacity
- cannot exceed available retail allocation

Output:
- retail_allocation_result

---

## Scenario Resolution

- scenario_delta applies field-level overrides
- unspecified values inherit from baseline

Rules:
- baseline is immutable
- all modifications must be explicit

---

## Data Contract

The engine operates exclusively on CSV:

data/runtime/input/  
data/runtime/reference/  
data/runtime/output/  

Rules:
- CSV is the only interface
- no implicit inputs
- no hidden state

---

## Contract Model

All data surfaces are defined through contract files.

Contracts define:
- table presence
- structure
- types
- constraints
- keys
- validation behavior

Rules:
- contracts are authoritative
- engine must not define schema
- no schema inference is allowed

All contract validation occurs before pipeline execution.

---

## Tables

Inputs:
- company  
- map_structure  
- production_plan  
- clearing_plan  
- retail_plan  

References:
- product  
- product_bom  
- building  
- pricing tables  

Outputs:
- production_intent  
- product_bom_consumption  
- balance_plan  
- clearing_result  
- allocation_summary  
- retail_allocation_result  

---

## Execution Flow

run.py:

load_contracts()  
→ discover_tables()  
→ load_inputs()  
→ validate()  
→ run_pipeline()  
→ write_outputs()  

Rules:
- contracts are dynamically discovered
- all validation occurs before pipeline execution

---

## Design Principles

- no routing logic  
- no bottleneck-constrained production  
- BOM defines all consumption  
- clearing resolves all imbalance  
- deterministic outputs  
- contract-driven structure  
- no implicit behavior  

---

## Summary

The system is a deterministic transformation pipeline that:

- computes production at full capacity  
- derives consumption via BOM  
- resolves imbalance via clearing  
- distributes retail via allocation  

All outputs are:

- fully resolved  
- explicit  
- deterministic  

No upstream logic is recomputed downstream.