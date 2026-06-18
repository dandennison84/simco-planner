# Development Process

## Purpose

Define how work progresses from idea → implementation → validation.

---

## Workflow

1. Define problem
2. Add or update decision (DECISIONS.md)
3. Update architecture if required
4. Update or create contract definitions (if structural change)
5. Add task (TASKS.md)
6. Implement change
7. Add tests (where applicable)
8. Commit using structured message
9. Validate output

---

## Rules

- No implementation without a defined task
- No task without clear scope
- No logic without testability
- No changes without commit traceability
- No structure defined in engine code
- No validation rules hardcoded if definable in contracts
- No contract duplication across YAML and Python

---

## Task Discipline

Tasks must be:
- small
- isolated
- testable

Avoid:
- multi-layer changes in one task
- ambiguous task definitions

---

## Decision Discipline

Add a decision when:
- architecture changes
- tooling changes
- rules are introduced

Do NOT add decisions for:
- minor refactors
- trivial fixes

---

## Contract Change Rules

Update contracts when:
- adding a new table
- changing field structure
- changing validation rules
- introducing required/non-empty semantics
- adding UI lookup behavior

Do NOT change engine code for:
- new tables of existing type
- adding fields within existing contracts (structure only)

Rule:
- contract changes must precede engine changes

---

## Layer Discipline

Before any work:

- Identify layer
- Identify grain
- Identify row behavior:
  - preserve
  - expand
  - collapse

---

## Contract Discipline

All structural changes must be contract-first.

Rules:

- No new tables without a contract
- No schema defined in engine code
- All structure defined in `/contracts`
- Contract updates must precede engine logic changes
- Contract metadata must define:
  - table presence
  - required / non-empty semantics
  - field structure and typing

Workflow:

1. Modify contract
2. Validate contract correctness
3. Update engine only if behavior requires it

Goal:

- Contracts define structure
- Engine executes against contracts

---

## Validation

All changes must be validated by:

- validating contract correctness
- inspecting outputs
- ensuring invariants hold
- confirming no unintended grain changes
- ensuring no contract/engine drift

---

## Summary

Process enforces:

- discipline
- traceability
- correctness
- contract-first architecture

All work must follow defined steps.