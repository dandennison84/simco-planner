# Git Workflow

## Purpose

Define how changes are tracked, named, and committed.

Ensures:
- traceability
- reproducibility
- clean history
- consistent evolution of the system


---

## Core Rules

- All work is committed locally before pushing
- Each commit represents a single logical change
- Commit messages must follow a consistent structure
- History must remain readable and meaningful
- Main branch must remain stable


---

## Commit Structure

Commits follow this format:

```
<type>(<scope>): <summary>
```

Examples:

```
feat(engine): add throughput allocation logic
fix(economics): correct cost attribution error
docs(architecture): add L7 optimization layer
```


---

## Commit Types

| Type | Meaning |
|------|--------|
| feat | New capability or behavior |
| fix | Bug fix or correction |
| docs | Documentation change |
| refactor | Structural change without behavior change |
| test | Test addition or modification |
| chore | Non-functional change (setup, formatting, tooling) |


---

## Commit Scope

Scope identifies the affected area.

Examples:

- engine
- staging
- generator
- throughput
- economics
- diagnostics
- optimization
- guidance
- output
- docs
- tooling
- tests

Rules:

- Scope must align with system structure
- Avoid vague scopes (e.g., "misc", "update")
- Prefer domain-aligned terms (layer or subsystem names)


---

## Commit Summary

- Must be concise and descriptive
- Must describe what changed, not how
- Must stand on its own without context

Good:

fix(throughput): correct unit conservation bug  

Bad:

fixed stuff  


---

## Commit Granularity

- One commit = one logical change
- Do not mix unrelated changes
- Avoid large, bundled commits
- Prefer small, traceable steps


---

## Branching Model

- main → stable baseline
- feature branches → all active work

Naming examples:

feature/throughput-allocation  
fix/diagnostics-signal-bug  

Rules:

- Do not commit directly to main for non-trivial work
- Merge only after validation
- Keep branches short-lived


---

## Changelog Discipline

Commit history must support changelog generation.

Mapping:

- feat → new capability
- fix → correction
- refactor → internal change
- docs → documentation update

Requirements:

- consistent commit types
- clear summaries
- no ambiguous messages


---

## File Organization Rules

- All code, data, and docs must live in repository
- No hidden state outside repository
- Generated outputs must not be manually edited
- Source inputs must remain versioned


---

## Workflow Steps

1. Clone repository
2. Create branch
3. Make changes
4. Commit locally
5. Push to remote
6. Merge after validation


---

## Non-Goals

- Git history is not a scratchpad
- Commits are not notes or journal entries
- Repository is not used for experimentation logs


---

## Summary

Git usage enforces:

- structured development
- traceable decisions
- clean system evolution

History must clearly explain how the system changes over time.