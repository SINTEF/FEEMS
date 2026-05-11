# FEEMS Examples

This directory contains examples demonstrating how to use FEEMS (Fuel, Emissions, Energy Calculation for Machinery System) for modeling marine power and propulsion systems.

## Overview

FEEMS is a Python library for simulating fuel consumption, emissions, and energy balance in marine power systems. These examples show you how to:

- Build electric power systems from components
- Configure shore power connections
- Run simulations with different operational scenarios
- Calculate fuel consumption and emissions
- Perform power balance calculations

## Examples

### 00_Basic_Example.ipynb
**Topics**: Component creation, serial systems, power balance

A comprehensive introduction to FEEMS covering:
- Creating atomic components (engines, generators)
- Building serial components (gensets, propulsion drives)
- Creating complete electric power systems
- Running power balance calculations
- Calculating fuel consumption and emissions

**Best for**: First-time users learning FEEMS fundamentals

### 01_Running_simulation.ipynb
**Topics**: Time-series simulation, operational profiles

Demonstrates running time-series simulations with:
- Variable load profiles over time
- Dynamic power management
- Simulation results analysis

**Best for**: Users who need to simulate realistic operational scenarios

### 02_Shore_Power_Example.ipynb
**Topics**: Shore power connections, emission reductions

Complete guide to modeling shore power systems:
- Creating simple shore power connections
- Building shore power systems with converters
- Comparing shore power vs genset operation
- Quantifying environmental benefits (fuel and emission savings)
- Simulating transitions between power sources

**Best for**: Port operations, emission reduction analysis, cold ironing studies

### shore_power_simple.py
**Topics**: Shore power (Python script version)

A simplified Python script version of the shore power example that can be run directly:
```bash
uv run python examples/shore_power_simple.py
```

**Best for**: Users who prefer scripts over notebooks, automation, CI/CD integration

## Getting Started

### Prerequisites

Ensure FEEMS is installed and the workspace is set up:

```bash
cd /path/to/FEEMS
uv sync
```

### Running Jupyter Notebooks

Start Jupyter Lab or Jupyter Notebook:

```bash
# Using Jupyter Lab (recommended)
uv run jupyter lab

# Or using Jupyter Notebook
uv run jupyter notebook
```

Then navigate to the `examples/` directory and open any `.ipynb` file.

### Running Python Scripts

Execute any Python script directly:

```bash
uv run python examples/shore_power_simple.py
```

## Project Structure

```
examples/
├── README.md                      # This file
├── 00_Basic_Example.ipynb         # Introduction to FEEMS
├── 01_Running_simulation.ipynb    # Time-series simulations
├── 02_Shore_Power_Example.ipynb   # Shore power modeling
├── shore_power_simple.py          # Shore power script
├── utils.py                       # Helper functions
├── equipment_data.json            # Sample equipment specifications
├── configuration.json             # Sample system configuration
└── data/                          # Output data directory
```

## Common Tasks

### Creating Components

```python
from feems.components_model import Engine, Genset
from feems.components_model.component_electric import ElectricMachine, ShorePowerConnection
from feems.types_for_feems import Power_kW, Speed_rpm, SwbId, TypeComponent, TypePower
import numpy as np

# Create an engine
engine = Engine(
    type_=TypeComponent.AUXILIARY_ENGINE,
    name="Auxiliary engine",
    rated_power=Power_kW(500),
    rated_speed=Speed_rpm(1500),
    bsfc_curve=np.array([[0.25, 0.5, 0.75, 1.0], [280.0, 220.0, 200.0, 210.0]]).T
)

# Create a generator
generator = ElectricMachine(
    type_=TypeComponent.GENERATOR,
    name="Generator",
    rated_power=Power_kW(475),
    rated_speed=Speed_rpm(1500),
    power_type=TypePower.POWER_SOURCE,
    switchboard_id=SwbId(1),
    eff_curve=np.array([[0.25, 0.5, 0.75, 1.0], [0.88, 0.92, 0.94, 0.95]]).T
)

# Create a genset
genset = Genset(name="Genset", aux_engine=engine, generator=generator)

# Create shore power
shore_power = ShorePowerConnection(
    name="Shore Power",
    rated_power=Power_kW(1000),
    switchboard_id=SwbId(1)
)
```

### Building a Power System

```python
from feems.system_model import ElectricPowerSystem

# Create system with components
power_plant_components = [shore_power, genset, auxiliary_load]

system = ElectricPowerSystem(
    name="Ship Power System",
    power_plant_components=power_plant_components,
    bus_tie_connections=[]
)
```

### Running Simulations

