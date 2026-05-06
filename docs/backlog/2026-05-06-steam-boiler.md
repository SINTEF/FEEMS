# [BACKLOG] Steam Boiler Model

## Summary

Add a `SteamBoiler` component to FEEMS for modelling fuel-fired auxiliary boilers that produce saturated steam for non-power thermal loads (cargo heating, fuel oil heating, accommodation). The boiler is standalone — outside the switchboard/shaft-line topology — and integrates into all four system model classes via a shared base-class helper.

## Context / Motivation

FEEMS currently has no model for fuel-fired auxiliary boilers, which are significant fuel consumers on tankers and other vessels with high thermal load requirements. The `COGAS` component covers steam turbines for power generation, but has no relationship to standalone auxiliary boilers. This feature is needed to provide accurate total vessel fuel consumption and emissions accounting in simulations that include steam thermal loads.

## Acceptance Criteria

### Component (`feems`)

- [ ] `TypeComponent.STEAM_BOILER = 30` added to `TypeComponent` enum
- [ ] `SteamBoiler` class in `component_mechanical.py` with:
  - `rated_steam_production_kg_per_h: float` as rated capacity
  - `working_pressure_bar: float` for saturated steam lookup
  - `feed_water_temperature_c: float = 80.0` (default)
  - `fuel_type`, `fuel_origin` for single-fuel, or `multi_fuel_characteristics: List[FuelCharacteristics]` for multi-fuel (follow `EngineMultiFuel` pattern)
  - `emissions_curves: List[EmissionCurve] | None` (full `EmissionType` support)
  - Three curve input types accepted at construction: `kg_fuel_per_h_curve`, `kg_fuel_per_kg_steam_curve`, `thermal_efficiency_curve` — all normalised to `thermal_efficiency_curve` as single source of truth
  - `get_boiler_run_point(steam_demand_kg_per_h)` → `BoilerRunPoint`
- [ ] `BoilerRunPoint` dataclass with `load_ratio`, `fuel_flow_rate_kg_per_s: FuelConsumption`, `steam_production_kg_per_s`, `thermal_efficiency`, `emissions_g_per_s`
- [ ] Saturated steam lookup table (1–20 bar, `h_g` in kJ/kg) with scipy interpolation; `InputError` if pressure is outside range
- [ ] Feed water enthalpy computed as `h_fw = 4.18 × T_fw` kJ/kg
- [ ] `Δh = h_g(P_working) - h_fw(T_fw)` used in all fuel calculations

### System Model (`feems`)

- [ ] `MachinerySystem._calculate_boiler_result(boilers: List[SteamBoiler], steam_demand_kg_per_h: np.ndarray) -> FEEMSResult` base-class helper
- [ ] All four `get_fuel_energy_consumption_running_time` methods (`ElectricPowerSystem`, `MechanicalPropulsionSystem`, `HybridPropulsionSystem`, `MechanicalPropulsionSystemWithElectricPowerSystem`) accept `boilers: List[SteamBoiler] = []` and `steam_demand_kg_per_h: np.ndarray | None = None`; boiler result merged via `sum_and_extend_duration`

### FEEMSResult (`feems`)

- [ ] New scalar fields: `running_hours_boiler_total_hr: float = 0.0`, `steam_production_boiler_total_kg: float = 0.0`
- [ ] New field: `fuel_consumption_boiler_total: FuelConsumption` (boiler fuel separate from aggregated `multi_fuel_consumption_total_kg`)
- [ ] Boiler fuel folds into `multi_fuel_consumption_total_kg` (aggregated total)
- [ ] Boiler emissions fold into `total_emission_kg` and `co2_emission_total_kg`
- [ ] Per-timestep boiler columns added to `detail_result` DataFrame
- [ ] `__merge` updated to handle new fields correctly

### MachSysS (`machinery-system-structure`)

- [ ] `STEAM_BOILER = 30` in `ComponentType` proto enum
- [ ] `SteamBoiler` proto message with: `name`, `uid`, `rated_steam_production_kg_per_h`, `working_pressure_bar`, `feed_water_temperature_c`, fuel fields (reuse existing `FuelType`, `FuelOrigin`), multi-fuel support (reuse `FuelMode`), `emissions_curves`, curve input (efficiency curve)
- [ ] `convert_to_protobuf.py` — `SteamBoiler` → proto
- [ ] `convert_to_feems.py` — proto → `SteamBoiler`
- [ ] Compile proto and regenerate `*_pb2.py` / `*_pb2.pyi`

### Tests (`feems`)

- [ ] Unit tests for `SteamBoiler` construction from all three curve input types, verifying they produce identical thermal efficiency curves
- [ ] Unit tests for `get_boiler_run_point` at multiple load ratios: correct fuel flow, steam production, emissions
- [ ] Test that working pressure outside 1–20 bar raises `InputError`
- [ ] Test multi-fuel boiler follows same `set_fuel_in_use` contract as `EngineMultiFuel`
- [ ] Integration test: `ElectricPowerSystem.get_fuel_energy_consumption_running_time` with one boiler — verify `FEEMSResult` has correct `running_hours_boiler_total_hr`, `steam_production_boiler_total_kg`, and boiler fuel in `multi_fuel_consumption_total_kg`
- [ ] `uv run pytest` passes

## Scope

**In scope**: `SteamBoiler` component; saturated steam lookup table 1–20 bar; three curve input types normalised to thermal efficiency; multi-fuel support; full emission curve support; `FEEMSResult` new fields; `MachinerySystem` base helper; all four system model classes updated; proto + converters; unit and integration tests.

**Out of scope**: Exhaust gas boilers (waste heat recovery); superheated steam; steam distribution networks; boiler load-sharing PMS logic; `RunFEEMSSim` integration (separate backlog item).

## Package(s) Affected

- [x] feems
- [x] machinery-system-structure
- [ ] RunFEEMSSim

## Priority

High

## Issue

#92

## Status

Backlog

## PDCA Links

- Plan doc: `docs/01-plan/features/steam-boiler.plan.md`
- Design doc: `docs/02-design/features/steam-boiler.design.md`
- Analysis: `docs/03-analysis/steam-boiler.analysis.md`
- Report: `docs/04-report/features/steam-boiler.report.md`

## ADRs

- `docs/adr/0001-steam-boiler-capacity-in-kg-per-h.md`
- `docs/adr/0002-steam-boiler-standalone-topology.md`
