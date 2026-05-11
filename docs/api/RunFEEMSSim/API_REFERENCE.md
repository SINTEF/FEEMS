# RunFEEMSSim API Reference

This document covers the public API of the `RunFEEMSSim` package — a higher-level simulation runner built on top of FEEMS and MachSysS.

## Table of Contents

- [Overview](#overview)
- [`MachineryCalculation`](#machinerycalculation)
  - [Constructor](#constructor)
  - [Properties](#properties)
  - [`calculate_machinery_system_output_from_gymir_result`](#calculate_machinery_system_output_from_gymir_result)
  - [`calculate_machinery_system_output_from_propulsion_power_time_series`](#calculate_machinery_system_output_from_propulsion_power_time_series)
  - [`calculate_machinery_system_output_from_time_series_result`](#calculate_machinery_system_output_from_time_series_result)
  - [`calculate_machinery_system_output_from_statistics`](#calculate_machinery_system_output_from_statistics)
- [`convert_gymir_result_to_propulsion_power_series`](#convert_gymir_result_to_propulsion_power_series)
- [PMS (Power Management System)](#pms-power-management-system)
  - [`PmsLoadTable`](#pmsloadtable)
  - [`PmsLoadTableSimulationInterface`](#pmsloadtablesimulationinterface)
  - [`get_min_load_table_dict_from_feems_system`](#get_min_load_table_dict_from_feems_system)
- [Return Types](#return-types)
  - [steam_demand_kg_per_h behaviour](#steam_demand_kg_per_h-behaviour)
  - [fuel_option behaviour](#fuel_option-behaviour)

---

## Overview

`RunFEEMSSim` wraps the FEEMS core with:

- **PMS logic** — automatically starts/stops gensets based on load demand
- **Input adapters** — accepts Gymir protobuf results, pandas time-series, or statistical distributions
- **Steam boiler integration** — passes per-timestep steam demand to the attached `SteamBoiler`

The main entry point is `MachineryCalculation`.

---

## `MachineryCalculation`

```python
from RunFeemsSim.machinery_calculation import MachineryCalculation
```

Orchestrates FEEMS power-balance calculations and PMS genset scheduling for a full machinery system.

### Constructor

```python
MachineryCalculation(
    feems_system: Union[
        ElectricPowerSystem,
        MechanicalPropulsionSystemWithElectricPowerSystem,
        HybridPropulsionSystem,
    ],
    pms: SimulationInterface = None,
    maximum_allowed_power_source_load_percentage: float = 80,
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `feems_system` | `ElectricPowerSystem \| MechanicalPropulsionSystemWithElectricPowerSystem \| HybridPropulsionSystem` | Fully configured FEEMS system model |
| `pms` | `SimulationInterface` | Custom PMS. If `None`, a `PmsLoadTableSimulationInterface` is built automatically from the system's rated capacity using `maximum_allowed_power_source_load_percentage`. |
| `maximum_allowed_power_source_load_percentage` | `float` | Load threshold (%) used when auto-building the default PMS. Default `80`. |

### Properties

#### `electric_system`

```python
@property
def electric_system(self) -> ElectricPowerSystem
```

Returns the `ElectricPowerSystem` sub-object. For an `ElectricPowerSystem` this is the system itself; for mechanical/hybrid systems it returns the embedded `electric_system` attribute.

#### `system_is_not_electric`

```python
@property
def system_is_not_electric(self) -> bool
```

`True` when the wrapped system has a `mechanical_system` component (i.e. it is `MechanicalPropulsionSystemWithElectricPowerSystem` or `HybridPropulsionSystem`).

---

### `calculate_machinery_system_output_from_gymir_result`

```python
def calculate_machinery_system_output_from_gymir_result(
    *,
    gymir_result: proto_gymir.GymirResult,
    fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
    ignore_power_balance: bool = False,
    fuel_option: Optional[FuelOption] = None,
) -> Union[FEEMSResult, FEEMSResultForMachinerySystem]
```

Runs a simulation from a Gymir protobuf result. Propulsion power and auxiliary load are extracted from the protobuf message.

| Parameter | Type | Description |
|-----------|------|-------------|
| `gymir_result` | `GymirResult` | Gymir result protobuf message containing epoch timestamps, per-step power, and a fixed auxiliary load. |
| `fuel_specified_by` | `FuelSpecifiedBy` | Emission factor set to apply (`IMO` / `EU` / `USER`). Default `FuelSpecifiedBy.IMO`. |
| `ignore_power_balance` | `bool` | Skip PMS genset scheduling and use component statuses as-is. Default `False`. |
| `fuel_option` | `FuelOption \| None` | Alternative fuel selection. See [fuel_option behaviour](#fuel_option-behaviour). |

**Returns** `FEEMSResult` (electric system) or `FEEMSResultForMachinerySystem` (mechanical/hybrid).

> **Note:** This method does **not** accept `steam_demand_kg_per_h`. If the system has a boiler, set `boiler.steam_out_kg_per_h` directly before calling, or use one of the other calculation methods.

---

### `calculate_machinery_system_output_from_propulsion_power_time_series`

```python
def calculate_machinery_system_output_from_propulsion_power_time_series(
    *,
    propulsion_power: Union[pd.Series, pd.DataFrame],
    auxiliary_power_kw: Numeric,
    fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
    ignore_power_balance: bool = False,
    fuel_option: Optional[FuelOption] = None,
    steam_demand_kg_per_h: Optional[np.ndarray] = None,
) -> Union[FEEMSResult, FEEMSResultForMachinerySystem]
```

Runs a simulation from a pandas propulsion power time series.

| Parameter | Type | Description |
|-----------|------|-------------|
| `propulsion_power` | `pd.Series \| pd.DataFrame` | Propulsion power time series. **Series**: total power equally distributed across all drives; index is epoch timestamps (s). **DataFrame**: one column per propulsion drive (column names must match drive names); index is epoch timestamps (s). |
| `auxiliary_power_kw` | `int \| float \| np.ndarray` | Auxiliary/hotel load in kW. Scalar or array with same length as `propulsion_power`. |
| `fuel_specified_by` | `FuelSpecifiedBy` | Emission factor set. Default `FuelSpecifiedBy.IMO`. |
| `ignore_power_balance` | `bool` | Skip PMS scheduling. Default `False`. |
| `fuel_option` | `FuelOption \| None` | Alternative fuel. See [fuel_option behaviour](#fuel_option-behaviour). |
| `steam_demand_kg_per_h` | `np.ndarray \| None` | Per-timestep steam demand in kg/h. See [steam_demand_kg_per_h behaviour](#steam_demand_kg_per_h-behaviour). |

**Raises**
- `TypeError` — if `propulsion_power` is not a `pd.Series` or `pd.DataFrame`
- `ValueError` — if `steam_demand_kg_per_h` length does not match `propulsion_power` length

---

### `calculate_machinery_system_output_from_time_series_result`

```python
def calculate_machinery_system_output_from_time_series_result(
    *,
    time_series: Union[
        proto_gymir.TimeSeriesResult,
        proto_gymir.TimeSeriesResultForMultiplePropulsors,
    ],
    fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
    ignore_power_balance: bool = False,
    fuel_option: Optional[FuelOption] = None,
    steam_demand_kg_per_h: Optional[np.ndarray] = None,
) -> Union[FEEMSResult, FEEMSResultForMachinerySystem]
```

Runs a simulation from a protobuf time-series result message.

| Parameter | Type | Description |
|-----------|------|-------------|
| `time_series` | `TimeSeriesResult \| TimeSeriesResultForMultiplePropulsors` | Protobuf time-series. `TimeSeriesResult` carries a single propulsion power column plus auxiliary load; `TimeSeriesResultForMultiplePropulsors` carries one column per propulsor. |
| `fuel_specified_by` | `FuelSpecifiedBy` | Emission factor set. Default `FuelSpecifiedBy.IMO`. |
| `ignore_power_balance` | `bool` | Skip PMS scheduling. Default `False`. |
| `fuel_option` | `FuelOption \| None` | Alternative fuel. See [fuel_option behaviour](#fuel_option-behaviour). |
| `steam_demand_kg_per_h` | `np.ndarray \| None` | Per-timestep steam demand in kg/h. Length must match the number of rows in the decoded time-series. See [steam_demand_kg_per_h behaviour](#steam_demand_kg_per_h-behaviour). |

**Raises**
- `TypeError` — if `time_series` is neither `TimeSeriesResult` nor `TimeSeriesResultForMultiplePropulsors`
- `ValueError` — if `steam_demand_kg_per_h` length does not match the time-series length

---

### `calculate_machinery_system_output_from_statistics`

```python
def calculate_machinery_system_output_from_statistics(
    *,
    propulsion_power: np.ndarray,
    frequency: np.ndarray,
    auxiliary_power_kw: Numeric,
    fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
    ignore_power_balance: bool = False,
    fuel_option: Optional[FuelOption] = None,
    steam_demand_kg_per_h: Optional[np.ndarray] = None,
) -> Union[FEEMSResult, FEEMSResultForMachinerySystem]
```

Runs a simulation from a statistical distribution of operating modes (propulsion power bins × duration).

| Parameter | Type | Description |
|-----------|------|-------------|
| `propulsion_power` | `np.ndarray` | Propulsion power per mode in kW. |
| `frequency` | `np.ndarray` | Duration of each mode in seconds. If values are normalized (sum to 1), the result should be interpreted as per-second values. |
| `auxiliary_power_kw` | `int \| float \| np.ndarray` | Auxiliary load per mode in kW. Scalar or same length as `propulsion_power`. |
| `fuel_specified_by` | `FuelSpecifiedBy` | Emission factor set. Default `FuelSpecifiedBy.IMO`. |
| `ignore_power_balance` | `bool` | Skip PMS scheduling. Default `False`. |
| `fuel_option` | `FuelOption \| None` | Alternative fuel. See [fuel_option behaviour](#fuel_option-behaviour). |
| `steam_demand_kg_per_h` | `np.ndarray \| None` | Steam demand per mode in kg/h. Must have the same length as `propulsion_power`. See [steam_demand_kg_per_h behaviour](#steam_demand_kg_per_h-behaviour). |

**Raises**
- `ValueError` — if `steam_demand_kg_per_h` length does not match `propulsion_power` length

---

## `convert_gymir_result_to_propulsion_power_series`

```python
def convert_gymir_result_to_propulsion_power_series(
    gymir_result: proto_gymir.GymirResult,
) -> pd.Series
```

Utility function that extracts the propulsion power time series from a Gymir protobuf result.

**Returns** `pd.Series` with epoch timestamps (s) as the index and propulsion power (kW) as values.

---

## PMS (Power Management System)

```python
from RunFeemsSim.pms_basic import (
    PmsLoadTable,
    PmsLoadTableSimulationInterface,
    get_min_load_table_dict_from_feems_system,
)
```

### `PmsLoadTable`

Holds the minimum-load → genset-on/off pattern as a dict.

```python
PmsLoadTable(min_load2on_pattern: dict)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `min_load2on_pattern` | `dict` | Maps minimum total load thresholds (kW) to a list of genset on/off patterns. |

### `PmsLoadTableSimulationInterface`

`SimulationInterface` implementation that uses a `PmsLoadTable` to decide genset status at each timestep.

```python
PmsLoadTableSimulationInterface(
    n_bus_ties: int,
    pms_load_table: PmsLoadTable,
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `n_bus_ties` | `int` | Number of bus-tie connections in the electric system. |
| `pms_load_table` | `PmsLoadTable` | Load table that maps load levels to genset patterns. |

### `get_min_load_table_dict_from_feems_system`

```python
def get_min_load_table_dict_from_feems_system(
    system: Union[
        ElectricPowerSystem,
        MechanicalPropulsionSystemWithElectricPowerSystem,
        HybridPropulsionSystem,
    ],
    maximum_allowed_genset_load_percentage: float = 80,
) -> dict
```

Derives the default PMS load-table from the rated capacities of all gensets in the system.

| Parameter | Type | Description |
|-----------|------|-------------|
| `system` | FEEMS system | The configured FEEMS system. |
| `maximum_allowed_genset_load_percentage` | `float` | Maximum genset load as a percentage of rated capacity. Default `80`. |

**Returns** `dict` suitable for `PmsLoadTable(min_load2on_pattern=...)`.

---

## Return Types

All `calculate_*` methods return either:

- **`FEEMSResult`** — when the system is a pure `ElectricPowerSystem`
- **`FEEMSResultForMachinerySystem`** — when the system is `MechanicalPropulsionSystemWithElectricPowerSystem` or `HybridPropulsionSystem`

Both types are defined in `feems.types_for_feems` / `feems.system_model`. See the [FEEMS API Reference](../feems/API_REFERENCE.md) for their field definitions, including the `detail_result` DataFrame layout and `co2_emission_total_kg`.

---

### `steam_demand_kg_per_h` behaviour

The `steam_demand_kg_per_h` parameter is accepted by three of the four calculation methods (all except the Gymir-result method). It controls the per-timestep steam output of the `SteamBoiler` attached to the system.

- If the system has no boiler (`system_feems.boiler is None`), this parameter is silently ignored.
- If `steam_demand_kg_per_h=None` and a boiler is present, the boiler demand is set to zero for all timesteps (boiler is not running).
- The array length must exactly match the number of timesteps in the input data; a mismatch raises `ValueError`.

The boiler's fuel consumption, CO2 emissions, and running hours appear in the returned `FEEMSResult` / `FEEMSResultForMachinerySystem` and in its `detail_result` DataFrame under the component row named after the boiler.

---

### `fuel_option` behaviour

`fuel_option` accepts a `FuelOption` NamedTuple `(fuel_type, fuel_origin, for_pilot=False, primary=True)`. When provided, FEEMS selects the specified fuel across all components that support it.

For details on validation rules, sub-system scoping in `HybridPropulsionSystem` and `MechanicalPropulsionSystemWithElectricPowerSystem`, and boiler-only fuel switching, see the [`fuel_option` behaviour section in the FEEMS API Reference](../feems/API_REFERENCE.md#fuel_option-behaviour).
