# Engine Decisions Log

This file captures major architectural and development decisions.

Rules:
- One row per decision
- Append-only for *meaning* (do not delete prior decisions)
- If a decision is no longer active, mark it **❌ Superseded** and fill **ReplacedBy**
- Any new decision that replaces an old one must fill **Supersedes**
- Keep statements short and implementation-agnostic

---

## Lifecycle Legend

Status values (use emojis for scanability):
- ✅ Active — current authoritative decision
- ❌ Superseded — no longer in force (retained for history)
- ⚠️ Partial — transitional / partially enforced

Markdown strikethrough (optional for the *Decision* cell when superseded):
- `~~text~~`

---

## Development Environment

| # | Status | Supersedes | ReplacedBy | Topic | Problem | Key Points | Decision |
|---:|:---:|:---|:---|---|---|---|---|
| 1 | ✅ |  |  | Dev Environment | Excel/M is slow and untestable | No standalone execution, no testing, UI-coupled | Core logic must run outside Excel |
| 2 | ✅ |  |  | Runtime | Need expressive, testable execution system | Must support modular pipelines and deterministic transforms | Use a general-purpose runtime for engine execution |
| 3 | ✅ |  |  | Editor | Need productive development interface | Must support coding, debugging, and integration | Use a modern code editor |
| 4 | ✅ |  |  | Version Control | Need change tracking and rollback | Required for safe iteration and traceability | Use version control system |
| 5 | ✅ |  |  | Repository | Need persistent system state | Must store code, docs, and tests | Use centralized repository as source of truth |
| 6 | ✅ |  |  | Environment Isolation | Need reproducible dependencies | Avoid version conflicts | Use isolated project environments |
| 7 | ✅ |  |  | Project Structure | Need maintainable organization | Separate engine, data, tests, docs | Use structured repository layout |
| 8 | ✅ |  |  | Testing Framework | Need automated validation | Must support structured and repeatable tests | Use a programmable testing framework |
| 9 | ✅ |  |  | Test Strategy | Need scalable rule validation | Tables match domain logic | Use table-driven testing |
| 10 | ✅ |  |  | Test Data | Need clean test definition | Separate logic from data | Store test cases as tables |
| 11 | ✅ |  |  | Execution Model | Need repeatable runs | Avoid UI-triggered execution | Run engine as standalone process |
| 12 | ✅ |  |  | Data Contract | Need stable interface | Inputs/outputs must be inspectable | Use flat files as contract boundary |
| 13 | ✅ |  |  | Debugging | Need traceable behavior | Inspectable state preferred | Debug via data inspection |
| 14 | ✅ |  |  | Automation | Need regression safety | Standard software practice | Design for automated testing workflows |
| 15 | ✅ |  |  | Coding Style | Need data transformations and side effect avoidance | Standard software practice | Use FP when possible except where it overcomplicates |
| 16 | ✅ |  |  | Assignment Completeness | Partial assignment leads to silent capacity loss | All slots must be explicitly allocated | All economic slots must have explicit assignment rows |
| 17 | ✅ |  |  | No Fallback Behavior | Implicit defaults hide user intent errors | Deterministic systems require explicit inputs | No fallback or inferred allocation behavior is allowed |
| 18 | ✅ |  |  | Assignment Canonical Source | Assignment could originate from multiple surfaces | Must enforce a single authoritative source | Assignment must originate from a single canonical input surface |
| 19 | ✅ |  |  | Assignment Grain Definition | Assignment identity unclear across dimensions | Requires full identity including quality level | Assignment is uniquely defined by slot × product × quality level |
| 20 | ✅ |  |  | Split Integrity | Allocation fractions could drift or misalign | Must preserve total capacity | Split fractions must sum exactly to 1 per slot |
| 21 | ✅ |  |  | Input Validation Discipline | Invalid data could propagate silently | Engine must fail early and clearly | All invalid, incomplete, or malformed inputs must fail validation |
| 22 | ✅ |  |  | No Silent Data Correction | Systems may auto-correct bad inputs | Hidden correction causes trust issues | Invalid inputs must not be corrected, only rejected |
| 23 | ✅ |  |  | Throughput Resolution Rule | Multiple passes could distort quantities | Flow must resolve once deterministically | Throughput must be resolved once and never recomputed or redistributed |
| 24 | ✅ |  |  | Channel Projection Constraint | Channel logic could distort base quantities | Channel is projection, not production | Channels must only distribute resolved throughput, never create or alter it |
| 25 | ✅ |  |  | Stock vs Flow Boundary Enforcement | Structural metrics risk contaminating flow logic | Layer boundaries must remain strict | Structural/stock values must never be used as inputs into throughput or modeled economics |

