# RunFeemsSim Package

> The RunFeemsSim package is a Python package for running FEEMS simulations. It provides a simple 
> interface for running FEEMS simulations and for visualizing the results. It also provides a basic 
> pms model to apply for an electric power system that has a functionality of load dependent 
> start-stop of gensets.

## Installation

### For Developers (Workspace)
This package is part of the FEEMS workspace managed by `uv`.
To set up the environment, run the following from the workspace root:

```bash
uv sync
```

This will install `RunFeemsSim` in editable mode along with its dependencies (`feems`, `MachSysS`).

### From Package Registry
If you are installing from a package registry (e.g. Azure Artifacts):

```bash
pip install RunFeemsSim
```

## Development

This package uses `nbdev`. The source code is generated from Jupyter Notebooks (e.g., `00_machinery_calculation.ipynb`).
- Modify the notebooks.
- Run `nbdev_export` to update the Python modules in `RunFeemsSim/`. (Ensure you have `nbdev` installed or use the workspace tools if configured).

## Usage

## Usage


