# MachSysS API Reference

This document covers the public API for the `machinery-system-structure` (MachSysS) package: Protobuf schema definitions, and the Python converters that translate between Protobuf messages and FEEMS component objects.

## Table of Contents

- [Overview](#overview)
- [Proto Schema — Key Messages](#proto-schema--key-messages)
  - [COGAS](#cogas-message)
  - [Engine.EngineCycleType](#engineenginecycletype-enum)
- [Converters: Protobuf → FEEMS](#converters-protobuf--feems)
  - [convert_proto_cogas_to_feems](#convert_proto_cogas_to_feems)
  - [convert_proto_coges_to_feems](#convert_proto_coges_to_feems)
  - [convert_proto_engine_to_feems](#convert_proto_engine_to_feems)
  - [convert_proto_multifuel_engine_to_feems](#convert_proto_multifuel_engine_to_feems)
  - [convert_proto_genset_to_feems](#convert_proto_genset_to_feems)
  - [convert_proto_electric_system_to_feems](#convert_proto_electric_system_to_feems)
  - [convert_proto_mechanical_system_to_feems](#convert_proto_mechanical_system_to_feems)
  - [convert_proto_propulsion_system_to_feems](#convert_proto_propulsion_system_to_feems)
- [Converters: FEEMS → Protobuf](#converters-feems--protobuf)
  - [convert_cogas_component_to_protobuf](#convert_cogas_component_to_protobuf)
  - [convert_engine_component_to_protobuf](#convert_engine_component_to_protobuf)
  - [convert_multi_fuel_engine_to_protobuf](#convert_multi_fuel_engine_to_protobuf)
  - [convert_electric_system_to_protobuf](#convert_electric_system_to_protobuf)
  - [convert_mechanical_system_to_protobuf](#convert_mechanical_system_to_protobuf)

---

## Overview

MachSysS provides a serialization layer between FEEMS Python objects and Protocol Buffer messages. Typical usage:

```python
from MachSysS import system_structure_pb2 as proto
from MachSysS.convert_to_feems import convert_proto_electric_system_to_feems
from MachSysS.convert_to_protobuf import convert_electric_system_to_protobuf

# Deserialize from bytes
system_proto = proto.MachinerySystem()
system_proto.ParseFromString(raw_bytes)

# Convert to FEEMS objects
feems_system = convert_proto_electric_system_to_feems(system_proto)

# Convert back to proto (round-trip)
system_proto_out = convert_electric_system_to_protobuf(feems_system)
```

---

## Proto Schema — Key Messages

### COGAS message

`machinery-system-structure/proto/system_structure.proto`

Represents a Combined Gas And Steam (COGAS) prime mover. This message is embedded in a `Subsystem` alongside an electric machine to form a COGES power source.

| Field | Type | Description |
|---|---|---|
| `name` | `string` | Component name |
| `rated_power_kw` | `double` | Rated shaft power (kW) |
| `rated_speed_rpm` | `double` | Rated shaft speed (rpm) |
| `fuel` | `Fuel` | Primary fuel (type and origin) |
| `nox_calculation_method` | `NOxCalculationMethod` | IMO Tier / direct-calculation method |
| `gas_turbine_power_curve` | `PowerCurve` | GT efficiency vs. load-ratio |
| `steam_turbine_power_curve` | `PowerCurve` | ST efficiency vs. load-ratio (optional) |
| `emission_curves` | `repeated EmissionCurve` | Per-pollutant emission curves (g/kWh vs. load-ratio) |
| `uid` | `string` | Stable unique identifier |
| `fuel_modes` | `repeated COGAS.FuelMode` | Multi-fuel mode definitions. Each mode contains its own `Efficiency eff`, emission curves, and optional `secondary_fuel`. |
| `ch4_factor_gch4_per_gfuel` | `optional double` | Scalar CH₄ emission factor (g CH₄ / g fuel). If absent, library applies IPCC 2006 Brayton default (`0.000192`). |
| `n2o_factor_gn2o_per_gfuel` | `optional double` | Scalar N₂O emission factor (g N₂O / g fuel). If absent, library applies IPCC 2006 Brayton default (`0.000048`). |
| `c_slip_percent` | `optional double` | Methane slip (% of fuel mass). If absent, library applies Brayton default (`0.01 %`). Explicit `0.0` is preserved (e.g. for H₂ modes). |

**Optional-field semantics**: `ch4_factor_gch4_per_gfuel`, `n2o_factor_gn2o_per_gfuel`, and `c_slip_percent` are declared `optional double`. The conversion layer uses `HasField` to distinguish an unset field (→ use IPCC 2006 Brayton default) from an explicitly serialised `0.0` (→ use the value as-is). This allows H₂ or NH₃ modes—where CH₄/slip genuinely should be zero—to round-trip correctly.

### Engine.EngineCycleType enum

```protobuf
enum EngineCycleType {
    NONE    = 0;
    DIESEL  = 1;
    OTTO    = 2;
    LEAN_BURN_SPARK_IGNITION = 3;
    BRAYTON = 4;   // Gas turbine (Brayton thermodynamic cycle)
}
```

`BRAYTON` is used for gas-turbine fuel modes within a `COGAS` component. It selects IPCC 2006 Vol. 2 Ch. 2 default emission factors when no explicit values are provided.

---

## Converters: Protobuf → FEEMS

### convert_proto_cogas_to_feems

```python
def convert_proto_cogas_to_feems(proto_cogas: proto.COGAS) -> COGAS
```

Converts a `proto.COGAS` message to a `feems.components_model.component_mechanical.COGAS` object.

**Multi-fuel support**: If `proto_cogas.fuel_modes` is non-empty, each `COGAS.FuelMode` is converted to a `FuelCharacteristics` object (efficiency curve, emission curves, `engine_cycle_type`, optional secondary fuel) and collected in `multi_fuel_characteristics`.

**Scalar GHG defaults**: `ch4_factor`, `n2o_factor`, and `c_slip_percent` are read via `HasField`. If the field is absent (proto3 optional, not serialised), the corresponding IPCC 2006 Brayton module constant is used:

| Constant | Value |
|---|---|
| `_DEFAULT_BRAYTON_CH4_GFUEL` | `0.000192` g CH₄/g fuel |
| `_DEFAULT_BRAYTON_N2O_GFUEL` | `0.000048` g N₂O/g fuel |
| `_DEFAULT_BRAYTON_C_SLIP_PERCENT` | `0.01` % |

**Returns**: `COGAS` — changed from the previous return type of `Engine`.

---

### convert_proto_coges_to_feems

```python
def convert_proto_coges_to_feems(
    subsystem: proto.Subsystem,
    switchboard_id: int,
) -> COGES
```

Converts a `Subsystem` containing a COGES configuration (COGAS + electric machine) to a `COGES` object ready for use in an `ElectricPowerSystem`.

---

### convert_proto_engine_to_feems

```python
def convert_proto_engine_to_feems(proto_engine: proto.Engine) -> Engine
```

Converts a single-fuel `proto.Engine` to a FEEMS `Engine`.

---

### convert_proto_multifuel_engine_to_feems

```python
def convert_proto_multifuel_engine_to_feems(
    proto_engine: proto.MultiFuelEngine,
) -> EngineMultiFuel
```

Converts a multi-fuel engine proto message to `EngineMultiFuel`, preserving per-mode BSFC curves, emission curves, and pilot fuel information.

---

### convert_proto_genset_to_feems

```python
def convert_proto_genset_to_feems(
    subsystem: proto.Subsystem,
    switchboard_id: int,
) -> Genset
```

Converts a genset subsystem proto to a FEEMS `Genset`.

---

### convert_proto_electric_system_to_feems

```python
def convert_proto_electric_system_to_feems(
    system: proto.MachinerySystem,
) -> ElectricPowerSystem
```

Top-level converter for diesel-electric systems.

---

### convert_proto_mechanical_system_to_feems

```python
def convert_proto_mechanical_system_to_feems(
    system: proto.MachinerySystem,
) -> MechanicalPropulsionSystem
```

Top-level converter for mechanical propulsion systems.

---

### convert_proto_propulsion_system_to_feems

```python
def convert_proto_propulsion_system_to_feems(
    system: proto.MachinerySystem,
) -> MechanicalPropulsionSystemWithElectricPowerSystem
```

Top-level converter for hybrid (mechanical propulsion + electric power) systems.

---

## Converters: FEEMS → Protobuf

### convert_cogas_component_to_protobuf

```python
def convert_cogas_component_to_protobuf(
    component: COGAS,
    order_from_shaftline_or_switchboard: int = 1,
) -> proto.COGAS
```

Converts a FEEMS `COGAS` object to a `proto.COGAS` message. Serializes:
- Power curves (`gas_turbine_power_curve`, `steam_turbine_power_curve`)
- Emission curves
- Scalar GHG fields (`ch4_factor_gch4_per_gfuel`, `n2o_factor_gn2o_per_gfuel`, `c_slip_percent`)
- Multi-fuel modes (`fuel_modes`) — each `FuelCharacteristics` entry is mapped to a `MultiFuelEngine.FuelMode`

**Returns**: `proto.COGAS` — changed from the previous return type of `proto.Engine`.

---

### convert_engine_component_to_protobuf

```python
def convert_engine_component_to_protobuf(
    component: Engine,
    order_from_shaftline_or_switchboard: int = 1,
) -> proto.Engine
```

Converts a single-fuel `Engine` to `proto.Engine`.

---

### convert_multi_fuel_engine_to_protobuf

```python
def convert_multi_fuel_engine_to_protobuf(
    component: EngineMultiFuel,
    order_from_shaftline_or_switchboard: int = 1,
) -> proto.MultiFuelEngine
```

Converts a `EngineMultiFuel` to `proto.MultiFuelEngine`, including all fuel mode definitions.

---

### convert_electric_system_to_protobuf

```python
def convert_electric_system_to_protobuf(
    system: ElectricPowerSystem,
) -> proto.MachinerySystem
```

Converts a FEEMS `ElectricPowerSystem` to a `proto.MachinerySystem` message.

---

### convert_mechanical_system_to_protobuf

```python
def convert_mechanical_system_to_protobuf(
    system: MechanicalPropulsionSystem,
) -> proto.MachinerySystem
```

Converts a FEEMS `MechanicalPropulsionSystem` to a `proto.MachinerySystem` message.
