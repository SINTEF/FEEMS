# Design: Per-Component Performance Metrics

**Plan:** `docs/01-plan/features/per-component-performance-metrics.plan.md`
**Issue:** #97
**Date:** 2026-05-20
**Author:** Kevin Koosup Yum
**Status:** Approved

---

## 1. Context

`FEEMSResult.detail_result` is a `pd.DataFrame` with one row per fuel-consumer / power-source / energy-storage / load component. Each row currently reports cumulative quantities (fuel, energy, hours, emissions) plus type metadata. Users need three operating-point metrics not derivable from the cumulative columns alone:

- **Average power load** while the component is operating
- **Average efficiency** while the component is operating
- **Average specific fuel consumption (SFC)** while the component is operating

A naive duration-weighted mean would include shut-down periods and produce misleading numbers. We compute every average **only over the on-state timesteps**.

PTI/PTO is the one bidirectional component. A single signed average would conflate motoring and generation, so we add a dedicated **`operating_avg_reversible_power_kw`** field — populated only for PTI/PTO, zero elsewhere.

---

## 2. New fields

### 2.1 On `FEEMSResult` (`feems/feems/types_for_feems.py`)

```python
@dataclass
class FEEMSResult:
    ...
    operating_avg_power_kw: float = 0.0
    operating_avg_reversible_power_kw: float = 0.0
    operating_avg_efficiency: float = 0.0
    operating_avg_sfc_g_per_kwh: float = 0.0
```

`__merge` handles these in the default branch with `max(self_value, other_value)`. Rationale: each `detail_result` row originates from exactly one component, and `sum_with_freeze_duration` is called once per component into a single aggregator. The aggregator never sees two non-zero values for the same field, so `max` correctly picks the populated one. This avoids inventing time-weighted aggregation rules that have no real semantics here.

### 2.2 DataFrame column labels

Appended after the existing `"fuel consumer type"` column, in this order:

| Position | Label                                  |
|----------|----------------------------------------|
| 12       | `"operating avg power [kW]"`           |
| 13       | `"operating avg reversible power [kW]"`|
| 14       | `"operating avg efficiency"`           |
| 15       | `"operating avg SFC [g/kWh]"`          |

### 2.3 Proto `ResultPerComponent` (`machinery-system-structure/proto/feems_result.proto`)

```proto
message ResultPerComponent {
    ...                                          // IDs 1-15 unchanged
    double operating_avg_power_kw            = 16;
    double operating_avg_reversible_power_kw = 17;
    double operating_avg_efficiency          = 18;
    double operating_avg_sfc_g_per_kwh       = 19;
}
```

### 2.4 Converter mapping (`MachSysS/convert_feems_result_to_proto.py:_COLUMN_NAMES`)

```python
_COLUMN_NAMES = {
    ...                                                                       # existing keys
    "operating avg power [kW]":             "operating_avg_power_kw",
    "operating avg reversible power [kW]":  "operating_avg_reversible_power_kw",
    "operating avg efficiency":             "operating_avg_efficiency",
    "operating avg SFC [g/kWh]":            "operating_avg_sfc_g_per_kwh",
}
```

---

## 3. Computation

### 3.1 On-state mask

```python
power_array = np.atleast_1d(component.power_output)
dt          = np.atleast_1d(time_interval_s)            # broadcast/match length
mask        = power_array != 0.0                        # matches existing running_hours_h
on_dt       = dt[mask] if dt.size == mask.size else dt  # scalar dt → scalar
on_time_s   = on_dt.sum()
```

For PTI/PTO, two masks (matching `node.py:284-331`):

```python
pti_mask = component.power_input > 0   # electric in → mechanical out
pto_mask = component.power_input < 0   # mechanical in → electric out
```

### 3.2 Helper module-level functions (added in `feems/feems/components_model/node.py`)

