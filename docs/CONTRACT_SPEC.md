# Contract Specification

## Purpose

Defines the canonical structure and format of all contract files.

Covers:
- table contracts  
- lookup contracts  
- typing  
- validation  

Does NOT define:
- business logic  
- pipeline behavior  
- domain rules  

→ See DATA_CONTRACTS.md for meaning and grain.

---

## Principles

- Contracts define structure  
- Engine does not infer schema  
- Contracts must be complete  
- Contracts must be machine-validated  
- Adding contracts requires no engine change  

---

## Contract Kinds

### Table

kind: table

### Lookup

kind: lookup_mapping

---

## Table Contract Format

kind: table  
version: 1  

table: <name>  
surface: <input | reference | output | internal>  
intent: <description>  

presence:  
  required: <true | false>  
  non_empty: <true | false>  

keys:  
  - <field>  

fields:  
  <field>:  
    type: <string | int | float | boolean>  
    required: <true | false>  
    unique: <true | false>  
    constraints:  
      min: <number>  
      max: <number>  

---

## Table Rules

### Top-level rules

- One file defines one table  
- table matches filename  
- surface matches directory  
- keys exist in fields  
- keys must be required  
- no unknown properties  

---

### Field rules

- Must define type and required  
- Types allowed:
  - string  
  - int  
  - float  
  - boolean  
- unique optional  
- constraints only for numeric fields  
- no unknown field properties  

---

## Lookup Format

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

- Defined in contracts only  
- No UI logic in code  
- Must reference valid tables  
- No YAML/code duplication  

---

## Contract Discovery

- Load from /contracts  
- No fixed filenames  
- Load all files  
- No duplicate (surface, table)  

---

## Validation Model

### Stage 1 — Contract validation

- Schema is valid  
- Required fields present  
- Keys consistent  
- Contract complete  

---

### Stage 2 — Data validation

- CSV matches contract  
- Strict typing enforced  
- Constraints enforced  
- Key uniqueness enforced  
- Validation is atomic  

---

## Internal Tables

- Exist only inside engine  
- Still require contracts  
- Same validation rules  
- Not part of external boundary  

---

## Non-Goals

Contracts do NOT define:
- pipeline logic  
- transformations  
- cross-table rules  
- domain rules  
- execution order  

Handled by:
- REQUIREMENTS.md  
- RULES.md  
- engine pipeline  

---

## Summary

Contracts define structure.  
Engine executes against contracts.  
No schema exists outside contracts.