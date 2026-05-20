# Implementation Plan: Per-Component Performance Metrics

**Issue:** #97
**Backlog:** `docs/backlog/2026-05-20-per-component-performance-metrics.md`
**Branch:** `feature/issue-97-per-component-metrics`

---

## Overview

Add four operating-average scalars to every row of `FEEMSResult.detail_result` and the matching `ResultPerComponent` proto. Averages are time-weighted over the component's on-state timesteps only, so values are not diluted by shut-down periods. Non-applicable metrics are reported as `0.0`.

| Field                              | DataFrame column                       | Proto ID |
|------------------------------------|----------------------------------------|----------|
| `operating_avg_power_kw`           | `operating avg power [kW]`             | 16       |
| `operating_avg_reversible_power_kw`| `operating avg reversible power [kW]`  | 17       |
| `operating_avg_efficiency`         | `operating avg efficiency`             | 18       |
| `operating_avg_sfc_g_per_kwh`      | `operating avg SFC [g/kWh]`            | 19       |

## Architecture Decisions

- **Mask = `power_output != 0`** for all components (matches existing `running_hours_h` semantics in `node.py:177-181`).
- **PTI/PTO is the only directional component**: PTO mask = `power_input < 0`, PTI mask = `power_input > 0`. Both metrics reported as positive magnitudes.
- **Compute the scalars inside `get_fuel_emission_energy_balance_for_component`** in `feems/feems/components_model/node.py`. That function already classifies every component type and has access to the relevant run-points, fuel flow, and on-state masks — no new traversal needed.
- **Carry the scalars on the per-component `FEEMSResult`** (new fields on the dataclass) so the existing `sum_with_freeze_duration` aggregation continues to work; aggregation of these new fields uses `max(self, other)` semantics (only one component per row), keeping the math local.
- **Boiler handled separately** in `system_model.py:_calculate_boiler_result` because boilers are outside the switchboard / shaft-line topology — same as the existing per-row code for engines/gensets.
- **Proto field IDs 16-19** are additive; no existing tag is changed → wire-compatible.

## Dependency Graph

```
T1 add fields to FEEMSResult dataclass
 └─► T2 compute scalars in get_fuel_emission_energy_balance_for_component
      ├─► T3 wire columns through Switchboard.get_fuel_energy_consumption_running_time
      ├─► T4 wire columns through ShaftLine.get_fuel_energy_consumption_running_time
      └─► T5 wire columns through MachinerySystem._calculate_boiler_result
           └─► ═══ CHECKPOINT A: feems-side tests green ═══
                ├─► T6 proto: 4 new fields + recompile
                │    └─► T7 converter: _COLUMN_NAMES mapping + round-trip test
                │         └─► ═══ CHECKPOINT B: proto round-trip green ═══
                │              └─► T9 API reference updates
                └─► T8 feems unit tests across component families
                     └─► converges at CHECKPOINT B
```

T6-T7 (proto) is independent of T8 (feems tests) after CHECKPOINT A and can run in parallel.

## Task List

### Phase 1: Foundation

#### Task T1 — Add new fields to `FEEMSResult` dataclass

**Description:** Add four float fields to `FEEMSResult` in `feems/feems/types_for_feems.py` so the existing aggregation pipeline can carry them through. Default to `0.0`. Update `__merge` to take `max(self, other)` for these fields (each row is produced by exactly one component, so only one side is non-zero at any time).

**Acceptance criteria:**
- [ ] Four new attributes on `FEEMSResult`: `operating_avg_power_kw`, `operating_avg_reversible_power_kw`, `operating_avg_efficiency`, `operating_avg_sfc_g_per_kwh`
- [ ] `__merge` handles them without `if field_name == ...` proliferation — a `max` default branch is acceptable for now since per-row results don't overlap
- [ ] `sum_with_freeze_duration` and `sum_and_extend_duration` continue to behave identically for all existing fields

**Verification:** `uv run pytest feems/tests/ -x` (no behaviour regression on existing tests).

