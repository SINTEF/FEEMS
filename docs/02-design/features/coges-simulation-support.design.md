# Design: COGES Simulation Support

**Plan:** `docs/01-plan/features/coges-simulation-support.plan.md`  
**Date:** 2026-04-27  
**Author:** Kevin Koosup Yum  
**Status:** Draft

---

## 1. Context

`COGAS`/`COGES` classes already exist. `COGAS` holds the combined GT+ST efficiency curve
and emission curve mechanism (issue #85). `COGES` wraps a `COGAS` + `ElectricMachine` and
participates in `ElectricPowerSystem` load sharing as a `POWER_SOURCE` alongside Gensets.

Three gaps block complete simulation:

1. No `BRAYTON` enum value → gas turbines cannot be identified by cycle type
2. No CH4/N2O/slip defaults for gas turbines → GHG calculation uses 0 from IMO table
3. `COGAS` has no multi-fuel mode structure → secondary fuel (LNG/H2 blends) not representable
4. `node.py` COGES branch is missing `fuel_type`, `fuel_origin`, `user_defined_fuels` forwarding

PMS (`pms_basic.py`) already handles COGES correctly via the generic `power_sources` list — no
change needed there.

---

## 2. Changes

### 2.1 `feems/feems/types_for_feems.py`

Add `BRAYTON = 4` to `EngineCycleType`:

```python
class EngineCycleType(Enum):
    NONE = 0
    DIESEL = auto()    # 1
    OTTO = auto()      # 2
    LEAN_BURN_SPARK_IGNITION = auto()  # 3
    BRAYTON = auto()   # 4  ← new
```

---

### 2.2 `feems/feems/fuel.py`

#### 2.2.1 New enum value

```python
class FuelConsumerClassFuelEUMaritime(Enum):
    NONE = 0
    ICE = 1
    LNG_OTTO_MEDIUM_SPEED = 2
    LNG_OTTO_SLOW_SPEED = 3
    LNG_DIESEL = 4
    LNG_LBSI = 5
    FUEL_CELL = 6
    GAS_TURBINE = 7  # ← new; provisional mapping to Steam Turbines/Boilers factors
```

Add to `_FUEL_CONSUMER_CLASS_FUEL_EU_MARITIME_MAPPING`:

```python
FuelConsumerClassFuelEUMaritime.GAS_TURBINE: "Gas Turbine",
```

#### 2.2.2 Extend `Fuel.with_emission_curve_ghg_overrides()`

Add an explicit `c_slip_percent` parameter. `None` preserves existing behaviour (zero c_slip
when `ch4_factor` is given); a float value is used as-is. This allows gas turbine scalar
overrides to set a non-zero `c_slip_percent` alongside `ch4_factor`.

```python
def with_emission_curve_ghg_overrides(
    self,
    ch4_factor_gch4_per_gfuel: Optional[float] = None,
    n2o_factor_gn2o_per_gfuel: Optional[float] = None,
    c_slip_percent: Optional[float] = None,   # ← new parameter
) -> "Fuel":
    if ch4_factor_gch4_per_gfuel is None and n2o_factor_gn2o_per_gfuel is None and c_slip_percent is None:
        return self
    import copy, dataclasses
    new_ttw = [
        dataclasses.replace(
            entry,
            ch4_factor_gch4_per_gfuel=(
                ch4_factor_gch4_per_gfuel
                if ch4_factor_gch4_per_gfuel is not None
                else entry.ch4_factor_gch4_per_gfuel
            ),
            n2o_factor_gn2o_per_gfuel=(
                n2o_factor_gn2o_per_gfuel
                if n2o_factor_gn2o_per_gfuel is not None
                else entry.n2o_factor_gn2o_per_gfuel
            ),
            c_slip_percent=(
                c_slip_percent             if c_slip_percent is not None      # explicit value given
                else 0.0                   if ch4_factor_gch4_per_gfuel is not None  # legacy: zero slip
                else entry.c_slip_percent  # unchanged
            ),
        )
        for entry in self.ghg_emission_factor_tank_to_wake
    ]
    new_fuel = copy.copy(self)
    new_fuel.ghg_emission_factor_tank_to_wake = new_ttw
    return new_fuel
```

Backward compatibility: existing callers pass only `ch4_factor` and/or `n2o_factor`, and
`c_slip_percent` defaults to `None`, so the legacy zero-out behaviour is preserved.

---

### 2.3 `feems/feems/package_data/fuel_eu_fuel_table.csv`

Add `Gas Turbine` rows for each fuel type, copying factors from "Steam Turbines and Boilers"
(the closest Annex II analogy: Cslip = 0.01%). Since the FuelEU Maritime regulation does not
define a gas turbine consumer class, these rows are **provisional**.

Rows to add (one per relevant fuel pathway, same structure as existing LNG rows):

```
# Gas Turbine rows — provisional, no FuelEU Annex II entry for gas turbines.
# Factors copied from "Steam Turbines and Boilers" (Cslip = 0.01%).
# Source: IPCC 2006 Vol.2 Ch.2 (Cf_CH4 = 4 kg/TJ, Cf_N2O = 1 kg/TJ) via IMO MEPC.391(81).
# Update when FuelEU Annex II is amended to include gas turbines.
Fossil,HFO,0.0405,13.5,Gas Turbine,3.114,0.000192,0.000048,0.01,...
Fossil,LNG,0.048,18.5,Gas Turbine,2.75,0.000192,0.000048,0.01,...
Fossil,Diesel,0.0427,14.4,Gas Turbine,3.206,0.000192,0.000048,0.01,...
Fossil,H2,0.12,132,Gas Turbine,0,0,0,0,...
... (one row per fossil/bio/RFNBO pathway used by COGAS)
```

The `Cf_CH4` and `Cf_N2O` values are the IPCC 2006 defaults (4 kg/TJ and 1 kg/TJ at LNG LCV
48 MJ/kg → 0.000192 g/g and 0.000048 g/g). `C_slip = 0.01%` matches spec document default.

---

### 2.4 `feems/feems/components_model/component_mechanical.py`

#### 2.4.1 Module-level constants

```python
_DEFAULT_BRAYTON_C_SLIP_PERCENT: float = 0.01
_DEFAULT_BRAYTON_CH4_GFUEL: float = 0.000192   # IPCC 2006 Vol.2 Ch.2, Table 2.6 (4 kg/TJ at LNG LCV 48 MJ/kg)
_DEFAULT_BRAYTON_N2O_GFUEL: float = 0.000048   # IPCC 2006 Vol.2 Ch.2, Table 2.6 (1 kg/TJ at LNG LCV 48 MJ/kg)
```

#### 2.4.2 `FuelCharacteristics` — add `secondary_fuel_type` property

`FuelCharacteristics` is a dataclass. Add a `secondary_fuel_type` property that is an alias for
`pilot_fuel_type` to clarify semantics for BRAYTON engines (no change to stored field):

```python
@dataclass
class FuelCharacteristics:
    nox_calculation_method: NOxCalculationMethod = NOxCalculationMethod.TIER_2
    main_fuel_type: TypeFuel = TypeFuel.DIESEL
    main_fuel_origin: FuelOrigin = FuelOrigin.FOSSIL
    pilot_fuel_type: TypeFuel = None          # kept for backward compat
    pilot_fuel_origin: FuelOrigin = None
    bsfc_curve: np.ndarray = None
    bspfc_curve: np.ndarray = None
    emission_curves: List[EmissionCurve] = None
    engine_cycle_type: EngineCycleType = EngineCycleType.DIESEL

    @property
    def secondary_fuel_type(self) -> Optional[TypeFuel]:
        return self.pilot_fuel_type

    @secondary_fuel_type.setter
    def secondary_fuel_type(self, value: Optional[TypeFuel]) -> None:
        self.pilot_fuel_type = value

    @property
    def secondary_fuel_origin(self) -> Optional[FuelOrigin]:
        return self.pilot_fuel_origin

    @secondary_fuel_origin.setter
    def secondary_fuel_origin(self, value: Optional[FuelOrigin]) -> None:
        self.pilot_fuel_origin = value
```

#### 2.4.3 `COGAS.__init__` — new parameters

```python
def __init__(
    self,
    name: str = "",
    rated_power: Power_kW = Power_kW(0),
    eff_curve: np.ndarray = np.array([1]),
    rated_speed: Speed_rpm = Speed_rpm(0),
    gas_turbine_power_curve: np.ndarray = None,
    steam_turbine_power_curve: np.ndarray = None,
    fuel_type: TypeFuel = TypeFuel.DIESEL,
    fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
    emissions_curves: List[EmissionCurve] = None,
    nox_calculation_method: NOxCalculationMethod = NOxCalculationMethod.TIER_3,
    uid: Optional[str] = None,
    # ↓ new parameters
    multi_fuel_characteristics: Optional[List[FuelCharacteristics]] = None,
    ch4_factor_gch4_per_gfuel: float = _DEFAULT_BRAYTON_CH4_GFUEL,
    n2o_factor_gn2o_per_gfuel: float = _DEFAULT_BRAYTON_N2O_GFUEL,
    c_slip_percent: float = _DEFAULT_BRAYTON_C_SLIP_PERCENT,
):
```

Store them as instance attributes:

```python
self.multi_fuel_characteristics = multi_fuel_characteristics
self.ch4_factor_gch4_per_gfuel = ch4_factor_gch4_per_gfuel
self.n2o_factor_gn2o_per_gfuel = n2o_factor_gn2o_per_gfuel
self.c_slip_percent = c_slip_percent
if multi_fuel_characteristics:
    self.fuel_type = multi_fuel_characteristics[0].main_fuel_type
    self.fuel_origin = multi_fuel_characteristics[0].main_fuel_origin
    self._fuel_in_use: FuelCharacteristics = multi_fuel_characteristics[0]
else:
    self._fuel_in_use = None
```

#### 2.4.4 `COGAS.set_fuel_in_use()`

Mirror `EngineMultiFuel.set_fuel_in_use()`:

```python
def set_fuel_in_use(
    self, fuel_type: TypeFuel = None, fuel_origin: FuelOrigin = None
) -> None:
    if self.multi_fuel_characteristics is None:
        return
    if fuel_type is None or fuel_origin is None:
        self._fuel_in_use = self.multi_fuel_characteristics[0]
        return
    fc = next(
        (
            fc for fc in self.multi_fuel_characteristics
            if fc.main_fuel_type == fuel_type and fc.main_fuel_origin == fuel_origin
        ),
        None,
    )
    if fc is None:
        raise ValueError(
            f"No FuelCharacteristics for fuel_type={fuel_type}, fuel_origin={fuel_origin}."
        )
    self._fuel_in_use = fc
    self.fuel_type = fc.main_fuel_type
    self.fuel_origin = fc.main_fuel_origin
```

#### 2.4.5 `COGAS.fuel_consumer_type_fuel_eu_maritime`

```python
@property
def fuel_consumer_type_fuel_eu_maritime(self) -> FuelConsumerClassFuelEUMaritime:
    return FuelConsumerClassFuelEUMaritime.GAS_TURBINE
```

(Remove the `Warning(...)` call and `return None`.)

#### 2.4.6 `COGAS.get_gas_turbine_run_point_from_power_output_kw()` — GHG override

Remove the `ValueError` guard for `FUEL_EU_MARITIME`. After the existing issue #85 emission-curve
block, add a scalar-field override using the new `c_slip_percent` parameter:

```python
# --- emission-curve GHG override (issue #85, highest priority) ---
_ch4_g_per_kwh = (
    self.emissions_g_per_kwh(EmissionType.CH4, load_ratio)
    if EmissionType.CH4 in self._emissions_per_kwh_interp else None
)
_n2o_g_per_kwh = (
    self.emissions_g_per_kwh(EmissionType.N2O, load_ratio)
    if EmissionType.N2O in self._emissions_per_kwh_interp else None
)
if _ch4_g_per_kwh is not None or _n2o_g_per_kwh is not None:
    _power_kwh_per_s = power_kw / 3600
    _bsfc_eq_g_per_kwh = fuel_consumption_kg_per_s * 1000 / _power_kwh_per_s
    fuel = fuel.with_emission_curve_ghg_overrides(
        ch4_factor_gch4_per_gfuel=(
            _ch4_g_per_kwh / _bsfc_eq_g_per_kwh if _ch4_g_per_kwh is not None else None
        ),
        n2o_factor_gn2o_per_gfuel=(
            _n2o_g_per_kwh / _bsfc_eq_g_per_kwh if _n2o_g_per_kwh is not None else None
        ),
        # c_slip_percent=None → legacy zero-out behaviour
    )
else:
    # --- scalar-field / module-default override (BRAYTON defaults, lower priority) ---
    fuel = fuel.with_emission_curve_ghg_overrides(
        ch4_factor_gch4_per_gfuel=self.ch4_factor_gch4_per_gfuel,
        n2o_factor_gn2o_per_gfuel=self.n2o_factor_gn2o_per_gfuel,
        c_slip_percent=self.c_slip_percent,  # explicit: not zeroed
    )
```

If `multi_fuel_characteristics` is set, use `self._fuel_in_use` to resolve the active BSFC
curve and emissions curves instead of the top-level fields. This mirrors how `EngineMultiFuel`
delegates to `engine_in_use`:

```python
if self._fuel_in_use is not None:
    # replace eff_curve with _fuel_in_use.bsfc_curve equivalent
    # (actual implementation: re-run get_efficiency_from_load_percentage using _fuel_in_use)
    # See section 2.4.7 below
    pass
```

#### 2.4.7 `COGAS` with `multi_fuel_characteristics` — active mode BSFC

When `multi_fuel_characteristics` is set, `_fuel_in_use.bsfc_curve` replaces the top-level
`eff_curve` for efficiency lookup. Add a helper that returns the effective `eff_curve`:

```python
@property
def _effective_eff_curve(self) -> np.ndarray:
    if self._fuel_in_use is not None and self._fuel_in_use.bsfc_curve is not None:
        return self._fuel_in_use.bsfc_curve
    return None  # fall back to self.eff_curve via parent get_efficiency_from_load_percentage
```

In `get_gas_turbine_run_point_from_power_output_kw`, use `_effective_eff_curve` when present:

```python
if self._effective_eff_curve is not None:
    # compute efficiency from bsfc_curve (same interpolation used by Engine)
    eff = get_efficiency_from_bsfc(self._effective_eff_curve, load_ratio)
else:
    eff = self.get_efficiency_from_load_percentage(load_ratio)
```

And use `_fuel_in_use.emission_curves` when present instead of `self.emission_curves`:

```python
active_emission_curves = (
    self._fuel_in_use.emission_curves
    if self._fuel_in_use is not None and self._fuel_in_use.emission_curves
    else self.emission_curves
)
```

> **Note:** `COGAS` without `multi_fuel_characteristics` (existing usage) is fully unchanged —
> `_fuel_in_use` is `None`, so the code falls through to the existing paths.

---

### 2.5 `feems/feems/components_model/node.py`

In `get_fuel_emission_energy_balance_for_component`, update the `TypeComponent.COGES` branch
(currently `node.py:382`):

```python
elif component.type == TypeComponent.COGES:
    component = cast(COGES, component)
    # ← call set_fuel_in_use before run-point so multi-fuel mode is active
    component.cogas.set_fuel_in_use(fuel_type=fuel_type, fuel_origin=fuel_origin)
    coges_run_point = component.get_system_run_point_from_power_output_kw(
        fuel_specified_by=fuel_specified_by,
        # ← forward user-defined fuels (parity with Genset)
        lhv_mj_per_g=effective_user_fuels[0].lhv_mj_per_g if effective_user_fuels else None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj=(
            effective_user_fuels[0].ghg_emission_factor_well_to_tank_gco2eq_per_mj
            if effective_user_fuels else None
        ),
        ghg_emission_factor_tank_to_wake=(
            [f.ghg_emission_factor_tank_to_wake[0] if f.ghg_emission_factor_tank_to_wake else None
             for f in effective_user_fuels]
            if effective_user_fuels else None
        ),
    )
    res.multi_fuel_consumption_total_kg = integrate_multi_fuel_consumption(
        fuel_consumption_kg_per_s=coges_run_point.cogas.fuel_flow_rate_kg_per_s,
        time_interval_s=time_interval_s,
        integration_method=integration_method,
    )
    # ← use _resolve_fuel_consumer_class instead of inline call
    fuel_consumer_class = _resolve_fuel_consumer_class(
        component, coges_run_point.cogas.fuel_flow_rate_kg_per_s
    )
    if fuel_consumer_class is not None:
        res.co2_emission_total_kg = (
            res.multi_fuel_consumption_total_kg.get_total_co2_emissions(
                fuel_consumer_class=fuel_consumer_class
            )
        )
    if (
        np.isscalar(coges_run_point.coges_load_ratio)
        or coges_run_point.coges_load_ratio.size == 1
    ):
        res.load_ratio_genset = coges_run_point.coges_load_ratio
    set_emission(
        engine_out=coges_run_point.cogas,
        integration_method=integration_method,
        result=res,
        time_interval_s=time_interval_s,
    )
    res.running_hours_genset_total_hr = running_hours
```

Also extend `_resolve_fuel_consumer_class` to handle `COGES`:

```python
def _resolve_fuel_consumer_class(...):
    ...
    if isinstance(source_component, COGES):
        return source_component.cogas.fuel_consumer_type_fuel_eu_maritime
    ...
```

---

### 2.6 `machinery-system-structure/proto/system_structure.proto`

#### 2.6.1 `Engine.EngineCycleType` — add `BRAYTON`

```proto
enum EngineCycleType {
    NONE = 0;
    DIESEL = 1;
    OTTO = 2;
    LEAN_BURN_SPARK_IGNITION = 3;
    BRAYTON = 4;  // ← new
}
```

#### 2.6.2 `COGAS` message — add new fields

```proto
message COGAS {
    // existing fields 1–14 unchanged
    string name = 1;
    double rated_power_kw = 2;
    double rated_speed_rpm = 3;
    Efficiency efficiency = 4;
    PowerCurve gas_turbine_power_curve = 5;
    PowerCurve steam_turbine_power_curve = 6;
    Fuel fuel = 7;
    uint32 order_from_switchboard_or_shaftline = 8;
    Engine.NOxCalculationMethod nox_calculation_method = 9;
    repeated EmissionCurve emission_curves = 10;
    double unit_price_usd = 11;
    double start_delay_s = 12;
    double turn_off_power_kw = 13;
    string uid = 14;
    // ← new fields (tags 15–18)
    repeated MultiFuelEngine.FuelMode fuel_modes = 15;   // multi-fuel mode switching
    double ch4_factor_gch4_per_gfuel = 16;               // IPCC default = 0.000192; 0 → use default
    double n2o_factor_gn2o_per_gfuel = 17;               // IPCC default = 0.000048; 0 → use default
    double c_slip_percent = 18;                           // spec default = 0.01; 0 → use default
}
```

Field tags 15–18 are the next available slots after 14. Tags 1–14 are untouched — backward
compatible with existing serialized proto messages (new fields default to 0 / empty when absent).

---

### 2.7 `machinery-system-structure/MachSysS/convert_to_feems.py`

Update `convert_proto_cogas_to_feems()`:

```python
def convert_proto_cogas_to_feems(proto_cogas: proto.COGAS) -> COGAS:
    nox_calculation_method = get_nox_calculation_method(proto_cogas)
    emission_curves = (
        [convert_emission_curve_to_feems(e) for e in proto_cogas.emission_curves]
        if proto_cogas.emission_curves else None
    )
    multi_fuel_characteristics = None
    if proto_cogas.fuel_modes:
        multi_fuel_characteristics = []
        for fuel_mode in proto_cogas.fuel_modes:
            fc = FuelCharacteristics(
                nox_calculation_method=convert_nox_calculation_method(
                    fuel_mode.nox_calculation_method
                ),
                main_fuel_type=TypeFuel(fuel_mode.main_fuel.fuel_type),
                main_fuel_origin=FuelOrigin(fuel_mode.main_fuel.fuel_origin),
                bsfc_curve=convert_proto_efficiency_bsfc_power_to_np_array(fuel_mode.main_bsfc),
                engine_cycle_type=EngineCycleType(fuel_mode.engine_cycle_type),
            )
            if (fuel_mode.HasField("pilot_fuel")
                    and fuel_mode.pilot_fuel.fuel_type != proto.FuelType.NONE3):
                fc.pilot_fuel_type = TypeFuel(fuel_mode.pilot_fuel.fuel_type)
                fc.pilot_fuel_origin = FuelOrigin(fuel_mode.pilot_fuel.fuel_origin)
            if fuel_mode.emission_curves:
                fc.emission_curves = [
                    convert_emission_curve_to_feems(e) for e in fuel_mode.emission_curves
                ]
            multi_fuel_characteristics.append(fc)

    # 0.0 in proto means "use module default" (proto3 default for double is 0)
    ch4 = proto_cogas.ch4_factor_gch4_per_gfuel or _DEFAULT_BRAYTON_CH4_GFUEL
    n2o = proto_cogas.n2o_factor_gn2o_per_gfuel or _DEFAULT_BRAYTON_N2O_GFUEL
    c_slip = proto_cogas.c_slip_percent or _DEFAULT_BRAYTON_C_SLIP_PERCENT

    return COGAS(
        name=proto_cogas.name,
        rated_power=proto_cogas.rated_power_kw,
        rated_speed=proto_cogas.rated_speed_rpm,
        eff_curve=convert_proto_efficiency_bsfc_power_to_np_array(proto_cogas.efficiency),
        gas_turbine_power_curve=convert_proto_efficiency_bsfc_power_to_np_array(
            proto_cogas.gas_turbine_power_curve
        ),
        steam_turbine_power_curve=convert_proto_efficiency_bsfc_power_to_np_array(
            proto_cogas.steam_turbine_power_curve
        ),
        fuel_type=TypeFuel(proto_cogas.fuel.fuel_type),
        fuel_origin=FuelOrigin(proto_cogas.fuel.fuel_origin),
        nox_calculation_method=nox_calculation_method,
        emissions_curves=emission_curves,
        uid=proto_cogas.uid if len(proto_cogas.uid) > _MIN_LENGTH_UID else None,
        multi_fuel_characteristics=multi_fuel_characteristics,
        ch4_factor_gch4_per_gfuel=ch4,
        n2o_factor_gn2o_per_gfuel=n2o,
        c_slip_percent=c_slip,
    )
```

> Import `_DEFAULT_BRAYTON_*` constants from `component_mechanical` in the conversion module.

---

### 2.8 `machinery-system-structure/MachSysS/convert_to_protobuf.py`

Update `convert_cogas_component_to_protobuf()`:

```python
def convert_cogas_component_to_protobuf(
    component: COGAS,
    order_from_shaftline_or_switchboard: int = 1,
) -> proto.COGAS:
    cogas = proto.COGAS(
        name=component.name,
        rated_power_kw=component.rated_power,
        rated_speed_rpm=component.rated_speed,
        efficiency=convert_efficiency_curve_to_protobuf(component),
        fuel=proto.Fuel(
            fuel_type=component.fuel_type.value,
            fuel_origin=component.fuel_origin.value,
        ),
        nox_calculation_method=convert_nox_calculation_method_to_protobuf(
            component.nox_calculation_method
        ),
        emission_curves=convert_emission_curves_to_protobuf(component.emission_curves),
        order_from_switchboard_or_shaftline=order_from_shaftline_or_switchboard,
        uid=component.uid,
        # ← new scalar fields (0 = proto3 default → receiver uses module default)
        ch4_factor_gch4_per_gfuel=component.ch4_factor_gch4_per_gfuel,
        n2o_factor_gn2o_per_gfuel=component.n2o_factor_gn2o_per_gfuel,
        c_slip_percent=component.c_slip_percent,
    )
    if component.gas_turbine_power_curve is not None:
        cogas.gas_turbine_power_curve.CopyFrom(
            convert_np_array_to_protobuf_power_curve(component.gas_turbine_power_curve)
        )
        cogas.steam_turbine_power_curve.CopyFrom(
            convert_np_array_to_protobuf_power_curve(component.steam_turbine_power_curve)
        )
    if component.multi_fuel_characteristics:
        for fc in component.multi_fuel_characteristics:
            fuel_mode = proto.MultiFuelEngine.FuelMode(
                main_fuel=proto.Fuel(
                    fuel_type=fc.main_fuel_type.value,
                    fuel_origin=fc.main_fuel_origin.value,
                ),
                main_bsfc=convert_bsfc_curve_to_protobuf(fc.bsfc_curve),
                engine_cycle_type=fc.engine_cycle_type.value,
                nox_calculation_method=convert_nox_calculation_method_to_protobuf(
                    fc.nox_calculation_method
                ),
            )
            if fc.pilot_fuel_type is not None:
                fuel_mode.pilot_fuel.CopyFrom(
                    proto.Fuel(
                        fuel_type=fc.pilot_fuel_type.value,
                        fuel_origin=fc.pilot_fuel_origin.value,
                    )
                )
            if fc.emission_curves:
                fuel_mode.emission_curves.extend(
                    convert_emission_curves_to_protobuf(fc.emission_curves)
                )
            cogas.fuel_modes.append(fuel_mode)
    return cogas
```

---

## 3. Implementation Order

| Step | File | Change | Test |
|------|------|--------|------|
| 1 | `types_for_feems.py` | Add `BRAYTON = 4` | — |
| 2 | `fuel.py` | Add `GAS_TURBINE`; extend `with_emission_curve_ghg_overrides` | `test_coges_simulation.py` §4.1, §4.2 |
| 3 | `fuel_eu_fuel_table.csv` | Add Gas Turbine rows | `test_coges_simulation.py` §4.3 |
| 4 | `component_mechanical.py` | Module defaults; `FuelCharacteristics` aliases; `COGAS` new params + `set_fuel_in_use` + `fuel_consumer_type_fuel_eu_maritime` + run-point override | `test_coges_simulation.py` §4.4–4.6 |
| 5 | `node.py` | Forward params; use `_resolve_fuel_consumer_class` | `test_coges_simulation.py` §4.7 |
| 6 | `system_structure.proto` | Add `BRAYTON`; new COGAS fields | — |
| 7 | `compile_proto.sh` | Regenerate `*_pb2.py` | — |
| 8 | `convert_to_feems.py` | Update `convert_proto_cogas_to_feems` | `test_coges_simulation.py` §4.8 |
| 9 | `convert_to_protobuf.py` | Update `convert_cogas_component_to_protobuf` | `test_coges_simulation.py` §4.8 |
| 10 | `API_REFERENCE.md` | Document new COGAS params and FuelConsumerClass value | — |
| 11 | `uv run pytest feems/tests/` | All green | — |

---

## 4. Tests — `feems/tests/test_coges_simulation.py`

### 4.1 `with_emission_curve_ghg_overrides` backward compat

- Existing callers (ch4 + n2o, no c_slip) → `c_slip_percent` still zeroed
- `c_slip_percent=None` + only `n2o` → `c_slip` unchanged

### 4.2 `with_emission_curve_ghg_overrides` new `c_slip_percent` param

- Provide `ch4_factor=X` and `c_slip_percent=0.01` → both stored; c_slip not zeroed
- `c_slip_percent=0.05` with no ch4/n2o → only slip updated

### 4.3 `GAS_TURBINE` FuelEU table lookup

- `get_ghg_emission_factor_from_fuel_eu_table(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL, FuelConsumerClassFuelEUMaritime.GAS_TURBINE)` returns row with `c_slip = 0.01`

### 4.4 BRAYTON defaults applied to `COGAS.get_gas_turbine_run_point_from_power_output_kw`

- Build a `COGAS` with default `ch4_factor_gch4_per_gfuel`, `n2o_factor_gn2o_per_gfuel`, `c_slip_percent`
- Call `get_gas_turbine_run_point_from_power_output_kw(fuel_specified_by=FuelSpecifiedBy.IMO)`
- Assert `fuel.ghg_emission_factor_tank_to_wake[0].ch4_factor_gch4_per_gfuel ≈ 0.000192`
- Assert `fuel.ghg_emission_factor_tank_to_wake[0].n2o_factor_gn2o_per_gfuel ≈ 0.000048`
- Assert `fuel.ghg_emission_factor_tank_to_wake[0].c_slip_percent ≈ 0.01`

### 4.5 Emission curve overrides module defaults

- Build `COGAS` with a flat CH4 emission curve of `X g/kWh`
- Assert the run-point fuel CH4 factor = `X / BSFC`, not `_DEFAULT_BRAYTON_CH4_GFUEL`
- Assert `c_slip_percent == 0.0` (legacy zeroing via issue #85 path)

### 4.6 Multi-fuel mode switching

- Build `COGAS` with `multi_fuel_characteristics = [LNG_mode, H2_mode]`
- `set_fuel_in_use(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)` → `fuel_type == NATURAL_GAS`
- `set_fuel_in_use(TypeFuel.HYDROGEN, FuelOrigin.FOSSIL)` → `fuel_type == HYDROGEN`
- Unknown fuel_type → `ValueError`

### 4.7 `node.py` COGES branch forwards `fuel_type`/`fuel_origin`

- Build a minimal `ElectricPowerSystem` with a multi-fuel `COGES`
- Call `get_fuel_energy_consumption_running_time(fuel_option=...)` with a specific fuel
- Assert `COGAS._fuel_in_use.main_fuel_type` matches the selected option

### 4.8 Proto round-trip

- Construct `COGAS` with `multi_fuel_characteristics`, `ch4_factor`, `n2o_factor`, `c_slip`
- Serialize via `convert_cogas_component_to_protobuf`
- Deserialize via `convert_proto_cogas_to_feems`
- Assert all fields preserved including `fuel_modes` length and scalar values

---

## 5. Non-Changes (Scope Boundary)

- `COGES.get_system_run_point_from_power_output_kw` signature unchanged — multi-fuel selection
  is triggered by the `set_fuel_in_use()` call in `node.py` before computation
- PMS (`pms_basic.py`) — already handles COGES via generic `power_sources` iteration; confirmed
- `EngineDualFuel` / `EngineMultiFuel` — untouched; COGAS multi-fuel is independent
- `FuelCharacteristics.bspfc_curve` (pilot BSFC) — not used for COGAS/BRAYTON; no secondary BSFC
  (per assumption 4: only Main fuel computed; fuel modes share one BSFC curve per mode)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-27 | Initial draft | Kevin Koosup Yum |
