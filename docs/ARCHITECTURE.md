# Engine Architecture

## Purpose

The engine is a deterministic, table-based transformation system.

It allows a player to define their company once and answer multiple well-scoped questions without duplicating inputs, recomputing observed reality, or contaminating results across tools.

It:
- consumes structured inputs
- applies staged transformations
- produces structured outputs

It is:
- deterministic
- traceable
- testable
- implementation-agnostic


---

## System Identity

This system is a modular, question-driven analytics and planning engine built on shared inputs and staged transformations.

It is explicitly not:
- a real-time mirror of the game
- a monolithic dashboard
- a prescriptive optimizer
- a solver that overwrites observed truth

Modeled results exist to explain or explore behavior.  
They must never replace or modify observed accounting reality.


---

## Core Principles

- Observed inputs are authoritative and immutable
- All transformations are explicit and staged
- Grain (row meaning) must always be defined
- No implicit expansion or collapse is allowed
- Business logic is centralized and not duplicated
- Outputs must be fully resolved and final-grain
- All behavior must be testable via data

All allocation, transformation, and constraint behavior must be explicitly defined.  
No inference, fallback, or hidden behavior is permitted.


---

## Separation of Concerns

The system enforces strict separation across three axes:

**1. Reality vs Model vs Hypothesis**
- Observed reality is captured once and never redefined
- Modeled explanation derives from observed inputs
- Hypothetical planning operates on explicit assumptions only

**2. Flow vs Value vs Structure**
- Flow (L4) represents quantities
- Value (L5) represents economics attached to flow
- Structure-derived measures (L6) represent stock and configuration

These domains must remain distinct and must not consume each other unless explicitly defined by layer contracts.

**3. Layer Authority**
- Each layer owns a specific transformation responsibility
- No layer may reinterpret upstream results
- No downstream logic may patch upstream errors


---

## System Structure

The system is organized as a staged pipeline:

Input → Staging → Generator → Throughput → Economics → Diagnostics → Optimization → Guidance → Output

Each stage:
- consumes tables
- produces tables
- obeys strict contracts


---

## Layer Model

| Layer | Name | Role |
|------|------|------|
| L0 | Input | Capture observed context and user-defined state |
| L1 | Reference / System | Provide external facts and configurable policies |
| L2 | Staging | Enforce structure, typing, and validity |
| L3 | Generator | Create new rows via controlled expansion |
| L4 | Throughput | Resolve quantities and constraints |
| L5 | Economics | Attach value to resolved quantities |
| L6 | Diagnostics | Describe system state and derive signals. It is a composite surface that integrates outputs from multiple layers (L4–L6) while preserving evaluation grain. |
| L7 | Optimization | Generate and evaluate candidate scenarios under explicit assumptions |
| L8 | Guidance | Summarize diagnostics (and optionally optimization) into attention cues |
| L9 | Output | Expose final, consumable surfaces |
| L10 | Tool | Render outputs for user interaction |

---

## Tool Model

The system is organized around question-driven tools.

Each tool exists to answer a single, well-defined question using the same underlying engine, while respecting strict boundaries on scope and behavior.

Tools do not redefine data.  
They consume stable output surfaces and operate within clearly defined constraints.

---

### Map Health

Map Health answers the question:

“What is the current state of my company?”

It operates strictly on observed snapshot data and provides diagnostics derived from facts and signals. It includes explainable signals and deterministic structural valuation such as replacement cost, build time, and scrap value.

Map Health does not perform:
- optimization
- time-based simulation
- prescriptive decision-making

All structural valuation is descriptive only. It exists to explain the system state and must not alter economic calculations or recommended actions.

---

### VI Planner

VI Planner answers the question:

“What should my company look like in steady state?”

It operates in a hypothetical, steady-state context under explicitly defined assumptions. It uses the same transformation engine but applies modeled conditions rather than observed ones.

VI Planner does not perform:
- reconciliation to observed results
- time sequencing or simulation

All planner-specific behavior must be explicit. No assumptions may be inferred from observed data unless defined as part of the planning context.

---

### Scenario Runner

Scenario Runner answers the question:

“What happens over time if I take specific actions?”

It operates as a time-segmented execution model. It introduces sequencing, transitions, and events such as downtime, upgrades, and state changes.

Scenario Runner does not assume steady-state conditions.  
Temporal behavior is isolated by design and must not contaminate steady-state calculations.

---

## Tool Separation

Tools are strictly separated by intent:

- Map Health → diagnosis of current state
- VI Planner → static hypothetical planning

---

## Tool Workflow

The system operates through question-driven tools:

- Map Health → “What is happening now?”
- VI Planner → “What should steady state look like?”
- Scenario Runner → “What happens over time if I act?”

Tools operate sequentially:

Map Health → VI Planner → Scenario Runner

Each tool:
- consumes stable output surfaces
- does not recompute upstream logic
- operates only within its defined scope


---

## Execution Model

- Execution is deterministic for identical inputs
- Each stage operates independently
- No stage may reinterpret upstream results
- No stage may modify upstream data
- All transformations must be explicit

Components that emit more rows than they receive are generators.  
All generators must explicitly declare their expansion behavior and own their output schema.


---

## Data Contracts

### Inputs

- Defined as structured tables
- Must be explicit and complete
- Must not be inferred or reconstructed

### Outputs

- Represent final, resolved results
- Must not require downstream interpretation
- Serve as the system interface boundary


---

## Diagnostics Principles

Diagnostics are observational and explanatory only.

- Derived strictly from prior layers
- Must not recompute upstream logic
- Must preserve full evaluation grain
- Must preserve causal identity through Evidence

Aggregation must not destroy causal identity.  
All diagnostic outputs must retain traceability to their originating rows.


---

## Optimization Principles

Optimization is optional and explicitly invoked.

- Produces candidate scenarios only
- Must not alter observed truth
- Must not run implicitly
- Must not replace user decision-making

It answers:
“What options exist under defined constraints?”


---

## Guidance Principles

Guidance synthesizes signals into attention.

- Non-prescriptive
- Signals-based only
- Does not optimize or decide

It answers:
“What should I pay attention to?”


---

## Mode and Channel

- Mode determines flow behavior and constraint resolution
- Channel represents projection or distribution of resolved flow

Channels do not drive flow.  
They only describe how resolved flow is expressed.


---

## Testing Model

Testing is table-driven.

- Inputs are structured tables
- Expected outputs are structured tables
- Each row or group represents a scenario
- Validation compares actual vs expected outputs

Testing must:
- cover individual transformations
- cover full pipeline behavior
- enforce invariants and rules


---

## Implementation Independence

The architecture defines:

- data behavior
- transformation rules
- invariants
- contracts

It does not define:

- programming language
- execution environment
- storage mechanism
- tooling

The system must be implementable in any environment without changing its behavior.


---

## Summary

This system is:

- a structured data transformation engine
- governed by layer contracts and invariants
- driven by question-based tools
- designed for explicit, traceable, and deterministic analysis
- independent of implementation technology