**Dependencies:** None.

**Files touched:** `feems/feems/types_for_feems.py`

**Estimated scope:** XS (1 file)

---

#### Task T2 — Compute scalars inside `get_fuel_emission_energy_balance_for_component`

**Description:** For each component-type branch of the function in `node.py`, compute the four scalars from the data already available (run-point objects, power signals, integrated fuel/energy). Write a small helper `_compute_operating_averages(power_signal, time_interval_s, mask)` that returns a `(avg_power, avg_eff, avg_sfc)` tuple, then call it with branch-specific arguments. PTI/PTO calls it twice with different masks and assigns to `operating_avg_power_kw` (PTO) and `operating_avg_reversible_power_kw` (PTI).

**Acceptance criteria:**
- [ ] Helper `_compute_operating_avg_power_kw` returns time-weighted mean of `|power|` on the masked subset; returns `0.0` if mask is all-False
- [ ] Helper `_compute_operating_avg_sfc_g_per_kwh` accepts integrated fuel kg and on-state energy kWh; returns `0.0` if energy is 0
- [ ] Helper `_compute_operating_avg_efficiency` accepts energy_out_MJ and energy_in_MJ; returns `0.0` if input is 0; clamps to `[0, 1]`
- [ ] Main-engine branch sets all three (efficiency from BSFC × LHV; SFC = total_fuel_g / shaft_kWh)
- [ ] Genset branch uses electric output as the "out" energy
- [ ] FuelCell branch uses electric output
- [ ] COGES branch uses electric output (COGAS run point)
- [ ] PTI/PTO branch produces correct PTO/PTI split using existing `index_pti_mode` / `index_pto_mode`
- [ ] OtherLoad / Propeller / Propulsion / ShorePower / Battery / SuperCap branches set `operating_avg_power_kw` and leave the rest at `0.0`

**Verification:** Component-family unit tests added in T8 pass.

**Dependencies:** T1.

**Files touched:** `feems/feems/components_model/node.py` (extend the function; add the small helpers in the same module).

**Estimated scope:** M (1 file, multiple branches)

---

### Phase 2: Wire Through DataFrame Assemblies

#### Task T3 — Switchboard column wiring

**Description:** In `Switchboard.get_fuel_energy_consumption_running_time` (`node.py` ~880-977), append the 4 new labels to `column_names` and the matching values to `data_to_add` for each component row.

**Acceptance criteria:**
- [ ] `column_names` extended in canonical order: power, reversible_power, efficiency, SFC
- [ ] `data_to_add` reads from the per-component `res_comp.operating_avg_*` attributes
- [ ] No column shadowing; pandas concat still works

**Verification:** Switchboard-level unit test in T8.

**Dependencies:** T2.

**Files touched:** `feems/feems/components_model/node.py`

**Estimated scope:** XS (~10 lines)

---

#### Task T4 — ShaftLine column wiring

**Description:** Mirror T3 for `ShaftLine.get_fuel_energy_consumption_running_time` (`node.py` ~1370-1450).

**Acceptance criteria:**
- [ ] `column_names` extended identically to T3
- [ ] `data_to_add` reads `res_comp.operating_avg_*`
- [ ] Existing shaftline tests still pass

**Verification:** Existing `feems/tests/` pass; new shaftline test in T8.

**Dependencies:** T2.

**Files touched:** `feems/feems/components_model/node.py`

**Estimated scope:** XS (~10 lines)

---

#### Task T5 — Boiler detail row

**Description:** In `MachinerySystem._calculate_boiler_result` (`system_model.py` ~294-376), extend `_BOILER_DETAIL_COLUMNS` with the 4 new labels and append values to the `detail_row` `pd.Series`. Use `BoilerRunPoint.thermal_efficiency` directly; compute steam-thermal kW from `ṁ_steam · Δh`; SFC = `g_fuel / kWh_steam`.

