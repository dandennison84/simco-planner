# Engine Decisions Log

This file captures major architectural and development decisions.

Rules:
- One row per decision
- Append-only (do not rewrite history), must reference impacted row(s)
- Capture: problem → key reasoning → decision
- Keep statements short and implementation-agnostic

---

## Development Environment

| # | Topic | Problem | Key Points | Decision |
|---|------|--------|-----------|----------|
| 1 | Dev Environment | Excel/M is slow and untestable | No standalone execution, no testing, UI-coupled | Core logic must run outside Excel |
| 2 | Runtime | Need expressive, testable execution system | Must support modular pipelines and deterministic transforms | Use a general-purpose runtime for engine execution |
| 3 | Editor | Need productive development interface | Must support coding, debugging, and integration | Use a modern code editor |
| 4 | Version Control | Need change tracking and rollback | Required for safe iteration and traceability | Use version control system |
| 5 | Repository | Need persistent system state | Must store code, docs, and tests | Use centralized repository as source of truth |
| 6 | Environment Isolation | Need reproducible dependencies | Avoid version conflicts | Use isolated project environments |
| 7 | Project Structure | Need maintainable organization | Separate engine, data, tests, docs | Use structured repository layout |
| 8 | Testing Framework | Need automated validation | Must support structured and repeatable tests | Use a programmable testing framework |
| 9 | Test Strategy | Need scalable rule validation | Tables match domain logic | Use table-driven testing |
|10 | Test Data | Need clean test definition | Separate logic from data | Store test cases as tables |
|11 | Execution Model | Need repeatable runs | Avoid UI-triggered execution | Run engine as standalone process |
|12 | Data Contract | Need stable interface | Inputs/outputs must be inspectable | Use flat files as contract boundary |
|13 | Debugging | Need traceable behavior | Inspectable state preferred | Debug via data inspection |
|14 | Automation | Need regression safety | Standard software practice | Design for automated testing workflows |

---

## Architecture

| # | Topic | Problem | Key Points | Decision |
|---|------|--------|-----------|----------|
|15 | Engine Ownership | Logic spread across layers | Hard to maintain and verify | Single engine owns all logic |
|16 | Integration Layer | UI layer overloaded with logic | Weak for testing and iteration | Integration layer is thin only |
|17 | System Boundary | Need clear separation | Prevent cross-layer contamination | Use explicit data contract boundary |
|18 | Data Flow | Need deterministic pipeline | Transformation must be explicit | Pipeline is staged and directional |
|19 | Testing Level | Unit tests insufficient | Need system-level validation | Add acceptance testing layer |
|20 | Test Model | Rules are table-based | Align with domain thinking | Use table-driven acceptance tests |
|21 | Layer Model | Existing model is strong | Already enforces correctness | Keep full layer model |
|22 | Documentation Role | Docs tied to implementation | Limits flexibility | Docs define invariants only |
|23 | Implementation Independence | Language coupling limits portability | System should outlive tooling | Remove implementation-specific language |

---

## Governance

| # | Topic | Problem | Key Points | Decision |
|---|------|--------|-----------|----------|
|24 | Source of Truth | Conversations are not persistent | Risk of drift | Repository docs are authoritative |
|25 | Decision Tracking | Decisions get lost | Need continuity | Maintain decisions log |
|26 | Execution Independence | System tied to tooling | Limits evolution | Define system independent of runtime |