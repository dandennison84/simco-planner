# Engine Rules Registry

### Purpose

Define non-negotiable behavioral invariants of the engine that cannot be cleanly expressed as architectural or governance decisions.

These rules govern:

- evaluation correctness  
- diagnostic integrity  
- signal behavior  
- evidence preservation  

They are:

- independent of implementation  
- always-on constraints  
- enforced through pipeline design, testing, and structural discipline  

---

## Rule Status Legend

| Status | Meaning |
|-------|--------|
| ✅ Active | Current invariant |
| ❌ Superseded | No longer valid (retained for history) |
| ⚠️ Partial | Not fully implemented yet |

---

## Rules Table

| RuleId | Status | Supersedes | ReplacedBy | Domain | Rule | Rationale | Enforcement | Notes |
|--------|--------|-----------|------------|--------|------|-----------|-------------|-------|
| ER-25 | ✅ |  |  | Signals | Signals must be derived only from fact surfaces | Prevents dependence on unstable intermediate data | Signal layer design | Ensures composability |
| ER-27 | ✅ |  |  | Signals | Signals must preserve full evaluation grain | Prevents loss of context and incorrect aggregation | Schema + evaluation logic | All context keys required |
| ER-30 | ✅ |  |  | Evidence | Signals must include Evidence preserving causal row identity | Enables traceability and diagnostics | Signal generation | Evidence captured pre-aggregation |
| ER-31 | ✅ |  |  | Signals | Suppression must operate at full signal grain | Prevents cross-context suppression errors | Signal engine logic | No partial matching |
| ER-34 | ✅ |  |  | Signals | Signals must not implicitly aggregate or deduplicate rows | Preserves event-level correctness | Query design discipline | Explicit collapse only |
| ER-36 | ✅ |  |  | Evidence | Evidence represents row-level causality and must not be interpreted as entity counts | Prevents misinterpretation of diagnostics | Diagnostics layer discipline | Distinguish row vs entity counts |

---

## Principles

- These rules are **never optional**
- These rules are **not decisions** — they are invariants
- These rules apply wherever Signals, Facts, or Evidence exist
- These rules must be enforced by:
  - schema design  
  - pipeline structure  
  - testing  
  - code review discipline  

---

## Summary

This registry ensures:

- signal correctness  
- causal traceability  
- deterministic diagnostics  
- preservation of evaluation grain  

These rules protect the integrity of the diagnostic system.