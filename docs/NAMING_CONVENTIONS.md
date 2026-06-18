# Naming Conventions

## Purpose

Define consistent naming rules across the system.

These rules ensure:
- clarity
- consistency
- implementation independence
- alignment with domain concepts

---

## Core Principles

- All names must be implementation-agnostic
- Names must describe meaning, not role or origin
- Naming must be consistent across all layers
- No tool- or language-specific conventions

Names must answer:
“What is this thing?”

---

## Case Style

- Use snake_case
- Use lowercase only
- Separate words with underscores

Examples:

company_snapshot  
structure_map  
slot_product_assignment  
market_pricing  
diagnostics  

---

## Naming Model

### Domain-Based Naming

Names must reflect domain meaning.

Correct:

- company_snapshot
- financial_snapshot
- structure_map
- slot_product_assignment
- market_pricing
- diagnostics
- guidance

Incorrect:

- input_company_snapshot
- ref_pricing
- tbl_diagnostics
- q_signal_table

---

### No Role-Based Prefixes

Do not encode system role in names.

Do NOT use:

- input_*
- ref_*
- sys_*
- out_*
- tbl_*
- stg_*
- q_*

Role is defined by:
- location (DATA_CONTRACTS)
- grain
- usage

NOT by name.

---

### No Tool-Specific Naming

Names must not reflect:

- Power Query
- Python
- SQL
- Excel

Avoid:

- query_pricing
- dataframe_sales
- table_output

Names must remain valid across any implementation.

---

## Surface Naming

### Input Surfaces

Use domain nouns:

- company_snapshot
- financial_snapshot
- structure_map
- slot_product_assignment

---

### Reference Surfaces

Use domain nouns:

- market_pricing
- product_bom
- system_parameters

---

### Output Surfaces

Use semantic nouns:

- diagnostics
- guidance
- signal_evidence

---

### Tool Views

Tool-specific views may include tool name:

- map_health_view

These represent presentation only.

---

## Column Naming

- Use snake_case
- Use full words
- Avoid abbreviations unless standard (bom, id)
- Include units where required

Examples:

snapshot_key  
product_key  
quality_level  
split_fraction  
net_income_per_day  

---

## Key Naming

Keys must:
- be explicit
- be consistent across surfaces
- reflect grain

Examples:

snapshot_key  
structure_key  
slot_key  
product_key  
signal_code  

---

## Engine Stage Naming

Stages must describe the transformation performed.

Correct:

- structure
- production_resolution
- product_bom_consumption
- balance
- clearing_allocation

Rule:

"allocation" refers only to distribution across channels, not production.

---

## Derived vs Base Naming

- Base surfaces use nouns
- Derived surfaces use semantic meaning

Correct:

diagnostics  
guidance  

Incorrect:

calculated_diagnostics  
processed_guidance  

---

## Avoided Patterns

Do not use:

- unnecessary abbreviations
- implementation hints
- redundant prefixes/suffixes

Avoid:

data_table_sales  
final_output_results  
stg_structure_map  

---

## Evolution Rule

If a name becomes ambiguous:

- rename at the source
- update all references

Do not layer meaning onto poor names.

---

## Summary

Naming must be:

- simple
- explicit
- domain-driven
- implementation-independent

Names describe meaning.

Structure and behavior define everything else.