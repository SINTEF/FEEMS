# Design: Organic Rankine Cycle (ORC) Waste-Heat Recovery

**Issue:** #104
**Plan:** `docs/01-plan/features/orc-waste-heat-recovery.plan.md`
**Branch:** `feat/ORC-ai-workflow`

---

## 1. Context

An ORC turns low-temperature waste heat (exhaust, jacket water) into electricity without burning fuel. Its output depends on the heat its host rejects, which depends on the host load. That is the key difference from every other feems power source: an ORC cannot follow the electric demand.

feems therefore does not model the thermodynamics. The proto carries the ORC data so that a client can compute:

- the setpoint of a main engine ORC for each timestep (from main engine load), or
- a lifted efficiency curve of a genset / fuel cell that has an ORC on its exhaust.

feems only needs a component that injects a given power into a switchboard and accounts for it.

## 2. Proto (`machinery-system-structure/proto/system_structure.proto`)

### 2.1 Message

```proto
message OrganicRankineCycle {
  double rated_power_kw = 1;                 // electric output rating
  double rated_efficiency = 2;               // thermal-to-electric efficiency at design heat input
  Curve1D relative_efficiency_curve = 3;     // x: heat input / design heat input, y: efficiency / rated efficiency
  double waste_heat_fraction = 4;            // share of host rejected heat reaching the evaporator
  double unit_price_usd = 5;
  string uid = 6;
  uint32 switchboard_id = 7;                 // > 0: separate source; 0: integrated in host
  string name = 8;
}
```

Fields 2–5 are not used inside feems; they are client inputs (ORC physics and CAPEX) kept next to the ORC so the system proto stays the single source of truth.

### 2.2 Host fields

| Message | Field | Tag | Meaning |
|---------|-------|-----|---------|
| `Engine` | `orc` | 16 | ORC on a main engine or on a genset engine |
| `MultiFuelEngine` | `orc` | 12 | same for multi-fuel engines |
| `MachinerySystem` | `fuel_cell_orc` | 10 | one ORC on the fuel-cell group (shared exhaust) |

Presence is tested with `HasField("orc")`.

### 2.3 Result (`feems_result.proto`)

`FeemsResult.energy_input_waste_heat_recovery_total_mj = 17`.

## 3. feems

### 3.1 Component (`component_electric.py`)

```python
class OrganicRankineCycle(ElectricComponent):
    def __init__(self, name, rated_power, switchboard_id=SwbId(0), uid=None):
        super().__init__(TypeComponent.ORGANIC_RANKINE_CYCLE, name, rated_power,
                         power_type=TypePower.POWER_SOURCE,
                         switchboard_id=switchboard_id, uid=uid)
```

No efficiency and no fuel: the electric output is the quantity of interest; the heat side is the client's concern.

**Operation:** the caller sets `status = 1` and `load_sharing_mode = power / rated_power` for each timestep. This uses the existing fixed load-sharing path in `ElectricPowerSystem`: sources with `load_sharing_mode > 0` deliver exactly that share of their rating, and sources with `load_sharing_mode == 0` share the remaining load. No change to the dispatch logic was needed.

### 3.2 Power-source registration (`system_model.py`)

`OrganicRankineCycle` is added to the tuple of classes accepted as `TypePower.POWER_SOURCE` in `ElectricPowerSystem.__init__`, and to the error message.

### 3.3 Energy balance (`node.py`)

```python
elif component.type == TypeComponent.ORGANIC_RANKINE_CYCLE:
    res.energy_input_waste_heat_recovery_total_mj = integrate_data(component.power_output, ...) / 1000
```

`_assign_operating_avg_metrics`: `operating_avg_power_kw` over `power_output != 0`; efficiency and SFC stay `0.0` (no fuel input).

### 3.4 Power balance rounding residual (`system_model.py`)

