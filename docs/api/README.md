# FEEMS API Reference

Auto-generated and manually maintained API documentation for all FEEMS packages.

## Packages

- [`feems/`](feems/) — Core fuel, emissions, and energy calculation library
- [`machinery-system-structure/`](machinery-system-structure/) — Protobuf system structure definitions and converters
- [`RunFEEMSSim/`](RunFEEMSSim/) — Simulation runner and Power Management System (PMS)

## Generating Docs

```bash
# Install pdoc (if not already available)
uv add --dev pdoc

# Generate HTML API docs
uv run pdoc feems --output-dir docs/api/feems
uv run pdoc machinery_system_structure --output-dir docs/api/machinery-system-structure
uv run pdoc RunFeemsSim --output-dir docs/api/RunFEEMSSim
```
