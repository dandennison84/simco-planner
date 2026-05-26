# Data Contracts

## Overview

The engine operates on a fixed set of tables.

Each table is represented as a single CSV file and forms the input/output contract boundary.


## Table Surfaces

### Input Tables

- company_snapshot
- structure_map
- slot_product_assignment
- sales_demand
- financial_snapshot

### Reference Tables

- product_bom
- market_pricing

### System Tables

- system_parameters


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


## File Rules

- One file per table
- File name == table name
- CSV format only
- Headers must match exactly (case + whitespace)
- No implicit columns
- No system metadata columns


## Table Loading Behavior

- Table names are defined in the engine
- Missing files are loaded as empty tables
- Validator determines if empty is acceptable


## Schema Integration (Current State)

- Schema is defined in: schema/schema.yml
- Schema is applied AFTER CSV ingestion
- Schema validates structure only
- Schema does NOT define table existence (yet)


## Responsibilities

User (Excel):
- provides input values only

CSV:
- transport layer

Schema:
- defines structure

Validator:
- enforces rules

Pipeline:
- applies business logic


## Observability

Every engine run must report:

- rows read per table
- total tables processed

The engine must never run silently.