# [BACKLOG] Per-Component Performance Metrics in FEEMSResult

## Summary

Extend `FEEMSResult.detail_result` (the per-component DataFrame) and the matching proto `ResultPerComponent` so each component row also reports four scalars averaged over the component's on-state timesteps only:

- `operating_avg_power_kw` — primary output power magnitude
- `operating_avg_reversible_power_kw` — reverse-direction power magnitude (PTI direction for PTI/PTO; `0.0` for everything else)
- `operating_avg_efficiency` — energy-out / energy-in
- `operating_avg_sfc_g_per_kwh` — specific fuel consumption

For components where a metric is not applicable, the value is `0.0` to keep the DataFrame homogeneous and proto serialization trivial.

## Context / Motivation

Today `FEEMSResult.detail_result` reports cumulative quantities (fuel, energy, running hours, emissions) per component but no operating-point metrics. Users post-processing simulation output cannot tell whether a genset is running at 30 % or 90 % average load, what the steady-state SFC was, or what efficiency the fuel cells averaged. These three numbers are the standard performance dashboard items requested for vessel reports and operational-efficiency analyses.

The averages must be computed over the component's **on-state timesteps only** (matching the existing `running_hours_h` semantics: `power_output != 0`). A simple duration-weighted mean would include shut-down periods and produce misleading values (e.g. a genset that ran half the time at 80 % load would show 40 % "average load").

PTI/PTO is the one component type where output direction is genuinely bidirectional. A single signed average would conflate motoring and generation. We split it into `operating_avg_power_kw` (PTO mode = shaft generator) and `operating_avg_reversible_power_kw` (PTI mode = motor). Both reported as positive magnitudes; direction is encoded by which field is non-zero.

## Acceptance Criteria

### `feems`

- [ ] `get_fuel_emission_energy_balance_for_component` (node.py) returns the 4 new scalars on its `FEEMSResult` for every supported component type
- [ ] On-state mask = `power_output != 0` (matches existing `running_hours_h`); for PTI/PTO the mask is split into `power_input < 0` (PTO) and `power_input > 0` (PTI)
- [ ] Averages are time-weighted: `Σ(x · Δt) / Σ(Δt)` over masked timesteps
- [ ] If a component never runs in the simulation, all four metrics are `0.0`
- [ ] `Switchboard.get_fuel_energy_consumption_running_time` and `ShaftLine.get_fuel_energy_consumption_running_time` add 4 new columns to `detail_result`
- [ ] `MachinerySystem._calculate_boiler_result` adds the same 4 columns to the boiler row, computed from `BoilerRunPoint` (efficiency direct; SFC g_fuel/kWh_thermal; reversible = 0; primary power = steam-thermal kW)
- [ ] Component-by-component semantics:
  - MainEngine / w-Gearbox: power_kw = avg shaft kW; efficiency = mech_kWh_out / (fuel_kg × LHV); SFC = g_fuel / kWh_shaft
  - Genset: power_kw = avg electric kW; efficiency = elec_kWh_out / fuel_energy_in; SFC = g_fuel / kWh_elec
  - FuelCell / FuelCellSystem: same as Genset, electric out
  - COGES: same as Genset, electric out (uses COGAS run point)
  - SteamBoiler: power_kw = avg steam-thermal kW (`ṁ_steam · Δh`); efficiency = thermal_efficiency from BoilerRunPoint; SFC = g_fuel / kWh_steam
  - PTI/PTO: power_kw = PTO-mode avg elec out, reversible = PTI-mode avg elec in, efficiency = single avg across both modes, SFC = 0
  - Battery / SuperCap (system): power_kw = avg net flow magnitude, efficiency = 0, SFC = 0
  - ShorePower / OtherLoad / Propeller / Propulsion drive: power_kw = avg, efficiency = 0, SFC = 0

### `machinery-system-structure`

- [ ] 4 new fields appended to `ResultPerComponent` (proto IDs 16-19) — backwards-compatible additions
  - `double operating_avg_power_kw            = 16;`
  - `double operating_avg_reversible_power_kw = 17;`
  - `double operating_avg_efficiency          = 18;`
  - `double operating_avg_sfc_g_per_kwh       = 19;`
- [ ] `compile_proto.sh` re-run, generated `*_pb2.py` / `*_pb2.pyi` committed
- [ ] `_COLUMN_NAMES` in `convert_feems_result_to_proto.py` extended with the 4 new mappings
- [ ] Round-trip proto serialization test: build a `FEEMSResult` with all 4 fields set, convert to proto, verify values

### Documentation

- [ ] Plan doc in `docs/01-plan/features/`
- [ ] Design doc in `docs/02-design/`
- [ ] Analysis doc in `docs/03-analysis/`
- [ ] Report doc in `docs/04-report/`
- [ ] API reference updated for both packages

### Tests

- [ ] Unit test per component family in `feems/tests/`: engine, genset, fuel cell, PTI/PTO (both modes in one run), other-load
- [ ] Boiler test extending existing `test_steam_boiler.py` to assert the 4 columns
- [ ] Round-trip proto test in `machinery-system-structure/tests/`

## Scope

- **In scope**: scalar averages on per-component result; proto + converter updates; tests; docs.
- **Out of scope**:
  - Per-timestep time series of these metrics (already covered by `result_time_series`)
  - `load_ratio` (% of rated capacity) — easy follow-up
  - `RunFEEMSSim` PMS changes
  - Battery round-trip efficiency (would require per-cycle accounting beyond existing energy_stored signal)

## Package(s) Affected

- [x] feems
- [x] machinery-system-structure
- [ ] RunFEEMSSim

## Priority

Medium

## Issue

#97

## Status

In Progress

## PDCA Links

- Plan doc: `docs/01-plan/features/per-component-performance-metrics.plan.md`
- Design doc: `docs/02-design/features/per-component-performance-metrics.design.md`
- Analysis: `docs/03-analysis/per-component-performance-metrics.analysis.md`
- Report: `docs/04-report/per-component-performance-metrics.report.md`