---

## Architecture

| # | Status | Supersedes | ReplacedBy | Topic | Problem | Key Points | Decision |
|---:|:---:|:---|:---|---|---|---|---|
| 01 | ✅ |  |  | Engine Ownership | Logic spread across layers | Hard to maintain and verify | Single engine owns all logic |
| 02 | ✅ |  |  | Integration Layer | UI layer overloaded with logic | Weak for testing and iteration | Integration layer is thin only |
| 03 | ✅ |  |  | System Boundary | Need clear separation | Prevent cross-layer contamination | Use explicit data contract boundary |
| 04 | ✅ |  |  | Data Flow | Need deterministic pipeline | Transformation must be explicit | Pipeline is staged and directional |
| 05 | ✅ |  |  | Testing Level | Unit tests insufficient | Need system-level validation | Add acceptance testing layer |
| 06 | ✅ |  |  | Test Model | Rules are table-based | Align with domain thinking | Use table-driven acceptance tests |
| 07 | ✅ |  |  | Layer Model | Existing model is strong | Already enforces correctness | Keep full layer model |
| 08 | ✅ |  |  | Documentation Role | Docs tied to implementation | Limits flexibility | Docs define invariants only |
| 09 | ✅ |  |  | Implementation Independence | Language coupling limits portability | System should outlive tooling | Remove implementation-specific language |
| 10 | ✅ |  |  | Runtime Isolation | Test data interfered with runtime behavior | Needed separation without changing engine logic | Separate runtime and test data directories |
| 11 | ✅ |  |  | CSV Contract Boundary | Considered reading Excel directly | Engine must remain deterministic and UI-independent | CSV is the sole contract boundary |
| 12 | ✅ |  |  | Validator Layer | No clear data validation boundary | Pipeline must remain pure logic | Add schema-driven validator before pipeline |
| 13 | ✅ |  |  | Schema Ownership | Unclear whether user or system defines structure | User experience must remain simple | Schema owned by system, not input tables |
| 14 | ✅ |  |  | Schema Versioning | Considered embedding version in CSV data | Would complicate user input and pollute tables | Versioning exists only in schema, not CSV |
| 15 | ✅ |  |  | Observability | Engine execution was silent | No signal of data consumption | Always emit table-level run summaries |
| 16 | ✅ |  |  | Schema Scope | Considered schema defining table presence | Schema not yet mature | Keep table surfaces defined in engine for now |
| 17 | ✅ |  |  | User Responsibility | Users potentially managing system metadata | Creates unnecessary complexity | Users only provide business data, no system fields |
| 18 | ✅ |  |  | Slot State Semantics | Slot states previously ignored in logic | Only certain states contribute to production | Only capacity-contributing slot states participate in production |
| 19 | ✅ |  |  | Automation Semantics | Automation behavior unclear in model | Must match game mechanics | Automation affects costs only, not throughput |
| 20 | ✅ |  |  | Production Symmetry | Production modifiers potentially distort economics | Must maintain balanced effect | Production modifiers apply symmetrically to output and labor |
| 21 | ✅ |  |  | Economics Primitives | Revenue used inconsistently | Profit and cost must be consistent base | Profit and cost are primitives; revenue is derived only |
| 22 | ✅ |  |  | Stock vs Flow Separation | Structural values risk contaminating flow logic | Must maintain layer integrity | Stock/structure values must not be used in throughput or economics |
| 23 | ✅ |  |  | Assignment Driven Throughput | Structure previously used for capacity directly | Assignment defines production | Throughput must be driven exclusively by assignment surfaces |
| 24 | ✅ |  |  | Generator Discipline | Row expansion logic implicit | Expansion must be controlled | Any component increasing rows must explicitly declare schema and expansion cause |
| 25 | ✅ |  |  | Scenario Model | Scenario logic embedded in tool-specific inputs | Need reusable, tool-independent state derivation | Scenarios are defined as baseline snapshot plus scenario_delta applied as partial updates |
| 26 | ✅ |  |  | Execution Identity | Snapshot and scenario identities conflict during execution | Pipeline must remain simple and deterministic | Engine generates a unique state_key for execution and does not rely on snapshot_key or scenario_key internally |
| 27 | ❌ |  | 30 | ~~Flow Policy Layer~~ | Internal resource routing not explicitly modeled | Flow behavior must be separated | ~~Introduce a flow policy stage~~ |
| 28 | ❌ |  | 30 | ~~Sales Strategy Model~~ | Demand-based models created implicit behavior | Required explicit table-driven behavior | ~~Replace sales_demand with sales_strategy~~ |
| 29 | ❌ |  | 30 | ~~Flow vs Sales Strategy Separation~~ | Internal vs external allocation modeled separately | Separation introduced duplicated logic | ~~Maintain separation of flow_policy and sales_strategy~~ |
| 30 | ✅ | 27,28,29 |  | Consumption and Clearing Model | Flow and sales allocation models introduced routing and priority complexity | BOM fully determines consumption; market resolves imbalance; routing not required | Replace flow_policy and sales_strategy with production → BOM consumption → balance → clearing |
| 31 | ❌ | | | ~~Production Model~~ | ~~Ambiguity between full-capacity and bottleneck-constrained production created uncertainty in pipeline behavior and clearing logic~~ | ~~Must preserve deterministic staged pipeline; avoid routing or dependency-based constraint solving; align with clearing-based imbalance resolution~~ | ~~Production is computed at full capacity independent of input availability. All shortages are resolved via the clearing layer. Production is not constrained by input bottlenecks. Production quantities may be adjusted via run normalization to ensure integer BOM consumption without reducing capacity-driven output.~~ |
| 32 | ✅ | | | Validation Architecture | Structural validation was interleaved with stage logic, leading to duplicated checks and unclear guarantees about data integrity throughout the pipeline | Must ensure deterministic execution and eliminate redundant validation while enabling strong stage contracts | All structural validation (schema, typing, required tables, key constraints) must be performed once before pipeline execution. Downstream stages may assume structurally valid and typed data. Behavioral correctness is enforced via stage-level invariants. |
| 33 | ✅ | 31 | | Production Model | Run normalization introduced non-game-realistic behavior and distorted planner outputs | Continuous production better reflects player decision making and avoids artificial truncation | Production is computed at full capacity as a continuous rate. BOM consumption is computed as continuous fractional usage. No integer run normalization or global rounding is applied. |

