# MachSysS (Machinery System Structure)

`MachSysS` provides the data structures, Protocol Buffer definitions, and conversion utilities for the FEEMS ecosystem. It facilitates data exchange between different components of the system.

## Development

This package is a standard Python package managed within the FEEMS workspace.

### Prerequisites
- `protobuf` compiler (`protoc`) if you need to regenerate Python files from `.proto` definitions.

### Installation
From the workspace root:
```bash
uv sync
```

### Regenerating Protobuf Files
If you modify files in `proto/`, you need to regenerate the Python bindings:
```bash
protoc -I=proto --python_out=MachSysS proto/*.proto --pyi_out=MachSysS
```

### Running Tests
```bash
uv run pytest tests/
```
