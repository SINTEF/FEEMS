# Plan: Support User-Defined Fuel with Arbitrary LHV and GHG Intensity

**Issue:** #80  
**Branch:** `feature/issue-80-user-defined-fuel`

## Problem

`FuelSpecifiedBy.USER = 3` is reserved but not fully wired up. Two user-defined fuels with the
same `fuel_type` and `origin` but different LHV/GHG values are silently merged during aggregation
because the equality key `(fuel_type, origin, fuel_specified_by)` does not include a name.
Additionally, proto messages lack a `name` field for user-defined fuels.

## Approach

1. Add an optional `name: str` field to the `Fuel` dataclass; require it (non-empty) when
   `fuel_specified_by == FuelSpecifiedBy.USER`.
2. Update `FuelConsumption.__add__` to include `name` in the equality key for `USER` fuels.
3. Propagate `name` through `Fuel.copy` and `copy_except_mass_or_mass_fraction`.
4. Add `optional string name` to `FuelScalar` and `FuelArray` in `feems_result.proto`.
5. Add `optional string name` to `Fuel` in `system_structure.proto`.
6. Update conversion functions to map `name` in both directions.
7. Recompile proto bindings via `compile_proto.sh`.
8. Add unit tests for the new behaviour.

## Files to Change

| File | Change |
|------|--------|
| `feems/feems/fuel.py` | Add `name` field, validation, aggregation key |
| `machinery-system-structure/proto/feems_result.proto` | Add `name` to `FuelScalar`, `FuelArray` |
| `machinery-system-structure/proto/system_structure.proto` | Add `name` to `Fuel` |
| `machinery-system-structure/MachSysS/convert_feems_result_to_proto.py` | Map `name` |
| `machinery-system-structure/MachSysS/convert_to_protobuf.py` | Map `name` |
| `machinery-system-structure/MachSysS/convert_to_feems.py` | Read `name` |
| `feems/tests/` | New unit tests |

## Key Decisions

- `name` defaults to `""` for non-USER fuels; no existing callers break.
- `ValueError` (not `AssertionError`) raised when `name` is empty for USER fuels, consistent with
  the backlog acceptance criteria.
- Proto field tag for `name`: field `8` in `FuelScalar`/`FuelArray` (tags 1–7 are taken); field
  `3` in the `Fuel` message in `system_structure.proto` (tags 1–2 are taken).
