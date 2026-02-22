# FEEMS API Reference

This document provides a comprehensive reference for the FEEMS API.

## Table of Contents

- [Overview and Modeling Principles](#overview-and-modeling-principles)
  - [What is FEEMS?](#what-is-feems)
  - [Work Process](#work-process)
  - [System Configuration](#system-configuration)
  - [Component Class Hierarchy](#component-class-hierarchy)
  - [Basic Modeling Principles](#basic-modeling-principles)
  - [Power Balance Calculation](#power-balance-calculation)
- [Component Models](#component-models)
  - [Base Classes](#base-classes)
  - [Mechanical Components](#mechanical-components)
  - [Electric Components](#electric-components)
  - [Serial Systems](#serial-systems)
  - [Energy Storage](#energy-storage)
  - [Fuel Cell](#fuel-cell)
  - [PTI/PTO](#ptipito)
  - [Run Point Data Classes](#run-point-data-classes)
  - [System Types](#system-types)
- [System Model](#system-model)
- [Fuel and Emissions](#fuel-and-emissions)
  - [GhgEmissionFactorTankToWake](#ghgemissionfactortanktowake)
  - [Fuel](#fuel)
- [Types](#types)
  - [TypeComponent](#typecomponent)
  - [TypePower](#typepower)
  - [EmissionType](#emissiontype)
  - [EngineCycleType](#enginecycletype)
  - [NOxCalculationMethod](#noxcalculationmethod)
- [Utilities](#utilities)

## Overview and Modeling Principles

### What is FEEMS?

FEEMS (**Fuel, Emissions, Energy Calculation for Machinery System**) is a component-based simulation library for marine power and propulsion systems. It calculates fuel consumption, exhaust emissions, energy balance, and equipment running hours for:

- Conventional diesel-electric propulsion
- Hybrid propulsion with PTI/PTO (Power Take-In / Power Take-Off)
- Mechanical propulsion with a separate electric power system

FEEMS was developed at SINTEF Ocean (Kevin Koosup Yum, 2020) and is suited for design studies, operational optimization, and environmental assessment of ship power plants.

---

### Work Process

A FEEMS simulation follows four steps:

```
1. System Configuration
       ↓
2. Load / Operation Mode Parameter Input
       ↓
3. Power Balance Calculation
       ↓
4. Fuel Consumption / Emissions / Running Hours
```

| Step | Description |
|------|-------------|
| **1. System Configuration** | Assemble a system model from individual components (engines, generators, batteries, etc.) connected through switchboards or shaftlines. |
| **2. Load / Operation Mode Input** | Provide time-series consumer power loads and control inputs (breaker status, genset on/off). |
| **3. Power Balance Calculation** | For each time step, distribute load across power sources using the power balance algorithm. |
| **4. Fuel / Emissions / Running Hours** | Compute fuel consumption and emissions from the operating point of each prime mover; accumulate running hours. |

---

### System Configuration

Build a system model by instantiating components and wiring them together:

```
Create Components          →  Engine, Generator, Battery, PropulsionDrive, …
        ↓
Create Serial Components   →  SerialSystem / SerialSystemElectric
        ↓
Create Nodes               →  Switchboard (electric) or Shaftline (mechanical)
        ↓
Create System              →  ElectricPowerSystem
                               MechanicalPropulsionSystem
                               MechanicalPropulsionSystemWithElectricPowerSystem
```

> **Topology constraint**: The system uses a **single-level hierarchy**. All components (or serial component chains) connect directly to a switchboard or shaftline. Nested switchboards are not supported.

---

### Component Class Hierarchy

```
BasicComponent
├── Component
│   ├── Engine
│   │   ├── EngineDualFuel
│   │   └── EngineMultiFuel
│   ├── ElectricComponent
│   │   ├── ElectricMachine
│   │   │   └── PTIPTO
│   │   ├── Battery
│   │   ├── FuelCell
│   │   └── SuperCapacitor
│   └── MainEngineForMechanicalPropulsion
├── SerialSystem
│   └── SerialSystemElectric
│       └── Genset  (Engine + Generator in series)

Node
├── Switchboard  (electric bus)
└── Shaftline    (mechanical bus)
```

---

### Basic Modeling Principles

#### Sign Convention

Every component is modelled with an **input port** and an **output port**. Power values carry a sign that encodes the direction of energy flow:

| Condition | P_in | P_out |
|-----------|------|-------|
| Forward (normal) operation | > 0 | > 0 |
| Reverse operation | < 0 | < 0 |

**Load percentage** (used to look up fuel / efficiency curves):

$$PL = \frac{P_{out}}{P_{rated}} \quad \text{(forward)} \qquad PL = \frac{P_{in}}{P_{rated}} \quad \text{(reverse)}$$

**Efficiency**:

$$\eta = \frac{P_{out}}{P_{in}} \quad \text{(forward)} \qquad \eta = \frac{P_{in}}{P_{out}} \quad \text{(reverse)}$$

#### Power-Type Sign Conventions

| `TypePower` | Component examples | P_in (source side) | P_out (bus side) | Notes |
|---|---|---|---|---|
| `POWER_SOURCE` | Generator, Genset | Mechanical / fuel energy (+) | Electrical power to switchboard (+) | P_in is fuel equivalent |
| `POWER_CONSUMER` | Propulsion drive, hotel load | Electrical power from switchboard (+) | Shaft / mechanical power (+) | P_in from bus |
| `PTI_PTO` | Shaft generator / motor | Motoring: P_in > 0, P_out > 0 | Generating: P_in < 0, P_out < 0 | Bidirectional |
| `ENERGY_STORAGE` | Battery, Supercapacitor | Charging: P_in > 0 | Discharging: P_out > 0 | P_in/P_out sign changes with mode |

#### Serial Component Efficiency

When multiple components are arranged in series (e.g., engine → gearbox → generator), the output power is:

$$P_{out,n} = \eta_1 \cdot \eta_2 \cdots \eta_n \cdot P_{in,1}$$

and equivalently the combined efficiency is:

$$\eta_{total} = \prod_{i=1}^{n} \eta_i$$

`SerialSystem` and `SerialSystemElectric` implement this calculation transparently.

---

### Power Balance Calculation

At each time step the switchboard / shaftline solves for how much power each source must supply, given the total consumer demand.

**Symmetric load sharing** (equal load *ratio* across all connected sources of the same type):

$$P_{out,k} = \frac{P_{rated,k}}{\sum_j P_{rated,j}} \cdot P_{load,total}$$

where the sum is over all connected, running power sources *j*, and *k* is an individual source.

The algorithm iterates:

```
1.  Collect consumer loads → total bus load
2.  Distribute load to power sources (symmetric sharing)
3.  If any source exceeds its rated power, re-distribute remaining load
    across sources still within capacity
4.  Calculate fuel consumption and emissions for each prime mover
    at its operating point
5.  Aggregate results into FEEMSResult
```

---

## Component Models

### Base Classes

#### `BasicComponent`

Base class for all atomic components.

**Attributes:**
- `type_: TypeComponent` - Component type classification
- `name: str` - Component name
- `rated_power: Power_kW` - Rated power in kW
- `rated_speed: Speed_rpm` - Rated speed in RPM
- `power_type: TypePower` - Power type (source, consumer, transmission)
- `eff_curve: np.ndarray` - Efficiency curve [[load, eff], ...]
- `uid: Optional[str]` - Unique identifier

**Key Methods:**
- `get_efficiency_from_load_percentage(load: Union[float, np.ndarray]) -> Union[float, np.ndarray]`
  - Returns efficiency at given load percentage(s). Clipped to [0.01, 1.0].

- `get_load(power=None) -> Union[float, np.ndarray]`
  - Returns `|power| / rated_power`. Uses `power_input` if `power` is None.

- `get_power_output_from_bidirectional_input(power_input, strict_power_balance=False) -> Tuple[power_output, load]`
  - Calculates output power from input power accounting for efficiency (bidirectional).

- `get_power_input_from_bidirectional_output(power_output, strict_power_balance=False) -> Tuple[power_input, load]`
  - Calculates input power from output power accounting for efficiency (bidirectional).

- `set_power_input_from_output(power_output) -> Tuple[power_input, load]`
  - Sets `self.power_output` and computes/stores `self.power_input`. Returns `(power_input, load)`.

- `set_power_output_from_input(power_input) -> Tuple[power_output, load]`
  - Sets `self.power_input` and computes/stores `self.power_output`. Returns `(power_output, load)`.

#### `Component`

Base class for all components that carry power state (`power_input`, `power_output`, `status`).
`Engine`, `Genset`, `MainEngineForMechanicalPropulsion` inherit from this directly.

**Attributes:**
- `name: str`, `type_: TypeComponent`, `power_type: TypePower`
- `rated_power: Power_kW`, `rated_speed: Speed_rpm`
- `status: np.ndarray` - On/off boolean array (length = number of time steps)
- `power_input: np.ndarray`, `power_output: np.ndarray`
- `uid: str` - Auto-generated UUID if not provided

> Note: `switchboard_id` and `load_sharing_mode` are defined on `ElectricComponent`, not `Component`.

#### `SerialSystem`

Base class for components arranged in series.

**Attributes:**
- `components: List[Component]` - Ordered list of components in series

**Methods:** Inherits all `BasicComponent` methods including `set_power_input_from_output()` and `set_power_output_from_input()`.

### Mechanical Components

#### `Engine`

Diesel or gas engine component.

```python
from feems.components_model import Engine
from feems.types_for_feems import TypeComponent, Power_kW, Speed_rpm
import numpy as np

engine = Engine(
    type_=TypeComponent.AUXILIARY_ENGINE,
    name="Aux Engine",
    rated_power=Power_kW(1000),
    rated_speed=Speed_rpm(1500),
    bsfc_curve=np.array([[0.25, 0.5, 0.75, 1.0],
                         [280, 220, 200, 210]]).T
)
```

**Attributes:**
- `bsfc_curve: np.ndarray` - Brake Specific Fuel Consumption curve [[load, bsfc], ...]
- `fuel_type: TypeFuel` - Fuel type (default: `TypeFuel.DIESEL`)
- `fuel_origin: FuelOrigin` - Fuel origin (default: `FuelOrigin.FOSSIL`)
- `engine_cycle_type: EngineCycleType` - Engine cycle (default: `EngineCycleType.DIESEL`)
- `nox_calculation_method: NOxCalculationMethod` - NOx calculation method (default: `NOxCalculationMethod.TIER_2`)

**Key Methods:**
- `get_engine_run_point_from_power_out_kw(power_kw: Optional[np.ndarray] = None) -> EngineRunPoint`
  - Calculate engine operating point from power output
  - Returns fuel consumption, BSFC, load ratio, emissions

**Returns:** `EngineRunPoint`
- `fuel_flow_rate_kg_per_s: FuelConsumption` - Fuel consumption
- `bsfc_g_per_kWh: np.ndarray` - BSFC at operating point
- `load_ratio: np.ndarray` - Load as fraction of rated power
- `emissions_g_per_s: Dict[EmissionType, np.ndarray]` - Emissions per second keyed by `EmissionType` (NOX, SOX, PM, CO, HC, CH4, N2O)

#### `EngineDualFuel`

Engine that burns a primary fuel (e.g., LNG) with a small diesel pilot injection for ignition.
Inherits from `Engine`.

```python
from feems.components_model.component_mechanical import EngineDualFuel
from feems.fuel import TypeFuel, FuelOrigin
from feems.types_for_feems import EngineCycleType, NOxCalculationMethod

dual_fuel = EngineDualFuel(
    type_=TypeComponent.MAIN_ENGINE,
    name="Dual Fuel Engine",
    rated_power=Power_kW(5000),
    rated_speed=Speed_rpm(120),
    bsfc_curve=bsfc_lng,           # Main fuel BSFC curve (g/kWh vs. load)
    fuel_type=TypeFuel.NATURAL_GAS,
    fuel_origin=FuelOrigin.FOSSIL,
    bspfc_curve=bspfc_pilot,        # Pilot fuel BSFC curve (g/kWh vs. load)
    pilot_fuel_type=TypeFuel.DIESEL,
    pilot_fuel_origin=FuelOrigin.FOSSIL,
    engine_cycle_type=EngineCycleType.OTTO,
    nox_calculation_method=NOxCalculationMethod.TIER_3,
)
```

**Additional Attributes (vs `Engine`):**
- `bspfc_curve: np.ndarray` - Brake Specific Pilot Fuel Consumption curve (g/kWh vs. load)
- `pilot_fuel_type: TypeFuel` - Pilot fuel type (default: `TypeFuel.DIESEL`)
- `pilot_fuel_origin: FuelOrigin` - Pilot fuel origin (default: `FuelOrigin.FOSSIL`)

**Returns:** `EngineRunPoint` with `fuel_flow_rate_kg_per_s` containing two fuels (main + pilot).
The `bspfc_g_per_kWh` field is also populated on the returned `EngineRunPoint`.

#### `EngineMultiFuel`

Engine that can operate on multiple alternative fuel configurations (e.g., diesel, LNG, methanol).
Each configuration is defined by a `FuelCharacteristics` object.

```python
from feems.components_model.component_mechanical import EngineMultiFuel, FuelCharacteristics
from feems.fuel import TypeFuel, FuelOrigin
from feems.types_for_feems import EngineCycleType, NOxCalculationMethod

fuel_options = [
    FuelCharacteristics(
        main_fuel_type=TypeFuel.DIESEL,
        main_fuel_origin=FuelOrigin.FOSSIL,
        bsfc_curve=bsfc_diesel,
    ),
    FuelCharacteristics(
        main_fuel_type=TypeFuel.NATURAL_GAS,
        main_fuel_origin=FuelOrigin.FOSSIL,
        bsfc_curve=bsfc_lng,
        bspfc_curve=bspfc_pilot,
        pilot_fuel_type=TypeFuel.DIESEL,
        pilot_fuel_origin=FuelOrigin.FOSSIL,
        engine_cycle_type=EngineCycleType.OTTO,
        nox_calculation_method=NOxCalculationMethod.TIER_3,
    ),
]

engine = EngineMultiFuel(
    type_=TypeComponent.MAIN_ENGINE,
    name="Multi-Fuel Engine",
    rated_power=Power_kW(5000),
    rated_speed=Speed_rpm(120),
    multi_fuel_characteristics=fuel_options,
)
```

**Attributes:**
- `multi_fuel_characteristics: List[FuelCharacteristics]` - Available fuel configurations
- `fuel_in_use: FuelCharacteristics` - Currently active fuel configuration

**Methods:**
- `set_fuel_in_use(fuel_type=None, fuel_origin=None)` - Switch active fuel. Defaults to first.
- `engine_in_use` *(property)* - Returns the active `Engine` or `EngineDualFuel` object.
- `get_engine_run_point_from_power_out_kw(...)` - Same signature as `Engine`.

#### `FuelCharacteristics`

Dataclass defining one fuel configuration for `EngineMultiFuel`.

```python
from feems.components_model.component_mechanical import FuelCharacteristics

FuelCharacteristics(
    nox_calculation_method=NOxCalculationMethod.TIER_2,  # default
    main_fuel_type=TypeFuel.DIESEL,                      # default
    main_fuel_origin=FuelOrigin.FOSSIL,                  # default
    pilot_fuel_type=None,                                # None for no pilot
    pilot_fuel_origin=None,
    bsfc_curve=None,                    # np.ndarray [[load, bsfc_g_per_kWh], ...]
    bspfc_curve=None,                   # Pilot fuel BSFC curve (optional)
    emission_curves=None,               # List[EmissionCurve]
    engine_cycle_type=EngineCycleType.DIESEL,
)
```

#### `MainEngineForMechanicalPropulsion`

Wraps an `Engine` / `EngineDualFuel` / `EngineMultiFuel` for use in a mechanical shaftline.

```python
from feems.components_model.component_mechanical import MainEngineForMechanicalPropulsion

main_engine = MainEngineForMechanicalPropulsion(
    name="Main Engine",
    engine=engine,          # Engine / EngineDualFuel / EngineMultiFuel
    shaft_line_id=1,        # Shaftline ID (default: 1)
)
```

**Attributes:**
- `engine: Union[Engine, EngineDualFuel, EngineMultiFuel]`
- `shaft_line_id: int`

**Methods:**
- `get_engine_run_point_from_power_out_kw(power=None, fuel_specified_by=..., fuel_type=None, fuel_origin=None) -> EngineRunPoint`

#### `MainEngineWithGearBoxForMechanicalPropulsion`

`MainEngineForMechanicalPropulsion` subclass with an integrated gearbox efficiency model.

### Electric Components

#### `ElectricComponent`

Basic electrical component with efficiency curve.

```python
from feems.components_model.component_electric import ElectricComponent
from feems.types_for_feems import TypeComponent, TypePower

transformer = ElectricComponent(
    type_=TypeComponent.TRANSFORMER,
    name="Transformer",
    rated_power=Power_kW(1000),
    power_type=TypePower.POWER_TRANSMISSION,
    switchboard_id=SwbId(1),
    eff_curve=np.array([[0.25, 0.5, 0.75, 1.0],
                        [0.96, 0.97, 0.98, 0.98]]).T
)
```

**Attributes:**
- `switchboard_id: SwbId` - Connected switchboard ID
- `power_type: TypePower` - POWER_SOURCE, POWER_CONSUMER, or POWER_TRANSMISSION

#### `ElectricMachine`

Electric generator or motor.

```python
from feems.components_model.component_electric import ElectricMachine

generator = ElectricMachine(
    type_=TypeComponent.GENERATOR,
    name="Generator",
    rated_power=Power_kW(665),
    rated_speed=Speed_rpm(1500),
    power_type=TypePower.POWER_SOURCE,
    switchboard_id=SwbId(1),
    eff_curve=np.array([[0.25, 0.5, 0.75, 1.0],
                        [0.88, 0.92, 0.94, 0.95]]).T
)
```

**Attributes:**
- `number_of_poles: int` - Number of magnetic poles (default: 1)

**Methods:**
- `get_shaft_power_load_from_electric_power(power_electric, strict_power_balance=False)`
  - Convert electrical power to shaft power
  - Accounts for efficiency losses

- `get_electric_power_load_from_shaft_power(power_shaft, strict_power_balance=False)`
  - Convert shaft power to electrical power
  - Accounts for efficiency losses

#### `Battery`

Battery energy storage system.

```python
from feems.components_model.component_electric import Battery

battery = Battery(
    name="Battery Pack",
    rated_capacity_kwh=1000,
    charging_rate_c=0.5,       # Max charging: 500 kW
    discharge_rate_c=1.0,      # Max discharge: 1000 kW
    soc0=0.80,                 # Initial SoC: 80%
    eff_charging=0.975,
    eff_discharging=0.975,
    switchboard_id=SwbId(1)
)
```

**Attributes:**
- `rated_capacity_kwh: float` - Energy capacity in kWh
- `charging_rate_c: float` - Maximum charging rate in C-rate
- `discharge_rate_c: float` - Maximum discharge rate in C-rate
- `soc0: float` - Initial state of charge (0-1)
- `eff_charging: float` - Charging efficiency (0-1)
- `eff_discharging: float` - Discharging efficiency (0-1)

**Properties:**
- `max_charging_power_kw: Power_kW` - Maximum charging power in kW (`charging_rate_c × rated_capacity_kwh`)
- `max_discharging_power_kw: Power_kW` - Maximum discharging power in kW

**Methods:**
- `get_soc(time_interval_s, integration_method, accumulated_time_series=False) -> np.ndarray`
  - Calculate state of charge from power profile. `power_input` must be set first.
  - Returns SoC array (initial SoC + integrated charge/discharge)
- `get_energy_stored_kj(time_interval_s, integration_method, accumulated_time_series=False) -> Union[float, np.ndarray]`
  - Calculate net energy stored (kJ) from current `power_input`

#### `ShorePowerConnection`

Shore power connection component.

```python
from feems.components_model.component_electric import ShorePowerConnection

shore_power = ShorePowerConnection(
    name="Shore Power",
    rated_power=Power_kW(1000),
    switchboard_id=SwbId(1)
)
```

**Attributes:**
- Same as `ElectricComponent` with `type_=TypeComponent.SHORE_POWER`
- Automatically set to `power_type=TypePower.POWER_SOURCE`

#### `ShorePowerConnectionSystem`

Shore power with converter.

```python
from feems.components_model.component_electric import ShorePowerConnectionSystem

shore_system = ShorePowerConnectionSystem(
    name="Shore Power System",
    shore_power_connection=shore_power,
    converter=converter,
    switchboard_id=SwbId(1)
)
```

**Attributes:**
- `shore_power_connection: ShorePowerConnection`
- `converter: ElectricComponent`

### Serial Systems

Serial systems combine multiple components in series to represent subsystems like gensets (engine + generator) or propulsion drives (transformer + converter + motor). FEEMS uses a mathematical framework for calculating power flow and efficiency through series-connected components.

#### Mathematical Framework

For components connected in series, the output power of one component becomes the input power of the next. The overall efficiency is the product of individual efficiencies.

**Forward Power Flow** (P_in, P_out > 0):
```
Power Load (PL) = P_out / P_rated
Efficiency (η) = P_out / P_in
Overall Output: P_out,n = η₁ · η₂ · ... · ηₙ · P_in
```

**Reverse Power Flow** (P_in, P_out < 0):
```
Power Load (PL) = P_in / P_rated
Efficiency (η) = P_in / P_out
Overall Input: P_in,n = P_out / (η₁ · η₂ · ... · ηₙ)
```

**Example**: Propulsion drive with three components (η₁=0.98, η₂=0.97, η₃=0.95)
```
P_motor_shaft = 1000 kW (desired output)
P_switchboard = P_motor_shaft / (η₁ · η₂ · η₃)
              = 1000 / (0.98 × 0.97 × 0.95)
              = 1106.3 kW (required input)
Overall efficiency = 1000 / 1106.3 = 90.4%
```

This framework automatically handles:
- Bidirectional power flow (motoring vs generating in PTI/PTO)
- Load-dependent efficiency curves for each component
- Power losses distributed across all components
- Complex configurations with multiple serial stages

#### `Genset`

Generator set (engine + generator).

```python
from feems.components_model import Genset

genset = Genset(
    name="Genset 1",
    aux_engine=engine,
    generator=generator
)
```

**Attributes:**
- `aux_engine: Union[Engine, EngineDualFuel, EngineMultiFuel]` - Auxiliary engine
- `generator: ElectricMachine` - Generator (or generator+rectifier serial system for DC gensets)

**Methods:**
- `get_fuel_cons_load_bsfc_from_power_out_generator_kw(power=None, fuel_specified_by=FuelSpecifiedBy.IMO, lhv_mj_per_g=None, ghg_emission_factor_well_to_tank_gco2eq_per_mj=None, ghg_emission_factor_tank_to_wake=None, fuel_type=None, fuel_origin=None) -> GensetRunPoint`
  - Calculate fuel consumption from generator electrical output
  - `fuel_type` / `fuel_origin`: override for `EngineMultiFuel` gensets

**Returns:** `GensetRunPoint` *(NamedTuple)*
- `genset_load_ratio: np.ndarray` - Generator load as fraction of rated power
- `engine: EngineRunPoint` - Engine operating point (fuel, BSFC, emissions)

#### `SerialSystemElectric`

Electric serial system (e.g., propulsion drive).

```python
from feems.components_model.component_electric import SerialSystemElectric

propulsion_drive = SerialSystemElectric(
    type_=TypeComponent.PROPULSION_DRIVE,
    name="Propulsion Drive",
    power_type=TypePower.POWER_CONSUMER,
    components=[transformer, rectifier, inverter, motor],
    rated_power=motor.rated_power,
    rated_speed=motor.rated_speed,
    switchboard_id=SwbId(1)
)
```

**Attributes:**
- `components: List[ElectricComponent]` - Ordered list of components

**Methods:**
- `set_power_input_from_output(power_output) -> Tuple[np.ndarray, np.ndarray]`
  - Calculate switchboard power from shaft power
  - Returns (power_input, load_ratio)

### Energy Storage

#### `BatterySystem`

Battery with an integrated DC/DC converter (extends `Battery`).

```python
from feems.components_model.component_electric import BatterySystem

battery_sys = BatterySystem(
    name="Battery System",
    battery=battery,          # Battery object
    converter=converter,      # ElectricComponent (DC/DC converter)
    switchboard_id=SwbId(1),
)
```

**Attributes:** Same as `Battery` plus:
- `battery: Battery`
- `converter: ElectricComponent`

#### `SuperCapacitor`

Supercapacitor energy storage.

```python
from feems.components_model.component_electric import SuperCapacitor

supercap = SuperCapacitor(
    name="Supercapacitor",
    rated_capacity_wh=5000,    # Capacity in Wh
    rated_power=Power_kW(500),
    soc0=0.8,
    eff_charging=0.995,
    eff_discharging=0.995,
    switchboard_id=SwbId(1),
)
```

**Methods:** Same as `Battery`: `get_soc()`, `get_energy_stored_kj()`.

#### `SuperCapacitorSystem`

`SuperCapacitor` with an integrated converter.

### Fuel Cell

#### `FuelCell`

Hydrogen (or other fuel) fuel cell module.

```python
from feems.components_model.component_electric import FuelCell
from feems.fuel import TypeFuel, FuelOrigin

fuel_cell = FuelCell(
    name="Fuel Cell Module",
    rated_power=Power_kW(500),
    eff_curve=np.array([[0.25, 0.5, 0.75, 1.0],
                        [0.55, 0.58, 0.56, 0.53]]).T,
    fuel_type=TypeFuel.HYDROGEN,           # default
    fuel_origin=FuelOrigin.RENEWABLE_NON_BIO,  # default
)
```

**Methods:**
- `get_fuel_cell_run_point(power_out_kw=None, fuel_specified_by=FuelSpecifiedBy.IMO, ...) -> ComponentRunPoint`
  - Returns fuel consumption and efficiency at the given output power.

#### `FuelCellSystem`

`FuelCell` + DC/DC converter, connected to a switchboard.

```python
from feems.components_model.component_electric import FuelCellSystem

fc_system = FuelCellSystem(
    name="Fuel Cell System",
    fuel_cell_module=fuel_cell,
    converter=converter,        # ElectricComponent (DC/DC converter)
    switchboard_id=SwbId(1),
    number_modules=2,           # Number of parallel fuel cell modules (default: 1)
)
```

**Methods:**
- `get_fuel_cell_run_point(power_out_kw=None, fuel_specified_by=..., ...) -> ComponentRunPoint`

### PTI/PTO

#### `PTIPTO`

Power Take-In / Power Take-Off system — bidirectional shaft-electric connection.
Extends `SerialSystemElectric` with `power_type=TypePower.PTI_PTO`.

```python
from feems.components_model.component_electric import PTIPTO

pti_pto = PTIPTO(
    name="PTI/PTO",
    components=[converter, electric_machine],  # Ordered from switchboard side
    switchboard_id=SwbId(1),
    rated_power=Power_kW(2000),
    rated_speed=Speed_rpm(150),
    shaft_line_id=1,            # Shaftline this PTI/PTO is connected to (default: 1)
)
```

**Additional Attributes:**
- `shaft_line_id: int` - ID of the connected mechanical shaftline
- `full_pti_mode: np.ndarray` - Boolean array, True when operating in full PTI mode

### Run Point Data Classes

#### `ComponentRunPoint`

Generic run point for components that don't produce fuel but consume it (e.g., fuel cells).

**Fields:**
- `load_ratio: np.ndarray`
- `efficiency: np.ndarray`
- `fuel_flow_rate_kg_per_s: FuelConsumption`
- `emissions_g_per_s: Dict[EmissionType, np.ndarray]` *(default: empty dict)*

### System Types

#### `MechanicalPropulsionSystem`

System for conventional mechanical propulsion (one or more shaftlines with main engines).

```python
from feems.system_model import MechanicalPropulsionSystem

# components_list can mix main engines, PTI/PTO, and mechanical loads.
# Categorization is automatic based on component type and shaft_line_id.
mech_system = MechanicalPropulsionSystem(
    name="Mechanical Propulsion",
    components_list=[main_engine_1, propeller_load_1],
)
```

**Attributes (auto-populated from `components_list`):**
- `main_engines: List[MainEngineForMechanicalPropulsion]`
- `pti_ptos: List[PTIPTO]`
- `mechanical_loads: List[MechanicalComponent]`

- `get_fuel_energy_consumption_running_time(fuel_specified_by=...) -> FEEMSResult`

#### `MechanicalPropulsionSystemWithElectricPowerSystem`

Combined mechanical propulsion + separate electric system (connected via optional PTI/PTO).

```python
from feems.system_model import MechanicalPropulsionSystemWithElectricPowerSystem

combined = MechanicalPropulsionSystemWithElectricPowerSystem(
    name="Combined System",
    electric_system=electric_power_system,     # ElectricPowerSystem
    mechanical_system=mechanical_system,       # MechanicalPropulsionSystem
)
```

- `get_fuel_energy_consumption_running_time(time_interval_s, fuel_specified_by=...) -> FEEMSResultForMachinerySystem`
  - Returns `FEEMSResultForMachinerySystem(electric_system: FEEMSResult, mechanical_system: FEEMSResult)`

## System Model

### `ElectricPowerSystem`

Complete electric power system.

```python
from feems.system_model import ElectricPowerSystem

system = ElectricPowerSystem(
    name="Ship Power System",
    power_plant_components=[genset1, genset2, drive1, load1],
    bus_tie_connections=[(1, 2)]
)
```

**Attributes:**
- `name: str` - System name
- `power_sources: List[Component]` - All power sources
- `propulsion_drives: List[Component]` - Propulsion consumers
- `pti_pto: List[Component]` - PTI/PTO systems
- `energy_storage: List[Component]` - Batteries, etc.
- `other_load: List[Component]` - Auxiliary loads
- `switchboards: Dict[int, Switchboard]` - Switchboard objects by ID
- `bus_tie_breakers: List[BusBreaker]` - Bus-tie breakers

**Key Methods:**

#### Configuration

- `set_power_input_from_power_output_by_switchboard_id_type_name(...)`
  ```python
  system.set_power_input_from_power_output_by_switchboard_id_type_name(
      power_output=np.array([300, 350, 400]),
      switchboard_id=1,
      type_=TypePower.POWER_CONSUMER,
      name="Auxiliary Load"
  )
  ```

- `set_status_by_switchboard_id_power_type(...)`
  ```python
  # Shape: [time_points, n_sources_on_bus]
  status = np.ones([100, 2]).astype(bool)
  system.set_status_by_switchboard_id_power_type(
      switchboard_id=1,
      power_type=TypePower.POWER_SOURCE,
      status=status
  )
  ```

- `set_load_sharing_mode_power_sources_by_switchboard_id_power_type(...)`
  ```python
  # 0 = equal sharing, custom values for weighted sharing
  load_sharing = np.zeros([100, 2])
  system.set_load_sharing_mode_power_sources_by_switchboard_id_power_type(
      switchboard_id=1,
      power_type=TypePower.POWER_SOURCE,
      load_sharing_mode=load_sharing
  )
  ```

- `set_bus_tie_status_all(status: np.ndarray)`
  ```python
  # Shape: [time_points, n_bus_ties]
  # True = closed (buses connected), False = open (isolated)
  status = np.ones([100, 1]).astype(bool)
  system.set_bus_tie_status_all(status)
  ```

#### Simulation

- `set_time_interval(time_step_s: float, integration_method: IntegrationMethod = ...)`
  ```python
  from feems.system_model import IntegrationMethod
  system.set_time_interval(60, integration_method=IntegrationMethod.simpson)
  ```

- `do_power_balance_calculation()`
  - Performs comprehensive power balance calculation across the entire system
  - Algorithm steps:
    1. **Assign consumer loads**: Sets power output for all consumers (propulsion, auxiliaries)
    2. **Hybrid mode decision**: Determines ESS (Energy Storage System) operating mode if applicable
    3. **ESS load sharing**: Calculates battery/energy storage contribution
    4. **Electric source status**: Assigns on/off status and load sharing modes for generators
    5. **PTI/PTO assignment**: Sets power input/output for shaft generators/motors
    6. **Load sharing**: Distributes total load among available power sources based on:
       - Status (on/off)
       - Load sharing mode (equal or weighted)
       - Rated power and availability
    7. **Bus tie breakers**: Handles power flow between switchboards if closed
    8. **Full PTI mode check**: For mechanical propulsion, handles full power take-in scenarios
    9. **Power balance**: Performs final power balance for electric and mechanical domains
    10. **Fuel calculation**: Calculates fuel consumption for each power source based on loads
  - Updates `power_output` and `power_input` attributes of all components
  - Automatically handles component efficiency losses through serial system calculations

- `get_fuel_energy_consumption_running_time(fuel_specified_by=FuelSpecifiedBy.IMO, fuel_option=None) -> FEEMSResult`
  - Returns comprehensive results including:
    - Total fuel consumption
    - Total emissions (CO2, NOx, etc.)
    - Energy consumption breakdown
    - Operating hours
    - Per-component results

**Returns:** `FEEMSResult`
```python
result = system.get_fuel_energy_consumption_running_time()

# Access results
fuel_kg = result.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction
co2_kg = result.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel
nox_kg = result.total_emission_kg[EmissionType.NOX]
energy_propulsion_mj = result.energy_consumption_propulsion_total_mj
genset_hours = result.running_hours_genset_total_hr

# Per-component details
detail_df = result.detail_result
```

> **Note**: For `MechanicalPropulsionSystemWithElectricPowerSystem`, the method returns
> `FEEMSResultForMachinerySystem` (a NamedTuple with `.electric_system: FEEMSResult` and
> `.mechanical_system: FEEMSResult`). Access sub-results as
> `result.electric_system.multi_fuel_consumption_total_kg`, etc.

#### Results Data Structure

**`FEEMSResult`**

Comprehensive results object returned by `ElectricPowerSystem.get_fuel_energy_consumption_running_time()`. Contains aggregated system-level metrics and detailed per-component breakdowns.

**System-Level Attributes:**

**Fuel Consumption:**
- `multi_fuel_consumption_total_kg: FuelConsumption` - Total fuel consumed for all fuel types
  - Access mass: `result.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction`
  - Supports multiple fuels (diesel, LNG, hydrogen, etc.)
- `fuel_consumption_total_kg: float` *(property)* - Scalar total fuel consumption in kg

**Emissions:**
- `co2_emission_total_kg: GHGEmissions` - Total CO2 equivalent emissions
  - Tank-to-Wake (operational): `.tank_to_wake_kg_or_gco2eq_per_gfuel`
  - Well-to-Tank (upstream): `.well_to_tank_kg_or_gco2eq_per_gfuel`
  - Well-to-Wake (total lifecycle): `.well_to_wake_kg_or_gco2eq_per_gfuel`
- `total_emission_kg: Dict[EmissionType, float]` - Individual pollutants
  - NOx: `result.total_emission_kg[EmissionType.NOX]`
  - SOx: `result.total_emission_kg[EmissionType.SOX]`
  - PM: `result.total_emission_kg[EmissionType.PM]`

**Energy Consumption:**
- `energy_consumption_electric_total_mj: float` - Electrical energy consumed
- `energy_consumption_mechanical_total_mj: float` - Mechanical energy consumed (PTI/PTO)
- `energy_consumption_propulsion_total_mj: float` - Energy for propulsion shaft
- `energy_consumption_auxiliary_total_mj: float` - Energy for auxiliary loads
- `energy_input_mechanical_total_mj: float` - Mechanical energy input (generator/PTO)
- `energy_input_electric_total_mj: float` - Electrical energy input (shore power)

**Operating Hours:**
- `running_hours_genset_total_hr: float` - Total genset operating hours (all generators combined)
- `running_hours_main_engines_hr: float` - Total main engine hours
- `running_hours_fuel_cell_total_hr: float` - Total fuel cell operating hours
- `running_hours_pti_pto_total_hr: float` - PTI/PTO operating hours

**Energy Storage:**
- `energy_stored_total_mj: float` - Net energy change in batteries/storage
  - Positive: Energy stored; Negative: Energy depleted
- `load_ratio_genset: Optional[float]` - Average genset load ratio

**Per-Component Results:**
- `detail_result: pd.DataFrame` - Detailed breakdown for each component

**DataFrame Structure (`detail_result`):**

The `detail_result` DataFrame contains time-series results for each component with the following columns:

| Column | Description |
|--------|-------------|
| `component_name` | Name of the component |
| `component_type` | Type (engine, generator, motor, etc.) |
| `switchboard_id` | Connected switchboard ID |
| `time_point` | Time index (0, 1, 2, ...) |
| `power_output_kw` | Electrical output power (kW) |
| `power_input_kw` | Electrical input power (kW) |
| `load_ratio` | Load as fraction of rated power (0-1) |
| `efficiency` | Component efficiency at this load point |
| `fuel_consumption_kg` | Fuel consumed in this time step (kg) |
| `co2_emission_kg` | CO2 emissions in this time step (kg) |
| `nox_emission_kg` | NOx emissions (kg) |
| `running_hours_hr` | Operating hours in this time step |
| `status` | On (True) or Off (False) |

**Example: Analyzing Results**

```python
result = system.get_fuel_energy_consumption_running_time()

# System totals
print(f"Total fuel: {result.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction:.2f} kg")
print(f"Total fuel (scalar): {result.fuel_consumption_total_kg:.2f} kg")
print(f"Total CO2 (Tank-to-Wake): {result.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel:.2f} kg")
print(f"Total CO2 (Well-to-Wake): {result.co2_emission_total_kg.well_to_wake_kg_or_gco2eq_per_gfuel:.2f} kg")
print(f"Electrical energy: {result.energy_consumption_electric_total_mj:.2f} MJ")
print(f"Propulsion energy: {result.energy_consumption_propulsion_total_mj:.2f} MJ")
print(f"Auxiliary energy: {result.energy_consumption_auxiliary_total_mj:.2f} MJ")
print(f"Genset hours: {result.running_hours_genset_total_hr:.2f} hr")
print(f"Energy stored: {result.energy_stored_total_mj:.2f} MJ")

# Per-component analysis
df = result.detail_result

# Filter for specific component
genset1_data = df[df['component_name'] == 'Genset 1']
avg_load = genset1_data['load_ratio'].mean()
fuel_used = genset1_data['fuel_consumption_kg'].sum()
print(f"Genset 1 average load: {avg_load:.2%}")
print(f"Genset 1 fuel consumption: {fuel_used:.2f} kg")

# Aggregate by component type
fuel_by_type = df.groupby('component_type')['fuel_consumption_kg'].sum()
print("Fuel consumption by component type:")
print(fuel_by_type)

# Time-series analysis
import matplotlib.pyplot as plt
genset1_data.plot(x='time_point', y='power_output_kw',
                  title='Genset 1 Power Output Over Time')
plt.ylabel('Power (kW)')
plt.show()
```

**Use Cases:**
- **Voyage Analysis**: Calculate fuel and emissions for a complete voyage
- **Annual Performance**: Simulate full-year operations with detailed profiles
- **Component Sizing**: Compare different configurations to optimize system design
- **Maintenance Planning**: Track running hours for maintenance scheduling
- **Emissions Reporting**: Generate compliance reports (IMO, FuelEU Maritime)
- **Economic Analysis**: Calculate Total Cost of Ownership (TCO) based on fuel consumption
- **Energy Management**: Analyze battery usage, shore power savings, load distribution

## Fuel and Emissions

### `TypeFuel`

Enumeration of fuel types.

```python
from feems.fuel import TypeFuel

TypeFuel.DIESEL
TypeFuel.HFO            # Heavy Fuel Oil
TypeFuel.NATURAL_GAS    # Liquefied Natural Gas (LNG)
TypeFuel.HYDROGEN
TypeFuel.AMMONIA
TypeFuel.METHANOL
TypeFuel.ETHANOL
TypeFuel.LPG_PROPANE
TypeFuel.LPG_BUTANE
TypeFuel.LFO            # Light Fuel Oil
TypeFuel.LSFO_CRUDE     # Low Sulphur Fuel Oil (Crude)
TypeFuel.LSFO_BLEND     # Low Sulphur Fuel Oil (Blend)
TypeFuel.ULSFO          # Ultra Low Sulphur Fuel Oil
TypeFuel.VLSFO          # Very Low Sulphur Fuel Oil
TypeFuel.NONE
```

### `FuelOrigin`

Origin classification for fuel (affects lifecycle GHG emission factors).

```python
from feems.fuel import FuelOrigin

FuelOrigin.FOSSIL           # Conventional fossil fuel
FuelOrigin.BIO              # Biofuel
FuelOrigin.RENEWABLE_NON_BIO  # Renewable non-bio (e.g., e-fuels, RFNBO)
FuelOrigin.NONE
```

### `FuelSpecifiedBy`

Emission calculation methodology.

```python
from feems.fuel import FuelSpecifiedBy

FuelSpecifiedBy.IMO              # IMO emission factors (default)
FuelSpecifiedBy.FUEL_EU_MARITIME # FuelEU Maritime methodology
FuelSpecifiedBy.USER             # Custom emission factors (USER-defined)
FuelSpecifiedBy.NONE
```

### `GhgEmissionFactorTankToWake`

Dataclass holding tank-to-wake GHG emission factors for one fuel/consumer-class combination.

**Fields:**
- `co2_factor_gco2_per_gfuel: float` - CO₂ emission factor (gCO₂/gfuel)
- `ch4_factor_gch4_per_gfuel: Union[float, np.ndarray]` - CH₄ emission factor (gCH₄/gfuel). May be a numpy array when overridden by a load-dependent engine emission curve.
- `n2o_factor_gn2o_per_gfuel: Union[float, np.ndarray]` - N₂O emission factor (gN₂O/gfuel). May be a numpy array when overridden by a load-dependent engine emission curve.
- `c_slip_percent: Union[float, np.ndarray]` - Methane slip as a percentage of fuel mass. Set to `0.0` when `ch4_factor_gch4_per_gfuel` is curve-derived (the curve already accounts for total methane including slip).
- `fuel_consumer_class: Optional[Union[FuelConsumerClassFuelEUMaritime, str]]` - Consumer class for FuelEU Maritime lookup; `None` for IMO/USER fuels.

**Properties:**
- `ghg_emission_factor_gco2eq_per_gfuel: Union[float, np.ndarray]` - Combined GHG factor in gCO₂eq/gfuel, accounting for CO₂, CH₄ (×GWP100), N₂O (×GWP100), and methane slip.

### `Fuel`

A single fuel with its GHG emission factors and consumption quantity.

**Key Attributes:**
- `fuel_type: TypeFuel`
- `origin: FuelOrigin`
- `fuel_specified_by: FuelSpecifiedBy`
- `mass_or_mass_fraction: Union[float, np.ndarray]` - Mass in kg or kg/s (or mass fraction)
- `lhv_mj_per_g: float` - Lower heating value in MJ/g
- `ghg_emission_factor_tank_to_wake: List[GhgEmissionFactorTankToWake]`

**Key Methods:**
- `get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel(fuel_consumer_class=None, exclude_slip=False) -> Union[float, np.ndarray]`
  - Returns the tank-to-wake GHG factor in gCO₂eq/gfuel for the given consumer class.
  - Returns a `np.ndarray` when the stored `ch4_factor_gch4_per_gfuel` / `n2o_factor_gn2o_per_gfuel` fields are arrays (i.e., when set via engine emission curves over multiple load points).

- `with_emission_curve_ghg_overrides(ch4_factor_gch4_per_gfuel=None, n2o_factor_gn2o_per_gfuel=None) -> Fuel`
  - Returns a copy with CH₄ and/or N₂O GHG factors replaced by engine-curve-derived values.
  - **Parameters accept `Union[float, np.ndarray]`** — when `power_kw` is a numpy array the engine computes per-timestep factors as arrays, and this method propagates them correctly through element-wise arithmetic.
  - When `ch4_factor_gch4_per_gfuel` is provided, `c_slip_percent` is zeroed in all `GhgEmissionFactorTankToWake` entries (the curve already captures total methane including slip).
  - Returns `self` unchanged when both arguments are `None`.

### `FuelConsumption`

Fuel consumption data structure.

**Attributes:**
- `fuels: List[Fuel]` - List of `Fuel` objects with consumption data

**Methods:**
- `get_total_co2_emissions(fuel_consumer_class=None) -> GHGEmissions`
  - Returns total GHG emissions in kg (or kg/s), aggregated across all fuels.

### `GHGEmissions`

Greenhouse gas emissions data (dataclass in `feems.fuel`).

**Fields:**
- `tank_to_wake_kg_or_gco2eq_per_gfuel: float` - Operational (combustion) emissions
- `well_to_tank_kg_or_gco2eq_per_gfuel: float` - Upstream (supply chain) emissions
- `tank_to_wake_kg_or_gco2eq_per_gfuel_without_slip: float` - Operational emissions excluding methane slip
- `tank_to_wake_kg_or_gco2eq_per_gfuel_from_green_fuel: float` - Contribution from green fuels
- `tank_to_wake_kg_or_gco2eq_per_gfuel_without_slip_from_green_fuel: float`

**Properties (computed):**
- `well_to_wake_kg_or_gco2eq_per_gfuel` - Total lifecycle (tank-to-wake + well-to-tank)
- `well_to_wake_without_slip_kg_or_gco2eq_per_gfuel` - Lifecycle excluding methane slip
- `tank_to_wake_emissions_kg_for_ets` - ETS-reportable emissions (excludes green fuel credit)
- `tank_to_wake_emissions_without_slip_kg_for_ets` - ETS emissions excluding methane slip

## Types

### Power and Speed Types

```python
from feems.types_for_feems import Power_kW, Speed_rpm, SwbId

power = Power_kW(1000)  # 1000 kW
speed = Speed_rpm(1500)  # 1500 RPM
swb_id = SwbId(1)       # Switchboard 1
```

### `TypeComponent`

Component type enumeration.

```python
from feems.types_for_feems import TypeComponent

TypeComponent.NONE
TypeComponent.MAIN_ENGINE
TypeComponent.AUXILIARY_ENGINE
TypeComponent.GENERATOR
TypeComponent.PROPULSION_DRIVE
TypeComponent.OTHER_LOAD
TypeComponent.PTI_PTO_SYSTEM
TypeComponent.BATTERY_SYSTEM
TypeComponent.FUEL_CELL_SYSTEM
TypeComponent.RECTIFIER
TypeComponent.MAIN_ENGINE_WITH_GEARBOX
TypeComponent.ELECTRIC_MOTOR
TypeComponent.GENSET
TypeComponent.TRANSFORMER
TypeComponent.INVERTER
TypeComponent.CIRCUIT_BREAKER
TypeComponent.ACTIVE_FRONT_END
TypeComponent.POWER_CONVERTER
TypeComponent.SYNCHRONOUS_MACHINE
TypeComponent.INDUCTION_MACHINE
TypeComponent.GEARBOX
TypeComponent.FUEL_CELL
TypeComponent.PROPELLER_LOAD
TypeComponent.OTHER_MECHANICAL_LOAD
TypeComponent.BATTERY
TypeComponent.SUPERCAPACITOR
TypeComponent.SUPERCAPACITOR_SYSTEM
TypeComponent.SHORE_POWER
TypeComponent.COGAS
TypeComponent.COGES
```

### `TypePower`

Power type classification.

```python
from feems.types_for_feems import TypePower

TypePower.NONE
TypePower.POWER_SOURCE           # Generates power (gensets, shore power, fuel cells)
TypePower.POWER_CONSUMER         # Consumes power (motors, loads)
TypePower.PTI_PTO                # Bidirectional (shaft generator/motor)
TypePower.ENERGY_STORAGE         # Storage system (batteries, supercapacitors)
TypePower.POWER_TRANSMISSION     # Transmits power (transformers, converters)
```

### `EmissionType`

Pollutant type enumeration used as keys in `EngineRunPoint.emissions_g_per_s` and
`FEEMSResult.total_emission_kg`.

```python
from feems.types_for_feems import EmissionType

EmissionType.SOX   # Sulphur oxides
EmissionType.NOX   # Nitrogen oxides
EmissionType.CO    # Carbon monoxide
EmissionType.PM    # Particulate matter
EmissionType.HC    # Hydrocarbons
EmissionType.CH4   # Methane
EmissionType.N2O   # Nitrous oxide
```

### `EngineCycleType`

Engine thermodynamic cycle type (affects FuelEU Maritime classification for LNG engines).

```python
from feems.types_for_feems import EngineCycleType

EngineCycleType.DIESEL                  # Diesel cycle (default)
EngineCycleType.OTTO                    # Otto cycle
EngineCycleType.LEAN_BURN_SPARK_IGNITION  # LBSI cycle
EngineCycleType.NONE
```

### `NOxCalculationMethod`

Method for calculating NOx emissions.

```python
from feems.types_for_feems import NOxCalculationMethod

NOxCalculationMethod.TIER_2    # IMO Tier 2 (default)
NOxCalculationMethod.TIER_1    # IMO Tier 1
NOxCalculationMethod.TIER_3    # IMO Tier 3
NOxCalculationMethod.CURVE     # Custom NOx emission curve (requires EmissionType.NOX in emissions_curves)
```

## Utilities

### `IntegrationMethod`

Time integration methods for fuel/energy calculation.

```python
from feems.system_model import IntegrationMethod

IntegrationMethod.trapezoid    # Trapezoidal rule
IntegrationMethod.simpson      # Simpson's rule (more accurate)
IntegrationMethod.sum_with_time  # Simple summation
```

### Logging

FEEMS uses Python's standard logging module.

```python
from feems import get_logger

logger = get_logger(__name__)
logger.setLevel('DEBUG')  # Set log level
```

## Common Patterns

### Pattern 1: Create and Configure System

```python
# 1. Create components
components = [genset1, genset2, load1, drive1]

# 2. Create system
system = ElectricPowerSystem(
    name="System",
    power_plant_components=components,
    bus_tie_connections=[(1, 2)]
)

# 3. Set loads
system.set_power_input_from_power_output_by_switchboard_id_type_name(...)

# 4. Configure power sources
system.set_status_by_switchboard_id_power_type(...)
system.set_load_sharing_mode_power_sources_by_switchboard_id_power_type(...)

# 5. Set bus-tie status
system.set_bus_tie_status_all(...)

# 6. Run simulation
system.set_time_interval(60)
system.do_power_balance_calculation()
result = system.get_fuel_energy_consumption_running_time()
```

### Pattern 2: Time-Series Analysis

```python
import pandas as pd

# Create time-series load profile
time_points = 1000
time_step = 1.0  # seconds
load_profile = pd.DataFrame({
    'time': np.arange(0, time_points * time_step, time_step),
    'power': 100 + 50 * np.random.random(time_points)
})

# Set as system load
system.set_power_input_from_power_output_by_switchboard_id_type_name(
    power_output=load_profile['power'].values,
    ...
)

# Configure and run
system.set_time_interval(time_step)
system.do_power_balance_calculation()
result = system.get_fuel_energy_consumption_running_time()
```

### Pattern 3: Comparison Studies

```python
# Scenario 1: Shore power
shore_status = np.ones([n_points, 1]).astype(bool)
genset_status = np.zeros([n_points, 1]).astype(bool)
status_shore = np.hstack([shore_status, genset_status])

system.set_status_by_switchboard_id_power_type(1, TypePower.POWER_SOURCE, status_shore)
system.do_power_balance_calculation()
result_shore = system.get_fuel_energy_consumption_running_time()

# Scenario 2: Genset
shore_status = np.zeros([n_points, 1]).astype(bool)
genset_status = np.ones([n_points, 1]).astype(bool)
status_genset = np.hstack([shore_status, genset_status])

system.set_status_by_switchboard_id_power_type(1, TypePower.POWER_SOURCE, status_genset)
system.do_power_balance_calculation()
result_genset = system.get_fuel_energy_consumption_running_time()

# Compare
fuel_saved = result_genset.fuel_consumption_total_kg - result_shore.fuel_consumption_total_kg
```

## Error Handling

FEEMS raises standard Python exceptions:

- `ValueError`: Invalid parameter values
- `TypeError`: Incorrect parameter types
- `FileNotFoundError`: Missing configuration files
- `RuntimeError`: Calculation failures

Example:
```python
try:
    system.do_power_balance_calculation()
except RuntimeError as e:
    logger.error(f"Power balance failed: {e}")
    # Handle error (e.g., adjust generator status, reduce loads)
```

## Performance Tips

1. **Use appropriate time steps**: Larger time steps (60-300s) for long simulations
2. **Pre-allocate arrays**: When creating load profiles, use numpy arrays
3. **Batch calculations**: Configure all settings before running power balance
4. **Integration method**: Use `trapezoid` for speed, `simpson` for accuracy

## Further Reading

- Examples: `../examples/` directory
- Source code: `feems/` directory
- Tests: `tests/` directory for usage examples
