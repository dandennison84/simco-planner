# SimCo Planner

A deterministic, table-based engine for analyzing and planning Sim Companies businesses.

This system is contract-driven. See `/docs/CONTRACT_SPEC.md` for the structural foundation.
---

## Overview

SimCo Planner allows you to define your company once and answer multiple well-scoped questions without duplicating inputs, recomputing observed reality, or contaminating results across tools.

The system is built around:

- shared, structured inputs
- staged transformations
- question-driven tools

It produces:

- diagnostics (what is happening)
- guidance (what to pay attention to)
- scenarios (what could happen)

---

## Where to go next

If you are new:
→ Start with system structure: /docs/SYSTEM.md

If you want to understand behavior:
→ See requirements and domain rules: /docs/REQUIREMENTS.md

If you are making changes:
→ Follow development process: /docs/PROCESS.md

If you need implementation details:
→ See data contracts: /docs/DATA_CONTRACTS.md  
→ See contract structure: /docs/CONTRACT_SPEC.md

---

## Documentation Index

The system is defined through a set of focused documents. Each has a distinct role and avoids overlap.

### Core System

- `/docs/SYSTEM.md`  
  → Defines system architecture, data flow, and pipeline structure

- `/docs/DATA_CONTRACTS.md`  
  → Defines table meaning, grain, and invariants

- `/docs/CONTRACT_SPEC.md`  
  → Defines contract structure, typing, and validation rules

---

### Behavior & Rules

- `/docs/REQUIREMENTS.md`  
  → Defines all functional requirements and domain rules

- `/docs/RULES.md`  
  → Defines strict invariants (signals, evidence, contract enforcement)

---

### Governance & Evolution

- `/docs/DECISIONS.md`  
  → Records architectural decisions and evolution over time

- `/docs/ROADMAP.md`  
  → Tracks planned future capabilities and system direction

---

### Development

- `/docs/PROCESS.md`  
  → Defines how work is performed (task → implementation → validation)

- `/docs/GIT_WORKFLOW.md`  
  → Defines version control and commit conventions

- `/docs/NAMING_CONVENTIONS.md`  
  → Defines naming standards for tables, fields, and code

- `/docs/TOOLING.md`  
  → Defines development tools and environment setup

---

## System Model

The engine operates as a layered transformation system:

USER INPUT (CSV CONTRACTS)
(company, map_structure, production_plan, clearing_plan, overrides)
        ↓
CONTRACT VALIDATION
(schema + typing + required tables + key constraints)
        ↓
PRODUCTION (FULL CAPACITY)
(units_produced_per_hour)
        ↓
BOM CONSUMPTION
(recursive input demand across all levels)
        ↓
BALANCE
(net = produced - consumed)
        ↓
CLEARING
(resolve all surplus and shortage via channels)
        ↓
ENGINE OUTPUT (FACT TABLES)
(production_intent, product_bom_consumption, balance_plan, clearing_result, allocation_summary)

---

## Core Idea

The engine is not a dashboard or optimizer.

It is a data transformation system that:

- preserves observed truth
- applies explicit rules
- produces deterministic outputs

All behavior is:

- explicit
- testable
- traceable

All structure and validation are defined through explicit contracts.

---

## Tools

The system is used through question-driven tools:

### Map Health
Diagnose the current state of the company  
→ “What is happening right now?”

### VI Planner
Design steady-state production systems  
→ “What should I build?”

### Scenario Runner
Simulate time-based decisions  
→ “What happens if I do this over time?”

Tools are strictly separated and operate on shared engine outputs.

---

## Workflow

Typical usage flow:

Map Health → VI Planner → Scenario Runner

Each step builds on stable, previously computed results.  
No tool recomputes upstream logic.

---

## Data Model

The system operates on a defined set of core data surfaces:

### Inputs

- company_snapshot
- financial_snapshot
- structure_map
- slot_product_assignment

### References

- market_pricing
- product_bom
- system_parameters

### Outputs (Engine Layer)

- production_intent
- product_bom_consumption
- balance_plan
- clearing_result
- clearing_remainder
- allocation_summary

Diagnostics, guidance, and signal_evidence are derived in later layers (not part of the engine output contract).

---

## Architecture

The engine is structured as a staged pipeline:

Input → Staging → Generator → Throughput → Economics → Diagnostics → Optimization → Guidance → Output

Each stage:

- consumes tables
- produces tables
- enforces strict contracts

All tables and validation rules are defined externally via contracts.

→ System structure, pipeline, and layers: /docs/ARCHITECTURE.md

---

## Requirements

System behavior is defined through:

- domain rules (Sim Companies mechanics)
- calculation rules (formulas)
- expected outputs (test scenarios)

All requirements are explicit and testable.

→ System requirements: /docs/REQUIREMENTS.md

---

## Design Principles

- Observed data is authoritative
- No implicit logic or inference
- Grain must always be defined
- Outputs must be fully resolved
- Signals must preserve causal evidence

---

## Development

The project follows:

- structured commit conventions
- table-driven requirements
- CSV-based data contracts

→ Development workflow and contribution rules:
/docs/PROCESS.md

→ Version control and commits:
/docs/GIT_WORKFLOW.md

→ Naming standards:
/docs/NAMING_CONVENTIONS.md

---

## Status

Foundational documentation and architecture are defined.

Next steps:

- finalize and document engine output contract
- align documentation with implemented pipeline
- prepare diagnostics layer

---

## Summary

SimCo Planner is a:

- deterministic analytics engine
- built on explicit data contracts
- designed for correctness, traceability, and modular growth

It answers:

- what is happening
- why it is happening
- what options exist

Without ever replacing observed truth.

## Reference

→ Decision history and architecture evolution:
/docs/DECISIONS.md

→ Engine invariants (advanced):
/docs/RULES.md