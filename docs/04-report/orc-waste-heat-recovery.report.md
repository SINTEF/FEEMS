# Report: Organic Rankine Cycle (ORC) Waste-Heat Recovery

**Issue:** #104
**Branch:** `feat/ORC-ai-workflow`
**Date:** 2026-11-02
**Author:** Lukas Kistner

---

## Outcome

feems and the system structure can now represent an organic Rankine cycle that recovers electric power from waste heat:

| Host | Proto field | `switchboard_id` | In feems |
|------|-------------|------------------|----------|
| Main engine | `Engine.orc` (16) / `MultiFuelEngine.orc` (12) | > 0 | `OrganicRankineCycle` power source on that switchboard, fixed setpoint, no fuel |
| Genset engine | `Engine.orc` (16) | 0 | not converted; client lifts the genset BSFC curve |
| Fuel-cell group | `MachinerySystem.fuel_cell_orc` (10) | 0 | not converted; client lifts the fuel-cell efficiency |

Recovered electric energy is reported as `FEEMSResult.energy_input_waste_heat_recovery_total_mj` (proto `FeemsResult` field 17).

## Plan ↔ Outcome

All 8 plan tasks completed. Analysis match rate: **16/16 = 100 %**. One defect found at check time (zero-rated ORC) and fixed.

## Files Changed

### `feems/`
- `feems/feems/types_for_feems.py` — `TypeComponent.ORGANIC_RANKINE_CYCLE`, `FEEMSResult.energy_input_waste_heat_recovery_total_mj`.
- `feems/feems/components_model/component_electric.py` — `OrganicRankineCycle` class.
- `feems/feems/components_model/node.py` — energy-balance and operating-average branches.
- `feems/feems/system_model.py` — power-source registration; rounding-residual guard in the bus load calculation.

### `machinery-system-structure/`
- `proto/system_structure.proto` — `OrganicRankineCycle` message; host fields.
- `proto/feems_result.proto` — field 17.
- `MachSysS/*_pb2.py(i)` — regenerated.
- `MachSysS/convert_to_feems.py` — `convert_proto_orc_to_feems`, `collect_orcs_on_switchboards`, additional-component arguments on switchboard / electric-system conversion.
- `MachSysS/convert_to_protobuf.py` — skip ORC on switchboards.
- `MachSysS/convert_feems_result_to_proto.py` — accept ORC as a power source.

### Tests
- `feems/tests/test_system_simplified.py` — `TestOrganicRankineCycle` (5 tests).
- `machinery-system-structure/tests/test_convert_to_feems.py` — `TestConvertOrganicRankineCycle` (5 tests).

### Documentation
- `docs/backlog/2026-11-02-orc-waste-heat-recovery.md`
- `docs/01-plan/features/orc-waste-heat-recovery.plan.md`
- `docs/02-design/features/orc-waste-heat-recovery.design.md`
- `docs/03-analysis/orc-waste-heat-recovery.analysis.md`
- `docs/04-report/orc-waste-heat-recovery.report.md` (this file)
- `docs/api/feems/API_REFERENCE.md` — `OrganicRankineCycle`, new type and result field.
- `docs/api/machinery-system-structure/API_REFERENCE.md` — `OrganicRankineCycle` message, host fields, conversion rules.

## Test Results

| Suite | Result |
|-------|--------|
| `feems/tests/` | 274 passed + 1 skipped, 44 subtests |
| `machinery-system-structure/tests/` | 41 passed |
| `RunFEEMSSim/tests/` | 7 passed |
| **Total** | **322 passed**, 1 skipped |

## Backwards Compatibility

- **Proto:** new message and tags only; existing data reads as "no ORC".
- **API:** new enum value, new dataclass field with default, new optional keyword arguments; no existing signature changed.
- **Power balance:** changed only for |load| < 1e-6 kW with no balancing power online, which previously produced inf/NaN load ratios.

## Lessons / Notes Worth Carrying Forward

1. **Keep host-dependent physics out of feems.** The ORC output depends on host heat, which depends on host load, which feems computes. Solving that loop inside feems would need an iteration in the power balance. Letting the client compute the setpoint (main engine load is known from the propulsion demand) keeps feems linear and the component trivial.
2. **Fixed setpoints exposed a latent NaN.** Any fixed source that covers the whole bus load leaves a floating-point residual for zero balancing capacity. The guard helps all fixed sources, not only the ORC.
3. **Store attached equipment on its host.** Writing the ORC as a switchboard subsystem on feems → proto would have duplicated it on the next conversion; skipping it keeps the round trip stable.

## What's Next (Out of Scope)

- ORC-aware dispatch in `RunFEEMSSim` PMS (setpoint from main engine load).
- ORC on COGES / COGAS hosts.

## PDCA Status

| Phase | Doc | Status |
|-------|-----|--------|
| Plan | `docs/01-plan/features/orc-waste-heat-recovery.plan.md` | ✅ |
| Design | `docs/02-design/features/orc-waste-heat-recovery.design.md` | ✅ |
| Do | Code + tests in `feems/`, `machinery-system-structure/` | ✅ |
| Check | `docs/03-analysis/orc-waste-heat-recovery.analysis.md` (100 % match) | ✅ |
| Act | This report; ready to open PR | ✅ |

---

## Revision after review (2026-11-04)

Review of PR #105 (kevinksyTRD, Copilot) and the main developers' feedback led to the changes in
design §9: every ORC is a feems component (no host-curve lift), protobuf round trip keeps the ORC,
curtailment above the bus load, `InputError` for an ORC as balancing unit (basic PMS keeps ORCs off),
heat model on the component, `running_hours_orc_total_hr` (field 18), stubs regenerated with protoc 29.6.

| Suite | Result |
|---|---|
| `feems/tests` | 280 passed, 1 skipped |
| `machinery-system-structure/tests` | 50 passed |
| `RunFEEMSSim/tests` | 8 passed |