When fixed-setpoint sources cover the whole bus load, `sum_load` for the balancing sources is a floating-point residual (order 1e-12 kW) while `sum_power_avail` is 0 because no balancing source is on. The old code computed `residual / 0` → inf load ratio → NaN downstream.

```python
is_rounding_residual_without_balancing_power = (sum_power_avail == 0) & (np.abs(sum_load) < 1e-6)
index_non_zero = (sum_load != 0) & ~is_rounding_residual_without_balancing_power
```

Only the case "no balancing power **and** |load| < 1e-6 kW" changes. A real load without balancing power keeps the previous behaviour (it is still flagged as non-zero and the caller sees the overload).

## 4. Conversion (`MachSysS`)

### 4.1 proto → feems (`convert_to_feems.py`)

```
convert_proto_propulsion_system_to_feems
  └─ MECHANICAL / HYBRID:
       collect_orcs_on_switchboards(system)        → {switchboard_id: [OrganicRankineCycle]}
       convert_proto_electric_system_to_feems(..., additional_components_by_switchboard=...)
         ├─ unknown switchboard ids → ValueError
         └─ convert_proto_switchboard_to_feems(..., additional_components=...)
```

`collect_orcs_on_switchboards` walks `mechanical_system.shaft_lines[*].subsystems[*]` (`engine` or `multi_fuel_engine`) and skips an ORC when:

| Condition | Reason |
|-----------|--------|
| no `orc` field | no ORC |
| `switchboard_id == 0` | integrated in host (handled by client) |
| `rated_power_kw <= 0` | feems components reject a zero rating; an unrated ORC has no output |

ELECTRIC propulsion has no main engines on shaft lines, so no ORC sources are collected there. Genset ORCs (on `Genset.engine`) are never collected because gensets are switchboard subsystems, not shaft-line subsystems.

### 4.2 feems → proto (`convert_to_protobuf.py`)

`convert_switchboard_to_protobuf` skips components of type `ORGANIC_RANKINE_CYCLE`: the ORC is stored on its host engine, and writing it as a switchboard subsystem would duplicate it on the next proto → feems conversion.

### 4.3 Result conversion (`convert_feems_result_to_proto.py`)

The time-series collector accepts `ORGANIC_RANKINE_CYCLE` as a power source (power output only, no fuel series) instead of raising `NotImplementedError`.

## 5. Backwards compatibility

- Proto: new message and new tags only; old data reads with no ORC, old readers ignore the new fields.
- feems: new enum value and new dataclass field with default; no existing signature changed. `convert_proto_switchboard_to_feems` and `convert_proto_electric_system_to_feems` gain optional keyword arguments.
- Power balance: behaviour changes only for |load| < 1e-6 kW with zero balancing power, which previously produced inf/NaN.

## 6. Edge cases

| Case | Behaviour |
|------|-----------|
| ORC setpoint covers the whole bus load | gensets get zero load, no NaN (§3.4) |
| ORC on a switchboard that does not exist | `ValueError` at conversion |
| ORC with `rated_power_kw = 0` | not converted |
| ORC with `switchboard_id = 0` on a main engine | not converted (client may integrate it) |
| Round trip proto → feems → proto | ORC stays on the host engine, not duplicated on the switchboard |
| ORC setpoint never set (`status = 0`) | zero output, zero recovered energy |

## 7. Validation plan

- `feems/tests/test_system_simplified.py::TestOrganicRankineCycle` — power-source registration, setpoint reduces balancing unit, no fuel and recovered energy, rounding residual without NaN, real load without balancing power unchanged.
- `machinery-system-structure/tests/test_convert_to_feems.py::TestConvertOrganicRankineCycle` — main engine ORC becomes a source, integrated ORC not converted, zero-rated ORC not converted, unknown switchboard raises, conversion back to proto skips the ORC.

## 8. Out of scope

- ORC thermodynamics and host-curve lifting (client side).
- Dispatch of the ORC setpoint in `RunFEEMSSim` PMS — the client provides the setpoint.
- ORC on COGES / COGAS hosts.
