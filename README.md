# SimCo Planner

A deterministic, table-based engine for analyzing and planning Sim Companies businesses.

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

### Outputs

- diagnostics
- guidance
- signal_evidence

Full definitions are in:

/docs/DATA_CONTRACTS.md

---

## Architecture

The engine is structured as a staged pipeline:

Input → Staging → Generator → Throughput → Economics → Diagnostics → Optimization → Guidance → Output

Each stage:

- consumes tables
- produces tables
- enforces strict contracts

See:

/docs/ARCHITECTURE.md

---

## Requirements

System behavior is defined through:

- domain rules (Sim Companies mechanics)
- calculation rules (formulas)
- expected outputs (test scenarios)

All requirements are explicit and testable.

See:

/docs/REQUIREMENTS.md

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

See:

/docs/GIT_WORKFLOW.md  
/docs/PROCESS.md  
/docs/NAMING_CONVENTIONS.md

---

## Status

Foundational documentation and architecture are defined.

Next steps:

- implement engine skeleton
- define first executable scenarios
- validate core domain rules

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
