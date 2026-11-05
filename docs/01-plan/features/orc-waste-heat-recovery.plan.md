# Implementation Plan: Organic Rankine Cycle (ORC) Waste-Heat Recovery

**Issue:** #104
**Backlog:** `docs/backlog/2026-11-02-orc-waste-heat-recovery.md`
**Branch:** `feat/ORC-ai-workflow`

> The feature was developed against a client (KSOE Machinery Design Lab) before this plan
> was filed. The plan records the task breakdown as implemented, so that review can
> follow the dependency order.

---

## Overview

Model electric power recovered from waste heat by an ORC. Two patterns:

| Host | `switchboard_id` | Representation in feems |
|------|------------------|-------------------------|
| Main engine (`Engine`, `MultiFuelEngine` on a shaft line) | > 0 | `OrganicRankineCycle` power source on that switchboard, fixed setpoint |
| Genset engine, fuel-cell group (`MachinerySystem.fuel_cell_orc`) | 0 | Not converted; the client folds the ORC into the host efficiency curve |

The ORC physics (heat available at a given host load, part-load efficiency, cut-in) stay with the client. feems receives either a setpoint for the main engine ORC or an already lifted host curve.

## Architecture Decisions

- **ORC data lives on its host in the proto.** An ORC has no meaning without the heat source, so it is a field of `Engine` / `MultiFuelEngine` and of `MachinerySystem` (fuel-cell group), not a switchboard subsystem. One message type serves all three hosts.
- **`switchboard_id` selects the representation.** `> 0` means a separate electric source on that switchboard; `0` means integrated in the host. No extra enum needed.
- **Main engine ORC is a fixed-setpoint source.** Its output follows the main engine load, not the electric demand, so it must not take part in load sharing. It uses the existing fixed load-sharing mechanism (`load_sharing_mode > 0`), which already lowers the load on the balancing units.
- **New `TypeComponent.ORGANIC_RANKINE_CYCLE`.** Reusing `GENERATOR` or `SHORE_POWER` would mix fuel accounting and result columns; a dedicated type keeps the energy balance explicit.
- **Recovered energy gets its own result field** (`energy_input_waste_heat_recovery_total_mj`) instead of being hidden in `energy_input_electric_total_mj` (shore power).
- **All proto changes are additive** (new message, new field tags) — wire-compatible with existing data.

## Dependency Graph

```
T1 TypeComponent + FEEMSResult field
 └─► T2 OrganicRankineCycle component + power-source registration
      └─► T3 energy balance (node.py) + operating avg power
           └─► T4 power-balance rounding residual
                └─► ═══ CHECKPOINT A: feems tests green ═══
                     └─► T5 proto message + fields, recompile
                          ├─► T6 proto → feems conversion (collect ORCs per switchboard)
                          └─► T7 feems → proto skip + result converter
                               └─► ═══ CHECKPOINT B: MachSysS tests green ═══
                                    └─► T8 API references
```

## Task List

### Phase 1: feems

#### T1 — Types
Add `TypeComponent.ORGANIC_RANKINE_CYCLE = 31` and `FEEMSResult.energy_input_waste_heat_recovery_total_mj` (default `0.0`).
**Files:** `feems/feems/types_for_feems.py` · **Scope:** XS

#### T2 — Component
`OrganicRankineCycle(ElectricComponent)` with `TypePower.POWER_SOURCE`; add it to the accepted power-source classes in `ElectricPowerSystem`.
**Acceptance:** the component appears in `power_sources`; a fixed setpoint reduces the balancing gensets' load.
**Files:** `component_electric.py`, `system_model.py` · **Scope:** S

#### T3 — Energy balance
Branch in `get_fuel_emission_energy_balance_for_component` integrating `power_output` into the new result field; no fuel. Branch in `_assign_operating_avg_metrics` for `operating_avg_power_kw`.
**Files:** `node.py` · **Scope:** S

#### T4 — Power balance robustness
When fixed sources cover the whole load, the remaining load is a rounding residual (~1e-12 kW) while no balancing power is online. The load ratio `residual / 0` must become 0, not inf/NaN. A real load without balancing power keeps its existing behaviour.
**Files:** `system_model.py` (`ElectricPowerSystem` load calculation) · **Scope:** XS

### Phase 2: machinery-system-structure

#### T5 — Proto
`OrganicRankineCycle` message; `Engine.orc = 16`, `MultiFuelEngine.orc = 12`, `MachinerySystem.fuel_cell_orc = 10`, `FeemsResult.energy_input_waste_heat_recovery_total_mj = 17`. Recompile with `compile_proto.sh`.
**Scope:** S

#### T6 — proto → feems
`collect_orcs_on_switchboards` walks the shaft lines and returns feems ORCs by switchboard id; `convert_proto_electric_system_to_feems` / `convert_proto_switchboard_to_feems` accept these as additional components. Wired for MECHANICAL and HYBRID propulsion. Unknown switchboard ids raise `ValueError`.
**Files:** `convert_to_feems.py` · **Scope:** M

#### T7 — feems → proto
Skip ORC components when converting switchboards back to proto (they are stored on their host engine). Accept the ORC type in `FEEMSResultConverter`.
**Files:** `convert_to_protobuf.py`, `convert_feems_result_to_proto.py` · **Scope:** XS

### Phase 3: Docs

#### T8 — API references
`docs/api/feems/API_REFERENCE.md`, `docs/api/machinery-system-structure/API_REFERENCE.md`.

## Verification

```bash
uv run pytest feems/tests machinery-system-structure/tests RunFEEMSSim/tests
uv run ruff check feems/feems machinery-system-structure/MachSysS
```
