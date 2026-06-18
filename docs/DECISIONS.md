# Engine Decisions Log

This file captures major architectural and development decisions.

Rules:
- One row per decision
- Append-only for meaning (do not delete prior decisions)
- If a decision is no longer active, mark as ❌ Superseded and fill ReplacedBy
- Replacement decisions must fill Supersedes
- Keep statements short and implementation-agnostic

---

## Lifecycle Legend

Status values:
- ✅ Active — current authoritative decision
- ❌ Superseded — no longer in force
- ⚠️ Partial — transitional / partially enforced

Optional:
- Use ~~strikethrough~~ on superseded decisions

---

## Development Environment

| # | Status | Supersedes | ReplacedBy | Topic | Problem | Key Points | Decision |
|---:|:---:|:---|:---|---|---|---|---|
| 1 | ✅ | | | Dev Environment | Excel/M is slow and untestable | No standalone execution | Core logic must run outside Excel |
| 2 | ✅ | | | Runtime | Need expressive system | Deterministic pipeline required | Use general-purpose runtime |
| 3 | ✅ | | | Editor | Need dev interface | Must support debugging | Use modern code editor |
| 4 | ✅ | | | Version Control | Need traceability | Safe iteration required | Use VCS |
| 5 | ✅ | | | Repository | Need persistence | Store code + docs | Central repo is source of truth |
| 6 | ✅ | | | Environment Isolation | Dependency conflicts | Reproducibility required | Use isolated environments |
| 7 | ✅ | | | Project Structure | Maintainability | Separate concerns | Structured repo layout |
| 8 | ✅ | | | Testing Framework | Need validation | Repeatable testing | Use programmable framework |
| 9 | ✅ | | | Test Strategy | Rules are tabular | Scale validation | Use table-driven tests |
| 10 | ✅ | | | Test Data | Logic/data separation | Clean test inputs | Store tests as tables |
| 11 | ✅ | | | Execution Model | Avoid UI coupling | Deterministic runs | Engine runs standalone |
| 12 | ✅ | | | Data Contract | Stable interface needed | Inspectability | Use CSV contract boundary |
| 13 | ✅ | | | Debugging | Need traceability | Inspect state directly | Debug via data inspection |
| 14 | ✅ | | | Automation | Regression safety | Standard practice | Enable automated workflows |
| 15 | ✅ | | | Coding Style | Side-effects risk | Predictability | Prefer FP where reasonable |
| 16 | ✅ | | | Assignment Completeness | Partial assignment loss | Capacity integrity | All slots must be assigned |
| 17 | ✅ | | | No Fallback | Hidden defaults | Non-deterministic | No inferred behavior |
| 18 | ✅ | | | Assignment Source | Multiple sources | Ambiguity | Single canonical input |
| 19 | ✅ | | | Assignment Grain | Identity ambiguity | Needs full precision | slot × product × quality |
| 20 | ✅ | | | Split Integrity | Fraction drift | Capacity loss | Splits must equal 1 |
| 21 | ✅ | | | Input Validation | Silent errors | Fail fast | Invalid input must fail |
| 22 | ✅ | | | Input Correction | Hidden fixes | Trust issues | No auto-correction |
| 23 | ✅ | | | Throughput | Multi-pass distortion | Determinism required | Resolve once |
| 24 | ✅ | | | Channels | Output mutation risk | Misleading outputs | Channels distribute only |
| 25 | ✅ | | | Stock vs Flow | Cross-contamination | Layer integrity | No stock → flow usage |

---

## Architecture

