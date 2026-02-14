# MachSysS - Machinery System Structure

[![PyPI version](https://badge.fury.io/py/MachSysS.svg)](https://badge.fury.io/py/MachSysS)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

`MachSysS` provides Protocol Buffer definitions, data structures, and conversion utilities for the FEEMS ecosystem. It enables standardized data exchange, serialization, and interoperability across different tools and programming languages.

## Features

### 🔄 Data Exchange
- **Protocol Buffer Schemas**: Well-defined data structures for machinery systems
- **Language Independence**: Use in Python, C++, Java, Go, and more
- **Version Control Friendly**: Text-based proto definitions
- **Compact Binary Format**: Efficient storage and transmission

### 🔧 Conversion Utilities
- **FEEMS ↔ Protobuf**: Bidirectional conversion between FEEMS objects and protobuf messages
- **Result Serialization**: Save simulation results for analysis and reporting
- **System Configuration**: Load/save complete system configurations
- **Time-Series Data**: Handle time-series results with pandas integration

### 📊 Data Structures
- **System Configuration**: Complete machinery system layout
- **Component Specifications**: Engines, generators, converters, loads
- **Simulation Results**: Fuel consumption, emissions, energy flows
- **Time-Series Profiles**: Operational data over time

## Installation

### From PyPI

```bash
pip install MachSysS
```

### From Source (Developers)

```bash
# Clone repository
git clone https://github.com/SINTEF/FEEMS.git
cd FEEMS

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e machinery-system-structure/
```

## Quick Start

### Save a FEEMS System to Protobuf

```python
from feems.system_model import ElectricPowerSystem
from MachSysS.convert_to_protobuf import convert_electric_system_to_protobuf_machinery_system

# Create or load a FEEMS system
system = ElectricPowerSystem(...)

# Convert to protobuf
system_pb = convert_electric_system_to_protobuf_machinery_system(system)

# Save to file
with open("system_config.pb", "wb") as f:
    f.write(system_pb.SerializeToString())
```

### Load a System from Protobuf

```python
from MachSysS.system_structure_pb2 import MachinerySystem
from MachSysS.convert_to_feems import convert_proto_propulsion_system_to_feems

# Load from file
with open("system_config.pb", "rb") as f:
    system_pb = MachinerySystem()
    system_pb.ParseFromString(f.read())

# Convert to FEEMS system
feems_system = convert_proto_propulsion_system_to_feems(system_pb)

# Use with FEEMS
feems_system.do_power_balance_calculation()
```

### Save Simulation Results

```python
from MachSysS.convert_feems_result_to_proto import convert_feems_result_to_proto

# Run simulation
result = system.get_fuel_energy_consumption_running_time()

# Convert results to protobuf
result_pb = convert_feems_result_to_proto(result, system)

# Save to file
with open("simulation_results.pb", "wb") as f:
    f.write(result_pb.SerializeToString())
```

### Convert Results to Pandas DataFrames

```python
from MachSysS.convert_proto_timeseries import convert_proto_power_timeseries_to_df

# Load results
from MachSysS.feems_result_pb2 import FeemsResult
with open("simulation_results.pb", "rb") as f:
    result_pb = FeemsResult()
    result_pb.ParseFromString(f.read())

# Convert to DataFrame
df = convert_proto_power_timeseries_to_df(result_pb.power_timeseries)

# Analyze with pandas
print(df.describe())
df.plot()
```

## Protocol Buffer Schemas

### System Structure (`system_structure.proto`)

Defines the complete machinery system configuration:

```protobuf
message MachinerySystem {
  string name = 1;
  repeated Component components = 2;
  repeated Connection connections = 3;
  repeated Switchboard switchboards = 4;
  repeated BusTieBreaker bus_tie_breakers = 5;
}

message Component {
  string id = 1;
  string name = 2;
  ComponentType type = 3;
  double rated_power_kw = 4;
  double rated_speed_rpm = 5;
  PerformanceCurve performance_curve = 6;
  // ...
}
```

### Simulation Results (`feems_result.proto`)

Stores simulation outputs:

```protobuf
message FeemsResult {
  string system_id = 1;
  double duration_s = 2;
  FuelConsumption total_fuel_consumption = 3;
  Emissions total_emissions = 4;
  EnergyConsumption energy_consumption = 5;
  repeated ComponentResult component_results = 6;
  PowerTimeSeries power_timeseries = 7;
}
```

### Time-Series Data (`gymir_result.proto`)

Alternative format for time-series results:

```protobuf
message PowerTimeSeries {
  repeated double timestamp_s = 1;
  map<string, PowerProfile> component_powers = 2;
}

message PowerProfile {
  repeated double power_kw = 1;
  repeated double efficiency = 2;
}
```

## Conversion API

### System Conversion

#### FEEMS → Protobuf

```python
from MachSysS.convert_to_protobuf import (
    convert_electric_system_to_protobuf_machinery_system,
    convert_component_to_protobuf
)

# Convert complete system
system_pb = convert_electric_system_to_protobuf_machinery_system(feems_system)

# Convert individual component
component_pb = convert_component_to_protobuf(genset)
```

#### Protobuf → FEEMS

```python
from MachSysS.convert_to_feems import (
    convert_proto_propulsion_system_to_feems,
    convert_proto_component_to_feems
)

# Convert complete system
feems_system = convert_proto_propulsion_system_to_feems(system_pb)

# Convert individual component
component = convert_proto_component_to_feems(component_pb)
```

### Results Conversion

```python
from MachSysS.convert_feems_result_to_proto import (
    convert_feems_result_to_proto,
    convert_fuel_consumption_to_proto,
    convert_emissions_to_proto
)

# Convert complete result
result_pb = convert_feems_result_to_proto(feems_result, system)

# Convert individual metrics
fuel_pb = convert_fuel_consumption_to_proto(fuel_consumption)
emissions_pb = convert_emissions_to_proto(emissions)
```

### Time-Series Conversion

```python
from MachSysS.convert_proto_timeseries import (
    convert_proto_power_timeseries_to_df,
    convert_df_to_proto_power_timeseries
)

# Protobuf → DataFrame
df = convert_proto_power_timeseries_to_df(power_timeseries_pb)

# DataFrame → Protobuf
power_timeseries_pb = convert_df_to_proto_power_timeseries(df)
```

## Use Cases

### 1. Data Archiving
- Save system configurations for version control
- Archive simulation results for compliance
- Store reference designs

### 2. Tool Integration
- Exchange data with other simulation tools
- Import/export to CAD software
- Connect to databases

### 3. API Development
- Build REST APIs with protobuf serialization
- gRPC services for remote simulation
- Microservices architecture

### 4. Cross-Language Support
- Python simulation, C++ visualization
- Java backend, Python frontend
- Go microservices with Python analysis

### 5. Reporting
- Generate standardized reports
- Export to business intelligence tools
- Regulatory compliance submissions

## Package Structure

```
machinery-system-structure/
├── MachSysS/
│   ├── __init__.py
│   ├── system_structure_pb2.py     # Generated from .proto
│   ├── system_structure_pb2.pyi    # Type stubs
│   ├── feems_result_pb2.py         # Generated from .proto
│   ├── gymir_result_pb2.py         # Generated from .proto
│   ├── convert_to_protobuf.py      # FEEMS → Protobuf
│   ├── convert_to_feems.py         # Protobuf → FEEMS
│   ├── convert_feems_result_to_proto.py
│   └── convert_proto_timeseries.py
├── proto/
│   ├── system_structure.proto
│   ├── feems_result.proto
│   └── gymir_result.proto
├── tests/
├── compile_proto.sh                 # Protobuf compilation script
└── README.md
```

## Development

### Prerequisites

- Python ≥ 3.10
- Protocol Buffer compiler (`protoc`) for regenerating Python bindings

#### Install protoc

**macOS:**
```bash
brew install protobuf
```

**Ubuntu/Debian:**
```bash
apt-get install protobuf-compiler
```

**Windows:**
Download from [GitHub Releases](https://github.com/protocolbuffers/protobuf/releases)

### Workspace Setup

```bash
# Clone and sync
git clone https://github.com/SINTEF/FEEMS.git
cd FEEMS
uv sync
```

### Regenerating Protobuf Files

When you modify `.proto` files:

```bash
cd machinery-system-structure
./compile_proto.sh
```

This script:
1. Compiles `.proto` files to Python
2. Generates type stubs (`.pyi` files)
3. Fixes imports for relative module references

**Manual compilation:**
```bash
cd machinery-system-structure
protoc -I=proto --python_out=MachSysS proto/*.proto --pyi_out=MachSysS
```

### Running Tests

```bash
# All tests
uv run pytest machinery-system-structure/tests/

# Specific test file
uv run pytest machinery-system-structure/tests/test_convert_to_protobuf.py

# With coverage
uv run pytest --cov=MachSysS machinery-system-structure/tests/
```

### Code Quality

```bash
# Linting
uv run ruff check machinery-system-structure/

# Formatting
uv run ruff format machinery-system-structure/
```

## Requirements

- Python ≥ 3.10
- protobuf >= 5.29.6, < 6
- feems (for conversion utilities)
- pandas (for time-series conversion)

## Related Packages

- **feems**: Core FEEMS library for marine power system modeling
- **RunFeemsSim**: High-level simulation interface with PMS logic

## Contributing

Contributions welcome! See `CONTRIBUTING.md` for guidelines.

When adding new proto definitions:
1. Edit `.proto` files in `proto/`
2. Run `./compile_proto.sh`
3. Add conversion utilities in `MachSysS/`
4. Write tests in `tests/`
5. Update documentation

## License

Licensed under the Apache License 2.0 - see LICENSE file for details.

## Citation

```bibtex
@software{machsyss2024,
  title = {MachSysS: Machinery System Structure},
  author = {Yum, Kevin Koosup and contributors},
  year = {2024},
  url = {https://github.com/SINTEF/FEEMS}
}
```

## Support

- **Issues**: [GitHub Issues](https://github.com/SINTEF/FEEMS/issues)
- **Documentation**: [https://keviny.github.io/MachSysS/](https://keviny.github.io/MachSysS/)
- **Email**: kevinkoosup.yum@sintef.no

## Acknowledgments

Developed by SINTEF Ocean as part of the FEEMS ecosystem for standardized marine power system data exchange.
