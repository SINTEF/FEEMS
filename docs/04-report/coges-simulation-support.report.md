# COGES Simulation Support — Completion Report

**Issue:** #89  
**Branch:** `feature/issue-89-coges-simulation-support`  
**Author:** Kevin Koosup Yum  
**Report Date:** 2026-04-27  
**Status:** Complete ✅

---

## Executive Summary

Full simulation support for COGES (Combined Gas And Steam with Electric generation) units has been completed across the FEEMS maritime power system modeling framework. The feature adds missing BRAYTON cycle identification, IPCC-derived default emission factors for gas turbines, multi-fuel mode support mirroring the `EngineMultiFuel` pattern, and completes the fuel option toolchain integration. Gap analysis confirms 96% design match rate (threshold: ≥90%).

**Key deliverables:**
- Added `BRAYTON = 4` cycle type to `EngineCycleType` enum (both Python and Proto)
- Implemented gas turbine default emission factors: CH4=0.000192, N2O=0.000048, slip=0.01%
- Extended COGAS to support multi-fuel mode switching via `FuelCharacteristics` list
- Completed proto schema and bidirectional serialization (convert_to_feems/convert_to_protobuf)
- Integrated COGES through full fuel option toolchain in system model
- 25 unit tests + 1 integration test covering all scenarios
- FuelEU Maritime mapping for gas turbines (provisional GAS_TURBINE class)

---

## PDCA Cycle Summary

### Plan Phase ✅

**Document:** `docs/01-plan/features/coges-simulation-support.plan.md`

**Key planning decisions:**
1. **BRAYTON cycle type** — New enum value to identify gas turbines by engine cycle classification
2. **Emission defaults** — CH4=0.000192 g/g, N2O=0.000048 g/g, c_slip=0.01% (IPCC 2006 Vol.2 sourced via 4th IMO GHG Study)
3. **Multi-fuel model** — `EngineMultiFuel`-style mode switching (not dual-fuel co-combustion) via `FuelCharacteristics` list
4. **FuelEU Maritime compliance** — Provisional mapping to "Gas Turbine" class; no dedicated Annex II entry exists yet
5. **Scope boundary** — Only `fuel_in_use` (main fuel) computed per assumption; full fuel-mode switching deferred

**Assumptions validated:**
- COGES is a single generator unit; combined GT+ST BSFC curve encodes ST contribution at fixed per-load ratio
- Onboard steam demand is constant
- Multi-fuel: only main fuel computed; secondary fuel labeling for future annual optimization
- Regulation fallback: FuelEU gas turbine → provisional "Steam Turbines and Boilers" factors pending Annex II amendment

### Design Phase ✅

**Document:** `docs/02-design/features/coges-simulation-support.design.md`

**Design decisions and rationale:**

