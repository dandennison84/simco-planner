# Tooling Specification

## Purpose

Define the tools used in the system and why they were selected.

This document records tool decisions only.
It does not define architecture or behavior.


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
| Test Data | Format | Structured tables (CSV) | Define test inputs and expected outputs |
| Data Contract | Format | Flat files (CSV) | Engine input/output boundary |
| Integration | Data Loader | Thin ingestion layer | Load outputs into UI |
| UI | Interface | Spreadsheet application | Final user-facing interface |


---

## Tooling Principles

- Tools must not define system behavior
- All behavior must be expressed in data and transformations
- Tooling must support deterministic execution
- Tooling must enable testing and iteration
- Tooling must not introduce hidden logic
- Tooling must be replaceable without changing system behavior


---

## Selection Rationale

| Concern | Requirement | Resolution |
|--------|------------|-----------|
| Development Speed | Fast iteration cycle | Use local execution environment |
| Testability | Structured validation | Use programmable testing system |
| Transparency | Inspectable state | Use flat file data contracts |
| Flexibility | Avoid tool lock-in | Keep implementation-agnostic design |
| Accessibility | User-friendly interface | Use spreadsheet UI |
| Maintainability | Clear separation of concerns | Centralize logic in engine |


---

## Non-Goals

- Tools do not define business rules
- UI does not compute logic
- Data loaders do not transform or interpret results
- Testing tools do not define expected behavior


---

## Summary

The tooling stack supports:

- deterministic execution
- structured testing
- clear separation of concerns
- implementation independence

All system behavior is defined outside of tools.