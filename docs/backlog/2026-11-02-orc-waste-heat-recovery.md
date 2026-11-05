# [BACKLOG] Organic Rankine Cycle (ORC) Waste-Heat Recovery

## Summary

Add an organic Rankine cycle (ORC) to the system structure and to feems so that electric power recovered from engine or fuel-cell waste heat can be modelled. A main engine ORC feeds a switchboard as a fuel-free electric power source; a genset or fuel-cell ORC is stored on its host and integrated by the client (no separate feems component).

## Context / Motivation

Waste-heat recovery with ORC units is a common efficiency measure in ship machinery design studies (KSOE Machinery Design Lab). Without a model for it, a design tool cannot show the fuel saving an ORC brings, nor charge its CAPEX against that saving.

Two integration patterns are needed:

- **Main engine ORC** — the propulsion engine's exhaust heat drives an ORC generator that feeds the ship's switchboard. Its output depends on the engine load, not on the electric demand, so it is a fixed-setpoint power source that reduces the load on the gensets. It burns no fuel.
- **Genset / fuel-cell ORC** — the ORC sits on the same unit that already supplies the switchboard. The client folds the recovered power into the host's efficiency curve; feems only needs to carry the data in the proto.

## Acceptance Criteria

### `feems`

- [x] New `OrganicRankineCycle` electric component (`TypeComponent.ORGANIC_RANKINE_CYCLE = 31`, `TypePower.POWER_SOURCE`) accepted as a power source by `ElectricPowerSystem`
- [x] A fixed ORC setpoint (`load_sharing_mode = power / rated_power`, `status = 1`) reduces the power of the load-balancing units by the ORC output
- [x] The ORC burns no fuel; its electric energy is reported as `FEEMSResult.energy_input_waste_heat_recovery_total_mj`, and `operating_avg_power_kw` is filled
- [x] Power balance: when fixed sources cover the load up to a rounding residual and no balancing power is available, the load ratio is zero, not NaN/inf; a real load without balancing power behaves as before

### `machinery-system-structure`

- [x] New `OrganicRankineCycle` proto message (rated power, rated efficiency, relative efficiency curve, waste heat fraction, unit price, uid, switchboard id, name)
- [x] `Engine.orc = 16`, `MultiFuelEngine.orc = 12`, `MachinerySystem.fuel_cell_orc = 10`; `FeemsResult.energy_input_waste_heat_recovery_total_mj = 17` — all additive
- [x] `compile_proto.sh` re-run, generated `*_pb2.py` / `*_pb2.pyi` committed
- [x] proto → feems: a main engine ORC with `switchboard_id > 0` and `rated_power_kw > 0` becomes an `OrganicRankineCycle` on that switchboard (MECHANICAL and HYBRID propulsion)
- [x] proto → feems: an ORC with `switchboard_id == 0` (integrated) or without rated power is not converted
- [x] proto → feems: an ORC referring to a non-existent switchboard raises `ValueError`
- [x] feems → proto: ORC components are skipped on switchboards (they live on their host engine); the feems result converter accepts the ORC as a power source

### Documentation

- [x] Plan doc in `docs/01-plan/features/`
- [x] Design doc in `docs/02-design/features/`
- [x] Analysis doc in `docs/03-analysis/`
- [x] Report doc in `docs/04-report/`
- [x] API reference updated for `feems` and `machinery-system-structure`

### Tests

- [x] `feems/tests/test_system_simplified.py::TestOrganicRankineCycle` — power source, setpoint, no fuel, rounding residual, unchanged real-load behaviour
- [x] `machinery-system-structure/tests/test_convert_to_feems.py::TestConvertOrganicRankineCycle` — conversion, integrated skip, zero-rating skip, unknown switchboard, round trip

## Scope

- **In scope**: ORC component and its result field; proto messages and fields; proto ↔ feems conversion; power-balance robustness for fixed sources; tests; docs.
- **Out of scope**:
  - ORC physics (heat available vs. host load, part-load efficiency, cut-in) — computed by the client from the proto data; feems receives the resulting setpoint
  - Lifting genset / fuel-cell efficiency curves by the ORC gain — done by the client
  - Automatic ORC dispatch in `RunFEEMSSim` PMS
  - ORC on COGES / COGAS hosts

## Package(s) Affected

- [x] feems
- [x] machinery-system-structure
- [ ] RunFEEMSSim

## Priority

Medium

## Issue

#104

## Status

In Progress

## PDCA Links

- Plan doc: `docs/01-plan/features/orc-waste-heat-recovery.plan.md`
- Design doc: `docs/02-design/features/orc-waste-heat-recovery.design.md`
- Analysis: `docs/03-analysis/orc-waste-heat-recovery.analysis.md`
- Report: `docs/04-report/orc-waste-heat-recovery.report.md`
