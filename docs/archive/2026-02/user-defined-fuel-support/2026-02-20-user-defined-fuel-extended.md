# Report: User-Defined Fuel — Extended Implementation (Issue #80, Phase 2)

**Issue:** #80
**Branch:** `feature/issue-80-user-defined-fuel`
**Date:** 2026-02-20
**Match Rate:** 95% (exceeds 90% threshold)
**Status:** Complete — ready to commit and PR

---

## Summary

This phase extends the Phase-1 user-defined-fuel work (Fuel.name, proto, aggregation) to thread
`user_defined_fuels` through the entire calculation stack — from system-level API all the way
down to individual component run-points. It also introduces a per-component override dict
(`user_defined_fuels_by_component`) so callers can assign different custom fuels to different
engines/gensets/fuel cells within the same simulation call.

All 131 workspace tests pass with no regressions.

---

## What Was Delivered

### Sub-feature 1: `find_user_fuel()` helper (`fuel.py`)

New public function that looks up a `Fuel` with matching `(fuel_type, origin)` from a list:

```python
def find_user_fuel(
    user_defined_fuels: Optional[List[Fuel]],
    fuel_type: TypeFuel,
    fuel_origin: FuelOrigin,
) -> Optional[Fuel]:
```

Returns `None` when the list is `None`/empty or no entry matches. Used internally at every
component type to resolve the effective user-defined fuel.

### Sub-feature 2: USER fuel TTW GHG factor short-circuit (`fuel.py`)

`Fuel.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel()` now handles `FuelSpecifiedBy.USER`
explicitly: it reads `ghg_emission_factor_tank_to_wake[0]` directly, bypassing the
`fuel_consumer_class` lookup that is irrelevant for user-defined fuels. The `exclude_slip` flag
is still respected.

### Sub-feature 3: `user_defined_fuels` global threading

The parameter `user_defined_fuels: Optional[List[Fuel]]` was added to the public API of every
calculation method in the stack:

| Layer | Methods updated |
|-------|----------------|
| Component (node.py) | `get_fuel_emission_energy_balance_for_component` |
| Switchboard (node.py) | `get_fuel_energy_consumption_running_time`, `…_without_details` |
| ShaftLine (node.py) | `get_fuel_energy_consumption_running_time` |
| ElectricPowerSystem | `get_fuel_consumption`, `get_fuel_consumption_without_details` |
| MechanicalPropulsionSystem | `get_fuel_consumption` |
| HybridPropulsionSystem | `get_fuel_consumption` |
| MechanicalPropulsionSystemWithElectricPowerSystem | `get_fuel_consumption` |

### Sub-feature 4: `user_defined_fuels_by_component` per-component override

A new optional parameter `user_defined_fuels_by_component: Optional[Dict[str, List[Fuel]]]` is
added alongside `user_defined_fuels` at every layer listed above.

Resolution logic at the component boundary:
1. Look up `component.name` in the dict — if found, use that list.
2. If not found (or dict is `None`), fall back to the global `user_defined_fuels` list.
3. If neither is provided, use regulation-table lookup as before.

This allows, for example, running two gensets with different custom diesel blends in a single
`get_fuel_consumption()` call.

---

## Files Changed

| File | Change |
|------|--------|
| `feems/feems/fuel.py` | `find_user_fuel()` + USER fuel TTW short-circuit |
| `feems/feems/components_model/node.py` | `user_defined_fuels_by_component` added to 5 methods; resolution logic in component function |
| `feems/feems/system_model.py` | `user_defined_fuels_by_component` added to 5 system-level methods |
| `feems/tests/test_fuel.py` | 5 new `find_user_fuel` tests |
| `feems/tests/test_components.py` | `TestUserDefinedFuels` class — 10 new tests |

*(Component-level threading of `user_defined_fuels` in `component_electric.py` and*
*`component_mechanical.py` was committed in `06f4b4f` and is prerequisite for this phase.)*

---

## Test Results

```
131 passed, 1 skipped, 36 subtests passed  (full monorepo)
```

### New tests (15 total)

**`test_fuel.py` — `find_user_fuel` (5 tests):**
- `None` input, empty list, matching fuel, no match, first-entry-on-duplicate

**`test_components.py::TestUserDefinedFuels` (10 tests):**
- Engine: user factors applied, fallback to IMO when no match
- EngineDualFuel: both fuels get USER factors; partial match (main USER, pilot IMO)
- FuelCell: user factors applied; fallback to IMO
- Genset: `user_defined_fuels` propagated to inner engine
- `user_defined_fuels_by_component`: override applied for named component; global fallback for unmatched; per-component wins over global

---

## Gap Analysis Summary

**Match Rate: 95%** — exceeds 90% threshold, no iteration required.

| Gap | Severity | Decision |
|-----|----------|----------|
| `EngineMultiFuel` not explicitly tested with user fuels | Low | Shares `find_user_fuel` code path; acceptable |
| `user_defined_fuels_by_component` not tested at switchboard/system level | Low | Code is a pass-through; low risk |
| No formal design doc for extended sub-features | Info | Documented in analysis and this report |

---

## Open Items / Follow-up

1. **`simulation_interface.py`** — `user_defined_fuels_by_component` is not yet exposed in the
   top-level simulation interface. Callers using that interface cannot reach the feature yet.
   Tracked for a follow-up change before or alongside the PR review.

2. **`EngineMultiFuel` explicit test** — Low priority; can be added in a follow-up commit on
   the same branch before merge.

---

## PDCA Links

- Backlog: `docs/backlog/2026-02-19-user-defined-fuel-support.md`
- Plan: `docs/01-plan/2026-02-19-user-defined-fuel-support.md`
- Design: `docs/02-design/2026-02-19-user-defined-fuel-support.md`
- Phase-1 Analysis: `docs/03-analysis/2026-02-19-user-defined-fuel-support.md`
- Phase-1 Report: `docs/04-report/2026-02-19-user-defined-fuel-support.md`
- Phase-2 Analysis: `docs/03-analysis/2026-02-20-user-defined-fuel-extended.md`
- Phase-2 Report: `docs/04-report/2026-02-20-user-defined-fuel-extended.md` *(this file)*
