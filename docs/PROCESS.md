# Development Process

## Purpose

Define how work moves from idea → implementation → validation.

---

## Workflow

1. Define problem
2. Add or update decision (DECISIONS.md)
3. Define or update architecture if needed
4. Add task (TASKS.md)
5. Implement change
6. Add tests (where applicable)
7. Commit using structured message
8. Validate output

---

## Rules

- No implementation without a defined task
- No task without clear scope
- No logic without testability
- No changes without commit traceability

---

## Task Discipline

- Tasks must be:
  - small
  - isolated
  - testable

- Avoid:
  - multi-layer changes in one task
  - ambiguous task definitions

---

## Decision Discipline

- Add a decision when:
  - architecture changes
  - tooling changes
  - rules are introduced

- Do not add decisions for:
  - minor refactors
  - trivial fixes

---

## Layer Discipline

Before any work:

- Identify layer
- Identify grain
- Identify row behavior (preserve / expand / collapse)

---

## Validation

All changes must be validated by:

- inspecting outputs
- ensuring invariants hold
- confirming no unintended grain changes

---

## Summary

Process enforces:
- discipline
- traceability
- correctness

Work must flow through defined steps.