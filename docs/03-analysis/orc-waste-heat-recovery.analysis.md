# Analysis: Organic Rankine Cycle (ORC) Waste-Heat Recovery

**Issue:** #104
**Plan:** `docs/01-plan/features/orc-waste-heat-recovery.plan.md`
**Design:** `docs/02-design/features/orc-waste-heat-recovery.design.md`
**Branch:** `feat/ORC-ai-workflow`
**Date:** 2026-11-02

---

## Scope of Analysis

Verify that the implementation matches the design, that no existing behaviour regressed, and that the feature works end to end in the client that drives it (KSOE Machinery Design Lab).

## Design ↔ Implementation Match

| Design item | Implementation | Status |
|-------------|----------------|--------|
| `TypeComponent.ORGANIC_RANKINE_CYCLE = 31` | `feems/feems/types_for_feems.py:208` | ✅ |
| `FEEMSResult.energy_input_waste_heat_recovery_total_mj` | `types_for_feems.py` (default `0.0`) | ✅ |
| `OrganicRankineCycle(ElectricComponent)`, `POWER_SOURCE` | `feems/feems/components_model/component_electric.py:997` | ✅ |
| Accepted as power source in `ElectricPowerSystem` | `feems/feems/system_model.py:463` | ✅ |
| Energy balance branch, no fuel | `feems/feems/components_model/node.py:499` | ✅ |
| `operating_avg_power_kw` for the ORC | `node.py:648` | ✅ |
| Rounding residual without balancing power → zero load | `system_model.py:1048-1049` | ✅ |
| Proto `OrganicRankineCycle` + `Engine.orc` 16, `MultiFuelEngine.orc` 12, `MachinerySystem.fuel_cell_orc` 10 | `machinery-system-structure/proto/system_structure.proto` | ✅ |
| `FeemsResult.energy_input_waste_heat_recovery_total_mj = 17` | `machinery-system-structure/proto/feems_result.proto` | ✅ |
| Stubs regenerated | `MachSysS/system_structure_pb2.py(i)`, `feems_result_pb2.py(i)` | ✅ |
| `collect_orcs_on_switchboards` (skip `switchboard_id == 0`, `rated_power_kw <= 0`) | `MachSysS/convert_to_feems.py:711` | ✅ |
| Unknown switchboard id → `ValueError` | `convert_proto_electric_system_to_feems` | ✅ |
| Wired for MECHANICAL and HYBRID | `convert_proto_propulsion_system_to_feems` | ✅ |
| feems → proto skips ORC on switchboards | `MachSysS/convert_to_protobuf.py:499` | ✅ |
| Result converter accepts ORC | `MachSysS/convert_feems_result_to_proto.py:209` | ✅ |
| API references | `docs/api/feems/API_REFERENCE.md`, `docs/api/machinery-system-structure/API_REFERENCE.md` | ✅ |

**Match rate: 16/16 = 100 %**

## Test Coverage Summary

Run on the branch (`2020ff8`):

| Suite | Count | Status |
|-------|-------|--------|
| `feems/tests/` | 274 passed + 1 skipped, 44 subtests | ✅ |
| `machinery-system-structure/tests/` | 41 passed | ✅ |
| `RunFEEMSSim/tests/` | 7 passed | ✅ |
| **Total** | **322 passed** (+ 1 skipped) | ✅ |

`uv run ruff check feems/feems machinery-system-structure/MachSysS`: one `I001` (import order) in `convert_to_feems.py`, which is also present on `main`; not introduced here.

New tests:

- `feems/tests/test_system_simplified.py::TestOrganicRankineCycle` — 5 tests
- `machinery-system-structure/tests/test_convert_to_feems.py::TestConvertOrganicRankineCycle` — 5 tests

## Client Integration Check

The KSOE Machinery Design Lab process library was run end to end against this branch (pinned by commit):

- Main engine ORC: the client computes the ORC setpoint from main engine shaft power and sets it through the variable PMS; the gensets' load drops by the ORC output and genset fuel decreases.
- Genset / fuel-cell ORC (`switchboard_id = 0`): not converted by feems; the client lifts the host BSFC / efficiency curve.
- Recovered energy appears in the result; ORC CAPEX is charged from `unit_price_usd`.

## Issues Found at Check Time

1. **Zero-rated main engine ORC crashed the conversion.** A proto with `orc.switchboard_id > 0` but `rated_power_kw = 0` (e.g. an ORC slot not yet sized) reached the feems component constructor, which rejects a zero rating with `InputError`. Fixed by skipping `rated_power_kw <= 0` in `collect_orcs_on_switchboards`; covered by `test_orc_without_rated_power_is_not_converted`.

## Risks / Open Items

- **Setpoint is the caller's responsibility.** An `OrganicRankineCycle` with `load_sharing_mode == 0` is treated by `ElectricPowerSystem` like any other load-sharing source. A PMS that assigns equal load sharing to all sources (e.g. the basic `RunFEEMSSim` PMS) would dispatch the ORC like a fuel-free genset. Clients must set the ORC setpoint explicitly (documented in the class docstring and the API reference). Automatic handling in `RunFEEMSSim` is out of scope.

## Backwards Compatibility — Verified

- Proto additions only; no tag renumbered.
- New optional keyword arguments on the conversion functions; existing calls unchanged.
- All pre-existing tests pass unmodified.
