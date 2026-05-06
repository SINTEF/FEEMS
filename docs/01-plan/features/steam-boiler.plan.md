# Implementation Plan: Steam Boiler Model

**Issue:** #92  
**Backlog:** `docs/backlog/2026-05-06-steam-boiler.md`  
**ADRs:** `docs/adr/0001-steam-boiler-capacity-in-kg-per-h.md`, `docs/adr/0002-steam-boiler-standalone-topology.md`

---

## Dependency Graph

```
T1  saturated steam table (constant.py)
 └─► T2  SteamBoiler core — single-fuel, efficiency-curve only
      └─► T3  curve normalisation — kg_fuel/h + kg_fuel/kg_steam input types
           └─► T4  multi-fuel support (FuelCharacteristics)
                └─► ══ CHECKPOINT A: SteamBoiler standalone ══
                     ├─► T5  FEEMSResult new fields + __merge
                     │    └─► T6  MachinerySystem helper + ElectricPowerSystem
                     │         └─► T7  remaining three system model classes
                     │              └─► ══ CHECKPOINT B: system integration ══
                     │                   └─► T10  API reference
                     └─► T8  proto message + enum + compile
                          └─► T9  converters + round-trip tests
                               └─► ══ CHECKPOINT C: proto round-trip ══
```

T8–T9 are independent of T5–T7 after Checkpoint A. Both tracks converge at T10.

---

## Tasks

### T1 — Saturated steam lookup table

**Files:** `feems/feems/constant.py`

Add a module-level IAPWS-sourced table for `h_g` (saturated vapour enthalpy, kJ/kg) at pressures 1–20 bar, and a `get_saturated_steam_h_g_kj_per_kg(pressure_bar)` function that interpolates it (PchipInterpolator). Raise `InputError` if pressure is outside [1, 20] bar.

**Table values (IAPWS-IF97):**

| P (bar) | h_g (kJ/kg) |
|---------|-------------|
| 1       | 2675.6      |
| 2       | 2706.3      |
| 3       | 2724.9      |
| 4       | 2737.6      |
| 5       | 2747.5      |
| 6       | 2756.1      |
| 7       | 2763.1      |
| 8       | 2769.1      |
| 9       | 2774.3      |
| 10      | 2778.9      |
| 12      | 2786.5      |
| 15      | 2792.2      |
| 20      | 2798.3      |

**Acceptance criteria:**
- `get_saturated_steam_h_g_kj_per_kg(10.0)` returns value within ±0.1% of 2778.9
- `get_saturated_steam_h_g_kj_per_kg(7.0)` returns value within ±0.1% of 2763.1
- Pressure 0.5 bar raises `InputError`
- Pressure 21 bar raises `InputError`

**Verification:** `uv run pytest feems/tests/test_steam_boiler.py -k "steam_table"`

---

### T2 — SteamBoiler core (single-fuel, efficiency-curve input)

**Files:**
- `feems/feems/types_for_feems.py` — `TypeComponent.STEAM_BOILER = 30`
- `feems/feems/components_model/component_mechanical.py` — `BoilerRunPoint`, `SteamBoiler`

**`BoilerRunPoint` dataclass:**
```python
@dataclass(kw_only=True)
class BoilerRunPoint:
    load_ratio: np.ndarray
    fuel_flow_rate_kg_per_s: FuelConsumption
    steam_production_kg_per_s: np.ndarray
    thermal_efficiency: np.ndarray
    emissions_g_per_s: Dict[EmissionType, np.ndarray]
```

**`SteamBoiler` constructor (single-fuel path):**
```python
SteamBoiler(
    name: str,
    rated_steam_production_kg_per_h: float,
    working_pressure_bar: float,
    thermal_efficiency_curve: np.ndarray,       # [[load_ratio, η], ...]
    fuel_type: TypeFuel = TypeFuel.HFO,
    fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
    feed_water_temperature_c: float = 80.0,
    emissions_curves: List[EmissionCurve] | None = None,
    uid: str | None = None,
)
```

