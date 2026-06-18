# SimCo Planner

A deterministic, table-based engine for analyzing and planning Sim Companies businesses.

This system is contract-driven.  
→ See `/docs/CONTRACT_SPEC.md` for structural foundation.

---

## Overview

SimCo Planner allows you to define your company once and answer multiple well-scoped questions without:

- duplicating inputs  
- recomputing observed reality  
- contaminating results across tools  

The system is built around:

- structured inputs  
- staged transformations  
- question-driven tools  

It produces:

- diagnostics (what is happening)  
- guidance (what to do)  
- scenarios (what could happen)  

---

## Where to go next

If you are new:  
→ `/docs/SYSTEM.md`

If you want behavior:  
→ `/docs/REQUIREMENTS.md`

If you are making changes:  
→ `/docs/PROCESS.md`

If you need structure:  
→ `/docs/DATA_CONTRACTS.md`  
→ `/docs/CONTRACT_SPEC.md`

---

## Documentation Index

### Core System

- `/docs/SYSTEM.md`  
- `/docs/DATA_CONTRACTS.md`  
- `/docs/CONTRACT_SPEC.md`  

---

### Behavior & Rules

- `/docs/REQUIREMENTS.md`  
- `/docs/RULES.md`  

---

### Governance

- `/docs/DECISIONS.md`  
- `/docs/ROADMAP.md`  

---

### Development

- `/docs/PROCESS.md`  
- `/docs/GIT_WORKFLOW.md`  
- `/docs/NAMING_CONVENTIONS.md`  
- `/docs/TOOLING.md`  

---

## System Model

The engine is a deterministic pipeline:

INPUT (CSV CONTRACTS)  
→ VALIDATION  
→ STRUCTURE  
→ PRODUCTION_RESOLUTION  
→ BOM_CONSUMPTION  
→ BALANCE  
→ CLEARING  
→ RETAIL_ALLOCATION  
→ ENGINE OUTPUT  

---

## Core Data Flow

Production:

- computed at full capacity  
- independent of input availability  
- includes abundance effects  

Consumption:

- derived from BOM  
- recursive  
- globally aggregated  

Balance:

net = produced − consumed  

- surplus → clearing (sell / store)  
- shortage → clearing (source externally)  

Clearing:

- resolves all imbalance  
- uses explicit allocation channels  
- no routing or prioritization  

Retail Allocation:

- distributes retail output to buildings  
- respects capacity  
- uses priority ordering  

---

## Engine Outputs

The engine produces fact tables:

- production_intent  
- product_bom_consumption  
- balance_plan  
- clearing_result  
- allocation_summary  
- retail_allocation_result  

Properties:

- deterministic  
- complete  
- non-interpretive  

These tables are the foundation for all tools.

---

## Product Model

All product-level tables use:

(company_key, product_key, building_key, quality_level)

Key concepts:

- production is building-specific  
- all aggregation occurs after slot-level computation  
- no product identity exists without building context  

---

## Core Idea

The system is not:

- a dashboard  
- an optimizer  

It is a transformation engine that:

- preserves observed truth  
- applies explicit rules  
- produces deterministic outputs  

All behavior is:

- explicit  
- testable  
- traceable  

All structure is contract-defined.

---

## Tools

The system is used through tools:

### Map Health
“What is happening?”

### VI Planner
“What should I build?”

### Scenario Runner
“What happens over time?”

Tools:
- consume engine outputs  
- never recompute upstream logic  

---

## Workflow

Typical flow:

Map Health → VI Planner → Scenario Runner  

Each step uses stable outputs from prior steps.

---

## Data Model

### Inputs

- company  
- map_structure  
- production_plan  
- clearing_plan  
- retail_plan  

---

### References

- product  
- product_bom  
- building  
- pricing tables  

---

### Outputs

- production_intent  
- product_bom_consumption  
- balance_plan  
- clearing_result  
- allocation_summary  
- retail_allocation_result  

Derived layers (not engine outputs):

- diagnostics  
- guidance  
- plan_health  

---

## Architecture

The system is staged:

Input  
→ Production  
→ Consumption  
→ Balance  
→ Clearing  
→ Allocation  
→ Output  

Each stage:

- consumes tables  
- produces tables  
- enforces invariants  

All structure is defined externally via contracts.

---

## Design Principles

- observed data is authoritative  
- no implicit logic  
- grain must be explicit  
- outputs must be complete  
- no recomputation across layers  

---

## Development

The project follows:

- contract-first architecture  
- table-driven requirements  
- structured commit workflow  

→ `/docs/PROCESS.md`  
→ `/docs/GIT_WORKFLOW.md`  

---

## Status

Foundation and engine core are established.

Current focus:

- finalize engine outputs  
- align contracts and documentation  
- build diagnostics layer  

---

## Summary

SimCo Planner is a:

- deterministic engine  
- contract-driven system  
- modular analytics framework  

It answers:

- what is happening  
- why it is happening  
- what can be done  

Without altering observed truth.

---

## Reference

→ `/docs/DECISIONS.md`  
→ `/docs/RULES.md`