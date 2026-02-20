# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a monorepo for the FEEMS (Fuel, Emissions, Energy Calculation for Machinery System) ecosystem, managed by `uv` workspaces. It contains three interdependent packages for modeling and simulating marine power and propulsion systems.

### Packages

- **`feems/`**: Core library for fuel consumption, emissions, and energy balance calculations
- **`machinery-system-structure/`** (MachSysS): Protocol Buffer definitions and data conversion utilities for system interchange
- **`RunFEEMSSim/`**: Simulation runner with Power Management System (PMS) logic, uses nbdev (notebook-driven development)

## Development Commands

### Setup
```bash
uv sync  # Install all workspace packages and dependencies
```

### Testing
```bash
uv run pytest                                  # Run all tests
uv run pytest feems/tests/                     # Test specific package
uv run pytest machinery-system-structure/tests/
uv run pytest RunFEEMSSim/tests/
```

### Linting and Formatting
```bash
uv run ruff check     # Check code style
uv run ruff format    # Format code
```

Ruff is configured with:
- Line length: 120
- Target: Python 3.10+
- Excludes: `*_pb2.py`, `*_pb2.pyi`, `_modidx.py`
- Per-file ignores for notebooks (F811, F403, E501)

### Building Packages
```bash
cd <package-directory>
uv build
```

### Protocol Buffer Compilation (MachSysS)
When modifying `.proto` files in `machinery-system-structure/proto/`:
```bash
cd machinery-system-structure
./compile_proto.sh
```

This generates Python bindings (`*_pb2.py` and `*_pb2.pyi`) and fixes imports for relative module references.

### nbdev Workflow (RunFEEMSSim)
RunFEEMSSim uses notebook-driven development. The source of truth is the Jupyter notebooks:
- `00_machinery_calculation.ipynb` → `RunFeemsSim/machinery_calculation.py`
- `01_pms_basic.ipynb` → `RunFeemsSim/pms_basic.py`

**Important**: Edit the notebooks, not the generated Python files. After modifying notebooks, regenerate modules:
```bash
nbdev_export  # Regenerates Python modules from notebooks
```

## Architecture

### FEEMS Core (`feems/`)
Component-based modeling framework for marine power systems. Supports:
- Hybrid/Conventional Diesel Electric Propulsion
- Hybrid Propulsion with PTI/PTO
- Mechanical Propulsion with Separate Electric Power System

**Key modules**:
- `components_model/component_base.py`: Base classes and component interfaces
- `components_model/component_electric.py`: Electric components (generators, batteries, shore power, power buses, converters, switchboards)
- `components_model/component_mechanical.py`: Mechanical components (engines, gearboxes, propellers, shafts, PTI/PTO)
- `components_model/node.py`: Power distribution nodes (electrical and mechanical buses) with load balancing
- `system_model.py`: System-level modeling, connects components into a complete power system
- `fuel.py`: Fuel consumption and emissions calculations based on component loads
- `runsimulation.py`: Time-series simulation orchestration
- `simulation_interface.py`: External interface for running simulations

**Calculation flow**:
1. Configure system from single-line diagram using component library
2. Given operational control inputs and consumer power loads, perform power balance calculation
3. Determine loads on power producers (generators, engines)
4. Calculate fuel consumption and emissions

### MachSysS (`machinery-system-structure/`)
Data interchange layer using Protocol Buffers for serialization.

**Key modules**:
- `proto/system_structure.proto`: System configuration schema
- `proto/feems_result.proto`: Simulation result schema
- `proto/gymir_result.proto`: Alternative result format
- `convert_to_protobuf.py`: FEEMS model → Protobuf
- `convert_to_feems.py`: Protobuf → FEEMS model
- `convert_feems_result_to_proto.py`: FEEMS simulation results → Protobuf
- `convert_proto_timeseries.py`: Timeseries result conversion to Pandas DataFrames

### RunFeemsSim (`RunFEEMSSim/`)
Higher-level simulation interface with power management logic.

**Key modules**:
- `machinery_calculation.py`: Simulation runner that orchestrates FEEMS calculations
- `pms_basic.py`: Basic Power Management System with load-dependent genset start/stop logic

**Dependencies**: RunFeemsSim → MachSysS (for data structures)

## Development Workflow Rule

**Everything starts from the backlog** — except bug fixes and hot fixes, which may proceed directly.

| Work type       | Backlog required? |
|-----------------|-------------------|
| Feature         | ✅ Yes             |
| Refactor        | ✅ Yes             |
| Documentation   | ✅ Yes             |
| Bug fix         | ❌ No              |
| Hot fix         | ❌ No              |

1. Create a backlog item in `docs/backlog/` using the `write-backlog` skill (`.github/skills/write-backlog/`)
2. **Immediately open a GitHub issue** with the same title and record the issue number in the backlog file
3. Define acceptance criteria before moving to Plan
4. `git checkout main && git pull` then `git checkout -b feature/issue-{id}-{slug}`
5. Follow the PDCA flow: `backlog/ → docs/01-plan/ → docs/02-design/ → implementation → docs/03-analysis/ → docs/04-report/`
6. **Commit after each phase's report** if the feature is divided into phases
7. When the feature is complete, `git push` and open a Pull Request against `main`

See `docs/README.md` for the full documentation structure.

## Important Notes

- Python version: 3.10-3.12 supported
- The workspace uses `uv` for dependency management and virtual environment handling
- All packages are installed in editable mode during development via `uv sync`
- Generated files (`*_pb2.py`, `*_pb2.pyi`, `_modidx.py`) should never be manually edited
- When working with RunFEEMSSim, always edit source notebooks, not generated `.py` files