**Internal setup:**
- Call `get_saturated_steam_h_g_kj_per_kg(working_pressure_bar)` → store as `_h_g_kj_per_kg`
- Compute `_delta_h_kj_per_kg = _h_g_kj_per_kg - 4.18 * feed_water_temperature_c`
- Store `_thermal_efficiency_interp` via `get_efficiency_curve_from_points`
- Set `type = TypeComponent.STEAM_BOILER`

**`get_boiler_run_point(steam_demand_kg_per_h)`:**
```
load_ratio = steam_demand / rated_steam_production
η = _thermal_efficiency_interp(load_ratio)
Q_steam_kw = (steam_demand_kg_per_h / 3600) * _delta_h_kj_per_kg
fuel_power_kw = Q_steam_kw / η
fuel_kg_per_s = fuel_power_kw / (LHV_kJ_per_kg * 1000)  # LHV from Fuel object
emissions = {e: interp(load_ratio) * (steam_demand/3600 * _delta_h_kj_per_kg / η / 3600)
             for e in _emissions_interp}
```

**Acceptance criteria:**
- `TypeComponent.STEAM_BOILER` value is 30
- At 100% load (rated demand), `load_ratio == 1.0`
- `steam_production_kg_per_s * 3600 ≈ steam_demand_kg_per_h` (within float tolerance)
- `fuel_flow * LHV ≈ steam_flow * Δh / η` (energy balance holds to within 0.01%)
- Emissions at zero load are zero

**Verification:** `uv run pytest feems/tests/test_steam_boiler.py -k "core"`

---

### T3 — Curve normalisation (two additional input types)

**Files:** `feems/feems/components_model/component_mechanical.py`

Extend `SteamBoiler.__init__` to accept exactly one of three mutually-exclusive curve inputs. Normalise the non-efficiency inputs to `_thermal_efficiency_interp` during construction so the rest of the class is unchanged.

**`kg_fuel_per_kg_steam_curve` → η_th:**
```
η_th(x) = Δh / (sfc(x) * LHV)
```
where `sfc` is interpolated from `kg_fuel_per_kg_steam_curve` and LHV comes from the fuel type.

**`kg_fuel_per_h_curve` → sfc → η_th:**
```
sfc(x) = kg_fuel_per_h_curve(x) / (x * rated_steam_production_kg_per_h)
η_th(x) = Δh / (sfc(x) * LHV)
```

Raise `InputError` if more than one curve type is provided, or if none is provided.

**Acceptance criteria:**
- Three boilers constructed from three equivalent curves produce identical `fuel_flow_rate_kg_per_s` at the same `steam_demand_kg_per_h` (within 0.01%)
- `InputError` raised if two curve types supplied simultaneously
- `InputError` raised if no curve type supplied

**Verification:** `uv run pytest feems/tests/test_steam_boiler.py -k "curve_normalisation"`

---

### T4 — Multi-fuel SteamBoiler

**Files:** `feems/feems/components_model/component_mechanical.py`

Add `multi_fuel_characteristics: List[FuelCharacteristics] | None = None` to `SteamBoiler.__init__`. Follow the `EngineMultiFuel` pattern exactly:

- If `multi_fuel_characteristics` is provided, `fuel_type` and `fuel_origin` default from `multi_fuel_characteristics[0]`
- Add `set_fuel_in_use(fuel_type, fuel_origin)` — raises `ValueError` if the combination is not in the list
- `get_boiler_run_point` uses the active fuel's LHV; each `FuelCharacteristics` entry provides its own `thermal_efficiency_curve` (via `eff_curve` field)

**Acceptance criteria:**
- Multi-fuel boiler with HFO and LNG modes: switching fuel changes `fuel_flow_rate_kg_per_s` in proportion to LHV ratio
- `set_fuel_in_use` with an unknown fuel raises `ValueError`
- Single-fuel boiler is unaffected (no regression)

**Verification:** `uv run pytest feems/tests/test_steam_boiler.py -k "multi_fuel"`

---

### ══ CHECKPOINT A ══

```
uv run pytest feems/tests/test_steam_boiler.py
```

