# Requirements Ledger

## Purpose

This document captures the functional, structural, and behavioral requirements of the system.

Each row represents a single requirement, constraint, or invariant. Requirements are captured as they are discovered and refined.

This is a **living document** used to:

- capture system behavior and constraints
- document design decisions and tradeoffs
- preserve historical reasoning
- prevent architectural drift

Requirements may represent:

- functional requirements
- invariants
- domain rules
- validation rules
- system constraints
- expected behaviors

Rows are never deleted. Instead, they are marked inactive to preserve history.

---

## Requirements Table

| Requirement ID | Active | Requirement | Problem | Type | Scope | Notes |
|---------------|--------|-------------|----------|------|-------|--------|
REQ-001 | TRUE | Engine must execute all enabled company snapshots in a single run | Cannot compare scenarios or realms otherwise | Functional | Engine | Drives multi-snapshot execution design
REQ-002 | FALSE | Each company snapshot must explicitly select a Sales Plan Name | Prevents ambiguity across snapshots | Data Model | Sales | Replaces global sales assumption
REQ-003 | TRUE | Map Name must be globally unique across the workbook | Cannot distinguish maps otherwise | Data Model | Map | Enables unambiguous structure reference
REQ-004 | TRUE | Map structures must be independent and reusable entities | Enables reuse and scenario testing | Data Model | Map | Decouples structure from company
REQ-005 | TRUE | Production Plan must reference Map Structure via (Map Name, Slot) | Production cannot be associated with correct building otherwise | Data Model | Production | Core FK relationship
REQ-006 | TRUE | Production splits per (Map Name, Slot) must sum to 100% | Ensures full allocation of building capacity | Invariant | Production | Enforced during validation
REQ-007 | FALSE | Sales allocation must support both absolute and relative input formats | Users think in units and percentages | UX | Sales | Implemented via single Allocation field
REQ-008 | FALSE | Allocation inputs must be explicitly defined and non-zero | Prevents ambiguous or incomplete execution | Validation | Sales | Applies to all channels
REQ-009 | FALSE | Sales plans must only reference products that are produced | Prevents orphan sales allocations | Validation | Sales | Enforced post-throughput
REQ-010 | TRUE | Structure must remain independent from production assignment | Prevents duplication and inconsistency | Data Model | Structure | Separates tblMapStructure and tblProductionPlan
REQ-011 | TRUE | System must operate deterministically (same input produces same output) | Non-determinism breaks trust and debugging | Non-Functional | Engine | Core invariant
REQ-012 | TRUE | System must operate only on explicit inputs | Prevents hidden assumptions and implicit logic | Constraint | Engine | No implicit defaults
REQ-013 | TRUE | Validation must reject invalid input before execution | Prevents incorrect downstream results | Validation | Engine | Includes schema and rule validation
REQ-014 | TRUE | Bottlenecks must constrain production output | Reflects SimCo production mechanics | Domain Rule | Production | Core simulation behavior
REQ-015 | TRUE | Fractional BL must be explicitly represented | Prevents hidden rounding errors | Domain Rule | Production | Critical for accuracy
REQ-016 | TRUE | Output must not exceed available capacity | Prevents invalid production states | Invariant | Production | Applies at all stages
REQ-017 | FALSE | Sales channels distribute output but do not produce it | Prevents incorrect modeling of system flows | Domain Rule | Sales | Separation of concerns
REQ-018 | FALSE | Retail demand must be satisfied before other channels | Reflects SimCo priority rules | Domain Rule | Sales | Allocation precedence
REQ-019 | FALSE | Exchange sales must consume Transport Units (TU) which have an economic cost | Ignoring TU misprices exchange sales and distorts strategy | Domain Rule | Sales | TU are products with exchange prices
REQ-019A | FALSE | Contract sales must require 50% of the Transport Units of equivalent exchange transactions | Contracts have reduced transport requirements | Domain Rule | Sales | Applies only to contract channel
REQ-019B | TRUE | Transport must be modeled as an economic input, not a production constraint or bottleneck | Prevents incorrect capacity modeling | Domain Rule | Engine | Transport does not limit throughput
REQ-020 | TRUE | Pricing must be determined per product and quality level | Ensures correct economic modeling | Domain Rule | Pricing | Required for future economics layer
REQ-021 | TRUE | All user-controlled input tables must be explicitly defined and complete before execution | Missing or partial inputs lead to invalid or misleading results | Validation | Input | Applies to Company, MapStructure, ProductionPlan, SalesPlan
REQ-021A | TRUE | Reference data must be sourced from system reference tables and not user input | Prevents duplication and inconsistency | Data Model | Reference | Includes BOM and pricing inputs
REQ-022 | TRUE | Engine must produce diagnostics reflecting system state | Enables user understanding of outcomes | Functional | Output | Core Map Health output
REQ-023 | TRUE | Engine must support hypothetical scenario evaluation without altering observed data | Enables safe experimentation | Functional | Engine | Scenario capability
REQ-024 | TRUE | Invalid or incomplete assignments must result in execution failure | Prevents misleading outputs | Validation | Engine | Enforces strict correctness
REQ-025 | TRUE | Output must reflect excess production when production exceeds demand | Ensures correct system behavior | Functional | Output | Overproduction case
REQ-026 | TRUE | System must clearly represent constrained production under bottleneck conditions | Ensures correct interpretation of limits | Functional | Output | Bottleneck case
REQ-027 | FALSE | Sales plan should be global across all snapshots | Simplifies configuration | Data Model | Sales | Removed due to ambiguity across snapshots
REQ-028 | TRUE | Robot installation must restrict a building to produce a single product selected at installation time | Prevents invalid multi-product behavior under robot constraints | Domain Rule | Production | Locks production configuration
REQ-029 | TRUE | Robot installation must require downtime equal to the time required to upgrade the building to the next level | Ensures correct modeling of installation tradeoffs | Domain Rule | Structure | Uses building upgrade time as proxy
REQ-030 | TRUE | Robots must be uninstalled before a building can be upgraded or downgraded, returning 50% of robots at quality level 0 | Prevents invalid upgrade paths and enforces resource recovery rules | Domain Rule | Structure | Robot recovery always returns at Q0
REQ-031 | TRUE | Robots must reduce worker wages by 3% | Ensures correct economic modeling of robot efficiency | Domain Rule | Economics | Applies multiplicatively to wages
REQ-032 | TRUE | Administrative Overhead (AO) must increase wages by its percentage value | Captures management inefficiency costs | Domain Rule | Economics | AO applies as wage multiplier
REQ-033 | TRUE | Administrative Overhead (AO) must be calculated as (Total Building Level minus 1) divided by 170 | Ensures consistent AO calculation across all scenarios | Domain Rule | Economics | AO = (Total BL - 1) / 170
REQ-034 | TRUE | Executive management skill must reduce Administrative Overhead based on the formula (COO + (CTO + CMO + CFO) / 4 + COO Apprentice / 2) divided by 100 | Captures impact of executives on operational efficiency | Domain Rule | Economics | Applies as reduction factor to AO
REQ-035 | TRUE | Production Speed percentage must increase production output while reducing unit labor cost proportionally | Ensures correct modeling of speed-to-cost tradeoff | Domain Rule | Production | Output scales by 1/(1 - bonus), wages reduced by bonus
REQ-036 | FALSE | Sales Speed percentage must increase retail sales throughput by its percentage value | Ensures correct modeling of retail channel performance | Domain Rule | Sales | Applies only to retail channel
REQ-037 | TRUE | Number of robots required for a building must equal Building Level multiplied by IndustrialRobotsBL1 baseline | Incorrect robot counts distort cost, scrap value, and replacement modeling | Domain Rule | Structure | RobotsRequired = BL × IndustrialRobotsBL1
REQ-038 | TRUE | Required robot quality level must be calculated as the ceiling of Building Level divided by 3 minus 1, bounded at zero | Incorrect robot quality requirements misprice installation and replacement cost | Domain Rule | Structure | RobotQLRequired = max(0, ceil(BL / 3) - 1)
REQ-039 | TRUE | Building construction effort must scale according to BL weight sum defined as 1 plus BL times BL minus 1 divided by 2 | Linear scaling understates true construction cost and time | Domain Rule | Structure | BLWeightSum = 1 + BL × (BL - 1) / 2
REQ-040 | TRUE | Total building construction time must equal ConstructionTimeBL1PerHour multiplied by BL weight sum | Ensures correct cumulative upgrade time modeling | Domain Rule | Structure | BuildHours = ConstructionTimeBL1PerHour × BLWeightSum
REQ-041 | TRUE | Robot installation time must equal ConstructionTimeBL1PerHour multiplied by building level | Ensures robot install downtime matches upgrade timing rules | Domain Rule | Structure | RobotInstallHours = ConstructionTimeBL1PerHour × BL
REQ-042 | TRUE | Construction material requirements must equal BL1 baseline material quantities multiplied by BL weight sum | Prevents underestimation of total construction resource requirements | Domain Rule | Structure | MaterialTotal = MaterialBL1 × BLWeightSum
REQ-044 | TRUE | System must compute profit per day for each company snapshot | Users must assess overall company profitability | Functional | Output | ProfitPerDay = RevenuePerDay - TotalCostPerDay
REQ-045 | TRUE | System must compute return on invested capital (ROIC) for each company snapshot | Users must evaluate capital efficiency | Functional | Output | ROIC = ProfitPerDay / (CapitalBuildings + CapitalCIP)
REQ-046 | TRUE | System must compute profit per hour per total building level (BL) | Users must normalize profitability by scale of operation | Functional | Output | ProfitPerBL = ProfitPerHour / TotalBuildingLevel
REQ-047 | TRUE | System must compute profit per hour per building slot | Users must evaluate slot-level efficiency | Functional | Output | ProfitPerSlot = ProfitPerHour / BuildingCount
REQ-048 | TRUE | System must compute total production throughput in units per hour by product and in aggregate | Users must understand scale of production | Functional | Output | UnitsPerHour aggregated across all products
REQ-049 | TRUE | System must compute retail lost share for each product and overall | Users must detect unmet retail demand | Functional | Sales | RetailLostShare = RetailDemandUnmet / RetailDemandTotal
REQ-050 | TRUE | System must compute total transport units consumed per day | Users must assess transport burden and cost exposure | Functional | Logistics | Sum of TU consumption across all sales
REQ-051 | TRUE | System must compute transport units per unit sold for each product | Users must evaluate transport efficiency | Functional | Logistics | TUPerUnit = TUConsumed / UnitsSold
REQ-052 | TRUE | System must identify the product contributing the highest share of total transport usage | Users must detect concentration risk in logistics | Functional | Logistics | TopTransportShare = Max(TUProduct / TotalTU)
REQ-053 | TRUE | System must compute share of profit contributed by the top product | Users must assess revenue concentration risk | Functional | Output | TopProfitShare = Max(ProductProfit / TotalProfit)
REQ-054 | TRUE | System must compute profit concentration using a concentration index (e.g., HHI) | Users must understand diversification of profit sources | Functional | Output | HHI = Sum(ProductProfitShare^2)
REQ-055 | TRUE | System must compute total input cost per hour | Users must understand raw input cost burden | Functional | Economics | Sum of input purchase or internal valuation cost
REQ-056 | TRUE | System must compute total wages per hour including robot and AO adjustments | Users must understand labor cost contribution | Functional | Economics | WageCost includes robot reduction and AO increase
REQ-057 | TRUE | System must compute Administrative Overhead cost per hour | Users must quantify management overhead impact | Functional | Economics | AOCost = WageCost × AOEffectiveRate
REQ-058 | TRUE | System must compute total cost per hour | Users must understand full cost structure | Functional | Economics | TotalCost = InputCost + WageCost + AOCost + TransportCost
REQ-059 | TRUE | System must compute cost composition shares (input, wages, AO, transport) | Users must understand cost structure breakdown | Functional | Economics | Share = CategoryCost / TotalCost
REQ-060 | TRUE | System must compute total building count and total building level | Users must understand structural footprint of the map | Functional | Structure | BuildingCount and TotalBL derived from MapStructure
REQ-061 | TRUE | System must compute total replacement cost of all buildings | Users must understand capital required to rebuild the map | Functional | Structure | ReplacementCost = Sum(ReferenceValueBL1 × BL)
REQ-062 | TRUE | System must compute total scrap value of buildings | Users must estimate recoverable capital | Functional | Structure | ScrapValue = fraction of ReferenceValue (based on rules)
REQ-063 | TRUE | System must compute total construction time required to rebuild all buildings | Users must understand rebuild timeline | Functional | Structure | TotalBuildHours = Sum(BuildHours_Buildings)
REQ-064 | TRUE | System must compute total number of robots and maximum required robot quality level across the map | Users must assess robot investment and requirements | Functional | Structure | Aggregates from robot formulas
REQ-065 | TRUE | System must compare modeled profit per day with observed profit per day when observed data is available | Users must validate model accuracy | Functional | Diagnostics | ProfitGap = Modeled - Observed
REQ-066 | TRUE | System must compute modeled versus observed profit gap as a percentage | Users must assess magnitude of deviation | Functional | Diagnostics | GapPct = (Modeled - Observed) / Observed
REQ-067 | TRUE | System must flag when modeled versus observed gap exceeds a defined threshold | Users must quickly detect unreliable modeling conditions | Validation | Diagnostics | Uses ModeledObservedGapShareThreshold
REQ-068 | TRUE | System must compute total transport usage against defined threshold levels | Users must identify excessive logistics pressure | Validation | Logistics | Compare to TransportPressureUnitsPerDayThreshold
REQ-069 | TRUE | System must flag when transport usage is concentrated in a single product beyond defined threshold | Users must detect operational risk | Validation | Logistics | Uses TransportConcentrationShareThreshold
REQ-070 | TRUE | Production input requirements must round up fractional input quantities to the nearest whole unit based on total production | Prevents underconsumption of discrete inputs and ensures correct economic modeling of BOM usage | Domain Rule | Production | RequiredInputUnits = CEILING(InputQty × OutputUnits)
REQ-071 | TRUE | System must compute production quantities at full capacity per product × quality level | Required baseline for unconstrained analysis | Functional | Production | No prioritization or ordering allowed
REQ-072 | TRUE | System must compute material consumption using BOM explosion across all levels | Consumption must be fully deterministic and aggregate | Functional | Production | No routing or path logic allowed
REQ-073 | TRUE | System must compute net balance per product × quality level as produced minus consumed | Required to determine surplus and shortage | Functional | Engine | net = produced - consumed
REQ-074 | TRUE | System must generate balance_plan identifying surplus and shortage | Users must understand system imbalance | Functional | Output | Balance per product × QL
REQ-075 | TRUE | System must generate clearing_plan to resolve all imbalances | All imbalance resolved externally | Functional | Output | Core new layer
REQ-076 | TRUE | Clearing plan must support fractional allocation across channels | Enables blended strategies | Invariant | Clearing | Fractions sum to 1 per product × QL
REQ-077 | TRUE | System must not implement routing or priority-based allocation | Prevents reintroduction of deprecated model | Constraint | Engine | No flow logic of any type allowed
REQ-078 | TRUE | All consumption must be globally aggregated across demand sources | Prevents partial or path-based allocation | Constraint | Engine | Single total consumption per product × QL
REQ-079 | TRUE | All shortages must be resolved via external sourcing channels | Market replaces internal constraint solving | Domain Rule | Clearing | Exchange + Contract only
REQ-080 | TRUE | All surplus must be resolved via disposition channels | System must clear excess production | Domain Rule | Clearing | Exchange, Contract, Retail, Storage

---

## Consumption and Clearing

System must:

- compute production at full capacity
- compute consumption via BOM explosion
- support multi-level BOM
- aggregate all consumption globally

System must compute:

net = produced - consumed

System must:

- identify surplus and shortage
- output balance_plan

System must output clearing_plan:

Shortage:
- exchange
- contract

Surplus:
- exchange
- contract
- retail
- storage

Rules:
- allocations must sum to 1
- no implicit allocation
- no routing logic

---

## Summary

This ledger defines:

- what the system must do
- how the domain behaves
- what constraints must always hold

All behavior must be:

- explicit  
- testable  
- deterministic  

The ledger evolves alongside the system and serves as the **single source of truth for system requirements and invariants**.