```python
def _time_weighted_avg_magnitude_kw(
    power_signal: np.ndarray, dt_s: np.ndarray, mask: np.ndarray,
) -> float:
    """Return ⟨|P|⟩ over the masked subset of timesteps.  0.0 if mask is empty."""
    p   = np.atleast_1d(power_signal)
    dt  = np.atleast_1d(dt_s)
    m   = np.atleast_1d(mask)
    if dt.size == 1:
        # Scalar dt → uniform timestep → mean of |p[mask]|
        sel = np.abs(p[m]) if p.size == m.size else np.abs(p) * m
        return float(sel.mean()) if sel.size else 0.0
    sel_p  = np.abs(p)[m] if p.size == m.size else np.abs(p) * m
    sel_dt = dt[m] if dt.size == m.size else dt
    total  = sel_dt.sum()
    return float((sel_p * sel_dt).sum() / total) if total > 0 else 0.0


def _efficiency_from_totals(energy_out_mj: float, energy_in_mj: float) -> float:
    """Clamp to [0, 1]; 0.0 if energy_in is 0."""
    if energy_in_mj <= 0:
        return 0.0
    return max(0.0, min(1.0, energy_out_mj / energy_in_mj))


def _sfc_g_per_kwh(total_fuel_kg: float, useful_energy_kwh: float) -> float:
    """0.0 if useful_energy is 0."""
    if useful_energy_kwh <= 0:
        return 0.0
    return total_fuel_kg * 1000.0 / useful_energy_kwh
```

### 3.3 Per-component-type assignment

Inside `get_fuel_emission_energy_balance_for_component` (already a giant if/elif by component type), each branch assigns the four scalars before returning. Pseudocode below; "fuel_kg" means `res.multi_fuel_consumption_total_kg.total_fuel_consumption`, "fuel_mj" means `res.fuel_energy_total_mj`.

| Component branch                                              | `operating_avg_power_kw`           | `operating_avg_reversible_power_kw` | `operating_avg_efficiency`            | `operating_avg_sfc_g_per_kwh`                          |
|---------------------------------------------------------------|------------------------------------|-------------------------------------|---------------------------------------|--------------------------------------------------------|
| `MAIN_ENGINE` / `MAIN_ENGINE_WITH_GEARBOX`                    | avg \|P_shaft\| over on-state      | `0.0`                               | `mech_total_mj / fuel_mj`             | `fuel_kg × 1000 / mech_kwh`                            |
| `GENSET`                                                      | avg \|P_elec_out\| over on-state   | `0.0`                               | `elec_out_mj / fuel_mj`               | `fuel_kg × 1000 / elec_out_kwh`                        |
| `FUEL_CELL` / `FUEL_CELL_SYSTEM`                              | avg \|P_elec_out\| over on-state   | `0.0`                               | `elec_out_mj / fuel_mj`               | `fuel_kg × 1000 / elec_out_kwh`                        |
| `COGES`                                                       | avg \|P_elec_out\| over on-state   | `0.0`                               | `elec_out_mj / fuel_mj`               | `fuel_kg × 1000 / elec_out_kwh`                        |
| `PTI_PTO_SYSTEM`                                              | avg \|P_elec_out\| over **PTO** subset | avg \|P_elec_in\| over **PTI** subset | `total_e_out / total_e_in` over union | `0.0`                                                  |
| `GENERATOR`                                                   | avg \|P_elec\| over on-state       | `0.0`                               | `e_out_mj / e_in_mj` if both > 0      | `0.0`                                                  |
| `BATTERY_SYSTEM` / `SUPER_CAPACITOR_SYSTEM` (and bare classes)| avg \|net flow\| over on-state     | `0.0`                               | `0.0`                                 | `0.0`                                                  |
| `SHORE_POWER`                                                 | avg \|P_in\| over on-state         | `0.0`                               | `0.0`                                 | `0.0`                                                  |
| `OTHER_LOAD` / `OTHER_MECHANICAL_LOAD`                        | avg \|P\| over on-state            | `0.0`                               | `0.0`                                 | `0.0`                                                  |
| `PROPELLER_LOAD` / `PROPULSION_DRIVE`                         | avg \|P\| over on-state            | `0.0`                               | `0.0`                                 | `0.0`                                                  |
| `STEAM_BOILER` (assigned in `system_model._calculate_boiler_result`, not in this function) | avg \|P_steam_thermal\| over on-state | `0.0`                               | from `BoilerRunPoint.thermal_efficiency`, weighted | `fuel_kg × 1000 / steam_kwh_thermal`                   |

### 3.4 Engine "mechanical energy out" for SFC and efficiency

For `MAIN_ENGINE` / `MAIN_ENGINE_WITH_GEARBOX` we compute shaft kWh on-the-fly inside the branch (mirroring the existing GENSET aux-engine shaft-energy treatment in `node.py:214-246`):

