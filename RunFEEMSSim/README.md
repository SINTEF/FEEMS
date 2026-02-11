# RunFeemsSim - FEEMS Simulation Runner

[![PyPI version](https://badge.fury.io/py/RunFeemsSim.svg)](https://badge.fury.io/py/RunFeemsSim)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**RunFeemsSim** provides a high-level interface for running FEEMS simulations with automated power management. It simplifies time-series simulation, includes Power Management System (PMS) logic for automatic genset control, and integrates seamlessly with the FEEMS ecosystem.

## Features

### 🎯 High-Level Simulation Interface
- **Simple API**: Run complex simulations with minimal code
- **Time-Series Support**: Handle operational profiles over time
- **Automatic Power Balance**: Continuous load balancing across time points
- **Result Aggregation**: Comprehensive metrics collection

### 🔌 Power Management System (PMS)
- **Load-Dependent Control**: Automatic genset start/stop based on load
- **Multiple Strategies**: Configurable PMS algorithms
- **Efficiency Optimization**: Minimize fuel consumption
- **Blackout Prevention**: Ensure sufficient spinning reserve

### 📊 Results Analysis
- **Fuel Consumption**: Total and per-component fuel usage
- **Emissions**: CO2, NOx with FuelEU Maritime support
- **Energy Breakdown**: Propulsion vs. auxiliary energy
- **Operating Hours**: Runtime tracking for maintenance planning

### 🐍 Pure Python Development
- **Clean Python Modules**: Standard Python package structure
- **Easy to Understand**: Straightforward code organization
- **Simple to Extend**: Add new features easily
- **Type Hints**: Full type annotation support

## Installation

### From PyPI

```bash
pip install RunFeemsSim
```

This will install RunFeemsSim along with its dependencies (feems, MachSysS).

### From Source (Developers)

```bash
# Clone repository
git clone https://github.com/SINTEF/FEEMS.git
cd FEEMS

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e RunFEEMSSim/
```

## Quick Start

### Basic Simulation

```python
import numpy as np
import pandas as pd
from RunFeemsSim.machinery_calculation import MachineryCalculation
from feems.system_model import ElectricPowerSystem
from feems.fuel import FuelSpecifiedBy

# Create or load a FEEMS system
system = ElectricPowerSystem(...)

# Initialize machinery calculation
machinery_calc = MachineryCalculation(system)

# Define propulsion power time series
n_points = 1000
time_step_s = 1.0

propulsion_power = pd.DataFrame({
    'Propulsion Drive 1': 400 + 200 * np.random.random(n_points),
    'Propulsion Drive 2': 300 + 150 * np.random.random(n_points)
}, index=np.arange(0, n_points * time_step_s, time_step_s))

# Define auxiliary power
auxiliary_power = 100 + 50 * np.random.random(n_points)

# Run simulation
result = machinery_calc.calculate_machinery_system_output_from_propulsion_power_time_series(
    propulsion_power=propulsion_power,
    auxiliary_power_kw=auxiliary_power,
    fuel_specified_by=FuelSpecifiedBy.FUEL_EU_MARITIME
)

# Access results
print(f"Total fuel: {result.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction:.2f} kg")
print(f"Total CO2: {result.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel:.2f} kg")
print(f"Genset hours: {result.running_hours_genset_total_hr:.2f} hr")
```

### With Power Management System

```python
from RunFeemsSim.pms_basic import PMSBasic

# Create PMS with load-dependent genset control
pms = PMSBasic(
    load_threshold_start=0.75,  # Start additional genset at 75% load
    load_threshold_stop=0.40,   # Stop genset when load drops below 40%
    min_gensets_running=1       # Always keep at least 1 genset running
)

# Attach PMS to system
machinery_calc = MachineryCalculation(system, pms=pms)

# Run simulation with automatic genset management
result = machinery_calc.calculate_machinery_system_output_from_propulsion_power_time_series(
    propulsion_power=propulsion_power,
    auxiliary_power_kw=auxiliary_power,
    fuel_specified_by=FuelSpecifiedBy.FUEL_EU_MARITIME
)

# PMS automatically starts/stops gensets based on load
print(f"Genset start events: {pms.n_starts}")
print(f"Genset stop events: {pms.n_stops}")
```

## Core Components

### MachineryCalculation

Main class for running simulations.

```python
class MachineryCalculation:
    """High-level interface for FEEMS simulations."""

    def __init__(self, system: ElectricPowerSystem, pms: Optional[PMS] = None):
        """
        Initialize machinery calculation.

        Args:
            system: FEEMS ElectricPowerSystem
            pms: Optional Power Management System
        """
        ...

    def calculate_machinery_system_output_from_propulsion_power_time_series(
        self,
        propulsion_power: pd.DataFrame,
        auxiliary_power_kw: np.ndarray,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        integration_method: IntegrationMethod = IntegrationMethod.simpson,
        time_interval_s: float = 1.0
    ) -> ElectricSystemRunResult:
        """
        Run simulation from propulsion power time series.

        Args:
            propulsion_power: DataFrame with propulsion drive powers
                             Index: time in seconds
                             Columns: drive names
                             Values: power in kW
            auxiliary_power_kw: Auxiliary load time series (kW)
            fuel_specified_by: Emission calculation method
            integration_method: Time integration method
            time_interval_s: Time step in seconds

        Returns:
            ElectricSystemRunResult with comprehensive metrics
        """
        ...
```

### PMSBasic

Basic load-dependent Power Management System.

```python
class PMSBasic:
    """
    Basic PMS with load-dependent genset start/stop.

    Starts additional gensets when load exceeds threshold.
    Stops gensets when load drops below threshold.
    Maintains minimum number of running gensets.
    """

    def __init__(
        self,
        load_threshold_start: float = 0.85,
        load_threshold_stop: float = 0.40,
        min_gensets_running: int = 1,
        spinning_reserve: float = 0.20
    ):
        """
        Initialize PMS.

        Args:
            load_threshold_start: Start genset when load > this (0-1)
            load_threshold_stop: Stop genset when load < this (0-1)
            min_gensets_running: Minimum gensets to keep running
            spinning_reserve: Required spare capacity (0-1)
        """
        ...

    def determine_genset_status(
        self,
        current_load_kw: float,
        available_gensets: List[Genset],
        current_status: np.ndarray
    ) -> np.ndarray:
        """
        Determine which gensets should be running.

        Args:
            current_load_kw: Total system load
            available_gensets: List of all gensets
            current_status: Current on/off status

        Returns:
            Updated status array
        """
        ...
```

## Power Management Strategies

### Strategy 1: Load-Dependent Control

Automatically start/stop gensets based on load:

```python
pms = PMSBasic(
    load_threshold_start=0.80,  # Start at 80% of running capacity
    load_threshold_stop=0.35,   # Stop when below 35% of capacity
    min_gensets_running=1       # Always keep 1 running
)
```

**Behavior:**
- Load increases → Start additional gensets when threshold exceeded
- Load decreases → Stop gensets when load drops
- Prevents frequent switching with hysteresis
- Maintains spinning reserve

### Strategy 2: Time-Based Control

Control gensets based on time of day or operational mode:

```python
# Define mode schedule
mode_schedule = pd.DataFrame({
    'time': [0, 21600, 43200, 64800],      # 0h, 6h, 12h, 18h
    'mode': ['port', 'transit', 'transit', 'port']
})

# Different genset configurations per mode
genset_config = {
    'port': [True, False, False],      # 1 genset
    'transit': [True, True, False],    # 2 gensets
    'maneuvering': [True, True, True]  # 3 gensets
}
```

### Strategy 3: Efficiency Optimization

Run gensets at optimal load points:

```python
pms = PMSBasic(
    load_threshold_start=0.75,  # Target 75% load on running gensets
    load_threshold_stop=0.40,
    min_gensets_running=1
)
```

**Benefits:**
- Operates gensets in efficient range (70-85%)
- Minimizes fuel consumption
- Reduces emissions

## Development Workflow

RunFeemsSim follows standard Python development practices.

### Package Structure

```
RunFEEMSSim/
├── RunFeemsSim/
│   ├── __init__.py
│   ├── machinery_calculation.py     # Core simulation logic
│   ├── pms_basic.py                 # Power Management System
│   └── utils.py                     # Utility functions
├── tests/
│   ├── test_machinery_calculation.py
│   └── test_pms_basic.py
├── README.md
└── pyproject.toml
```

### Development Cycle

1. **Edit Python Files**: Make changes directly in `.py` files
   ```bash
   # Edit source files in your preferred editor/IDE
   vim RunFeemsSim/machinery_calculation.py
   ```

2. **Run Tests**: Test your changes
   ```bash
   uv run pytest RunFEEMSSim/tests/
   ```

3. **Lint and Format**: Ensure code quality
   ```bash
   uv run ruff check RunFEEMSSim/
   uv run ruff format RunFEEMSSim/
   ```

4. **Type Check**: Validate type hints (optional)
   ```bash
   uv run mypy RunFeemsSim/
   ```

5. **Build**: Create distribution packages
   ```bash
   cd RunFEEMSSim
   uv build
   ```

### Why Pure Python?

- **Simplicity**: Standard Python package structure everyone knows
- **IDE Support**: Full autocomplete, refactoring, and debugging
- **Type Safety**: Use mypy and type hints effectively
- **Flexibility**: Easy integration with any Python tooling
- **Transparency**: Source code is exactly what gets executed

## Use Cases

### 1. Route Planning

Estimate fuel consumption for planned voyages:

```python
# Load route profile
route_profile = pd.read_csv('route_profile.csv')  # time, speed, power

# Run simulation
machinery_calc = MachineryCalculation(system)
result = machinery_calc.calculate_machinery_system_output_from_propulsion_power_time_series(
    propulsion_power=route_profile[['power']],
    auxiliary_power_kw=route_profile['aux_power'].values
)

# Estimate fuel for voyage
fuel_kg = result.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction
distance_nm = route_profile['distance'].sum()
fuel_per_nm = fuel_kg / distance_nm
```

### 2. Emissions Reporting

Generate IMO/EU compliance reports:

```python
# Annual operation
annual_result = machinery_calc.calculate_machinery_system_output_from_propulsion_power_time_series(
    propulsion_power=annual_profile,
    auxiliary_power_kw=annual_aux,
    fuel_specified_by=FuelSpecifiedBy.FUEL_EU_MARITIME
)

# FuelEU Maritime compliance
well_to_wake_co2 = annual_result.co2_emission_total_kg.well_to_wake_kg_or_gco2eq_per_gfuel
energy_consumed = annual_result.energy_consumption_propulsion_total_mj
ghg_intensity = well_to_wake_co2 / (energy_consumed / 1000)  # gCO2eq/MJ

print(f"GHG Intensity: {ghg_intensity:.2f} gCO2eq/MJ")
```

### 3. System Comparison

Compare different configurations:

```python
# Scenario 1: Conventional (3 gensets)
system_conventional = create_conventional_system()
calc_conv = MachineryCalculation(system_conventional)
result_conv = calc_conv.calculate_machinery_system_output_from_propulsion_power_time_series(...)

# Scenario 2: Hybrid (2 gensets + battery)
system_hybrid = create_hybrid_system()
calc_hybrid = MachineryCalculation(system_hybrid)
result_hybrid = calc_hybrid.calculate_machinery_system_output_from_propulsion_power_time_series(...)

# Compare
fuel_savings = result_conv.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction - \
               result_hybrid.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction
savings_pct = (fuel_savings / result_conv.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction) * 100

print(f"Hybrid system saves {fuel_savings:.1f} kg ({savings_pct:.1f}%)")
```

### 4. PMS Optimization

Tune PMS parameters:

```python
import matplotlib.pyplot as plt

# Test different thresholds
thresholds = [0.70, 0.75, 0.80, 0.85]
results = {}

for threshold in thresholds:
    pms = PMSBasic(load_threshold_start=threshold)
    calc = MachineryCalculation(system, pms=pms)
    result = calc.calculate_machinery_system_output_from_propulsion_power_time_series(...)
    results[threshold] = result

# Plot fuel consumption vs. threshold
fuel_consumptions = [r.multi_fuel_consumption_total_kg.fuels[0].mass_or_mass_fraction
                     for r in results.values()]
plt.plot(thresholds, fuel_consumptions)
plt.xlabel('Load Threshold')
plt.ylabel('Fuel Consumption (kg)')
plt.title('PMS Threshold Optimization')
plt.show()
```

## Package Structure

```
RunFEEMSSim/
├── RunFeemsSim/
│   ├── __init__.py
│   ├── machinery_calculation.py     # Core simulation interface
│   ├── pms_basic.py                 # Power Management System
│   └── utils.py                     # Helper utilities
├── tests/
│   ├── test_machinery_calculation.py
│   └── test_pms_basic.py
├── docs/                            # Documentation
├── README.md
└── pyproject.toml
```

## Requirements

- Python ≥ 3.10
- pandas
- numpy
- MachSysS
- feems

## Related Packages

- **feems**: Core FEEMS library
- **MachSysS**: Data structures and protobuf definitions

## Contributing

Contributions welcome! See `CONTRIBUTING.md`.

### Development Setup

```bash
git clone https://github.com/SINTEF/FEEMS.git
cd FEEMS
uv sync
```

### Making Changes

1. **Edit Python files** directly in `RunFeemsSim/`
2. **Add tests** in `tests/`
3. **Run tests**: `uv run pytest RunFEEMSSim/tests/`
4. **Lint code**: `uv run ruff check RunFEEMSSim/`
5. **Format code**: `uv run ruff format RunFEEMSSim/`
6. **Type check** (optional): `uv run mypy RunFeemsSim/`

### Running Tests

```bash
# All tests
uv run pytest RunFEEMSSim/tests/

# Specific test file
uv run pytest RunFEEMSSim/tests/test_machinery_calculation.py

# With coverage
uv run pytest --cov=RunFeemsSim RunFEEMSSim/tests/

# Verbose output
uv run pytest -v RunFEEMSSim/tests/
```

### Code Quality

```bash
# Check for issues
uv run ruff check RunFEEMSSim/

# Auto-fix issues
uv run ruff check --fix RunFEEMSSim/

# Format code
uv run ruff format RunFEEMSSim/

# Type checking
uv run mypy RunFeemsSim/
```

## License

Licensed under the Apache License 2.0 - see LICENSE file for details.

## Citation

```bibtex
@software{runfeemssim2024,
  title = {RunFeemsSim: FEEMS Simulation Runner},
  author = {Yum, Kevin Koosup and contributors},
  year = {2024},
  url = {https://github.com/SINTEF/FEEMS},
    version = {0.3.1}
}
```

## Support

- **Issues**: [GitHub Issues](https://github.com/SINTEF/FEEMS/issues)
- **Documentation**: [https://kevinkoosup.yum@sintef.no.github.io/RunFeemsSim/](https://kevinkoosup.yum@sintef.no.github.io/RunFeemsSim/)
- **Email**: kevinkoosup.yum@sintef.no

## Acknowledgments

Developed by SINTEF Ocean as part of the FEEMS ecosystem for simplified marine power system simulation.