```python
import numpy as np
from feems.system_model import IntegrationMethod

# Set load profile
load_profile = 200 + 100 * np.random.random(100)  # 100 time points
system.set_power_input_from_power_output_by_switchboard_id_type_name(
    power_output=load_profile,
    switchboard_id=1,
    type_=TypePower.POWER_CONSUMER,
    name="Auxiliary Load"
)

# Set power source status (on/off)
status = np.ones([100, 2]).astype(bool)  # Both sources on
system.set_status_by_switchboard_id_power_type(
    switchboard_id=1,
    power_type=TypePower.POWER_SOURCE,
    status=status
)

# Set load sharing (0 = equal sharing)
load_sharing = np.zeros([100, 2])
system.set_load_sharing_mode_power_sources_by_switchboard_id_power_type(
    switchboard_id=1,
    power_type=TypePower.POWER_SOURCE,
    load_sharing_mode=load_sharing
)

# Run calculation
system.set_time_interval(60, integration_method=IntegrationMethod.simpson)
system.do_power_balance_calculation()

# Get results
result = system.get_fuel_energy_consumption_running_time()
print(f"Total fuel: {result.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction:.2f} kg")
print(f"Total CO2: {result.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel:.2f} kg")
```

## Key Concepts

### Component Types

- **AUXILIARY_ENGINE**: Diesel/gas engines for power generation
- **GENERATOR**: Electric generators
- **GENSET**: Combined engine + generator
- **SHORE_POWER**: Shore power connection
- **POWER_CONVERTER**: Frequency/voltage converters
- **ELECTRIC_MOTOR**: Electric motors (propulsion or auxiliary)
- **OTHER_LOAD**: Generic electrical loads

### Power Types

- **POWER_SOURCE**: Components that generate power (gensets, shore power, batteries)
- **POWER_CONSUMER**: Components that consume power (motors, loads)
- **POWER_TRANSMISSION**: Components that transmit power (transformers, converters)

### Efficiency Curves

Efficiency curves define component efficiency vs. load:
```python
# Format: [[load_1, load_2, ...], [eff_1, eff_2, ...]]
eff_curve = np.array([
    [0.25, 0.5, 0.75, 1.0],      # Load percentages
    [0.88, 0.92, 0.94, 0.95]     # Efficiencies
]).T  # Transpose to get [[load_1, eff_1], [load_2, eff_2], ...]
```

### BSFC Curves

Brake Specific Fuel Consumption curves define fuel consumption vs. engine load:
```python
# Format: [[load_1, load_2, ...], [bsfc_1, bsfc_2, ...]]
bsfc_curve = np.array([
    [0.25, 0.5, 0.75, 1.0],           # Load percentages
    [280.0, 220.0, 200.0, 210.0]      # BSFC in g/kWh
]).T
```

## Typical Use Cases

### Port Operations with Shore Power
See: `02_Shore_Power_Example.ipynb`
- Model emissions during port stays
- Compare shore power vs genset operation
- Calculate cost/emission savings

### Hybrid Electric Propulsion
See: `00_Basic_Example.ipynb`
- Multiple gensets with load sharing
- Electric propulsion drives
- Battery integration (energy storage)

### Emission Reporting
See: `01_Running_simulation.ipynb`
- Time-series fuel consumption
- CO2 and NOx emissions
- IMO compliance reporting

## Data Format

### Equipment Data (equipment_data.json)
```json
{
  "type": "AUXILIARY_ENGINE",
  "name": "Auxiliary engine 700",
  "rated_power": 700,
  "rated_speed": 1500,
  "bsfc_curve": [[0.25, 0.5, 0.75, 1.0], [280.0, 220.0, 200.0, 210.0]]
}
```

### Configuration Data (configuration.json)
```json
{
  "name": "Genset 1",
  "component": "Auxiliary engine 700",
  "switchboard_id": 1,
  "connected_to": "Generator 1"
}
```

## Troubleshooting

### Import Errors
If you get import errors, ensure the workspace is synced:
```bash
uv sync
```

### Jupyter Not Found
Install Jupyter if not already installed:
```bash
uv add --dev jupyter jupyterlab
```

### Power Balance Errors
- Ensure all loads have corresponding power sources
- Check that power source status is set correctly
- Verify load sharing mode is configured

## Further Reading

- [FEEMS Documentation](../README.md)
- [CLAUDE.md](../CLAUDE.md) - Project overview and development guide
- [Component Model Source](../feems/feems/components_model/)
- [System Model Source](../feems/feems/system_model.py)

## Contributing

To add new examples:

1. Create a descriptive filename (e.g., `03_Battery_Integration.ipynb`)
2. Include clear documentation and comments
3. Follow the existing example structure
4. Update this README with your example
5. Test your example with `uv run`

## License

See the main project LICENSE file.

## Support

For issues or questions:
- GitHub Issues: [SINTEF/FEEMS](https://github.com/SINTEF/FEEMS/issues)
- Review existing examples for patterns and best practices
