# [BACKLOG] Support User-Defined Fuel with Arbitrary LHV and GHG Intensity

## Summary
Extend the FEEMS fuel model to support fully user-defined fuels (`FuelSpecifiedBy.USER`) where
LHV and GHG intensity are specified directly by the user rather than looked up from a regulation
table (IMO CII, FuelEU Maritime). User-defined fuels are identified by a unique name so they can
be correctly aggregated and distinguished from regulation-defined fuels.

## Context / Motivation
FEEMS currently supports fuels governed by IMO and FuelEU Maritime regulations.
Some workflows require an arbitrary fuel (e.g., a novel fuel blend or a project-specific
specification) where the user must supply `lhv_mj_per_g` and `ghg_emission_factor_*` directly.
The `FuelSpecifiedBy.USER = 3` enum value is already reserved but is not wired up anywhere in
the model, aggregation logic, protobuf schema, or conversion functions.

A naming field is required because the existing aggregation key
`(fuel_type, origin, fuel_specified_by)` is not unique for user-defined fuels — two fuels with
the same `fuel_type` and `origin` but different LHV/GHG values must be treated as distinct.

## Acceptance Criteria
- [ ] `Fuel` dataclass accepts an optional `name: str` field; required (non-empty) when `fuel_specified_by == FuelSpecifiedBy.USER`
- [ ] When `FuelSpecifiedBy.USER` is set, `lhv_mj_per_g` and all GHG emission factor fields must be provided; a clear `ValueError` is raised if they are missing
- [ ] Fuel aggregation (`FuelConsumption.__add__`) uses `name` as part of the equality key for `USER` fuels (in addition to `fuel_type` and `origin`)
- [ ] Component-level fuel consumption calculation works correctly for `USER` fuels (uses the user-supplied `lhv_mj_per_g`)
- [ ] Switchboard and shaftline aggregation correctly handles `USER` fuels (no silent merging of fuels with the same type/origin but different names)
- [ ] System-level result aggregation handles `USER` fuels correctly
- [ ] `FuelScalar` and `FuelArray` protobuf messages in `feems_result.proto` include an optional `name` field
- [ ] `Fuel` message in `system_structure.proto` includes an optional `name` field
- [ ] `convert_feems_result_to_proto.py` maps `Fuel.name` to the protobuf `name` field
- [ ] `convert_to_protobuf.py` maps `Fuel.name` to the protobuf `name` field
- [ ] `convert_to_feems.py` reads the `name` field from protobuf and populates `Fuel.name`
- [ ] Existing tests pass without modification
- [ ] New unit tests cover: USER fuel creation, missing-field validation, aggregation with name disambiguation, round-trip protobuf conversion

## Scope
- **In scope**:
  - `feems/feems/fuel.py` — `Fuel` dataclass, `FuelConsumption.__add__`, validation logic
  - `feems/feems/components_model/` — component-level fuel consumption where `lhv_mj_per_g` is used
  - `feems/feems/system_model.py` — system-level aggregation
  - `machinery-system-structure/proto/system_structure.proto` — `Fuel` message
  - `machinery-system-structure/proto/feems_result.proto` — `FuelScalar`, `FuelArray` messages
  - `machinery-system-structure/MachSysS/convert_to_protobuf.py`
  - `machinery-system-structure/MachSysS/convert_to_feems.py`
  - `machinery-system-structure/MachSysS/convert_feems_result_to_proto.py`
  - Proto recompilation via `compile_proto.sh`
- **Out of scope**:
  - UI or CLI changes
  - Regulation lookup tables (IMO / FuelEU Maritime) — unchanged
  - RunFEEMSSim PMS logic (no fuel-type-specific decisions there)

## Package(s) Affected
- [x] feems
- [x] machinery-system-structure
- [ ] RunFEEMSSim

## Priority
Medium

## Issue
#80

## Status
<!-- Backlog → Plan → In Progress → Done -->
In Progress

## PDCA Links
- Plan doc: `docs/01-plan/`
- Design doc: `docs/02-design/`
- Analysis: `docs/03-analysis/`
- Report: `docs/04-report/`

## Technical Notes
- Current aggregation key in `FuelConsumption.__add__` (fuel.py ~line 796):
  `fuel_type == each_fuel.fuel_type and origin == each_fuel.origin and fuel_specified_by == each_fuel.fuel_specified_by`
  → For `USER` fuels, add: `and name == each_fuel.name`
- `lhv_mj_per_g` is already an `Optional[float]` on `Fuel`; validation must enforce it is set for `USER` fuels
- Protobuf field tag numbers must not conflict with existing fields in `FuelScalar`, `FuelArray`, and `Fuel` messages
- After proto changes, run `./compile_proto.sh` in `machinery-system-structure/`
