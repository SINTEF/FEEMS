# FEEMS Workspace

This repository is a monorepo containing the FEEMS ecosystem packages. It uses `uv` for dependency management and workspace handling.

## Packages

- **`feems`**: The core Fuel, Emissions, Energy Calculation for Machinery System library.
- **`MachSysS`** (in `machinery-system-structure/`): Machinery System Structure. Contains Protocol Buffer definitions and utilities for data exchange.
- **`RunFeemsSim`**: A library for running FEEMS simulations and managing power management system (PMS) logic.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) must be installed.
- Python 3.10 or higher.

## Development Setup

1. **Clone the repository** (if you haven't already).

2. **Sync the environment**:
   Run the following command in the root directory completely set up the virtual environment with all workspace packages and dependencies:
   ```bash
   uv sync
   ```

## Building and Testing

### Running Tests
To run tests across all packages (where configured):
```bash
uv run pytest
```

To run tests for a specific package (e.g., `MachSysS`):
```bash
uv run pytest machinery-system-structure/tests/
```

### Building Packages
You can build individual packages using `uv build` within their respective directories.

```bash
cd machinery-system-structure
uv build
```

## Directory Structure

- `feems/`: Core library source.
- `machinery-system-structure/`: `MachSysS` package source and Proto definitions.
- `RunFEEMSSim/`: `RunFeemsSim` package source (nbdev-based).
