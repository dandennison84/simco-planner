# Data Contracts

## Purpose

Define the external data interfaces of the system.

These are the only surfaces the system guarantees.


---

## Input Surfaces

| Name | Description | Grain | Keys | Authority |
|------|------------|------|------|----------|
| company_snapshot | Observed company context and modifiers | snapshot_key | snapshot_key | Observed truth |
| financial_snapshot | Accounting results | snapshot_key | snapshot_key | Accounting truth |
| structure_map | Physical and organizational structure | structure_key + slot_key | structure_key, slot_key | Declared structure |
| slot_product_assignment | Explicit assignment of capacity to products | slot_key + product_key + quality_level | slot_key, product_key, quality_level | Explicit assignment |


---

## Reference Surfaces

| Name | Description | Grain | Keys | Authority |
|------|------------|------|------|----------|
| market_pricing | Observed market prices | realm_key + product_key + quality_level | realm_key, product_key, quality_level | Market observation |
| product_bom | Product input relationships | product_key + input_product_key | product_key, input_product_key | World rules |
| system_parameters | Engine defaults and policies | parameter | parameter | Engine configuration |


---

## Output Surfaces

| Name | Description | Grain | Keys | Authority |
|------|------------|------|------|----------|
| diagnostics | Derived signals and system state | snapshot_key + signal_code | snapshot_key, signal_code | Engine-derived |
| guidance | Attention cues derived from signals | snapshot_key + signal_code | snapshot_key, signal_code | Signal synthesis |
| signal_evidence | Full evaluation-level signal output | snapshot_key + product_key + quality_level + sales_channel_key + signal_code | snapshot_key + context + signal_code | Raw evaluation |
| map_health_view | Tool-specific projection of diagnostics | snapshot_key | snapshot_key | Presentation only |


---

## Rules

- Surface names must be semantic and implementation-agnostic
- Tool-specific naming is only allowed for presentation surfaces (e.g., map_health_view)
- Names must not encode system roles (input, ref, output)
- Names must not reference specific tools unless they are tool views
- Grain and keys must be explicitly defined
- All inputs must be explicit and complete
- Outputs must be final and fully resolved
- Internal pipeline artifacts must not appear here


---

## Summary

Data contracts define the system boundary.

They are the only stable interface between:
- engine internals
- user-visible outputs