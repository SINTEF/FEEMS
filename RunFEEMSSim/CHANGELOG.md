# Changelog

All notable changes to the RunFeemsSim package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1](https://github.com/SINTEF/FEEMS/compare/RunFeemsSim-v0.4.0...RunFeemsSim-v0.4.1) (2026-02-11)


### Bug Fixes

* release updated ([c0d2ea5](https://github.com/SINTEF/FEEMS/commit/c0d2ea5da92328f1feb69176dc821d60de79bb5a))

## [0.4.0](https://github.com/SINTEF/FEEMS/compare/RunFeemsSim-v0.3.1...RunFeemsSim-v0.4.0) (2026-02-11)


### Features

* add py.typed to packages ([6267bcd](https://github.com/SINTEF/FEEMS/commit/6267bcdbab3b25a6697b97c7b5d96a6a533b6896))


### Documentation

* add comprehensive documentation for PyPI publication ([d8a55ca](https://github.com/SINTEF/FEEMS/commit/d8a55cab4152d3bfc4602d0918e4dfbb06e70d70))

## [0.3.0](https://github.com/SINTEF/FEEMS/compare/RunFeemsSim-v0.2.6...RunFeemsSim-v0.3.0) (2026-02-11)


### Features

* add py.typed to packages ([6267bcd](https://github.com/SINTEF/FEEMS/commit/6267bcdbab3b25a6697b97c7b5d96a6a533b6896))


### Documentation

* add comprehensive documentation for PyPI publication ([d8a55ca](https://github.com/SINTEF/FEEMS/commit/d8a55cab4152d3bfc4602d0918e4dfbb06e70d70))

## [0.2.6] - 2024-02-11

### Changed
- **BREAKING**: Migrated from nbdev to pure Python development
- Source of truth is now Python files in `RunFeemsSim/` directory (not notebooks)
- Development workflow now uses standard Python tools (ruff, mypy, pytest)

### Removed
- Removed nbdev configuration files (settings.ini, _modidx.py, _nbdev.py)
- Removed nbdev entry points from pyproject.toml
- Removed [tool.nbdev] section from configuration

### Documentation
- Complete README.md rewrite for pure Python development
- Removed all nbdev workflow documentation
- Added pure Python development workflow guide
- Added code quality tools documentation (ruff, mypy, pytest)
- Created MIGRATION_FROM_NBDEV.md guide
- Enhanced API documentation in README
- Updated examples and use cases

### Added
- Documentation for standard Python development practices
- Type hints support documentation
- IDE integration guidance

### Note
- Existing Jupyter notebooks (*.ipynb) are retained as examples/documentation only
- They are no longer the source of truth for the codebase
- All development should be done directly in .py files

## [0.2.x] - Previous Releases

### Added
- MachineryCalculation class for high-level simulation interface
- PMSBasic class for load-dependent power management
- Automatic genset start/stop logic
- Time-series simulation support
- Integration with MachSysS for data exchange
- FuelEU Maritime emission calculations

### Changed
- Improved simulation performance
- Enhanced PMS algorithms
- Better error handling and validation

## [0.1.x] - Initial Releases

### Added
- Basic simulation interface
- Integration with FEEMS core
- Initial PMS functionality
- Time-series support

## Migration from nbdev

Version 0.2.6 represents a significant change in development methodology:

### Before (nbdev-based)
- Source code in Jupyter notebooks
- `nbdev_export` to generate Python files
- `nbdev_test` for testing
- Special cell directives (#| export, etc.)

### After (Pure Python)
- Source code in Python files (`RunFeemsSim/*.py`)
- Direct editing of .py files
- Standard pytest for testing
- Standard Python tooling (ruff, mypy)

### For Developers

If you were using nbdev workflow:
1. Now edit Python files directly in `RunFeemsSim/` directory
2. Use `pytest` instead of `nbdev_test`
3. Use `ruff` for linting and formatting
4. Notebooks can still be used for examples/docs, but are not source code

See [MIGRATION_FROM_NBDEV.md](MIGRATION_FROM_NBDEV.md) for detailed migration guide.

## Upgrade Guide

### To 0.2.6

**For Users** (no changes needed):
- API remains the same
- Import statements unchanged
- Existing code continues to work

**For Contributors**:
- Update your development workflow (see README.md)
- Edit .py files directly instead of notebooks
- Use standard Python tools (ruff, pytest, mypy)

**Breaking Changes for Developers Only**:
- Cannot use `nbdev_export` anymore
- No special notebook directives
- Development workflow changed to pure Python

## Core Features

### High-Level Simulation
- `MachineryCalculation`: Simplified simulation interface
- Time-series power profile support
- Automatic power balance calculation
- Comprehensive results aggregation

### Power Management System
- `PMSBasic`: Load-dependent genset control
- Automatic start/stop based on load thresholds
- Spinning reserve management
- Blackout prevention

### Results Analysis
- Fuel consumption tracking
- Emissions calculations (CO2, NOx)
- Energy breakdown (propulsion, auxiliary)
- Operating hours for maintenance planning

### Integration
- Seamless integration with FEEMS core
- MachSysS for data serialization
- pandas DataFrame support for time-series
- FuelEU Maritime compliance

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to RunFeemsSim.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/SINTEF/FEEMS/issues)
- **Documentation**: [https://kevinkoosup.yum@sintef.no.github.io/RunFeemsSim/](https://kevinkoosup.yum@sintef.no.github.io/RunFeemsSim/)
- **Email**: kevinkoosup.yum@sintef.no
