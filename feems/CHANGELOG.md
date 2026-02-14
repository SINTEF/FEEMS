# Changelog

All notable changes to the FEEMS package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.13.4](https://github.com/SINTEF/FEEMS/compare/feems-v0.13.3...feems-v0.13.4) (2026-02-11)


### Bug Fixes

* publish fix ([3378ce2](https://github.com/SINTEF/FEEMS/commit/3378ce2aa1710407617dc9810f96973475e649a7))
* publish fix ([55ffc6c](https://github.com/SINTEF/FEEMS/commit/55ffc6c1bbb5a8969cd55f105d8f84152248fc5c))

## [0.13.3](https://github.com/SINTEF/FEEMS/compare/feems-v0.13.2...feems-v0.13.3) (2026-02-11)


### Bug Fixes

* updated publish ([cefd41c](https://github.com/SINTEF/FEEMS/commit/cefd41cade63c4f85064507c232e7c6263def9e6))
* updated publish ([17494b8](https://github.com/SINTEF/FEEMS/commit/17494b8ffae95f8ae7afbf0e4f8cafe2ac598e7f))

## [0.13.2](https://github.com/SINTEF/FEEMS/compare/feems-v0.13.1...feems-v0.13.2) (2026-02-11)


### Bug Fixes

* deleted unnecessary files ([4f468db](https://github.com/SINTEF/FEEMS/commit/4f468db3eabb8c08bea24ecfdb6e3956761f5890))
* deleted unnecessary files ([d7fb5bd](https://github.com/SINTEF/FEEMS/commit/d7fb5bd1e650fd14910cb24a5b4b8bbb71429f1d))

## [0.13.1](https://github.com/SINTEF/FEEMS/compare/feems-v0.13.0...feems-v0.13.1) (2026-02-11)


### Bug Fixes

* release updated ([c0d2ea5](https://github.com/SINTEF/FEEMS/commit/c0d2ea5da92328f1feb69176dc821d60de79bb5a))

## [0.13.0](https://github.com/SINTEF/FEEMS/compare/feems-v0.12.1...feems-v0.13.0) (2026-02-11)


### Features

* Add available_fuel_options_by_converter property ([1badf62](https://github.com/SINTEF/FEEMS/commit/1badf626fb9f01aceb8cc9ec2bd0e426f8d9d7d3))
* Add available_fuel_options_by_converter property ([ecd0eba](https://github.com/SINTEF/FEEMS/commit/ecd0ebaae15adbd12660a67ba0b728b973ef6332))


### Bug Fixes

* Add ShorePower to ElectricPowerSystem ([#50](https://github.com/SINTEF/FEEMS/issues/50)) ([28d5cff](https://github.com/SINTEF/FEEMS/commit/28d5cff88e6d866ec3c20024083f5568892b4097))


### Documentation

* add comprehensive documentation for PyPI publication ([d8a55ca](https://github.com/SINTEF/FEEMS/commit/d8a55cab4152d3bfc4602d0918e4dfbb06e70d70))
* improve feems architecture documentation ([8ec3d3a](https://github.com/SINTEF/FEEMS/commit/8ec3d3aeb1bd0145aee96f6fc8b8e00818413fd2))

## [0.12.0](https://github.com/SINTEF/FEEMS/compare/feems-v0.11.13...feems-v0.12.0) (2026-02-11)


### Features

* Add available_fuel_options_by_converter property ([1badf62](https://github.com/SINTEF/FEEMS/commit/1badf626fb9f01aceb8cc9ec2bd0e426f8d9d7d3))
* Add available_fuel_options_by_converter property ([ecd0eba](https://github.com/SINTEF/FEEMS/commit/ecd0ebaae15adbd12660a67ba0b728b973ef6332))


### Bug Fixes

* Add ShorePower to ElectricPowerSystem ([#50](https://github.com/SINTEF/FEEMS/issues/50)) ([28d5cff](https://github.com/SINTEF/FEEMS/commit/28d5cff88e6d866ec3c20024083f5568892b4097))


### Documentation

* add comprehensive documentation for PyPI publication ([d8a55ca](https://github.com/SINTEF/FEEMS/commit/d8a55cab4152d3bfc4602d0918e4dfbb06e70d70))
* improve feems architecture documentation ([8ec3d3a](https://github.com/SINTEF/FEEMS/commit/8ec3d3aeb1bd0145aee96f6fc8b8e00818413fd2))

## [0.11.13] - 2024-02-11

### Documentation
- Added comprehensive README.md with features, installation, and usage examples
- Created complete API reference documentation (API_REFERENCE.md)
- Enhanced examples with detailed explanations and context
- Added shore power example (02_Shore_Power_Example.ipynb)
- Created shore power guide (SHORE_POWER_GUIDE.md)
- Updated pyproject.toml with proper metadata for PyPI

### Fixed
- Various bug fixes and improvements

## [0.11.x] - Previous Releases

### Added
- Shore power connection components (ShorePowerConnection, ShorePowerConnectionSystem)
- Battery energy storage support
- Multi-fuel engine support (EngineDualFuel, EngineMultiFuel)
- COGAS system support
- Enhanced emission calculations (FuelEU Maritime, IMO)
- Time-series simulation capabilities
- Power Management System integration

### Changed
- Improved power balance calculation algorithms
- Enhanced component efficiency calculations
- Optimized fuel consumption calculations

### Core Features (Existing)
- Component-based modeling framework
- Electric power system modeling
- Mechanical propulsion system modeling
- Hybrid propulsion support
- PTI/PTO systems
- Fuel consumption and emissions calculations
- Energy balance analysis
- Load sharing and bus-tie management

## Version History Overview

- **0.11.x**: Current stable release with comprehensive features
- **0.10.x**: Enhanced emission calculations and FuelEU Maritime support
- **0.9.x**: Added battery and energy storage support
- **0.8.x**: Shore power integration
- **0.7.x**: Multi-fuel engine support
- **0.6.x**: COGAS system support
- **0.5.x**: PTI/PTO functionality
- **0.4.x**: Hybrid propulsion support
- **0.3.x**: Mechanical propulsion systems
- **0.2.x**: Electric power system enhancements
- **0.1.x**: Initial release with basic functionality

## Upgrade Guide

### To 0.11.13

This release is primarily a documentation update with no breaking API changes. All existing code should work without modifications.

**What's New**:
- Comprehensive documentation for easier onboarding
- More examples and use cases
- API reference for developers

**No Action Required**: Existing code remains compatible.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to FEEMS.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/SINTEF/FEEMS/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SINTEF/FEEMS/discussions)
- **Email**: kevin.koosup.yum@gmail.com
