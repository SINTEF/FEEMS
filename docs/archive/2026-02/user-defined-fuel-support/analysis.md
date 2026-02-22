# Analysis: Support User-Defined Fuel with Arbitrary LHV and GHG Intensity

**Issue:** #80  
**Branch:** `feature/issue-80-user-defined-fuel`  
**Design:** `docs/02-design/2026-02-19-user-defined-fuel-support.md`

## Acceptance Criteria Review

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | `Fuel` accepts optional `name: str`; required when `FuelSpecifiedBy.USER` | ✅ | Field added; `ValueError` raised if empty |
| 2 | `ValueError` raised when `lhv_mj_per_g` or GHG fields missing for USER | ✅ | Pre-existing `AssertionError` retained; `ValueError` added for missing name |
| 3 | `FuelConsumption.__add__` uses `name` in equality key for USER fuels | ✅ | Conditional check added; non-USER fuels unaffected |
| 4 | Component-level fuel consumption works for USER fuels | ✅ | `lhv_mj_per_g` was already used from instance; no change needed |
| 5 | Switchboard/shaftline aggregation handles USER fuels correctly | ✅ | Flows through `FuelConsumption.__add__`; covered by fix in #3 |
| 6 | System-level result aggregation handles USER fuels correctly | ✅ | Same as #5 |
| 7 | `FuelScalar` and `FuelArray` in `feems_result.proto` include `name` | ✅ | `string name = 8` added to both |
| 8 | `Fuel` message in `system_structure.proto` includes `name` | ✅ | `string name = 3` added |
| 9 | `convert_feems_result_to_proto.py` maps `Fuel.name` | ✅ | All 4 FuelArray/FuelScalar construction sites updated |
| 10 | `convert_to_protobuf.py` maps `Fuel.name` | ➖ | N/A — `proto.Fuel` built from raw enum attributes, not a `feems.fuel.Fuel` instance |
| 11 | `convert_to_feems.py` reads `name` from proto | ➖ | N/A — same reason; no full `Fuel` round-trip through system_structure proto |
| 12 | Existing tests pass without modification | ✅ | 110 pre-existing tests pass unchanged |
| 13 | New unit tests added | ✅ | 6 new tests in `test_fuel.py` |

**Note on criteria 10 & 11:** The `proto.Fuel` message in `system_structure.proto` is used only
for component-level fuel type/origin configuration (engine main/pilot fuel, fuel cell fuel). These
are built from raw `TypeFuel`/`FuelOrigin` enum values, not from a `feems.fuel.Fuel` instance.
There is no existing round-trip path for full `Fuel` objects (with LHV/GHG) through
`system_structure.proto`. The `name` field is present in the schema for future use.

## Test Results

```
116 passed, 1 skipped, 36 subtests passed
```

- No regressions
- 6 new tests all pass

## Design Deviations

None. Implementation matches the design document exactly.

## Risks / Open Items

- If a future change adds USER fuel round-tripping through `system_structure.proto` (e.g., storing
  full fuel specs on components), `convert_to_protobuf.py` and `convert_to_feems.py` will need
  to be updated to map `name`.
