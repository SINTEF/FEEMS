# Plan: COGES Simulation Support

**Issue:** #89  
**Branch:** `feature/issue-89-coges-simulation-support`  
**Backlog:** `docs/backlog/2026-04-27-coges-simulation-support.md`  
**Date:** 2026-04-27  
**Author:** Kevin Koosup Yum  
**Status:** Draft

---

## 1. Problem

The `COGAS`/`COGES` component classes exist in FEEMS but the simulation is incomplete:

1. No `BRAYTON` (Gas Turbine) value in `EngineCycleType` — cannot identify gas turbines by cycle
2. No default CH4/N2O emission factors for gas turbines — regulations don't specify values, so
   user-supplied defaults are needed (methane slip 0.01%, N2O per Rule)
3. "Pilot fuel" is wrong terminology for gas turbines — for gas turbines, "secondary fuel"
   means multi-fuel MODE operation (e.g. LNG 100%/H2 0% → LNG 0%/H2 100%), not pilot ignition.
   `COGAS` needs multi-fuel mode support analogous to `EngineMultiFuel`.
4. `COGAS.fuel_consumer_type_fuel_eu_maritime` returns `None` with a warning — FuelEU Maritime
   integration is broken for COGES
5. PMS dispatch in `RunFEEMSSim` has not been verified to include COGES units alongside gensets

Source: HD Korea Shipbuilding & Offshore Engineering, *Hi-TCO 기술개발 요청 사항* (2026-04-17).

---

## 2. Key Assumptions (from spec document)

| # | Assumption |
|---|-----------|
| 1 | COGES is a single generator unit; the combined GT+ST BSFC curve already encodes steam turbine contribution at a fixed per-load-point ratio |
| 2 | Onboard Steam Demand is constant, so the combined BSFC has no variation from steam demand |
| 3 | Multiple COGES + auxiliary generators → generator combinations are selected for optimal fuel consumption |
| 4 | Multi-fuel: only Main fuel is used in this calculation; secondary fuel is labelled but not separately computed |
| 5 | CH4: default methane slip 0.01% (user-overridable input); N2O: default FuelEU Maritime Rule value (user-overridable) |

---

## 3. Approach

### 3.1 Add `BRAYTON` to `EngineCycleType`

- `feems/feems/types_for_feems.py`: add `BRAYTON = 4` to `EngineCycleType`
- `machinery-system-structure/proto/system_structure.proto`: add `BRAYTON = 4` to
  `Engine.EngineCycleType`
- Update `COGAS.fuel_consumer_type_fuel_eu_maritime` to return a new
  `FuelConsumerClassFuelEUMaritime.GAS_TURBINE` value (maps to ALL ICEs class in FuelEU Maritime
  calculations until the regulation provides a specific factor)

### 3.2 CH4/N2O Defaults for Gas Turbines

Gas turbines (Brayton cycle) are **not listed in FuelEU Maritime Annex II** — no dedicated
fuel-consumer-class row exists. The regulation's fallback for unlisted technologies (Article 10 /
ESSF SAPS WS1 guidance, May 2025) is to use the highest Annex II value in the same fuel class,
which for LNG is Cslip = 3.1%, Cf_N2O = 0.00011 g/g. The IMO 2024 LCA Guidelines (MEPC.391(81))
direct practitioners to use IPCC 2006 values (Tables 2.6/2.7) for engine types not covered:

| Source | Cf_CH4 (g/g) | Cf_N2O (g/g) | C_slip (%) |
|--------|-------------|-------------|------------|
| IPCC 2006 Vol.2 Ch.2 — gas turbine >3 MW | 0.000192 | 0.000048 | ~0 (captured via C_slip) |
| FuelEU "worst-case fallback" (LNG class max) | 0 | 0.000110 | 3.1 |
| Spec document default ("메탄슬립 0.01%") | — | — | 0.01 |

Adopted approach:
- **`c_slip_percent = 0.01`** — matches spec document and IPCC/industry consensus for gas turbines
- **`ch4_factor_gch4_per_gfuel = 0.000192`** — IPCC 4 kg/TJ combustion CH4; distinct from slip
- **`n2o_factor_gn2o_per_gfuel = 0.000048`** — IPCC 1 kg/TJ; gas turbines produce less N2O than
  ICEs due to higher combustion temperatures
- These are the "IPCC-derived" defaults, clearly documented as sourced from IPCC 2006 / 4th IMO
  GHG Study; no FuelEU-authoritative gas turbine value exists

FuelEU Maritime compliance note: since no Annex II gas turbine row exists, the FEEMS calculation
for FuelEU compliance must substitute one of the defined fuel consumer classes. The closest
structural analogy is "Steam Turbines and Boilers" (Cslip = 0.01%) — the plan is to add this
mapping under `GAS_TURBINE` with clear documentation that it is provisional pending a future
Annex II amendment.

Implementation:
- Add `c_slip_percent: float`, `ch4_factor_gch4_per_gfuel: Optional[float]`,
  `n2o_factor_gn2o_per_gfuel: Optional[float]` fields to `COGAS` (Python and Proto)
