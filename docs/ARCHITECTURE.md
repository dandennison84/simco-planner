# Engine Architecture

## Overview

The system is a deterministic transformation engine:

Excel (UI)
→ CSV (contract boundary)
→ Engine (Python)
→ CSV outputs
→ Excel (presentation)

The engine does not read Excel directly.


## Contract Boundary

CSV files under `data/{env}/*` are the ONLY interface between UI and the engine.

- No direct Excel reads
- No implicit data sources
- All inputs must be explicit and inspectable


## Data Environments

Runtime:
- data/runtime/input/
- data/runtime/reference/
- data/runtime/output/

Test:
- data/test/input/
- data/test/reference/
- data/test/output/

Test data MUST NOT interfere with runtime data.


## Execution Flow

run.py:
    load_contract_inputs()
    → load_schema()
    → validate_table()
    → run_pipeline()
    → write_contract_outputs()


## Layer Model

### L0 — Raw
- CSV ingestion
- Exact data read from files
- No interpretation

### L1 — Clean
- Trim whitespace (keys and values)
- Normalize shape only
- No logical transformation

### L2 — Validation
- Schema-based checks
- Structure enforcement
- No mutation of meaning

### Pipeline
- Deterministic business logic
- Assumes valid inputs
- No cleaning or validation logic


## Core Principles

- Engine operates only on CSV
- Pipeline never cleans or fixes data
- Validation happens before pipeline
- System behavior must be observable

Every run must report:
- tables processed
- rows read


## Schema System

- Defined in: `schema/schema.yml`
- Applied after CSV ingestion
- Defines structure and constraints

Schema does NOT:
- define business logic
- mutate data
- replace pipeline rules


## Integration Layer

Excel and Power Query:
- act as UI and shaping layer only
- produce canonical CSV tables
- do not contain business logic


## Testing Model

Tests use the same engine path:

tests → data/test/* → engine

This guarantees:
- no divergence between test and runtime
- consistent behavior across environments