**Acceptance criteria:**
- [ ] `_BOILER_DETAIL_COLUMNS` (module-level constant) has 4 new entries in the same order
- [ ] Boiler row contains numeric values (no Nones)
- [ ] Reversible power is always `0.0` for boilers
- [ ] Existing `test_steam_boiler.py` continues to pass after the columns are added (no assertion shapes change unless we extend them in T8)

**Verification:** `uv run pytest feems/tests/test_steam_boiler.py -x`.

**Dependencies:** T2 (only because we want the canonical column order in one place — we'll define a constant in `node.py` and import it here, or duplicate the labels — see Design doc for decision).

**Files touched:** `feems/feems/system_model.py`

**Estimated scope:** XS

---

### Checkpoint A — feems-side complete

- [ ] `uv run pytest feems/tests/` passes
- [ ] `uv run ruff check feems/` passes
- [ ] Manual: `feems_result.detail_result.columns` includes the 4 new columns

---

### Phase 3: Proto + Converter

#### Task T6 — Proto schema + recompile

**Description:** Add four `double` fields to `ResultPerComponent` in `machinery-system-structure/proto/feems_result.proto`, IDs 16-19. Run `./compile_proto.sh` and commit the regenerated `*_pb2.py` / `*_pb2.pyi`.

**Acceptance criteria:**
- [ ] Proto field IDs 16, 17, 18, 19 used in this order — never reuse
- [ ] `compile_proto.sh` succeeds without manual edits
- [ ] `MachSysS/feems_result_pb2.pyi` shows the new attributes
- [ ] Existing proto tests continue to pass

**Verification:** `cd machinery-system-structure && ./compile_proto.sh && uv run pytest machinery-system-structure/tests/`.

**Dependencies:** Checkpoint A.

**Files touched:**
- `machinery-system-structure/proto/feems_result.proto`
- generated: `machinery-system-structure/MachSysS/feems_result_pb2.py`, `*.pyi`

**Estimated scope:** XS

---

#### Task T7 — Converter mapping + round-trip test

**Description:** In `convert_feems_result_to_proto.py`, extend `_COLUMN_NAMES` with the 4 new (label → proto field) mappings. Add a round-trip integration test that builds a small FEEMSResult, converts to proto, and asserts the 4 fields survive.

**Acceptance criteria:**
- [ ] `_COLUMN_NAMES` has 4 new entries
- [ ] Existing converter still serialises a result without raising
- [ ] New test in `machinery-system-structure/tests/` builds a minimal `FEEMSResult` with `detail_result` populated, converts via `FEEMSResultConverter.get_feems_result_proto(...)`, and asserts `detailed_result[i].operating_avg_*` round-trip values

**Verification:** `uv run pytest machinery-system-structure/tests/`.

**Dependencies:** T6.

**Files touched:**
- `machinery-system-structure/MachSysS/convert_feems_result_to_proto.py`
- `machinery-system-structure/tests/test_<existing or new>.py`

**Estimated scope:** S

---

### Checkpoint B — Proto round-trip green

- [ ] `uv run pytest` all-green at repo root
- [ ] `uv run ruff check` clean
- [ ] Round-trip test asserts each of the 4 new fields

---

### Phase 4: Tests Across Component Families

#### Task T8 — Component-family unit tests

**Description:** Add focused unit tests in `feems/tests/` covering one specimen per component family. Each test instantiates the component, drives a known `power_output` signal with at least one off-period to validate on-state masking, calls `get_fuel_emission_energy_balance_for_component`, and asserts the four scalars match closed-form expectations.

**Specimens:**
- MainEngine (constant load with 50 % off-time)
- Genset (variable load)
- FuelCell (constant load)
- PTI/PTO (signal that crosses zero — covers both modes in one fixture)
- OtherLoad (validates `operating_avg_power_kw` only; others `0.0`)

**Acceptance criteria:**
- [ ] One test function per specimen
- [ ] `operating_avg_power_kw` validated to ≤ 1e-6 relative tolerance
- [ ] `operating_avg_efficiency` validated against analytic formula
- [ ] `operating_avg_sfc_g_per_kwh` validated against analytic formula
- [ ] PTI/PTO test asserts both `operating_avg_power_kw` AND `operating_avg_reversible_power_kw` are populated correctly
- [ ] OtherLoad test asserts `efficiency == 0.0` and `sfc == 0.0`

**Verification:** `uv run pytest feems/tests/test_node.py -x -k operating_avg`.

**Dependencies:** Checkpoint A.

**Files touched:** `feems/tests/test_node.py` (or a new `test_operating_averages.py`)

**Estimated scope:** M

---

#### Task T8b — Boiler detail-row test extension

**Description:** Extend `feems/tests/test_steam_boiler.py` to assert the 4 new columns on the boiler row of `detail_result` after a system-level calculation.

**Acceptance criteria:**
- [ ] Assertion: `operating_avg_power_kw == steam_kw_thermal` (within tol)
- [ ] Assertion: `operating_avg_efficiency == BoilerRunPoint.thermal_efficiency` average
- [ ] Assertion: `operating_avg_reversible_power_kw == 0.0`
- [ ] Existing assertions in the file are not weakened

**Verification:** `uv run pytest feems/tests/test_steam_boiler.py -x`.

**Dependencies:** T5.

**Files touched:** `feems/tests/test_steam_boiler.py`

**Estimated scope:** XS

---

### Phase 5: Documentation

#### Task T9 — API reference updates

**Description:** Document the 4 new fields in `docs/api/feems/API_REFERENCE.md` (under `FEEMSResult.detail_result` columns) and `docs/api/machinery-system-structure/API_REFERENCE.md` (under `ResultPerComponent`).

**Acceptance criteria:**
- [ ] Each of the 4 fields has a one-line definition, unit, on-state semantics
- [ ] Per-component matrix from the backlog reproduced in the feems doc
- [ ] Proto field IDs documented in MachSysS doc

**Verification:** Markdown renders; entries match implementation.

**Dependencies:** All implementation complete (so signatures are stable).

**Files touched:**
- `docs/api/feems/API_REFERENCE.md`
- `docs/api/machinery-system-structure/API_REFERENCE.md`

**Estimated scope:** S

---

### Checkpoint C — Ready for review

- [ ] All tests green
- [ ] `uv run ruff check` clean
- [ ] API ref updated
- [ ] Analysis doc written (`docs/03-analysis/per-component-performance-metrics.analysis.md`)
- [ ] Report doc written (`docs/04-report/per-component-performance-metrics.report.md`)

---

## Risks and Mitigations

| Risk                                                                                       | Impact | Mitigation                                                                                                                       |
|--------------------------------------------------------------------------------------------|--------|----------------------------------------------------------------------------------------------------------------------------------|
| Efficiency formula ambiguity for components without a documented efficiency curve          | Med    | Default such branches to `0.0` and document explicitly. Don't fabricate a number from indirect signals.                          |
| PTI/PTO direction convention mismatch with existing code                                   | High   | Re-use the existing `index_pti_mode` / `index_pto_mode` masks in `node.py:284-331` verbatim. Don't redefine signs.               |
| Proto field-ID collision if another branch concurrently adds a field to `ResultPerComponent` | Low    | Field IDs 16-19 are reserved by this PR; check on rebase before merge.                                                           |
| `detail_result` consumers downstream that index columns positionally                       | Med    | Append-only column order; existing positions preserved. Document the new column order in API ref.                                |
| LHV access for SFC/efficiency depends on `multi_fuel_consumption_kg.fuels[i].lhv_mj_per_g` | Low    | Reuse `fuel_energy_total_mj` pattern already in `FEEMSResult` (see `types_for_feems.py:69-74`).                                  |

## Open Questions

- *None — all decisions resolved in the approved plan thread.*

## Verification Pre-flight

- [x] Every task has acceptance criteria
- [x] Every task has a verification command
- [x] Task dependencies are explicit
- [x] No task touches more than ~3 files
- [x] Checkpoints exist between phases
- [x] User has reviewed and approved the plan (see conversation 2026-05-20)
