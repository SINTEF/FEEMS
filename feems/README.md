# FEEMS - Fuel, Emissions, Energy Calculation for Machinery System

[![PyPI version](https://badge.fury.io/py/feems.svg)](https://badge.fury.io/py/feems)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

FEEMS is a comprehensive modeling framework for marine power and propulsion systems, developed by SINTEF Ocean. It enables accurate calculation of fuel consumption, emissions, and energy balance for complex machinery configurations including conventional diesel-electric, hybrid propulsion with PTI/PTO, fuel cell systems, and shore power integration.

## Features

### 🚢 Supported System Types

- **Diesel Electric Propulsion** (Hybrid/Conventional)
  - Multiple generator sets with load sharing
  - Electric propulsion drives with power converters
  - Battery energy storage integration
  - Shore power connections

- **Hybrid Propulsion with PTI/PTO**
  - Power Take-In (PTI) and Power Take-Off (PTO) systems
  - Shaft generators and motors
  - Mechanical-electrical power transfer

- **Mechanical Propulsion**
  - Main engines with gearboxes
  - Separate electric power system for auxiliaries
  - COGAS (Combined Gas and Steam) systems

### ⚡ Key Capabilities

- **Component-Based Modeling**: Build systems from individual components (engines, generators, motors, converters)
- **Power Balance Calculation**: Automatic load distribution across power sources
- **Fuel Consumption**: Detailed fuel consumption based on BSFC curves and load profiles
- **Emissions Calculation**: CO2, NOx, SOx, PM emissions with multiple methodologies (IMO, FuelEU Maritime)
- **Energy Analysis**: Track energy flows through mechanical and electrical domains
- **Time-Series Simulation**: Analyze performance over operational profiles
- **Flexible Configuration**: Configure complex systems via code or data files

## Installation

### From PyPI (Users)

```bash
pip install feems
```

### From Source (Developers)

If you're working with the FEEMS workspace:

```bash
# Clone the repository
git clone https://github.com/SINTEF/FEEMS.git
cd FEEMS

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e feems/
```

## Quick Start

### Basic Example: Create a Genset

```python
import numpy as np
from feems.components_model import Engine, Genset
from feems.components_model.component_electric import ElectricMachine
from feems.types_for_feems import Power_kW, Speed_rpm, SwbId, TypeComponent, TypePower

# Create an engine with BSFC curve
engine = Engine(
    type_=TypeComponent.AUXILIARY_ENGINE,
    name="Auxiliary Engine",
    rated_power=Power_kW(700),
    rated_speed=Speed_rpm(1500),
    bsfc_curve=np.array([
        [0.25, 0.5, 0.75, 1.0],          # Load points
        [280.0, 220.0, 200.0, 210.0]     # BSFC in g/kWh
    ]).T
)

# Create a generator
generator = ElectricMachine(
    type_=TypeComponent.GENERATOR,
    name="Generator",
    rated_power=Power_kW(665),
    rated_speed=Speed_rpm(1500),
    power_type=TypePower.POWER_SOURCE,
    switchboard_id=SwbId(1),
    eff_curve=np.array([
        [0.25, 0.5, 0.75, 1.0],
        [0.88, 0.92, 0.94, 0.95]
    ]).T
)

# Combine into a genset
genset = Genset(name="Genset 1", aux_engine=engine, generator=generator)

# Calculate fuel consumption at 450 kW electrical output
result = genset.get_fuel_cons_load_bsfc_from_power_out_generator_kw(Power_kW(450))
fuel_kg_per_s = result.engine.fuel_flow_rate_kg_per_s.fuels[0].mass_or_mass_fraction
print(f"Fuel consumption: {fuel_kg_per_s:.4f} kg/s")
```

### Complete Power System Example

```python
from feems.system_model import ElectricPowerSystem, IntegrationMethod

# Create components (gensets, loads, propulsion drives)
components = [genset_1, genset_2, propulsion_drive, auxiliary_load]

# Create the power system
power_system = ElectricPowerSystem(
    name="Ship Power System",
    power_plant_components=components,
    bus_tie_connections=[(1, 2)]  # Connect bus 1 and bus 2
)

# Set loads
power_system.set_power_input_from_power_output_by_switchboard_id_type_name(
    power_output=np.array([300, 350, 400]),  # kW time series
    switchboard_id=1,
    type_=TypePower.POWER_CONSUMER,
    name="Auxiliary Load"
)

# Configure generator status (on/off)
status = np.ones([3, 2]).astype(bool)  # Both gensets on for 3 time points
power_system.set_status_by_switchboard_id_power_type(
    switchboard_id=1,
    power_type=TypePower.POWER_SOURCE,
    status=status
)

# Set load sharing mode (0 = equal sharing)
load_sharing = np.zeros([3, 2])
power_system.set_load_sharing_mode_power_sources_by_switchboard_id_power_type(
    switchboard_id=1,
    power_type=TypePower.POWER_SOURCE,
    load_sharing_mode=load_sharing
)

# Run power balance calculation
power_system.set_time_interval(60, integration_method=IntegrationMethod.simpson)
power_system.do_power_balance_calculation()

# Get results
result = power_system.get_fuel_energy_consumption_running_time()
print(f"Total fuel: {result.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction:.2f} kg")
print(f"Total CO2: {result.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel:.2f} kg")
```

## Architecture

### Component Hierarchy

FEEMS uses a component-based modeling approach where complex systems are built from individual components.

**Base Classes:**
```
Component (abstract base)
├── BasicComponent
│   ├── ElectricComponent
│   │   ├── ElectricMachine (Generator/Motor)
│   │   ├── Battery
│   │   ├── BatterySystem
│   │   ├── FuelCell
│   │   ├── FuelCellSystem
│   │   ├── ShorePowerConnection
│   │   ├── ShorePowerConnectionSystem
│   │   ├── SuperCapacitor
│   │   ├── SuperCapacitorSystem
│   │   └── MechanicalPropulsionComponent (Propeller, Gearbox, Clutch)
│   │
│   ├── SerialSystem (composite components)
│   │   ├── SerialSystemElectric
│   │   │   ├── PTIPTO (Power Take In/Power Take Off)
│   │   │   └── PropulsionDrive (Converter chain + Motor)
│   │   └── COGAS (Combined Gas and Steam)
│   │
│   └── COGES (Combined Gas and Electric System)
│
├── Engine
│   ├── EngineDualFuel (e.g., Diesel/Gas)
│   └── EngineMultiFuel (multiple fuel options)
│
├── MainEngineForMechanicalPropulsion
│   └── MainEngineWithGearBoxForMechanicalPropulsion
│
└── Genset (Engine + Generator composite)
```

### System Structure

FEEMS supports three main system configurations:

#### 1. Electric Power System

For diesel-electric and hybrid electric propulsion:

```
ElectricPowerSystem
│
├── Switchboard 1 (electrical bus)
│   ├── Power Sources
│   │   ├── Genset (Engine + Generator)
│   │   ├── FuelCellSystem
│   │   ├── ShorePowerConnection
│   │   └── COGES
│   ├── Energy Storage
│   │   ├── Battery / BatterySystem
│   │   └── SuperCapacitor / SuperCapacitorSystem
│   ├── Propulsion Drives
│   │   └── SerialSystemElectric (Converters + Motor)
│   ├── PTI/PTO Systems
│   │   └── PTIPTO (shaft generator/motor)
│   └── Other Loads
│       └── ElectricComponent (hotel, auxiliary loads)
│
├── Switchboard 2 (electrical bus)
│   └── [same structure as Switchboard 1]
│
└── Bus-Tie Breakers
    └── BusBreaker (connects Switchboard 1 ↔ Switchboard 2)
```

**Key Features:**
- Multiple switchboards with independent or connected operation
- Automatic load sharing among power sources
- Battery/shore power integration
- Bus-tie breakers for switchboard coupling

#### 2. Mechanical Propulsion System

For conventional mechanical propulsion:

```
MechanicalPropulsionSystem
│
├── ShaftLine 1
│   ├── Main Engine
│   │   └── MainEngineForMechanicalPropulsion
│   │       └── MainEngineWithGearBoxForMechanicalPropulsion
│   ├── PTI/PTO (optional)
│   │   └── PTIPTO (connects to electric system)
│   └── Mechanical Loads
│       ├── Propeller
│       ├── Gearbox
│       └── Clutch
│
└── ShaftLine 2
    └── [same structure as ShaftLine 1]
```

**Key Features:**
- Multiple independent shaftlines
- Optional PTI/PTO for hybrid operation
- Main engine with or without gearbox

#### 3. Hybrid System (Mechanical + Electric)

For vessels with both mechanical propulsion and electric auxiliary power:

```
MechanicalPropulsionSystemWithElectricPowerSystem
│
├── MechanicalPropulsionSystem
│   └── ShaftLine(s)
│       ├── Main Engine(s)
│       ├── PTI/PTO (optional, connects to electric side)
│       └── Propeller(s)
│
└── ElectricPowerSystem
    └── Switchboard(s)
        ├── Genset(s) (auxiliary power)
        ├── Shore Power
        └── Hotel/Auxiliary Loads
```

**Key Features:**
- Independent mechanical propulsion
- Separate electric system for auxiliaries
- PTI/PTO coupling between systems
- Full PTI mode for boost propulsion power

## Real-World Applications

FEEMS has been used in various marine vessel design and analysis studies:

- **Hydrogen-Powered Ferry Design**: Complete machinery system modeling for hydrogen fuel cell powered ferries, including operational simulation with real AIS data, power management system optimization, and Total Cost of Ownership (TCO) analysis. The framework successfully handled 2,400+ voyage simulations with detailed propulsion power predictions validated against actual vessel measurements.

- **Emissions Compliance**: FuelEU Maritime regulation compliance calculation for various vessel types, enabling accurate carbon intensity indicators (CII) and emissions reporting.

- **Hybrid System Optimization**: Analysis of battery sizing, load-dependent genset operation, and energy management strategies for various operating profiles.

- **Shore Power Integration**: Economic and environmental analysis of cold ironing capabilities for port operations, demonstrating 100% fuel and emission savings potential during port stays.

The framework's ability to handle 100,000+ data points in time-series simulations makes it suitable for detailed operational analysis, from single voyage assessment to full annual performance evaluation.

## Documentation

- **Examples**: See the `../examples/` directory for comprehensive tutorials
  - `00_Basic_Example.ipynb`: Component creation and system building
  - `01_Running_simulation.ipynb`: Time-series simulations
  - `02_Shore_Power_Example.ipynb`: Shore power integration

- **API Reference**: See [API_REFERENCE.md](API_REFERENCE.md)

- **Project Guide**: See `../CLAUDE.md` for development guidelines

## Requirements

- Python ≥ 3.10, < 3.13
- pandas ≥ 2.1.1
- scipy ≥ 1.11.2

## Related Packages

- **MachSysS**: Protocol Buffer definitions and data conversion utilities
- **RunFeemsSim**: Higher-level simulation interface with Power Management System logic

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/SINTEF/FEEMS.git
cd FEEMS
uv sync

# Run tests
uv run pytest feems/tests/

# Lint and format
uv run ruff check feems/
uv run ruff format feems/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Citation

If you use FEEMS in your research, please cite:

**Software:**
```bibtex
@software{feems2024,
  title = {FEEMS: Fuel, Emissions, Energy Calculation for Machinery System},
  author = {Yum, Kevin Koosup and contributors},
  year = {2024},
  url = {https://github.com/SINTEF/FEEMS},
  version = {0.12.1}
}
```

**Academic Paper:**
```bibtex
@inproceedings{yum2024designlab,
  title = {Design Lab: A Simulation-Based Approach for the Design of Maritime Vessels Using Hydrogen Fuel Cells},
  author = {Yum, Kevin Kosup and Tavakoli, Sadi and Aarseth, Torstein and Bremnes Nielsen, Jørgen and Sternesen, Dag},
  year = {2024},
  booktitle = {Proceedings of the Maritime Conference},
  organization = {SINTEF Ocean},
  note = {Case study: STENA Jutlandica ferry hydrogen fuel cell conversion analysis}
}
```

## Support

- **Issues**: [GitHub Issues](https://github.com/SINTEF/FEEMS/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SINTEF/FEEMS/discussions)
- **Email**: kevin.koosup.yum@gmail.com

## Acknowledgments

FEEMS is developed and maintained by **SINTEF Ocean**, Norway's leading marine technology research institute, for marine power system modeling, fuel consumption calculation, and emissions analysis.

The framework has been developed through various research projects focused on:
- Decarbonization of maritime transport
- Hybrid and electric propulsion systems
- Alternative fuels (hydrogen, ammonia, methanol)
- Energy efficiency optimization
- FuelEU Maritime regulation compliance

Special thanks to all contributors and the maritime industry partners who have provided valuable feedback and validation data.