```python
mech_out_mj = integrate_data(
    data_to_integrate=component.engine.power_output,
    time_interval_s=time_interval_s,
    integration_method=integration_method,
) / 1000.0     # kW·s → MJ ; divide-by-1000 because integrate_data returns kW·s = kJ
```

(`integrate_data` already exists; see existing main-engine branch.)

For `GENSET`, the genset branch already sets `res.energy_consumption_mechanical_total_mj` (engine shaft). For "out" we want **electric** energy out:

```python
elec_out_mj = integrate_data(
    data_to_integrate=component.power_output,   # generator side
    time_interval_s=time_interval_s,
    integration_method=integration_method,
) / 1000.0
```

For `FUEL_CELL` / `FUEL_CELL_SYSTEM` the `power_output` is electric; same integration.

For `COGES` the `coges_run_point` already carries the right energy; we use `component.power_output` (electric side) integrated.

### 3.5 PTI/PTO efficiency

PTI/PTO is bidirectional. Following the existing energy-balance logic in `node.py:284-331`, electric and mechanical sides exist on every timestep:

```python
# total mechanical and electric energies (already computed in the branch)
e_elec_in   = res.energy_consumption_electric_total_mj  # PTI side
e_elec_out  = res.energy_input_electric_total_mj        # PTO side
e_mech_in   = res.energy_input_mechanical_total_mj      # PTO side (shaft in)
e_mech_out  = res.energy_consumption_mechanical_total_mj # PTI side (shaft out)
```

Total useful energy out / total energy in (both directions summed):
```python
energy_out = e_elec_out + e_mech_out
energy_in  = e_elec_in  + e_mech_in
res.operating_avg_efficiency = _efficiency_from_totals(energy_out, energy_in)
```

A single number is sufficient because `SerialSystemElectric.efficiency` is a function of load only (not direction) in the current model.

### 3.6 Boiler-row computation (in `system_model._calculate_boiler_result`)

`BoilerRunPoint` already provides `steam_production_kg_per_s`, `thermal_efficiency`, and `fuel_flow_rate_kg_per_s`. We compute:

```python
steam_kw_thermal_series = rp.steam_production_kg_per_s * dh_kj_per_kg  # kW = kJ/s = kg/s × kJ/kg
mask                    = rp.steam_production_kg_per_s > 0
avg_power_kw            = _time_weighted_avg_magnitude_kw(steam_kw_thermal_series, dt, mask)

fuel_energy_mj          = boiler_fc.fuel_energy_total_mj_via_helper        # see §3.7
steam_energy_mj         = integrate_data(steam_kw_thermal_series, dt, im) / 1000.0
avg_eff                 = _efficiency_from_totals(steam_energy_mj, fuel_energy_mj)
avg_sfc                 = _sfc_g_per_kwh(boiler_fc.total_fuel_consumption, steam_energy_mj / 3.6)
```

`dh_kj_per_kg` = saturated steam enthalpy at working pressure minus feed-water enthalpy, both already used inside `SteamBoiler.get_boiler_run_point` — we expose it via an existing helper or recompute locally with the existing module-level functions.

### 3.7 Fuel energy helper

`FEEMSResult` already has `fuel_energy_total_mj` (property at `types_for_feems.py:69-74`). For per-component `res`, the same property is available because we attach the per-component fuel onto `res.multi_fuel_consumption_total_kg`. We reuse it directly:

```python
fuel_mj = res.fuel_energy_total_mj
```

For boiler we use `boiler_fc.fuels[i].lhv_mj_per_g * boiler_fc.fuels[i].mass_or_mass_fraction * 1e3` summed — identical formula, applied to `boiler_fc` directly since it is a `FuelConsumption`, not a `FEEMSResult`.

---

## 4. Wiring

### 4.1 Switchboard assembly (`node.py:Switchboard.get_fuel_energy_consumption_running_time`)

Existing column list (line ~893) gains 4 entries; `data_to_add` (line ~945) gains 4 reads from `res_comp`.

```python
column_names = [
    ...                                  # existing
    "operating avg power [kW]",
    "operating avg reversible power [kW]",
    "operating avg efficiency",
    "operating avg SFC [g/kWh]",
]

data_to_add = [
    *res_comp.to_list_for_electric_component(),
    component.type.name,
    component.rated_capacity,
    component.rated_capacity_unit,
    (... fuel consumer ...),
    res_comp.operating_avg_power_kw,
    res_comp.operating_avg_reversible_power_kw,
    res_comp.operating_avg_efficiency,
    res_comp.operating_avg_sfc_g_per_kwh,
]
```

