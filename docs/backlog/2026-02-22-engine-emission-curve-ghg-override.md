# [BACKLOG] Engine-Defined CH4/N2O Emission Curves Override GHG Factors

## Summary

When an engine component carries load-dependent emission curves for CH4 or N2O
(`EmissionType.CH4` / `EmissionType.N2O`), those curves should override the flat
`ch4_factor_gch4_per_gfuel` and `n2o_factor_gn2o_per_gfuel` (and the derived
`c_slip_percent`) that are otherwise read from the fuel standard tables (IMO /
FuelEU Maritime) or user-supplied `GhgEmissionFactorTankToWake` values.

## Context / Motivation

Engines are already modelled with per-load-ratio emission curves
(`EmissionCurve` / `_emissions_per_kwh_interp`) for pollutants such as NOX, SOX,
CO, PM, HC, **CH4**, and **N2O**.  However, the GHG emission accounting path
(tank-to-wake CO2eq) does not consult these curves.  It relies exclusively on the
flat `GhgEmissionFactorTankToWake` constants that come from regulation tables or
user overrides.  This causes two problems:

1. **Accuracy** — the flat factors ignore load-dependency.  Methane slip in an
   LNG engine, for instance, is strongly load-dependent; a curve-based value is
   physically more accurate.
2. **Consistency** — the same engine emits CH4/N2O at a rate computed from
   `_emissions_per_kwh_interp` (reported in `total_emission_kg`) but a *different*
   rate is used for CO2eq accounting.  These two numbers are inconsistent whenever
   a curve is present.

## Acceptance Criteria

- [ ] When `EmissionType.CH4` is in `engine._emissions_per_kwh_interp`, the
  effective `ch4_factor_gch4_per_gfuel` used in the GHG CO2eq calculation for
  that engine/time-step is derived from the curve:
  `ch4_factor = CH4_curve(load_ratio) / BSFC(load_ratio)`.
- [ ] When `EmissionType.N2O` is in `_emissions_per_kwh_interp`, the effective
  `n2o_factor_gn2o_per_gfuel` is similarly derived from the curve.
- [ ] When neither CH4 nor N2O curve is present, behaviour is identical to the
  current implementation (flat standard/user values unchanged).
- [ ] Curves override at the **engine run-point level** so that the override is
  time-step- and load-resolved, not a single averaged value.
- [ ] The override applies to both IMO and FuelEU Maritime GHG accounting paths.
- [ ] `c_slip_percent` in `GhgEmissionFactorTankToWake` is set to `0` when a
  CH4 curve is present, because the curve already captures total methane emissions
  (combusted + slipped); double-counting must be avoided.
- [ ] Existing unit tests continue to pass (no regression on curve-free code
  paths).
- [ ] New unit tests cover: CH4-curve-only override, N2O-curve-only override,
  both curves present, and the no-curve fallback.
- [ ] The MachSysS protobuf / conversion layer correctly round-trips emission
  curves for CH4/N2O (if not already supported).

## Scope

- **In scope**:
  - `feems/feems/components_model/component_mechanical.py` — engine run-point
    calculation where the override is applied.
  - `feems/feems/fuel.py` — possibly introducing a helper or a modified
    `GhgEmissionFactorTankToWake` factory that accepts curve-derived values.
  - `feems/tests/` — new unit tests.
  - `machinery-system-structure/` — verify CH4/N2O curves round-trip through
    proto (read-only audit; fix only if broken).

- **Out of scope**:
  - Changing the `EmissionCurve` / `EmissionType` data structures themselves.
  - Changing the WtT (well-to-tank) GHG factor path.
  - FuelCell or electric component GHG paths.
  - RunFEEMSSim-level changes (unless the engine run-point API changes require it).

## Package(s) Affected

- [x] feems
- [ ] machinery-system-structure (audit only)
- [ ] RunFEEMSSim

## Priority

Medium

## Issue

#85

## Status

Backlog

## PDCA Links

- Plan doc: `docs/01-plan/`
- Design doc: `docs/02-design/`
- Analysis: `docs/03-analysis/`
- Report: `docs/04-report/`
