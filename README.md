# FEEMS Ecosystem - Workspace

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/managed%20by-uv-blue)](https://docs.astral.sh/uv/)
[![License](https://img.shields.io/badge/license-MIT%2FApache--2.0-blue.svg)](LICENSE)

This is the monorepo for the **FEEMS (Fuel, Emissions, Energy Calculation for Machinery System)** ecosystem - a comprehensive suite of packages for modeling, simulating, and analyzing marine power and propulsion systems.

## 🎯 Overview

The FEEMS ecosystem enables accurate calculation of fuel consumption, emissions, and energy balance for complex marine machinery configurations. It supports vessel design, operational planning, emissions compliance, and performance optimization.

## 📦 Packages

### Core Packages

| Package | Version | Description | License |
|---------|---------|-------------|---------|
| **[feems](feems/)** | 0.11.13 | Core modeling framework for marine power systems | MIT |
| **[MachSysS](machinery-system-structure/)** | 0.7.7 | Protocol Buffer definitions and data conversion | Apache-2.0 |
| **[RunFeemsSim](RunFEEMSSim/)** | 0.2.6 | High-level simulation interface with PMS logic | Apache-2.0 |

### Package Relationships

```
┌─────────────────────────────────────────────────────┐
│                  User Applications                   │
│        (Route Planning, Emissions Reporting)         │
└──────────────────────┬──────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
    ┌──────▼──────┐         ┌─────▼────────┐
    │ RunFeemsSim │         │  MachSysS    │
    │  (v0.2.6)   │◄────────┤  (v0.7.7)    │
    │ Simulation  │         │ Data Exchange│
    └──────┬──────┘         └─────┬────────┘
           │                       │
           │      ┌───────────────┘
           │      │
        ┌──▼──────▼──┐
        │   feems     │
        │  (v0.11.13) │
        │ Core Engine │
        └─────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python** ≥ 3.10, < 3.13
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip
- **protoc** (optional, only needed for MachSysS development)

### Installation

#### For Users (Individual Packages)

Install packages as needed from PyPI:

```bash
# Core functionality
pip install feems

# With data serialization
pip install feems MachSysS

# Complete suite with simulation interface
pip install feems MachSysS RunFeemsSim
```

#### For Developers (Full Workspace)

Clone and setup the complete workspace:

```bash
# Clone repository
git clone https://github.com/SINTEF/FEEMS.git
cd FEEMS

# Setup with uv (recommended)
uv sync

# Or with pip
pip install -e feems/ -e machinery-system-structure/ -e RunFEEMSSim/
```

This installs all packages in editable mode with development dependencies.

### Verify Installation

```bash
# Check installations
python -c "import feems; print(f'FEEMS {feems.__version__}')"
python -c "import MachSysS; print('MachSysS OK')"
python -c "import RunFeemsSim; print('RunFeemsSim OK')"

# Run tests
uv run pytest
```

## 📚 Documentation

### Package Documentation

Each package has comprehensive documentation:

- **[feems/README.md](feems/README.md)** - Core library documentation
  - [feems/API_REFERENCE.md](feems/API_REFERENCE.md) - Complete API reference
- **[machinery-system-structure/README.md](machinery-system-structure/README.md)** - Protocol Buffer and data exchange
- **[RunFEEMSSim/README.md](RunFEEMSSim/README.md)** - Simulation interface and PMS

### Examples

Comprehensive examples with detailed explanations:

- **[examples/00_Basic_Example.ipynb](examples/00_Basic_Example.ipynb)** - Introduction to FEEMS
- **[examples/01_Running_simulation.ipynb](examples/01_Running_simulation.ipynb)** - Time-series simulations
- **[examples/02_Shore_Power_Example.ipynb](examples/02_Shore_Power_Example.ipynb)** - Shore power integration
- **[examples/README.md](examples/README.md)** - Examples overview and guide

### Guides

- **[CLAUDE.md](CLAUDE.md)** - Development guide for Claude Code
- **[examples/SHORE_POWER_GUIDE.md](examples/SHORE_POWER_GUIDE.md)** - Shore power detailed guide
- **[DOCUMENTATION_SUMMARY.md](DOCUMENTATION_SUMMARY.md)** - Documentation overview

### CHANGELOGs

- [feems/CHANGELOG.md](feems/CHANGELOG.md)
- [machinery-system-structure/CHANGELOG.md](machinery-system-structure/CHANGELOG.md)
- [RunFEEMSSim/CHANGELOG.md](RunFEEMSSim/CHANGELOG.md)

## 🛠️ Development

### Workspace Structure

```
FEEMS/
├── feems/                          # Core library
│   ├── feems/                      # Source code
│   ├── tests/                      # Tests
│   ├── README.md                   # Documentation
│   ├── API_REFERENCE.md            # API docs
│   ├── CHANGELOG.md                # Version history
│   └── pyproject.toml              # Package config
│
├── machinery-system-structure/      # MachSysS
│   ├── MachSysS/                   # Source code
│   ├── proto/                      # Protocol Buffer definitions
│   ├── tests/                      # Tests
│   ├── compile_proto.sh            # Protobuf compiler script
│   ├── README.md                   # Documentation
│   ├── CHANGELOG.md                # Version history
│   └── pyproject.toml              # Package config
│
├── RunFEEMSSim/                    # RunFeemsSim
│   ├── RunFeemsSim/                # Source code
│   ├── tests/                      # Tests
│   ├── README.md                   # Documentation
│   ├── CHANGELOG.md                # Version history
│   ├── MIGRATION_FROM_NBDEV.md     # nbdev migration guide
│   └── pyproject.toml              # Package config
│
├── examples/                        # Examples and tutorials
│   ├── *.ipynb                     # Jupyter notebooks
│   ├── *.py                        # Python scripts
│   ├── README.md                   # Examples guide
│   └── data/                       # Example data
│
├── pyproject.toml                   # Workspace configuration
├── uv.lock                         # Dependency lock file
├── README.md                       # This file
└── CLAUDE.md                       # Development guide
```

### Development Workflow

#### 1. Setup Development Environment

```bash
# Initial setup
git clone https://github.com/SINTEF/FEEMS.git
cd FEEMS
uv sync

# Activate virtual environment (if needed)
source .venv/bin/activate  # Unix/macOS
# or
.venv\Scripts\activate     # Windows
```

#### 2. Making Changes

```bash
# Edit code in your preferred editor
vim feems/feems/system_model.py

# Run tests for changed package
uv run pytest feems/tests/

# Run all tests
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .
```

#### 3. Testing

```bash
# Run all tests
uv run pytest

# Run tests for specific package
uv run pytest feems/tests/
uv run pytest machinery-system-structure/tests/
uv run pytest RunFEEMSSim/tests/

# Run with coverage
uv run pytest --cov=feems --cov=MachSysS --cov=RunFeemsSim

# Run specific test file
uv run pytest feems/tests/test_system_model.py

# Run specific test
uv run pytest feems/tests/test_system_model.py::test_power_balance
```

#### 4. Code Quality

```bash
# Check code quality
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Type checking (if mypy configured)
uv run mypy feems/
```

#### 5. Building Packages

```bash
# Build specific package
cd feems
uv build

# Build all packages
for dir in feems machinery-system-structure RunFEEMSSim; do
    (cd $dir && uv build)
done
```

#### 6. Documentation

```bash
# Edit documentation
vim feems/README.md

# Preview examples (Jupyter)
uv run jupyter lab examples/

# Generate docs (if using Sphinx)
cd docs
uv run make html
```

### Common Tasks

#### Update Dependencies

```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv add pandas@latest --package feems
```

#### Add New Dependency

```bash
# Add to specific package
cd feems
uv add scipy

# Add dev dependency
uv add --dev pytest-cov
```

#### Regenerate Protocol Buffers (MachSysS)

```bash
cd machinery-system-structure
./compile_proto.sh
```

## 🧪 Testing Strategy

### Test Organization

- **Unit Tests**: Test individual components and functions
- **Integration Tests**: Test package interactions
- **System Tests**: Test complete workflows

### Running Tests

```bash
# Fast: Run only modified tests
uv run pytest --lf

# Complete: Run all tests with coverage
uv run pytest --cov --cov-report=html

# Verbose: Detailed output
uv run pytest -v

# Parallel: Speed up with multiple processes
uv run pytest -n auto
```

### Test Coverage Goals

- **feems**: > 80% coverage
- **MachSysS**: > 70% coverage
- **RunFeemsSim**: > 75% coverage

## 📊 Code Quality

### Linting and Formatting

The workspace uses **ruff** for linting and formatting:

```bash
# Check all packages
uv run ruff check .

# Format all packages
uv run ruff format .

# Check specific package
uv run ruff check feems/
```

### Configuration

Ruff is configured in `pyproject.toml`:
- Line length: 120
- Target: Python 3.10+
- Excludes: Generated files (`*_pb2.py`, `*_pb2.pyi`, `_modidx.py`)

### Type Checking

Optional but recommended:

```bash
uv run mypy feems/
uv run mypy RunFeemsSim/
```

## 🚢 Publishing

### Pre-Publication Checklist

- [ ] All tests pass
- [ ] Code is formatted and linted
- [ ] Documentation is updated
- [ ] CHANGELOGs are updated
- [ ] Version numbers are bumped
- [ ] Examples work correctly

### Build Packages

```bash
# Build each package
cd feems && uv build && cd ..
cd machinery-system-structure && uv build && cd ..
cd RunFEEMSSim && uv build && cd ..
```

### Test in Clean Environment

```bash
# Create clean environment
uv venv test-env
source test-env/bin/activate

# Install built packages
pip install feems/dist/*.whl
pip install machinery-system-structure/dist/*.whl
pip install RunFEEMSSim/dist/*.whl

# Test imports
python -c "import feems; import MachSysS; import RunFeemsSim"

# Deactivate and remove
deactivate
rm -rf test-env
```

### Publish to PyPI

```bash
# Test PyPI first (recommended)
uv publish --repository testpypi feems/dist/*
uv publish --repository testpypi machinery-system-structure/dist/*
uv publish --repository testpypi RunFEEMSSim/dist/*

# Verify on Test PyPI
pip install --index-url https://test.pypi.org/simple/ feems

# If all looks good, publish to PyPI
uv publish feems/dist/*
uv publish machinery-system-structure/dist/*
uv publish RunFEEMSSim/dist/*
```

## 🤝 Contributing

We welcome contributions! Please see individual package documentation for specific guidelines.

### Getting Started

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Contribution Guidelines

- Follow existing code style (enforced by ruff)
- Add tests for new features
- Update documentation
- Keep commits atomic and well-described
- Ensure all tests pass before submitting PR

### Code Review Process

1. Automated checks run (tests, linting)
2. Maintainers review code
3. Address feedback
4. Merge when approved

## 📄 License

- **feems**: MIT License
- **MachSysS**: Apache License 2.0
- **RunFeemsSim**: Apache License 2.0

See individual package LICENSE files for details.

## 🆘 Support

### Getting Help

- **Documentation**: Start with package READMEs and examples
- **Issues**: [GitHub Issues](https://github.com/SINTEF/FEEMS/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SINTEF/FEEMS/discussions)
- **Email**:
  - FEEMS core: kevin.koosup.yum@gmail.com
  - MachSysS/RunFeemsSim: kevinkoosup.yum@sintef.no

### Reporting Issues

When reporting issues, please include:
- Package and version
- Python version
- Operating system
- Minimal reproducible example
- Expected vs actual behavior

### Feature Requests

We welcome feature requests! Please:
- Check existing issues first
- Describe the use case
- Explain expected behavior
- Consider contributing the feature

## 🏆 Acknowledgments

The FEEMS ecosystem is developed and maintained by **SINTEF Ocean**, Norway's leading marine technology research institute.

### About SINTEF Ocean

SINTEF Ocean conducts research and innovation within maritime technology, ocean space technology, and marine environment and operations. The institute works on:
- Decarbonization of maritime transport
- Alternative marine fuels (hydrogen, ammonia, methanol)
- Hybrid and electric propulsion systems
- Energy efficiency and emissions reduction
- Digital twins and simulation-based design

### Research Applications

FEEMS has been applied in various research projects including:
- Design and optimization of hydrogen fuel cell powered ferries
- FuelEU Maritime regulation compliance analysis
- Hybrid propulsion system sizing and optimization
- Total cost of ownership (TCO) analysis for alternative fuel vessels
- Operational performance prediction and validation

### Contributors

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for the list of contributors.

### Funding

This work has been supported by various research projects and industry collaborations focused on sustainable maritime transport.

## 📈 Project Status

- **feems**: Stable (v0.11.13)
- **MachSysS**: Stable (v0.7.7)
- **RunFeemsSim**: Pre-Alpha (v0.2.6)

### Roadmap

See individual package CHANGELOGs and GitHub milestones for planned features.

## 📚 Citation

If you use FEEMS in your research or publications, please cite:

**Software:**
```bibtex
@software{feems2024,
  title = {FEEMS: Fuel, Emissions, Energy Calculation for Machinery System},
  author = {Yum, Kevin Koosup and contributors},
  year = {2024},
  organization = {SINTEF Ocean},
  url = {https://github.com/SINTEF/FEEMS},
  version = {0.11.13}
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

## 🔗 Links

- **GitHub**: https://github.com/SINTEF/FEEMS
- **PyPI - feems**: https://pypi.org/project/feems/
- **PyPI - MachSysS**: https://pypi.org/project/MachSysS/
- **PyPI - RunFeemsSim**: https://pypi.org/project/RunFeemsSim/
- **Documentation**: Package-specific READMEs and API references

---