All SteamBoiler unit tests must pass. Zero failures before proceeding to T5–T8.

---

### T5 — FEEMSResult new fields + `__merge`

**Files:** `feems/feems/types_for_feems.py`

Add to `FEEMSResult`:
```python
running_hours_boiler_total_hr: float = 0.0
steam_production_boiler_total_kg: float = 0.0
fuel_consumption_boiler_total: FuelConsumption = field(default_factory=FuelConsumption)
```

Update `__merge`:
- `running_hours_boiler_total_hr` — sum (same as other running hours)
- `steam_production_boiler_total_kg` — sum
- `fuel_consumption_boiler_total` — `FuelConsumption.__add__` (already supports this)
- Boiler fuel is also added into `multi_fuel_consumption_total_kg` when merging

Update `to_list_for_electric_component` and `to_list_for_mechanical_component` if they need to surface boiler data (check callers — likely no change needed).

**Acceptance criteria:**
- `FEEMSResult() + FEEMSResult()` with non-zero boiler fields sums correctly
- `sum_and_extend_duration` on two boiler results produces correct totals
- `multi_fuel_consumption_total_kg` includes boiler fuel
- Default `FEEMSResult()` has `running_hours_boiler_total_hr == 0.0`

**Verification:** `uv run pytest feems/tests/ -k "feems_result"` (add new test cases)

---

### T6 — `MachinerySystem._calculate_boiler_result` + `ElectricPowerSystem`

**Files:** `feems/feems/system_model.py`

**Base class helper** (add to `MachinerySystem`):
```python
def _calculate_boiler_result(
    self,
    boilers: List[SteamBoiler],
    steam_demand_kg_per_h: np.ndarray,
) -> FEEMSResult:
```
- For each boiler: call `get_boiler_run_point(steam_demand_kg_per_h)`
- Integrate `fuel_flow_rate_kg_per_s` over `time_interval_s` → total fuel kg
- Integrate `steam_production_kg_per_s` → total steam kg
- Compute running hours from non-zero steam demand timesteps
- Return `FEEMSResult` with `running_hours_boiler_total_hr`, `steam_production_boiler_total_kg`, `fuel_consumption_boiler_total` (and boiler fuel in `multi_fuel_consumption_total_kg`)
- Accumulate emissions into `total_emission_kg` and `co2_emission_total_kg`

**ElectricPowerSystem.get_fuel_energy_consumption_running_time** — add optional parameters:
```python
boilers: List[SteamBoiler] = [],
steam_demand_kg_per_h: np.ndarray | None = None,
```
Call `_calculate_boiler_result` if `boilers` is non-empty; merge with `sum_with_freeze_duration`.

**Acceptance criteria:**
- `ElectricPowerSystem` with one HFO boiler, constant 10 000 kg/h steam demand for 3 600 s:
  - `running_hours_boiler_total_hr ≈ 1.0`
  - `steam_production_boiler_total_kg ≈ 10 000`
  - `fuel_consumption_boiler_total` non-zero
  - `multi_fuel_consumption_total_kg` includes boiler fuel
- `boilers=[]` produces identical result to before (no regression)

**Verification:** `uv run pytest feems/tests/test_steam_boiler.py -k "integration_electric"`

---

### T7 — Remaining three system model classes

**Files:** `feems/feems/system_model.py`

Apply identical changes to:
- `MechanicalPropulsionSystem.get_fuel_energy_consumption_running_time`
- `HybridPropulsionSystem.get_fuel_energy_consumption_running_time`
- `MechanicalPropulsionSystemWithElectricPowerSystem.get_fuel_energy_consumption_running_time`

One smoke test per system type: construct the minimal system, attach a boiler, verify `running_hours_boiler_total_hr > 0` in the result.

**Acceptance criteria:**
- All four system classes accept `boilers` and `steam_demand_kg_per_h`
- `uv run pytest` passes with no regressions

**Verification:** `uv run pytest feems/tests/`

---

### ══ CHECKPOINT B ══

```
uv run pytest feems/tests/
```

