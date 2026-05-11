# [BACKLOG] COGES Simulation Support

## Summary
Add Brayton (Gas Turbine) engine cycle type and complete COGES simulation support in FEEMS,
including default CH4/N2O emission factors, secondary fuel terminology, and PMS dispatch for
multiple COGES units.

## Context / Motivation
The `COGAS`/`COGES` component classes exist structurally but lack a `BRAYTON` cycle type enum,
default CH4 (methane slip) and N2O emission factor inputs for gas turbines, and correct fuel
terminology (secondary vs. pilot). Additionally, PMS dispatch has not been verified for
multi-COGES configurations. Requested by HD Korea Shipbuilding & Offshore Engineering
(Hi-TCO technical development request, 2026-04-17).

Reference: `docs/references/[Hi-TCO] 기술개발 요청 사항_260417.pdf`

## Acceptance Criteria
- [ ] `EngineCycleType.BRAYTON` added to Python enum and Proto `Engine.EngineCycleType`
- [ ] COGES treated as single generator unit with combined GT+ST BSFC (already done structurally; verified)
- [ ] CH4 (methane slip) and N2O scalar input fields on `COGAS`, with defaults:
      CH4 = 0.01% methane slip (0.0001 g_CH4/g_fuel), N2O = FuelEU Maritime ALL ICEs value
- [ ] "Secondary fuel" terminology for Brayton cycle engines in proto and Python (backward compat with existing `pilot_fuel`)
- [ ] `COGAS.fuel_consumer_type_fuel_eu_maritime` no longer raises/warns; maps to `GAS_TURBINE` class
- [ ] Multiple COGES units dispatched optimally by PMS in `RunFEEMSSim` (treated as gensets)
- [ ] MachSysS conversion functions updated for new proto fields
- [ ] Unit tests for all new behaviour; `uv run pytest` passes

## Scope
- **In scope**: `EngineCycleType.BRAYTON`; CH4/N2O defaults for COGAS; secondary-fuel terminology; FuelEU Maritime class for gas turbines; PMS multi-COGES dispatch
- **Out of scope**: Full FuelEU Maritime table entries for gas turbines; multi-fuel LNG/H2 blend calculation (only Main fuel used per assumption 3); fuel-conversion simulation

## Package(s) Affected
- [x] feems
- [x] machinery-system-structure
- [x] RunFEEMSSim

## Priority
High

## Issue
#89

## Status
In Progress

## PDCA Links
- Plan doc: `docs/01-plan/features/coges-simulation-support.plan.md`
- Design doc: `docs/02-design/features/coges-simulation-support.design.md`
- Analysis: `docs/03-analysis/coges-simulation-support.analysis.md`
- Report: `docs/04-report/features/coges-simulation-support.report.md`