| # | Status | Supersedes | ReplacedBy | Topic | Problem | Key Points | Decision |
|---:|:---:|:---|:---|---|---|---|---|
| 01 | ✅ | | | Engine Ownership | Logic fragmentation | Hard to verify | Single engine owns logic |
| 02 | ✅ | | | Integration | UI logic leakage | Hard to test | Thin integration layer |
| 03 | ✅ | | | Boundary | Layer contamination | Need separation | Explicit contract boundary |
| 04 | ✅ | | | Data Flow | Non-deterministic behavior | Implicit transforms | Staged pipeline |
| 05 | ✅ | | | Testing Level | Unit tests insufficient | System behavior matters | Acceptance testing |
| 06 | ✅ | | | Test Model | Domain is tabular | Alignment needed | Table-driven tests |
| 07 | ✅ | | | Layer Model | Already strong | Enforces correctness | Keep layered architecture |
| 08 | ✅ | | | Documentation | Coupled to code | Limits flexibility | Docs define invariants only |
| 09 | ✅ | | | Independence | Language coupling | Reduces portability | Remove implementation bias |
| 10 | ✅ | | | Runtime Isolation | Data contamination | Test vs runtime conflict | Separate directories |
| 11 | ✅ | | | CSV Boundary | Excel dependency risk | Determinism required | CSV-only boundary |
| 12 | ✅ | | | Validator Layer | Mixed validation | Duplicate logic | Schema-driven validator |
| 13 | ✅ | | | Schema Ownership | User vs system ambiguity | UX complexity | Schema owned by system |
| 14 | ✅ | | | Schema Versioning | Data-level versioning risk | Input complexity | Versioning in schema only |
| 15 | ✅ | | | Observability | Silent execution | No insight | Emit summaries |
| 16 | ✅ | | 34 | Schema Scope | Structure partly in code | Not scalable | Move to contracts |
| 17 | ✅ | | | User Responsibility | Users handling metadata | Complexity | Users provide only business data |
| 18 | ✅ | | | Slot Semantics | State ignored | Incorrect production | Only active slots used |
| 19 | ✅ | | | Automation | Misinterpreted effect | Gameplay mismatch | Affects cost only |
| 20 | ✅ | | | Production Symmetry | Distorted economics | Imbalance risk | Apply symmetrically |
| 21 | ✅ | | | Economics Model | Revenue misuse | Inconsistent base | Profit/cost are primitives |
| 22 | ✅ | | | Stock vs Flow | Contamination risk | Layer violation | Strict separation |
| 23 | ✅ | | | Throughput Driver | Structure used incorrectly | Logic mismatch | Assignment drives production |
| 24 | ✅ | | | Generator Discipline | Hidden row expansion | Traceability loss | Explicit expansion rules |
| 25 | ✅ | | | Scenario Model | Hardcoded scenarios | Lack of reuse | Use delta overlays |
| 26 | ✅ | | | Execution Identity | ID collisions | Complexity | Engine-generated key |
| 30 | ✅ | 27,28,29 | | Clearing Model | Routing complexity | Overly complex | Replace with production → BOM → balance → clearing |
| 32 | ✅ | | | Validation Architecture | Mixed validation | Inconsistency | Validate once pre-pipeline |
| 33 | ✅ | 31 | | Production Model | Rounding distortion | Unrealistic output | Continuous production only |
| 34 | ✅ | 16 | | Schema Scope | Not fully contract-driven | Limited extensibility | Contracts define surfaces |
| 35 | ✅ | | | Contract Architecture | YAML grouping limits flexibility | Inflexible | Fully contract-driven system |
| 36 | ✅ | | | Validation Ownership | Logic duplicated | Drift risk | Contracts define validation |
| 37 | ✅ | | | Contract Discovery | Fixed paths | Not scalable | Dynamic discovery |
| 38 | ✅ | | | UI Lookup | Dual definitions | Drift | Contract-driven lookups |
| 39 | ✅ | | | Contract Typing | Implicit typing | Parse ambiguity | Explicit kind required |
| 40 | ✅ | 16 | | Contract System | Mixed structure ownership | Drift and duplication | Contracts define all structure |

---

## Governance

| # | Status | Supersedes | ReplacedBy | Topic | Problem | Key Points | Decision |
|---:|:---:|:---|:---|---|---|---|---|
| 01 | ✅ | | | Source of Truth | Conversations lost | Drift risk | Repo docs authoritative |
| 02 | ✅ | | | Decision Tracking | Decisions lost | Continuity needed | Maintain log |
| 03 | ✅ | | | Independence | Tool coupling | Limits evolution | Define system independent |
| 04 | ✅ | | | Diagnostics | Mutation risk | Must remain read-only | Diagnostics observational only |
| 05 | ✅ | | | Guidance | Prescriptive outputs | User loss of control | Guidance not prescriptive |
| 06 | ✅ | | | Policy Location | Logic embedding risk | Not auditable | Policies table-driven |
| 07 | ✅ | | | Authority | Truth vs logic mixing | Ambiguity | Ref = truth, Sys = interpretation |
| 08 | ✅ | | | Docs Audience | Mixed audiences | Confusion | Engine docs = internal only |
| 09 | ✅ | | | Player Explanation | Leakage into engine docs | Misuse | Move to help layer |
| 10 | ✅ | | | Documentation Stability | Drift risk | Loss of authority | Controlled updates only |
| 11 | ✅ | | | Documentation Discipline | Over-documentation | Noise | Only document system-layer info |

---

## Lifecycle Rules

When replacing a decision:
- New row → Status = ✅ Active, fill Supersedes
- Old row → Status = ❌ Superseded, fill ReplacedBy

Example:
- Supersedes: 04
- ReplacedBy: 18

Rules:
- Use superseding only for real replacement
- Minor clarification → do NOT supersede