All feems tests pass. Zero regressions. `FEEMSResult` boiler fields populated correctly for all four system types.

---

### T8 — Proto message + enum + compile

**Files:** `machinery-system-structure/proto/system_structure.proto`

Add to `ComponentType` enum:
```protobuf
STEAM_BOILER = 30;
```

Add `SteamBoiler` message:
```protobuf
message SteamBoiler {
  string name = 1;
  string uid = 2;
  double rated_steam_production_kg_per_h = 3;
  double working_pressure_bar = 4;
  double feed_water_temperature_c = 5;
  FuelType fuel_type = 6;
  FuelOrigin fuel_origin = 7;
  EfficiencyCurve thermal_efficiency_curve = 8;
  repeated EmissionCurve emission_curves = 9;
  repeated COGAS.FuelMode fuel_modes = 10;  // reuse existing FuelMode for multi-fuel
}
```

Run `./compile_proto.sh` to regenerate `system_structure_pb2.py` and `system_structure_pb2.pyi`.

**Acceptance criteria:**
- Proto compiles without errors
- `system_structure_pb2.py` contains `SteamBoiler` class
- `ComponentType.STEAM_BOILER` value is 30 in the generated bindings

**Verification:** `python -c "from MachSysS import system_structure_pb2; print(system_structure_pb2.SteamBoiler())"`

---

### T9 — Converters + round-trip tests

**Files:**
- `machinery-system-structure/MachSysS/convert_to_protobuf.py`
- `machinery-system-structure/MachSysS/convert_to_feems.py`

**`convert_to_protobuf.py`:** add `steam_boiler_to_proto(boiler: SteamBoiler) -> proto.SteamBoiler`  
**`convert_to_feems.py`:** add `proto_to_steam_boiler(pb: proto.SteamBoiler) -> SteamBoiler`

Both handle:
- Single-fuel (fuel_type + fuel_origin + efficiency curve)
- Multi-fuel (fuel_modes, same proto structure as COGAS)
- Emission curves

**Acceptance criteria:**
- Round-trip: `proto_to_steam_boiler(steam_boiler_to_proto(boiler))` produces a boiler with identical `rated_steam_production_kg_per_h`, `working_pressure_bar`, `feed_water_temperature_c`, `fuel_type`, `fuel_origin`
- Round-trip: `get_boiler_run_point(10000)` on original vs. round-tripped boiler returns same `fuel_flow_rate_kg_per_s` (within 0.01%)
- Multi-fuel round-trip preserves all fuel modes

**Verification:** `uv run pytest machinery-system-structure/tests/ -k "steam_boiler"`

---

### ══ CHECKPOINT C ══

```
uv run pytest machinery-system-structure/tests/
```

All MachSysS tests pass including new round-trip tests.

---

### T10 — API reference updates

**Files:**
- `docs/api/feems/API_REFERENCE.md`
- `docs/api/machinery-system-structure/API_REFERENCE.md`

Document:
- `SteamBoiler` — constructor signature, all three curve input types, `get_boiler_run_point`
- `BoilerRunPoint` — all fields
- `FEEMSResult` — three new fields
- `MachinerySystem._calculate_boiler_result` — signature and contract
- MachSysS converters — `steam_boiler_to_proto`, `proto_to_steam_boiler`

**Acceptance criteria:**
- Every public method/class added in T1–T9 has an entry in the relevant API reference

---

## Parallel Work Opportunities

After **Checkpoint A**, T5–T7 (system model track) and T8–T9 (proto track) can proceed independently. If two developers are available, split there.

## Estimated Task Sizes

| Task | Effort |
|------|--------|
| T1 | XS — data entry + one function |
| T2 | M — new class + run-point math |
| T3 | S — constructor extension + normalisation math |
| T4 | S — mirrors EngineMultiFuel, mostly copy-adapt |
| T5 | S — dataclass fields + merge logic |
| T6 | M — integration logic + test setup |
| T7 | S — copy T6 pattern three times |
| T8 | S — proto syntax + compile |
| T9 | S — converters follow COGAS pattern |
| T10 | XS — documentation |