### 4.2 ShaftLine assembly (`node.py:ShaftLine.get_fuel_energy_consumption_running_time`)

Identical pattern at line ~1385/1434.

### 4.3 Boiler assembly (`system_model.py:_calculate_boiler_result`)

`_BOILER_DETAIL_COLUMNS` (module-level constant, currently 11 entries) gains 4 entries. `detail_row` (line ~350) gains 4 numeric values.

To prevent column-order drift between the three assembly sites, all three import the same constant from a single source. Concretely: define `OPERATING_AVG_COLUMNS = (...)` once in `feems/feems/types_for_feems.py` (alongside the dataclass) and import it where needed.

---

## 5. Backwards compatibility

- **Proto:** Fields 16-19 are additive. Old clients ignore them; new clients read `0.0` for messages produced by old code. No tag renumbered.
- **DataFrame:** Columns appended at the end; column index numerically preserved. Existing tests reading by **label** (e.g. `detail_result["running hours [h]"]`) continue to work. Existing tests reading by **position** would shift; a grep shows the only positional access is internal (`to_list_for_*_component()`), which is unaffected.
- **`FEEMSResult` dataclass:** New fields default to `0.0`; constructor calls without these kwargs continue to work.
- **`__merge`:** New fields fall into the existing default branch (`value = self_value + other_value`). To avoid summing two populated values across multiple rounds, we add an explicit branch for the four fields that takes `max`. Equivalent for the no-overlap case (one side is always 0) and safe.

---

## 6. Edge cases

| Case                                                                   | Expected behaviour                                                                                                   |
|------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| Component is off the entire simulation                                  | All four metrics = `0.0`. Mask is empty → guarded by `total > 0` check in helper.                                    |
| `time_interval_s` is a scalar (uniform timestep)                        | Helper detects scalar dt and falls back to `mean(|p|[mask])`. Verified in test fixture.                              |
| `power_output` is itself a scalar                                       | Helper broadcasts; result equals `|p|` if mask is True else `0.0`. Consistent with existing one-step engine tests.   |
| PTI/PTO never enters PTI mode                                           | `operating_avg_reversible_power_kw = 0.0`; PTO branch populated normally.                                            |
| PTI/PTO that's purely PTI                                               | `operating_avg_power_kw = 0.0`; `operating_avg_reversible_power_kw` populated.                                       |
| Engine running with zero fuel (theoretical)                             | `efficiency = 0.0`, `sfc = 0.0` — guarded by zero-denominator checks.                                                |
| Boiler with zero steam demand on every timestep                         | All four metrics = `0.0`.                                                                                            |
| Multiple components of the same `type` in one switchboard               | Each contributes its own row; no aggregation across rows for these fields.                                           |

---

## 7. Validation plan (referenced from Plan T8)

Each component-family test follows this pattern:

```python
def test_engine_operating_avg_metrics():
    # Fixture: known BSFC curve, LHV, power signal with 50 % off-time
    engine = Engine(name="E1", ...)
    engine.power_output = np.array([0, 100, 100, 100, 0, 100], dtype=float)
    dt = np.array([60, 60, 60, 60, 60, 60], dtype=float)   # 6 minutes

    res = get_fuel_emission_energy_balance_for_component(
        component=engine, time_interval_s=dt, integration_method=IntegrationMethod.SIMPSON,
    )

    expected_avg_power = 100.0          # 4 on-state timesteps × 100 kW / 4
    np.testing.assert_allclose(res.operating_avg_power_kw, expected_avg_power, rtol=1e-9)

    expected_eff = mech_kwh_total / fuel_mj_total
    np.testing.assert_allclose(res.operating_avg_efficiency, expected_eff, rtol=1e-6)
    ...
```

PTI/PTO test uses one fixture with mixed sign:

```python
pti_pto.power_input = np.array([-50, -50, 0, +30, +30, 0])   # PTO, PTO, off, PTI, PTI, off
# expected: operating_avg_power_kw = 50, operating_avg_reversible_power_kw = 30
```

---

## 8. Out-of-scope (deferred)

- Per-timestep series of these metrics (`result_time_series` already covers raw power & fuel)
- Load ratio vs rated capacity column (trivial follow-up; one more field)
- Battery round-trip efficiency (would need cycle-aware accounting)
- Configurable averaging window (whole run is sufficient for now)
