# Changelog

All notable changes to the MachSysS (Machinery System Structure) package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### To 0.7.7

This release is primarily a documentation update with no breaking API changes. All existing code should work without modifications.

**What's New**:
- Comprehensive documentation for easier integration
- More examples for common use cases
- Better understanding of protobuf schemas

**No Action Required**: Existing code remains compatible.

### Protobuf Compatibility

MachSysS uses Protocol Buffers ~4.21.12. If you regenerate Python bindings from `.proto` files, ensure you use a compatible `protoc` version:

```bash
protoc --version  # Should be 3.x or 4.x
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
