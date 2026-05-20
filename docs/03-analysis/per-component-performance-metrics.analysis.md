# Analysis: Per-Component Performance Metrics

**Issue:** #97
**Plan:** `docs/01-plan/features/per-component-performance-metrics.plan.md`
**Design:** `docs/02-design/features/per-component-performance-metrics.design.md`
**Branch:** `feature/issue-97-per-component-metrics`
**Date:** 2026-05-20

---

## Scope of Analysis

Verify that the implementation matches the design and the user-approved plan, and that
no existing behaviour has regressed.

## Design ↔ Implementation Match

| Design item                                                                     | Implementation                                                                                                  | Status |
|---------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|--------|
| 4 new fields on `FEEMSResult` dataclass                                         | `feems/feems/types_for_feems.py:85-88` (`operating_avg_power_kw`, …, defaults `0.0`)                            | ✅ |
| Single source of truth for DataFrame column labels                              | `OPERATING_AVG_COLUMNS` tuple in `types_for_feems.py:17-22`; imported by both `node.py` and `system_model.py`   | ✅ |
| `__merge` uses `max(self, other)` for the 4 fields                              | `types_for_feems.py:134-135` adds an explicit branch using `_OPERATING_AVG_FIELDS` frozenset                    | ✅ |
| Helpers `_time_weighted_avg_magnitude_kw`, `_efficiency_from_totals`, `_sfc_g_per_kwh` | `feems/feems/components_model/node.py:71-99`, `102-106`, `109-113`                                              | ✅ |
| `_integrate_kw_signal_to_mj` helper to guard against `IntegrationError`         | `node.py:116-132`                                                                                               | ✅ |
| Dispatch function `_assign_operating_avg_metrics`                               | `node.py` invoked at the end of `get_fuel_emission_energy_balance_for_component`                                | ✅ |
| Per-component branches: engine, genset, fuel-cell, COGES, PTI/PTO, generator, ENERGY_STORAGE, shore, loads | All branches present with the design-doc formulas                                                               | ✅ |
| PTI/PTO mask: PTO=`power_input<0`, PTI=`power_input>0`                          | Matches existing branch in `node.py:284-331`                                                                    | ✅ |
| Switchboard DataFrame column list extended with `OPERATING_AVG_COLUMNS`         | `node.py` Switchboard assembly                                                                                  | ✅ |
| ShaftLine DataFrame column list extended                                        | `node.py` ShaftLine assembly                                                                                    | ✅ |
| Boiler `_BOILER_DETAIL_COLUMNS` extended; boiler detail_row populates 4 numeric fields | `feems/feems/system_model.py` `_calculate_boiler_result` extended                                               | ✅ |
| Boiler computes `power_kw` from `ṁ_steam × Δh`                                  | `system_model.py` — `steam_thermal_kw_series = np.atleast_1d(steam_kg_per_s) * boiler.delta_h_kj_per_kg`        | ✅ |
| Proto fields 16-19 added to `ResultPerComponent`                                | `machinery-system-structure/proto/feems_result.proto`                                                           | ✅ |
| Proto regenerated (`*_pb2.py`, `*_pb2.pyi`)                                     | `bash compile_proto.sh` ran cleanly; `feems_result_pb2.pyi:125-128` shows the new fields                        | ✅ |
| Converter mapping `_COLUMN_NAMES` extended                                      | `convert_feems_result_to_proto.py`                                                                              | ✅ |
| Unit tests for helpers + each component family                                  | `feems/tests/test_operating_avg_metrics.py` — 12 tests                                                          | ✅ |
| Boiler row test extension                                                       | `feems/tests/test_steam_boiler.py` — 5 new tests inside `TestBoilerDetailResult`                                | ✅ |
| Round-trip proto test                                                           | `machinery-system-structure/tests/test_convert_feems_result_to_proto.py::test_operating_avg_metrics_roundtrip_to_proto` | ✅ |

**Match rate: 16/16 = 100 %**

## Test Coverage Summary

| Suite                                | Count   | Status |
|--------------------------------------|---------|--------|
| `feems/tests/`                       | 262 + 1 skipped | ✅ pass |
| `machinery-system-structure/tests/`  | 36      | ✅ pass |
| `RunFEEMSSim/tests/`                 | 7       | ✅ pass |
| **Total**                            | **310** (+ 1 skip, 43 subtests) | ✅ pass |

`uv run ruff check` clean for the source tree we modified.

New test files / new tests:

- `feems/tests/test_operating_avg_metrics.py` — 12 tests (helpers, main engine, PTI/PTO, OtherLoad, ShorePower)
- `feems/tests/test_steam_boiler.py` `TestBoilerDetailResult` — 5 new tests
- `machinery-system-structure/tests/test_convert_feems_result_to_proto.py` — 1 new round-trip test

## Decisions Confirmed at Implementation Time

1. **PTI/PTO magnitude basis** — both metrics use `|power_input|` (electric side) for symmetry. Documented in `_assign_operating_avg_metrics` PTI/PTO branch.
2. **Engine SFC / efficiency basis** — `component.engine.power_output` (engine-side shaft kW, after gearbox correction for `MAIN_ENGINE_WITH_GEARBOX`), matching the existing `energy_consumption_mechanical_total_mj` convention in `node.py` ShaftLine wiring.
3. **`integrate_data` single-point warning** — the existing function logs a warning when integrating a one-point series; this is unchanged. Our helper wraps the call in a `try`/`except IntegrationError` to harden against pathological inputs without changing existing behaviour.
4. **Aggregate-level values** — `FEEMSResult` aggregated through `sum_with_freeze_duration` carries the *max* of contributors for the 4 fields. These are not part of the public surface; only the per-row `detail_result` values are intended for consumers.

## Risks / Open Items

None. All design-doc items implemented and verified.

## Backwards Compatibility — Verified

- Proto fields 16-19 are additive; existing proto consumers ignore them, new consumers read `0.0` for old data.
- DataFrame column order: new columns appended at the end; existing positional access via `to_list_for_*_component` is unaffected.
- `FEEMSResult` dataclass: new fields default to `0.0`; constructors without these kwargs unchanged.
- All 310 pre-existing tests continue to pass without modification.