- Module-level constants in `component_mechanical.py`:
  - `_DEFAULT_BRAYTON_C_SLIP_PERCENT = 0.01`
  - `_DEFAULT_BRAYTON_CH4_GFUEL = 0.000192`
  - `_DEFAULT_BRAYTON_N2O_GFUEL = 0.000048`
- In `COGAS.get_gas_turbine_run_point_from_power_output_kw`: priority order is
  emission curve (issue #85) > instance scalar fields > module constants
- These scalars override the `GhgEmissionFactorTankToWake` entries fetched from the
  FuelEU/IMO table via `Fuel.with_emission_curve_ghg_overrides()` (same mechanism as issue #85)

### 3.3 Multi-Fuel Support for COGAS (Secondary Fuel as Fuel Mode)

`EngineDualFuel` models simultaneous co-combustion (diesel pilot + LNG main with separate BSFC).
For gas turbines, "secondary fuel" means **fuel-mode switching**: the turbine runs on one fuel
composition at a time (e.g. LNG 100%/H2 0%, LNG 50%/H2 50%, LNG 0%/H2 100%), each mode with
its own combined BSFC curve. This mirrors `EngineMultiFuel`.

- Add `multi_fuel_characteristics: List[FuelCharacteristics]` to `COGAS`, exactly as
  `EngineMultiFuel` does — each entry holds `main_fuel_type`, `secondary_fuel_type` (renames
  `pilot_fuel_type` for BRAYTON context), `bsfc_curve`, and `emissions_curves`
- Add `set_fuel_in_use(fuel_type, fuel_origin)` method to `COGAS` for mode selection
- `FuelCharacteristics.secondary_fuel_type` is an alias for `pilot_fuel_type` with clearer
  semantics for BRAYTON engines; the underlying field remains `pilot_fuel_type` for backward compat
- In `COGAS` proto: replace single `fuel` field approach with a `repeated FuelMode fuel_modes`
  field (same structure as `Engine.FuelMode`) alongside the existing `fuel` field for backward compat
- Per assumption 3, the simulation only computes `fuel_in_use` (Main fuel) — multi-fuel mode
  switching for annual fuel optimisation is deferred to a separate feature
- **`COGAS` without `multi_fuel_characteristics`** continues to use its single `fuel` field;
  no breaking change

### 3.4 FuelEU Maritime for COGES

Gas turbines have no dedicated Annex II row. The FuelEU "unlisted technology" fallback (worst-case
from same fuel class) is Cslip = 3.1%/Cf_N2O = 0.00011, which is physically wrong for gas
turbines. The provisionally correct mapping is "Steam Turbines and Boilers" (Cslip = 0.01%), the
only Annex II class with gas-turbine-comparable slip. This requires adding a new row to the FuelEU
table in FEEMS, since the current CSV does not have this class.

- Add a new `FuelConsumerClassFuelEUMaritime.GAS_TURBINE = 7` enum value
- Add a corresponding entry in `_FUEL_CONSUMER_CLASS_FUEL_EU_MARITIME_MAPPING`: `"Gas Turbine"`
- Add GAS_TURBINE rows to `fuel_eu_fuel_table.csv` for each fuel type, copying the factors from
  "Steam Turbines and Boilers" (Cslip = 0.01%, same CO2/N2O as corresponding LNG class) with a
  comment noting they are provisional pending FuelEU Annex II amendment
- `COGAS.fuel_consumer_type_fuel_eu_maritime` returns `GAS_TURBINE`
- Remove the `ValueError` guard for `FUEL_EU_MARITIME` in
  `COGAS.get_gas_turbine_run_point_from_power_output_kw` once section 3.2 defaults are in place

### 3.5 Fix Gaps in `node.py` COGES Handling

The Switchboard's `set_power_out_power_sources` already distributes load to COGES correctly
(same path as Genset). But `get_fuel_emission_energy_balance_for_component`'s COGES branch
(`node.py:384`) only forwards `fuel_specified_by` — three parameters are missing:

- Forward `fuel_type` and `fuel_origin` to `COGES.get_system_run_point_from_power_output_kw`
  so that once `multi_fuel_characteristics` is added to COGAS, the active fuel mode can be
  selected (mirrors what `Genset.get_fuel_cons_load_bsfc_from_power_out_generator_kw` does at
  line 704)
- Forward `user_defined_fuels` (parity with Genset)
- Fix FuelEU Maritime path: replace the inline `cogas.fuel_consumer_type_fuel_eu_maritime` call
  with `_resolve_fuel_consumer_class`; remove the `ValueError` guard in
  `COGAS.get_gas_turbine_run_point_from_power_output_kw` once `GAS_TURBINE` fuel consumer class
  exists

### 3.6 PMS Multi-COGES Dispatch

- Audit `RunFEEMSSim/nbs/` notebooks for `pms_basic.py` — verify that COGES units on a
  switchboard are included in the genset dispatch selection loop
- If COGES is not included, add it: `TypeComponent.COGES` treated identically to `TypeComponent.GENSET`
  in the load-combination optimisation

---

## 4. Files to Change

| File | Change |
|------|--------|
| `feems/feems/types_for_feems.py` | Add `BRAYTON = 4` to `EngineCycleType` |
| `feems/feems/fuel.py` | Add `GAS_TURBINE = 7` to `FuelConsumerClassFuelEUMaritime`; add mapping string |
| `feems/feems/package_data/fuel_eu_fuel_table.csv` | Add `Gas Turbine` rows (provisional, mapped to Steam Turbines/Boilers factors) |
| `feems/feems/components_model/component_mechanical.py` | `COGAS`: add `multi_fuel_characteristics` + `set_fuel_in_use()`; add `ch4_factor_gch4_per_gfuel`/`n2o_factor_gn2o_per_gfuel` with module-level defaults; `fuel_consumer_type_fuel_eu_maritime` returns `GAS_TURBINE`; `FuelCharacteristics`: `secondary_fuel_type` alias for `pilot_fuel_type` |
| `machinery-system-structure/proto/system_structure.proto` | Add `BRAYTON = 4` to `Engine.EngineCycleType`; add `repeated FuelMode fuel_modes` + `ch4_factor_gch4_per_gfuel`/`n2o_factor_gn2o_per_gfuel` to `COGAS` (existing fields kept) |
| `machinery-system-structure/MachSysS/convert_to_feems.py` | Map `BRAYTON`; convert `COGAS.fuel_modes` → `multi_fuel_characteristics`; map new scalar CH4/N2O fields |
| `machinery-system-structure/MachSysS/convert_to_protobuf.py` | Map `BRAYTON`; write `COGAS.fuel_modes` from `multi_fuel_characteristics`; write CH4/N2O scalar fields |
| `feems/feems/components_model/node.py` | Forward `fuel_type`, `fuel_origin`, `user_defined_fuels` to COGES branch; replace inline `fuel_consumer_type` call with `_resolve_fuel_consumer_class`; add `set_fuel_in_use()` call before run-point computation |
| `RunFEEMSSim/nbs/pms_basic.ipynb` | Verify/fix COGES inclusion in genset dispatch loop |
| `feems/tests/test_coges_simulation.py` (new) | Unit tests for BRAYTON defaults, CH4/N2O fallback, multi-fuel mode selection, node.py forwarding |

---

## 5. Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| C_slip default | 0.01% | Matches spec document; consistent with IPCC gas turbine data and industry practice |
| Cf_CH4 default | 0.000192 g/g (IPCC 4 kg/TJ) | IPCC 2006 Vol.2 Table 2.6 for natural gas gas turbines; sourced from 4th IMO GHG Study |
| Cf_N2O default | 0.000048 g/g (IPCC 1 kg/TJ) | IPCC 2006 same source; GT produces less N2O than ICEs due to high combustion temp |
| FuelEU compliance mapping | Provisional "Steam Turbines and Boilers" class (Cslip = 0.01%) | No dedicated Annex II row for gas turbines; closest structural analogy; flagged as provisional |
| Secondary fuel model | `EngineMultiFuel`-style mode switching, not dual-fuel co-combustion | Gas turbines switch fuel modes; `EngineDualFuel` is for ICE pilot ignition |
| Multi-fuel simulation scope | Only `fuel_in_use` (Main fuel) computed; mode switching deferred | Assumption 3: only Main fuel in this calculation; annual optimisation is separate |
| `FuelCharacteristics.secondary_fuel_type` | Alias of `pilot_fuel_type` for BRAYTON; underlying field unchanged | Backward compat with proto and existing Python code |
| FuelEU Maritime for gas turbines | Map to `ALL ICEs` as fallback | No regulatory entry for gas turbines yet |
| Emission curve priority | Curve (issue #85) > scalar field > module default | Scalar field is a simpler UX than a flat-line curve |

---

## 6. Non-Changes (Scope Boundary)

- Full FuelEU Maritime table row for gas turbines — regulation does not define one
- Runtime fuel-mode switching in simulation — structure is added but mode is locked at `fuel_in_use` per assumption 3
- Fuel-conversion simulation for optimal annual fuel ratio — separate feature
- COGES GT/ST power-curve structure — already implemented correctly

---

## 7. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Proto field numbering conflict | High | Assign next available field tag in each message; verify with `compile_proto.sh` |
| Breaking existing COGAS serialisation | High | Keep all existing proto fields; new fields are optional with zero default |
| FuelEU Maritime `GAS_TURBINE` mapping diverges from future regulation | Medium | Clearly mark mapping as provisional; easy to update when regulation adds gas turbine entry |
| RunFEEMSSim COGES PMS gap | Medium | Audit notebook before implementing; patch if gap found |

---

## 8. Next Steps

1. [ ] Open GitHub issue and record number in `docs/backlog/2026-04-27-coges-simulation-support.md`
2. [ ] `git checkout main && git pull && git checkout -b feature/issue-{id}-coges-simulation-support`
3. [ ] Write design document (`docs/02-design/features/coges-simulation-support.design.md`)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-27 | Initial draft | Kevin Koosup Yum |