---

## Governance

| # | Status | Supersedes | ReplacedBy | Topic | Problem | Key Points | Decision |
|---:|:---:|:---|:---|---|---|---|---|
| 01 | ✅ |  |  | Source of Truth | Conversations are not persistent | Risk of drift | Repository docs are authoritative |
| 02 | ✅ |  |  | Decision Tracking | Decisions get lost | Need continuity | Maintain decisions log |
| 03 | ✅ |  |  | Execution Independence | System tied to tooling | Limits evolution | Define system independent of runtime |
| 04 | ✅ |  |  | Diagnostics Integrity | Diagnostics could modify results | Must remain observational only | Diagnostics must not alter modeled or observed results |
| 05 | ✅ |  |  | Guidance Boundaries | Guidance could become prescriptive | Preserve user agency | Guidance must not prescribe actions or optimize decisions |
| 06 | ✅ |  |  | Policy Location | Thresholds risk being embedded in logic | Must be auditable and modular | All thresholds and policies must be table-driven |
| 07 | ✅ |  |  | Authority Separation | Ref and system logic can blur | Must maintain clarity of truth vs interpretation | Ref = world truth; Sys = engine interpretation |
| 08 | ✅ |  |  | Documentation Audience | Documentation mixing audiences | Engine docs should not explain player-facing output | Docs must only define engine invariants and intent, not player explanations |
| 09 | ✅ |  |  | Player Explanation Boundary | Player explanation appears in engine docs | Must separate internal vs external language | Player-facing explanations must exist only in Help or Tool layers |
| 10 | ✅ |  |  | Documentation Stability | Docs drift over time with ad hoc updates | Must preserve authority and traceability | Engine documentation is stable and only changes via controlled refactors |
| 11 | ✅ |  |  | Documentation Discipline | System accumulates unnecessary ideas and notes | Not all information should be captured | Information that does not clearly belong in a system layer must not be documented |

---

## Lifecycle Rules (Operational)

When introducing a replacement decision:
- Add a new row with **Status = ✅ Active** and fill **Supersedes** with the prior decision id(s)
- Update the prior row to **Status = ❌ Superseded** and fill **ReplacedBy** with the new decision id
- Optional: wrap the old Decision text in `~~ ~~` for quick visual scanning

Examples:
- Supersedes: `04`  
- ReplacedBy: `18`

Notes:
- Superseding should be used only when the older decision is no longer correct or has been materially replaced.
- Clarifications that do not change meaning should be captured as **Notes** in the new row (not as superseding).