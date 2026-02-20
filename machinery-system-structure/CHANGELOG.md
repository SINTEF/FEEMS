# Changelog

All notable changes to the MachSysS (Machinery System Structure) package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.0](https://github.com/SINTEF/FEEMS/compare/MachSysS-v0.9.4...MachSysS-v0.10.0) (2026-02-20)


### Features

* **fuel:** support user-defined fuel with name field ([#80](https://github.com/SINTEF/FEEMS/issues/80)) ([075a559](https://github.com/SINTEF/FEEMS/commit/075a559142024e21e9cac1d761b8d55ddf4dbd0d))
* user-defined fuel support with per-component override ([#80](https://github.com/SINTEF/FEEMS/issues/80)) ([9333703](https://github.com/SINTEF/FEEMS/commit/9333703d84b4840eaae5182a4921024ce1c2b1b5))

## [0.9.4](https://github.com/SINTEF/FEEMS/compare/MachSysS-v0.9.3...MachSysS-v0.9.4) (2026-02-11)


### Bug Fixes

* publish fix ([3378ce2](https://github.com/SINTEF/FEEMS/commit/3378ce2aa1710407617dc9810f96973475e649a7))
* publish fix ([55ffc6c](https://github.com/SINTEF/FEEMS/commit/55ffc6c1bbb5a8969cd55f105d8f84152248fc5c))

## [0.9.3](https://github.com/SINTEF/FEEMS/compare/MachSysS-v0.9.2...MachSysS-v0.9.3) (2026-02-11)


### Bug Fixes

* updated publish ([cefd41c](https://github.com/SINTEF/FEEMS/commit/cefd41cade63c4f85064507c232e7c6263def9e6))
* updated publish ([17494b8](https://github.com/SINTEF/FEEMS/commit/17494b8ffae95f8ae7afbf0e4f8cafe2ac598e7f))

## [0.9.2](https://github.com/SINTEF/FEEMS/compare/MachSysS-v0.9.1...MachSysS-v0.9.2) (2026-02-11)


### Bug Fixes

* deleted unnecessary files ([4f468db](https://github.com/SINTEF/FEEMS/commit/4f468db3eabb8c08bea24ecfdb6e3956761f5890))
* deleted unnecessary files ([d7fb5bd](https://github.com/SINTEF/FEEMS/commit/d7fb5bd1e650fd14910cb24a5b4b8bbb71429f1d))

## [0.9.1](https://github.com/SINTEF/FEEMS/compare/MachSysS-v0.9.0...MachSysS-v0.9.1) (2026-02-11)


### Bug Fixes

* release updated ([c0d2ea5](https://github.com/SINTEF/FEEMS/commit/c0d2ea5da92328f1feb69176dc821d60de79bb5a))

## [0.9.0](https://github.com/SINTEF/FEEMS/compare/MachSysS-v0.8.1...MachSysS-v0.9.0) (2026-02-11)


### Features

* add py.typed to packages ([6267bcd](https://github.com/SINTEF/FEEMS/commit/6267bcdbab3b25a6697b97c7b5d96a6a533b6896))


### Documentation

* add comprehensive documentation for PyPI publication ([d8a55ca](https://github.com/SINTEF/FEEMS/commit/d8a55cab4152d3bfc4602d0918e4dfbb06e70d70))

## [0.8.0](https://github.com/SINTEF/FEEMS/compare/MachSysS-v0.7.9...MachSysS-v0.8.0) (2026-02-11)


### Features

* add py.typed to packages ([6267bcd](https://github.com/SINTEF/FEEMS/commit/6267bcdbab3b25a6697b97c7b5d96a6a533b6896))


### Documentation

* add comprehensive documentation for PyPI publication ([d8a55ca](https://github.com/SINTEF/FEEMS/commit/d8a55cab4152d3bfc4602d0918e4dfbb06e70d70))

## [Unreleased]

## [0.7.9] - 2026-02-11

### Security
- **CRITICAL**: Updated protobuf from 4.21.12 to 5.29.6 to fix security vulnerabilities
  - CVE-2025-4565: Critical vulnerability in Protocol Buffers
  - CVE-2026-0994: Critical vulnerability in Protocol Buffers
- All tests pass with updated protobuf version (backward compatible upgrade)

### Added
- Subsystem fields: `start_delay_s`, `turn_off_power_kw`, `power_minimum_specific`

### Changed
- Regenerated protobuf Python bindings after schema updates
- Version bump to 0.7.9

### Removed
- Removed legacy `build_package.sh` script

### Documentation
- Updated MachSysS version references to 0.7.9

## [0.7.7] - 2024-02-11

### Documentation
- Complete README.md rewrite with comprehensive documentation
- Added Protocol Buffer schema documentation
- Added conversion API examples
- Added use cases and best practices
- Updated pyproject.toml metadata for PyPI publication
- Added development workflow guide (protobuf compilation)

### Added
- Documentation for all conversion utilities
- Examples for FEEMS ↔ Protobuf conversion
- Time-series data conversion examples
- Cross-language integration patterns

## [0.7.x] - Previous Releases

### Added
- Protocol Buffer definitions for machinery systems
- FEEMS to Protobuf conversion utilities
- Protobuf to FEEMS conversion utilities
- Simulation results serialization
- Time-series data structures
- Component specification schemas

### Changed
- Enhanced protobuf schemas for better compatibility
- Improved conversion efficiency
- Better error handling in conversions

## [0.6.x] - Earlier Releases

### Added
- Initial Protocol Buffer definitions
- Basic conversion utilities
- System structure schemas

### Changed
- Schema refinements based on feedback
- Conversion utility improvements

## Core Features

### Protocol Buffer Schemas
- **system_structure.proto**: Complete machinery system configuration
- **feems_result.proto**: Simulation results and metrics
- **gymir_result.proto**: Alternative time-series format

### Conversion Utilities
- **convert_to_protobuf.py**: FEEMS objects → Protobuf messages
- **convert_to_feems.py**: Protobuf messages → FEEMS objects
- **convert_feems_result_to_proto.py**: Simulation results → Protobuf
- **convert_proto_timeseries.py**: Time-series ↔ pandas DataFrames

### Data Exchange
- Cross-language compatibility (Python, C++, Java, Go, etc.)
- Efficient binary serialization
- Version control friendly schemas
- Backwards compatibility support

## Upgrade Guide

### To 0.7.9

This release updates protobuf to 5.29.6 to address critical security issues, with no breaking API changes. All existing code should work without modifications.

**What's New**:
- Security fixes via protobuf runtime upgrade
- Verified compatibility with existing APIs

**No Action Required**: Existing code remains compatible.

### Protobuf Compatibility

MachSysS uses Protocol Buffers 5.29.6. If you regenerate Python bindings from `.proto` files, ensure you use a compatible `protoc` version:

```bash
protoc --version  # Should be 5.x
./compile_proto.sh
```

## Development

### Regenerating Protobuf Files

When modifying `.proto` files:

```bash
cd machinery-system-structure
./compile_proto.sh
```

This generates:
- `*_pb2.py` - Python classes
- `*_pb2.pyi` - Type stubs for mypy
- Fixed imports for relative module references

### Testing

```bash
uv run pytest machinery-system-structure/tests/
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to MachSysS.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/SINTEF/FEEMS/issues)
- **Documentation**: [https://keviny.github.io/MachSysS/](https://keviny.github.io/MachSysS/)
- **Email**: kevinkoosup.yum@sintef.no
