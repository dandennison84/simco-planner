# Contract Specification

## Purpose

Defines the canonical structure and format of all contract files.

This document is the authoritative specification for:

- table contracts
- UI lookup contracts
- contract typing
- contract validation shape

This document does NOT define:

- business logic
- pipeline behavior
- domain rules

For table meaning, grain, and invariants, see `DATA_CONTRACTS.md`.

This document defines structure and validation only.

---

## Contract Principles

- Contracts are the single source of truth for structure
- Engine must not define or infer schema
- Contracts must be complete and explicit
- Contracts must be machine-validated
- Adding a contract must not require engine changes

---

## Contract Kinds

### Table Contracts

Used for:

- input tables
- reference tables
- output tables
- internal tables

Example:

    kind: table

---

### Lookup Mapping Contracts

Used for:

- UI lookup behavior
- Excel validation rules

Example:

    kind: lookup_mapping

---

## Table Contract Format

Canonical structure:

    kind: table
    version: 1

    table: <name>
    surface: <input|reference|output|internal>
    intent: <description>

    presence:
      required: <true|false>
      non_empty: <true|false>

    keys:
      - <field>

    fields:
      <field>:
        type: <string|int|float|boolean>
        required: <true|false>
        unique: <true|false>        # optional (default = false)
        constraints:
          min: <number>            # optional
          max: <number>            # optional

---

## Table Contract Rules

### Top-level rules

- One contract file defines exactly one table
- `table` must match filename (without extension)
- `surface` must match directory placement
- `keys` must not be empty for engine tables
- All keys must:
  - exist in `fields`
  - have `required: true`
- Unknown top-level properties are not allowed

---

### Field rules

- Every field must define:
  - `type`
  - `required`
- Allowed types:
  - string
  - int
  - float
  - boolean
- `unique` is optional and defaults to false
- `constraints`:
  - only valid for numeric types
  - supports `min` and `max`
- Unknown field properties are not allowed

---

## Lookup Mapping Format

    kind: lookup_mapping
    version: 1
    intent: <description>

    lookups:
      - ui_table: <name>
        ui_column: <name>

        ref_table: <name>
        ref_key_field: <name>
        ref_label_field: <name>

        excel:
          range_name: <name>
          sheet_name: <name>
          table_name: <name>

---

## Lookup Rules

- All lookup mappings must be defined in contracts
- UI logic must not be hardcoded
- Lookup must reference valid reference tables
- All lookup fields must be explicitly declared
- No duplication between YAML and code

---

## Contract Discovery

- All contracts are located under `/contracts`
- Contracts must be discovered dynamically
- Engine must not rely on fixed filenames
- All contracts within a directory must be loaded
- Duplicate `(surface, table)` pairs are not allowed

---

## Validation Model

Validation occurs in two stages:

### 1. Contract Validation

- schema structure is valid
- required fields are present
- keys and fields are consistent
- contract is complete

### 2. Data Validation

- CSV rows validated against contract
- strict typing enforced
- constraints enforced
- key uniqueness enforced
- failure is atomic (no partial validity)

---

## Non-Goals

Contracts do NOT define:

- pipeline behavior
- transformation logic
- cross-table rules
- domain invariants
- execution order

These belong to:

- REQUIREMENTS.md
- RULES.md
- pipeline implementation

---

## Summary

Contracts define structure and validation.

Engine executes against contracts.

No structure exists outside contracts.