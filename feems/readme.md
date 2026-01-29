# Fuel, Emissions, Energy Calculation for Machinery System (FEEMS)

FEEMS is modeling framework for a marine power and propulsion system for calculation of fuel consumption, emissions, and energy balance with the input of operation mode and external power load.In this framework, a modeler can configure a power system based on the single line diagram and component library. It supports the following types of power / propulsion systems

- Hybrid/Conventional Diesel Electric Propulsion
- Hybrid Propulsion with PTI/PTO
- Mechanical Propulsion with a Separate Electric Power System

After the system model is configured, given the operational control inputs and power load on the consumers, power balance calculation is performed to obtain the load on the power producers. Then fuel/emission calculation is performed.

## Installing FEEMS

This package is part of the FEEMS workspace.

### For Users
```bash
pip install feems
```

### For Developers (Workspace Setup)
Ensure you have `uv` installed, then from the workspace root:
```bash
uv sync
```

## Building from source

To build the package specifically:
```bash
cd feems
uv build
```