| Decision | Implementation | Rationale |
|----------|----------------|-----------|
| Emission factor source | IPCC 2006 Vol.2 Table 2.6 (gas turbines >3 MW) | IMO 2024 LCA Guidelines direct use for unlisted engine types |
| Scalar override priority | Curve (issue #85) > field scalar > module default | Curve is most specific; scalar is intermediate; module default is fallback |
| Multi-fuel pattern | `FuelCharacteristics` list + `set_fuel_in_use()` | Mirrors `EngineMultiFuel`; backward compat (no multi-fuel = no-op) |
| `secondary_fuel_type` alias | Property aliasing `pilot_fuel_type` | Clearer semantics for BRAYTON; no schema change |
| FuelEU fallback | Provisional `GAS_TURBINE = 7` enum class | Closest structural analogy (Cslip=0.01%); marked for future amendment |
| Node.py forwarding | Call `set_fuel_in_use()` before run-point; forward user_defined_fuels | Enables mode selection; parity with Genset path |

**Implementation order:**
1. Enums (`BRAYTON`, `GAS_TURBINE`)
2. Fuel module (`with_emission_curve_ghg_overrides` extension, FuelEU table)
3. Component model (`COGAS` new params, `set_fuel_in_use()`, run-point override)
4. Node forwarding (set_fuel_in_use, user-fuel lookup)
5. Proto schema + bidirectional converters
6. Tests covering all combinations

### Do Phase ✅

**Implementation commits (7 commits):**

1. `1927c2d` **feat: add COGES simulation support (#89)**
   - Proto schema, BRAYTON + GAS_TURBINE enums, COGAS multi-fuel params
   - FuelEU table rows (7 Gas Turbine entries)
   - Component model (defaults, FuelCharacteristics alias, set_fuel_in_use)
   - node.py forwarding + _resolve_fuel_consumer_class extension
   - Comprehensive test suite (25 tests)

2. `d915e09` **fix: use eff_curve (not bsfc) for COGAS multi-fuel modes; add missing Gas Turbine CSV rows**
   - Corrected `_effective_eff_curve` logic in multi-fuel BSFC selection
   - Filled in missing CSV rows (Diesel Fossil, H2 pathways)

3. `83fda04` **refactor: replace MultiFuelEngine.FuelMode with dedicated COGAS.FuelMode in proto**
   - Simplified: COGAS now uses `repeated FuelMode fuel_modes` (formerly attempting to share `MultiFuelEngine.FuelMode`)
   - Made schema clearer and proto generation simpler

4. `6fa09bc` **chore: remove unused Efficiency main_eff field from MultiFuelEngine.FuelMode**
   - Cleanup: deduplicated field from proto (was never used in Python)

5. `789b640` **feat: add COGES fuel options to available_fuel_options_by_converter**
   - Integrated COGES into `ElectricPowerSystem.available_fuel_options_by_converter`
   - COGES now returns all fuel modes (primary flag: i==0 convention)

6. `16b2559` **refactor: wire COGES through full fuel option toolchain in ElectricPowerSystem**
   - Extended `_extract_fuel_options_from_component` to handle COGES
   - Simplified `available_fuel_options` to single loop via helper
   - Ensured `multi_fuel_engine_inventory` includes COGES

7. `15f5979` **test: add COGES fuel option toolchain tests**
   - 6 new tests for `available_fuel_options*` properties with COGES

(Followed by integration test and `primary` flag fixes)

**Files changed:**

| File | Type | Key Additions |
|------|------|---------------|
| `feems/feems/types_for_feems.py` | Enum | `BRAYTON = 4` |
| `feems/feems/fuel.py` | Enum + Method | `GAS_TURBINE = 7`; `with_emission_curve_ghg_overrides(c_slip_percent)` |
| `feems/feems/package_data/fuel_eu_fuel_table.csv` | Data | 7 Gas Turbine rows (LNG, Diesel, H2 pathways) |
| `feems/feems/components_model/component_mechanical.py` | Class | COGAS: `multi_fuel_characteristics`, `set_fuel_in_use()`, scalar GHG fields; FuelCharacteristics: `secondary_fuel_type` alias |
| `feems/feems/components_model/node.py` | Method | COGES branch: `set_fuel_in_use()` call; user-fuel forwarding; `_resolve_fuel_consumer_class` extension |
| `feems/feems/system_model.py` | Method | `_extract_fuel_options_from_component` COGES handler; unified `available_fuel_options` loop |
| `machinery-system-structure/proto/system_structure.proto` | Schema | BRAYTON enum; COGAS fields 15–18 (fuel_modes, GHG scalars) |
| `machinery-system-structure/MachSysS/convert_to_feems.py` | Conversion | `convert_proto_cogas_to_feems()`: multi-fuel unpacking, default fallback |
| `machinery-system-structure/MachSysS/convert_to_protobuf.py` | Conversion | `convert_cogas_component_to_protobuf()`: multi-fuel serialization, GHG scalars |
| `feems/tests/test_coges_simulation.py` | Tests | 25 unit tests (8 test classes) |
| `RunFEEMSSim/tests/test_machinery_calculation.py` | Tests | 1 integration test for multi-fuel COGES via MachineryCalculation |

### Check Phase ✅

**Document:** `docs/03-analysis/coges-simulation-support.analysis.md`

**Match Rate: 96%** (threshold: ≥90% passed)

**Implemented:** All design sections (§2.1–2.8, §4 tests)

**Minor deviations (non-blocking):**
1. **node.py user-fuel forwarding** — Design showed `effective_user_fuels[0]` index access; actual uses `find_user_fuel()` lookup. More correct behavior (matches active fuel mode by type/origin rather than hardcoded index).

2. **`_effective_eff_curve` property** — Design sketched a named property; actual inlines the logic in run-point method. Same behavior, cleaner implementation.

**Verdict:** All design-mandated capabilities implemented. Deviations are equivalent or superior. No corrective action needed.

---

## What Was Planned vs What Was Delivered

### All Planned Items Completed ✅

| Plan Item | Status | Delivered |
|-----------|--------|-----------|
| Add `BRAYTON` to `EngineCycleType` | ✅ | Enum value in Python and proto |
| Add `GAS_TURBINE` to `FuelConsumerClassFuelEUMaritime` | ✅ | Enum + mapping string + table rows |
| CH4/N2O defaults with fallback | ✅ | Module constants + override logic at 3 priority levels |
| `FuelCharacteristics.secondary_fuel_type` alias | ✅ | Properties for `pilot_fuel_type` + `pilot_fuel_origin` |
| `COGAS.multi_fuel_characteristics` | ✅ | List of `FuelCharacteristics` + auto-selection of first mode |
| `COGAS.set_fuel_in_use()` | ✅ | Method mirroring `EngineMultiFuel`; `ValueError` on unknown fuel |
| Fuel mode selection in run-point | ✅ | BSFC curve + emission curves from `_fuel_in_use` when set |
| node.py COGES forwarding | ✅ | `fuel_type`, `fuel_origin`, `user_defined_fuels` all passed |
| FuelEU Maritime COGES lookup | ✅ | `_resolve_fuel_consumer_class` extended for COGES |
| Proto bidirectional serialization | ✅ | `fuel_modes` + scalar GHG fields in both directions |
| Test coverage for all scenarios | ✅ | 25 unit tests (8 classes) + 1 integration test |

### Scope Boundary Respected ✅

Items explicitly deferred (noted in plan):
- Full FuelEU Maritime gas turbine row (regulation undefined; provisional mapping sufficient)
- Runtime fuel-mode switching optimization (structure added; mode locked per assumption)
- Annual fuel-mode optimization (separate feature)
- COGES GT/ST power-curve structure (already implemented correctly)

---

## Key Design Decisions and Rationale

### 1. BRAYTON as Cycle Type (not just fuel classification)

**Decision:** Add `BRAYTON = 4` to `EngineCycleType` enum alongside DIESEL/OTTO/LEAN_BURN.

**Rationale:**
- Gas turbines are a distinct thermodynamic cycle (Brayton vs Otto/Diesel)
- Enables downstream code to identify engine type by cycle, not just by fuel
- Allows future specialization (e.g., NOx calculation methods that differ by cycle)
- Mirrors IMO classification where cycle type is primary; fuel is secondary

### 2. Emission Defaults: IPCC 2006 via IMO LCA Guidelines

**Decision:** CH4=0.000192 g/g, N2O=0.000048 g/g, c_slip=0.01%

**Rationale:**
- **Source**: IPCC 2006 Vol.2 Ch.2 Table 2.6 for natural gas gas turbines (>3 MW)
- **Authority**: IMO MEPC.391(81) LCA Guidelines (2024) direct practitioners to IPCC values for unlisted engine types
- **CH4 vs slip**: CH4 (0.000192) is combustion-phase production, distinct from slip (0.01%); both present in emissions
- **Regulation gap**: FuelEU Maritime Annex II has no dedicated gas turbine row. Fallback is highest-class value (Cslip=3.1%), which is physically wrong for gas turbines. IPCC-backed values are superior.
- **Provisional FuelEU mapping**: Added `GAS_TURBINE = 7` enum (maps to same factors as "Steam Turbines and Boilers", Cslip=0.01%); marked for future amendment when regulation adds gas turbine entry.

### 3. Multi-Fuel: Mode-Switching, Not Dual-Fuel Co-Combustion

**Decision:** Multi-fuel via `FuelCharacteristics` list (like `EngineMultiFuel`), not `EngineDualFuel` pattern.

**Rationale:**
- **Gas turbine physics**: Fuel switching is modal (100% LNG → blend → 100% H2), not simultaneous pilot+main
- **Schema reuse**: Aligns with existing `EngineMultiFuel` structure; reduces new concepts
- **Backward compat**: COGAS without `multi_fuel_characteristics` continues unchanged; no breaking changes
- **Scope**: Only `fuel_in_use` main fuel computed per assumption; mode switching for annual optimization deferred

### 4. `secondary_fuel_type` as Alias (not new schema field)

**Decision:** `FuelCharacteristics.secondary_fuel_type` property → alias of `pilot_fuel_type`.

**Rationale:**
- **Semantic clarity**: For BRAYTON, "secondary fuel" is mode switchable, not "pilot ignition"
- **Backward compat**: No proto change; existing `pilot_fuel_type` field reused
- **Property pattern**: Bidirectional property allows read/write semantics without schema impact
- **Future-proof**: If proto ever needs true distinct field, can migrate (property hides the change)

### 5. Three-Level Override Priority for GHG Factors

**Decision:** Emission curve (issue #85) > scalar field > module default.

**Rationale:**
- **Curve**: Most specific; user provided per-load-point GHG data → use it
- **Scalar field**: Intermediate; user set single COGAS instance value → use it
- **Module default**: Least specific; IPCC canonical value → fallback
- **UX ergonomic**: User can supply curve for precision, scalar for simplicity, or accept canonical default

### 6. `c_slip_percent` as Explicit Parameter (not zeroed out)

**Decision:** Extend `Fuel.with_emission_curve_ghg_overrides()` to accept `c_slip_percent` separately.

**Rationale:**
- **Issue #85 legacy**: When `ch4_factor` supplied, c_slip was zeroed (assumption: user provided CH4 separately)
- **COGAS need**: Gas turbines have *both* CH4 combustion production (0.000192) *and* slip (0.01%), distinct values
- **Backward compat**: `c_slip_percent=None` preserves legacy zero-out; explicit value passes through
- **Three-way logic**: Explicit pass (gas turbine), legacy zero (ICE), or unchanged (neither param given)

### 7. Node.py COGES Forwarding Pattern

**Decision:** Call `component.cogas.set_fuel_in_use(fuel_type, fuel_origin)` before run-point computation.

**Rationale:**
- **Activation of mode**: Fuel option passed from system level → must select active mode before efficiency/emission lookup
- **Parity with Genset**: Genset also receives fuel_type/fuel_origin and can have multi-fuel; same pattern
- **User-fuel lookup**: `find_user_fuel(effective_user_fuels, fuel_type, fuel_origin)` picks matching custom fuel; enables user-supplied fuel data for COGES
- **Integration**: Seamless integration with fuel option toolchain (`available_fuel_options_by_converter`)

### 8. Provisional FuelEU Mapping

**Decision:** Map gas turbines to new `GAS_TURBINE = 7` enum (factors copied from "Steam Turbines and Boilers").

**Rationale:**
- **Regulation gap**: FuelEU Maritime Annex II has no gas turbine entry; unlisted tech fallback is worst-case (Cslip=3.1%), physically wrong for GT
- **Fallback analogy**: Steam turbine is only Annex II class with Cslip=0.01% (appropriate for GT)
- **Provisional flag**: Clearly marked in CSV header; easy to update when regulation amends
- **Immediate benefit**: Enables FuelEU compliance calculation for COGES with correct factors pending amendment

---

## Test Coverage and Quality Metrics

### Test Suite: 26 Tests Total ✅

**Unit tests** (`feems/tests/test_coges_simulation.py`) **— 25 tests across 8 test classes:**

1. **TestWithEmissionCurveGhgOverridesBackwardCompat** (3 tests)
   - Legacy ch4+n2o → c_slip still zeroed
   - c_slip_percent=None + only n2o → c_slip unchanged
   - Verify backward compatibility

2. **TestWithEmissionCurveGhgOverridesExplicitSlip** (3 tests)
   - Explicit ch4_factor + c_slip_percent=0.01 → both stored
   - c_slip_percent=0.05 alone → only slip updated
   - Verify new parameter works independently

3. **TestGasTurbineFuelEUTable** (3 tests)
   - GAS_TURBINE lookup for NATURAL_GAS → returns Cslip=0.01 row
   - GAS_TURBINE for LNG variants (Fossil, BIO, RFNBO)
   - Verify table entries complete and accessible

4. **TestBraytonDefaultsInRunPoint** (4 tests)
   - COGAS with module defaults → run-point fuel has correct factors
   - Multiple fuel types (LNG, Diesel, H2) → all receive BRAYTON defaults
   - FuelEU maritime path → GAS_TURBINE enum returned
   - Verify defaults applied correctly

5. **TestEmissionCurveOverridesScalarDefaults** (1 test)
   - Emission curve present → curve overrides module default (issue #85 priority)
   - c_slip=0.0 with curve (legacy behavior preserved)

6. **TestMultiFuelModeSwitch** (7 tests)
   - Build COGAS with [LNG_mode, H2_mode] → set_fuel_in_use() selects each
   - set_fuel_in_use(unknown_fuel) → ValueError
   - fuel_type property reflects selection
   - Unknown fuel_origin → ValueError
   - No multi-fuel_characteristics → set_fuel_in_use() is no-op
   - Verify mode selection and error handling

7. **TestNodeCogesBranchForwarding** (2 tests)
   - Multi-fuel COGES through ElectricPowerSystem
   - get_fuel_energy_consumption_running_time(fuel_option=...) → COGAS._fuel_in_use matches selection
   - Verify node.py forwarding works end-to-end

8. **TestProtoRoundTrip** (2 tests)
   - COGAS with multi_fuel_characteristics, GHG scalars → serialize/deserialize
   - All fields preserved, fuel_modes list length correct
   - Verify proto conversion bidirectional

**Integration test** (`RunFEEMSSim/tests/test_machinery_calculation.py`) **— 1 test:**
- **test_machinery_calculation_multifuel_coges**
  - End-to-end via `MachineryCalculation` runner
  - Multi-fuel COGES in system → PMS includes it in dispatch
  - Verify full stack integration

### Code Quality ✅
- All tests pass: `uv run pytest feems/tests/test_coges_simulation.py -v` → 25 passed
- Integration test passes: `uv run pytest RunFEEMSSim/tests/test_machinery_calculation.py::test_machinery_calculation_multifuel_coges -v` → passed
- Ruff formatting: All files conform to 120-char line length, Python 3.10+ target
- No generated files modified (proto-generated `*_pb2.py`, `*_pb2.pyi` excluded from manual edits)

---

## Completed Work Summary

### Proto Schema (Backward Compatible) ✅
- `Engine.EngineCycleType.BRAYTON = 4`
- `COGAS` fields 15–18 (all optional, defaults to 0):
  - `repeated FuelMode fuel_modes` (multi-fuel list)
  - `double ch4_factor_gch4_per_gfuel` (0 → use module default)
  - `double n2o_factor_gn2o_per_gfuel` (0 → use module default)
  - `double c_slip_percent` (0 → use module default)
- Tags 1–14 untouched; deserializing old messages with new code is safe

### Converters (Bidirectional Serialization) ✅
- `convert_to_feems.py`: Proto → Python COGAS; unpacks `fuel_modes` → `multi_fuel_characteristics`; applies default fallback (`or _DEFAULT_*`)
- `convert_to_protobuf.py`: Python COGAS → Proto; serializes `multi_fuel_characteristics` → `fuel_modes`; writes scalar GHG fields

### COGAS Component Model (Backward Compatible) ✅
- `multi_fuel_characteristics: Optional[List[FuelCharacteristics]]` — None for legacy single-fuel
- `ch4_factor_gch4_per_gfuel`, `n2o_factor_gn2o_per_gfuel`, `c_slip_percent` with module-level defaults
- `set_fuel_in_use(fuel_type, fuel_origin)` → selects active mode; updates `fuel_type` and `fuel_origin` properties
- `fuel_consumer_type_fuel_eu_maritime` returns `GAS_TURBINE` (replaces error path)
- Active mode BSFC/emissions via `_fuel_in_use` in run-point method

### Fuel Option Toolchain (Complete Integration) ✅
- `ElectricPowerSystem._extract_fuel_options_from_component()` handles COGES
- COGES returns all `multi_fuel_characteristics` as options (primary: i==0 convention)
- `available_fuel_options` and `available_fuel_options_by_converter` include COGES
- No duplicate logic; single unified helper function

### Fuel EU Maritime Table ✅
- 7 Gas Turbine rows (Fossil/BIO/RFNBO for LNG, Diesel; H2 variants)
- Factors: Cf_CH4=0.000192, Cf_N2O=0.000048, C_slip=0.01% (except H2 zeroed)
- Header comment notes provisional status pending Annex II amendment

### Node.py COGES Path ✅
- `set_fuel_in_use()` call before run-point (activates mode)
- User-fuel lookup via `find_user_fuel()` (matches by type/origin)
- `_resolve_fuel_consumer_class` extended for COGES (returns `fuel_consumer_type_fuel_eu_maritime`)
- Forward all required parameters (fuel_specified_by, lhv, WtT, TtW)

---

## Lessons Learned

### What Went Well

1. **Design-first approach paid off** — Comprehensive plan (8 design sections) caught edge cases (e.g., CH4 vs slip distinction, three-level override priority, proto field tag planning). Gap analysis was minimal because design was precise.

2. **Backward compatibility maintained throughout** — COGAS without `multi_fuel_characteristics` remains fully functional; no existing code broken. Proto schema expansion (new optional fields) is transparent to old deserializers.

3. **Reuse of existing patterns** — `FuelCharacteristics`, `set_fuel_in_use()`, node.py forwarding followed `EngineMultiFuel` and Genset templates. Reduced new concepts and simplified onboarding.

4. **Regulatory guidance (IPCC 2006 via IMO LCA) provided strong foundation** — No ambiguity on emission defaults; clear sourcing in plan/design made implementation straightforward.

5. **Test-driven coverage ensured correctness** — 25 unit tests + 1 integration test caught edge cases (e.g., unknown fuel errors, c_slip_percent backward compat, proto round-trip). 96% match rate achieved on first design attempt.

### Areas for Improvement

1. **FuelEU Maritime "provisional" mapping** — Gas turbines are now mapped to `GAS_TURBINE` enum, but regulation doesn't define this class. Mitigation: clearly marked as provisional; easy to update when Annex II amended. Future work: monitor regulatory updates.

2. **Multi-fuel mode switching scope** — Current implementation only computes `fuel_in_use` (main fuel per assumption). Annual fuel-mode optimization (selecting optimal blend for a voyage) is deferred. Consideration: document in API reference that this is a future feature; users should not expect runtime mode switching without explicit design phase.

3. **FuelEU fallback for unlisted technologies is provisional** — Current design uses "Steam Turbines and Boilers" analogy. If future regulation adds dedicated gas turbine entry with different factors, will need CSV update + re-testing. Mitigation: periodic regulatory scan; flag in changelog when FuelEU amended.

4. **node.py user-fuel lookup pattern** — Current implementation uses `find_user_fuel(effective_user_fuels, fuel_type, fuel_origin)` to select matching fuel. Design spec showed index-based `[0]` access. While actual is more correct, could be clearer in code comments or API reference.

### To Apply Next Time

1. **Regulatory sourcing clarity** — When dealing with unlisted technologies, reference authoritative guidance (IMO LCA Guidelines, IPCC) in plan and design documents. Makes implementation and future amendments transparent.

2. **Proto schema versioning for optional fields** — Document the "0 → use default" convention in proto comments for fields like `ch4_factor_gch4_per_gfuel`. Helps future maintainers understand fallback semantics.

3. **Test edge cases for backward compat** — Explicitly test that code without new optional parameters (e.g., COGAS without `multi_fuel_characteristics`) still works. Catches breaking changes early.

4. **Provisional design decisions need changelog notes** — Mark features or mappings that depend on future regulation changes (e.g., FuelEU gas turbine) with future-amendment pointers in the changelog and API reference.

---

## API Reference for Users

### Configuration: Single-Fuel COGAS (Legacy)

```python
from feems.components_model.component_mechanical import COGAS
import numpy as np

cogas = COGAS(
    name="GT-100",
    rated_power=Power_kW(10000),
    eff_curve=efficiency_array,  # combined GT+ST curve
    fuel_type=TypeFuel.NATURAL_GAS,
    fuel_origin=FuelOrigin.FOSSIL,
    emissions_curves=[...],
    nox_calculation_method=NOxCalculationMethod.TIER_3,
    # ch4_factor_gch4_per_gfuel, n2o_factor_gn2o_per_gfuel, c_slip_percent
    # use module defaults (0.000192, 0.000048, 0.01) if not specified
)
```

**Emission factors applied:**
- CH4: 0.000192 g/g (IPCC 2006 default for gas turbines)
- N2O: 0.000048 g/g (IPCC 2006 default)
- Slip: 0.01% (spec document / IPCC consensus)

### Configuration: Multi-Fuel COGAS

```python
from feems.components_model.component_mechanical import COGAS, FuelCharacteristics

lng_mode = FuelCharacteristics(
    main_fuel_type=TypeFuel.NATURAL_GAS,
    main_fuel_origin=FuelOrigin.FOSSIL,
    bsfc_curve=lng_efficiency_array,
    emission_curves=[...],
    engine_cycle_type=EngineCycleType.BRAYTON,
)

h2_mode = FuelCharacteristics(
    main_fuel_type=TypeFuel.HYDROGEN,
    main_fuel_origin=FuelOrigin.FOSSIL,
    bsfc_curve=h2_efficiency_array,
    emission_curves=[...],
    engine_cycle_type=EngineCycleType.BRAYTON,
)

cogas = COGAS(
    name="GT-100-MultiF",
    rated_power=Power_kW(10000),
    eff_curve=None,  # not used when multi_fuel_characteristics present
    multi_fuel_characteristics=[lng_mode, h2_mode],
    # Emission defaults same as above; can also override per-instance
    ch4_factor_gch4_per_gfuel=0.000192,  # optional explicit override
    n2o_factor_gn2o_per_gfuel=0.000048,
    c_slip_percent=0.01,
)

# Later, in simulation:
cogas.set_fuel_in_use(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)  # Select LNG mode
# ... or ...
cogas.set_fuel_in_use(TypeFuel.HYDROGEN, FuelOrigin.FOSSIL)     # Select H2 mode
```

**First mode** (index 0) in `multi_fuel_characteristics` is auto-selected at initialization.

### FuelEU Maritime Integration

```python
cogas.fuel_consumer_type_fuel_eu_maritime
# Returns: FuelConsumerClassFuelEUMaritime.GAS_TURBINE

# In system-level fuel option queries:
system.available_fuel_options_by_converter.get('gt-100')
# Returns: {'fuel_type': [TypeFuel.NATURAL_GAS, TypeFuel.HYDROGEN], 'origin': [FuelOrigin.FOSSIL, ...]}
```

**Regulatory note:** Gas turbines are provisionally mapped to the `GAS_TURBINE` enum (Cslip=0.01%, same as "Steam Turbines and Boilers"). This mapping is **provisional**; it will be updated when FuelEU Maritime Annex II is amended to include a dedicated gas turbine class.

### Emission Curve GHG Override (Issue #85)

```python
# If you provide per-load-point emission data via EmissionCurve,
# it takes priority over the scalar factors:

cogas_with_curve = COGAS(
    ...,
    emissions_curves=[
        EmissionCurve(
            emission_type=EmissionType.CH4,
            load_percentage_array=[0, 25, 50, 75, 100],
            emission_g_per_kwh=[0.1, 0.08, 0.07, 0.06, 0.05],
        ),
        # ... additional curves
    ],
    ch4_factor_gch4_per_gfuel=0.000192,  # ignored in favor of curve
)

# In this case, the curve's per-load CH4 values are used,
# and the scalar `ch4_factor` is overridden (highest priority per design).
```

---

## Next Steps

### For Maintainers

1. **Monitor FuelEU Maritime Annex II updates** — When regulation adds a dedicated gas turbine class, update `fuel_eu_fuel_table.csv` and remove the "provisional" comment.

2. **Document multi-fuel mode switching as future feature** — In API reference or feature roadmap, clarify that annual fuel-mode optimization (selecting optimal LNG/H2 blend for each voyage) is deferred; current scope is per-scenario mode selection only.

3. **Track IPCC / IMO LCA guideline updates** — Every ~5 years, IPCC and IMO publish new emission methodology. Flag in changelog if defaults need revision.

### For Users Adopting COGES

1. **Define multi-fuel modes with per-mode emission curves** — If supplying custom BSFC/emission data, provide separate curves for each fuel composition (LNG vs H2 blend, etc.).

2. **Use `FuelEU Maritime` mode for regulatory compliance** — `fuel_consumer_type_fuel_eu_maritime` returns `GAS_TURBINE`; this is now properly supported in FuelEU lookups.

3. **Set active fuel mode before simulation** — Call `cogas.set_fuel_in_use()` in node.py is automatic, but if running COGAS outside of system simulation, remember to set the active mode.

4. **Validate emission defaults for your fleet** — IPCC 2006 defaults (CH4=0.000192, N2O=0.000048, slip=0.01%) are canonical for gas turbines >3 MW. If your units differ, override via constructor or emission curves.

---

## Related Documents

- **Plan:** `docs/01-plan/features/coges-simulation-support.plan.md`
- **Design:** `docs/02-design/features/coges-simulation-support.design.md`
- **Gap Analysis:** `docs/03-analysis/coges-simulation-support.analysis.md`
- **Issue:** GitHub #89
- **Branch:** `feature/issue-89-coges-simulation-support`

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-04-27 | Initial completion report; all deliverables 96% match rate | Kevin Koosup Yum |
