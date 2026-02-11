# FEEMS API Reference

This document provides a comprehensive reference for the FEEMS API.

## Table of Contents

- [Component Models](#component-models)
  - [Base Classes](#base-classes)
  - [Mechanical Components](#mechanical-components)
  - [Electric Components](#electric-components)
  - [Serial Systems](#serial-systems)
- [System Model](#system-model)
- [Fuel and Emissions](#fuel-and-emissions)
- [Types](#types)
- [Utilities](#utilities)

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
  - Returns efficiency at given load percentage(s)

- `get_power_output_from_bidirectional_input(...) -> Tuple[...]]`
  - Calculates output power from input power considering efficiency

- `get_power_input_from_bidirectional_output(...) -> Tuple[...]`
  - Calculates input power from output power considering efficiency

#### `Component`

Enhanced component class with serial system support.

**Additional Attributes:**
- `switchboard_id: SwbId` - Connected switchboard identifier
- `status: np.ndarray` - On/off status array
- `load_sharing_mode: np.ndarray` - Load sharing configuration

#### `SerialSystem`

Base class for components arranged in series.

**Attributes:**
- `components: List[Component]` - Ordered list of components in series

**Methods:**
- `get_total_efficiency(...) -> float` - Total efficiency through the chain
- `set_power_input_from_output(...) -> Tuple[...]` - Calculate input from output power

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
- `fuel_type: FuelType` - Fuel type (default: DIESEL)

**Key Methods:**
- `get_engine_run_point_from_power_out_kw(power_kw: Optional[np.ndarray] = None) -> EngineRunPoint`
  - Calculate engine operating point from power output
  - Returns fuel consumption, BSFC, load ratio, emissions

**Returns:** `EngineRunPoint`
- `fuel_flow_rate_kg_per_s: FuelConsumption` - Fuel consumption
- `bsfc_g_per_kWh: np.ndarray` - BSFC at operating point
- `load_ratio: np.ndarray` - Load as fraction of rated power
- `nox_emission_kg_per_s: np.ndarray` - NOx emissions

#### `EngineDualFuel`

Engine capable of running on two different fuels.

```python
from feems.components_model.component_mechanical import EngineDualFuel
from feems.fuel import FuelType

dual_fuel = EngineDualFuel(
    type_=TypeComponent.MAIN_ENGINE,
    name="Dual Fuel Engine",
    rated_power=Power_kW(5000),
    rated_speed=Speed_rpm(750),
    bsfc_curve_fuel_1=bsfc_diesel,
    bsfc_curve_fuel_2=bsfc_lng,
    fuel_type_fuel_1=FuelType.DIESEL,
    fuel_type_fuel_2=FuelType.LNG
)
```

**Attributes:**
- `bsfc_curve_fuel_1: np.ndarray` - BSFC curve for fuel 1
- `bsfc_curve_fuel_2: np.ndarray` - BSFC curve for fuel 2
- `fuel_type_fuel_1: FuelType` - Primary fuel type
- `fuel_type_fuel_2: FuelType` - Secondary fuel type

**Methods:**
- `get_engine_run_point_from_power_out_kw(..., fuel_sharing: Optional[np.ndarray] = None)`
  - `fuel_sharing`: Array specifying fraction of power from each fuel

#### `MainEngineForMechanicalPropulsion`

Main propulsion engine with propeller interaction.

**Additional Attributes:**
- `propeller: Propeller` - Connected propeller
- `gearbox: Optional[Gearbox]` - Optional gearbox

**Methods:**
- `get_engine_run_point_from_ship_speed(...)`
  - Calculate engine operating point from ship speed
  - Includes propeller loading and water interaction

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

**Methods:**
- `get_soc_from_electric_power(...) -> Tuple[np.ndarray, np.ndarray]`
  - Calculate state of charge from power profile
  - Returns (SoC array, actual power array)

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
- `aux_engine: Engine` - Auxiliary engine
- `generator: ElectricMachine` - Generator
- `fuel_type: FuelType` - Inherited from engine

**Methods:**
- `get_fuel_cons_load_bsfc_from_power_out_generator_kw(power_kw, fuel_specified_by=...) -> GensetRunPoint`
  - Calculate fuel consumption from generator electrical output
  - Returns complete operating point with fuel, emissions, efficiency

**Returns:** `GensetRunPoint`
- `engine: EngineRunPoint` - Engine operating point
- `generator_load_ratio: np.ndarray` - Generator load
- `generator_eff: np.ndarray` - Generator efficiency

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

- `get_fuel_energy_consumption_running_time() -> FEEMSResultForMachinerySystem`
  - Returns comprehensive results including:
    - Total fuel consumption
    - Total emissions (CO2, NOx, etc.)
    - Energy consumption breakdown
    - Operating hours
    - Per-component results

**Returns:** `FEEMSResultForMachinerySystem`
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

#### Results Data Structure

**`FEEMSResultForMachinerySystem`**

Comprehensive results object returned by `get_fuel_energy_consumption_running_time()`. Contains aggregated system-level metrics and detailed per-component breakdowns.

**System-Level Attributes:**

**Fuel Consumption:**
- `multi_fuel_consumption_total_kg: FuelConsumption` - Total fuel consumed for all fuel types
  - Access mass: `result.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction`
  - Supports multiple fuels (diesel, LNG, hydrogen, etc.)

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
- `energy_consumption_total_mj: float` - Total energy consumed by all components
- `energy_consumption_propulsion_total_mj: float` - Energy for propulsion only
- `energy_consumption_auxiliary_total_mj: float` - Energy for auxiliary loads

**Operating Hours:**
- `running_hours_genset_total_hr: float` - Total genset operating hours (all generators combined)
- `running_hours_main_engine_total_hr: float` - Total main engine hours
- `running_hours_fuel_cell_total_hr: float` - Total fuel cell operating hours
- `running_hours_battery_total_hr: float` - Battery charge/discharge hours

**Energy Storage:**
- `net_energy_stored_energy_storage_mj: float` - Net energy change in batteries/storage
  - Positive: Energy stored
  - Negative: Energy depleted
- `net_energy_from_shore_power_mj: float` - Total energy received from shore power

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
print(f"Total CO2 (Tank-to-Wake): {result.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel:.2f} kg")
print(f"Total CO2 (Well-to-Wake): {result.co2_emission_total_kg.well_to_wake_kg_or_gco2eq_per_gfuel:.2f} kg")
print(f"Propulsion energy: {result.energy_consumption_propulsion_total_mj:.2f} MJ")
print(f"Auxiliary energy: {result.energy_consumption_auxiliary_total_mj:.2f} MJ")
print(f"Genset hours: {result.running_hours_genset_total_hr:.2f} hr")

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

### `FuelType`

Enumeration of fuel types.

```python
from feems.fuel import FuelType

FuelType.DIESEL
FuelType.HFO            # Heavy Fuel Oil
FuelType.LNG            # Liquefied Natural Gas
FuelType.METHANOL
FuelType.AMMONIA
FuelType.HYDROGEN
FuelType.BATTERY_STORAGE
```

### `FuelSpecifiedBy`

Emission calculation methodology.

```python
from feems.fuel import FuelSpecifiedBy

FuelSpecifiedBy.IMO                    # IMO emission factors
FuelSpecifiedBy.FUEL_EU_MARITIME       # FuelEU Maritime methodology
FuelSpecifiedBy.USER_DEFINED           # Custom emission factors
```

### `FuelConsumption`

Fuel consumption data structure.

**Attributes:**
- `fuels: List[Fuel]` - List of fuel objects with consumption data

Each `Fuel` object contains:
- `fuel_type: FuelType`
- `mass_or_mass_fraction: float` - Total mass in kg or mass fraction
- `lhv_mj_per_g: float` - Lower heating value

### `GHGEmissions`

Greenhouse gas emissions data.

**Attributes:**
- `tank_to_wake_kg_or_gco2eq_per_gfuel: float` - Operational emissions
- `well_to_tank_kg_or_gco2eq_per_gfuel: float` - Upstream emissions
- `well_to_wake_kg_or_gco2eq_per_gfuel: float` - Total lifecycle emissions
- `tank_to_wake_kg_or_gco2eq_per_gfuel_without_slip: float` - Excluding methane slip
- (Additional attributes for green fuel accounting)

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

TypeComponent.AUXILIARY_ENGINE
TypeComponent.MAIN_ENGINE
TypeComponent.GENERATOR
TypeComponent.ELECTRIC_MOTOR
TypeComponent.BATTERY
TypeComponent.SHORE_POWER
TypeComponent.TRANSFORMER
TypeComponent.RECTIFIER
TypeComponent.INVERTER
TypeComponent.POWER_CONVERTER
TypeComponent.GENSET
TypeComponent.PROPULSION_DRIVE
TypeComponent.PTI_PTO_SYSTEM
TypeComponent.COGAS
TypeComponent.OTHER_LOAD
```

### `TypePower`

Power type classification.

```python
from feems.types_for_feems import TypePower

TypePower.POWER_SOURCE           # Generates power
TypePower.POWER_CONSUMER         # Consumes power
TypePower.POWER_TRANSMISSION     # Transmits power
TypePower.PTI_PTO                # Bidirectional
TypePower.ENERGY_STORAGE         # Storage system
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
fuel_saved = result_genset.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction - \
             result_shore.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction
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
