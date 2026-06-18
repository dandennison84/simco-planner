# Tooling Specification

## Purpose

Define the tools used in the system and why they are selected.

This document records tooling decisions only.

It does NOT define:
- system behavior
- business logic
- pipeline structure

---

## Tooling Stack

| Layer | Tool Type | Selection | Role |
|------|-----------|----------|------|
| Development | Editor | VS Code | Primary development interface |
| Version Control | VCS | Git | Track changes and history |
| Repository | Host | GitHub (or equivalent) | System of record |
| Execution | Runtime | General-purpose scripting runtime | Execute engine logic |
| Environment | Isolation | Project-level environments | Reproducibility and dependency control |
| Testing | Framework | Programmable test framework | Execute test suites |
| Test Data | Format | CSV tables | Define test inputs and expected outputs |
| Data Contract | Format | CSV files | Engine input/output boundary |
| Integration | Data Loader | Thin ingestion layer | Load outputs into UI |
| UI | Interface | Spreadsheet application | User interaction layer |

---

## Tooling Principles

- Tools must not define system behavior  
- All behavior must be expressed in data and transformations  
- Tooling must support deterministic execution  
- Tooling must enable testing and iteration  
- Tooling must not introduce hidden logic  
- Tooling must be replaceable without affecting system behavior  

---

## Selection Rationale

| Concern | Requirement | Resolution |
|--------|------------|-----------|
| Development Speed | Fast iteration | Local execution environment |
| Testability | Structured validation | Programmable testing framework |
| Transparency | Inspectable state | CSV contract boundary |
| Flexibility | Avoid tool lock-in | Implementation-agnostic design |
| Accessibility | User-friendly interface | Spreadsheet UI |
| Maintainability | Separation of concerns | Centralize logic in engine |

---

## Integration Rules

- UI must not compute logic  
- UI must only present inputs and outputs  
- Data loaders must not transform data  
- Data loaders must only move data across the boundary  

---

## Non-Goals

- Tools do not define business rules  
- UI does not compute logic  
- Data loaders do not interpret results  
- Testing tools do not define expected behavior  

---

## Summary

The tooling stack supports:

- deterministic execution  
- structured testing  
- separation of concerns  
- implementation independence  

All system behavior is defined outside tooling.