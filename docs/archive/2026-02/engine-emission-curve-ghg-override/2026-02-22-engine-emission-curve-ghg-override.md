# Design: Engine-Defined CH4/N2O Emission Curves Override GHG Factors

**Issue:** #85
**Branch:** `feature/issue-85-engine-emission-curve-ghg-override`
**Plan:** `docs/01-plan/2026-02-22-engine-emission-curve-ghg-override.md`

---

## 1. Context

`Engine._emissions_per_kwh_interp` is a `Dict[EmissionType, Callable]` populated
at construction from `emissions_curves: List[EmissionCurve]`. It already supports
`EmissionType.CH4` and `EmissionType.N2O` (g_gas/kWh at a given load ratio).

`GhgEmissionFactorTankToWake` holds flat scalar factors:

```python
@dataclass
class GhgEmissionFactorTankToWake:
    co2_factor_gco2_per_gfuel: float
    ch4_factor_gch4_per_gfuel: float   # ← to be overridden when CH4 curve present
    n2o_factor_gn2o_per_gfuel: float   # ← to be overridden when N2O curve present
    c_slip_percent: float               # ← zeroed when CH4 curve present
    fuel_consumer_class: Optional[...]
```

These are the only two data structures that need to change.

---

## 2. Unit Conversion

Emission curves supply `E_gas [g_gas/kWh]`; `GhgEmissionFactorTankToWake`
requires `F_gas [g_gas/g_fuel]`. The bridge is BSFC `[g_fuel/kWh]`:

```
F_gas = E_gas(load_ratio) / BSFC(load_ratio)
```

For `Engine` (BSFC-based), `bsfc_g_per_kwh` is computed first, so this division
is trivial. For `COGAS` (efficiency-based), the equivalent BSFC is derived from
the fuel consumption already computed:

```
bsfc_equivalent_g_per_kwh = fuel_consumption_kg_per_s * 1000 / (power_kw / 3600)
```

---

## 3. New Method: `Fuel.with_emission_curve_ghg_overrides()`

**Location:** `feems/feems/fuel.py`, inside the `Fuel` class.

```python
def with_emission_curve_ghg_overrides(
    self,
    ch4_factor_gch4_per_gfuel: Optional[float] = None,
    n2o_factor_gn2o_per_gfuel: Optional[float] = None,
) -> "Fuel":
    """Return a copy with CH4 and/or N2O GHG factors replaced by curve-derived values.

    When ch4_factor_gch4_per_gfuel is provided, c_slip_percent is set to 0 in all
    GhgEmissionFactorTankToWake entries to prevent double-counting: the emission
    curve already captures total methane (combusted + slipped).

    If both arguments are None, returns self unchanged.

    Args:
        ch4_factor_gch4_per_gfuel: Curve-derived factor in gCH4/gfuel, or None.
        n2o_factor_gn2o_per_gfuel: Curve-derived factor in gN2O/gfuel, or None.

    Returns:
        A new Fuel object with updated GhgEmissionFactorTankToWake entries.
    """
    if ch4_factor_gch4_per_gfuel is None and n2o_factor_gn2o_per_gfuel is None:
        return self

    import copy, dataclasses
    new_ttw = [
        dataclasses.replace(
            entry,
            ch4_factor_gch4_per_gfuel=(
                ch4_factor_gch4_per_gfuel
                if ch4_factor_gch4_per_gfuel is not None
                else entry.ch4_factor_gch4_per_gfuel
            ),
            n2o_factor_gn2o_per_gfuel=(
                n2o_factor_gn2o_per_gfuel
                if n2o_factor_gn2o_per_gfuel is not None
                else entry.n2o_factor_gn2o_per_gfuel
            ),
            c_slip_percent=(0.0 if ch4_factor_gch4_per_gfuel is not None else entry.c_slip_percent),
        )
        for entry in self.ghg_emission_factor_tank_to_wake
    ]
    new_fuel = copy.copy(self)          # shallow copy bypasses __init__ assertions
    new_fuel.ghg_emission_factor_tank_to_wake = new_ttw
    return new_fuel
```

**Why `copy.copy` instead of re-calling `__init__`:**
`Fuel.__init__` asserts that IMO/EU fuels must not receive explicit
`ghg_emission_factor_tank_to_wake`. A shallow copy bypasses that guard while
still producing a fresh object — the same approach as existing internal helpers.

---

## 4. Changes to `Engine.get_engine_run_point_from_power_out_kw()`

**Location:** `feems/feems/components_model/component_mechanical.py`, `Engine` class.

Insert after `fuel_consumption_component` is constructed (currently line ~230)
and before the `return EngineRunPoint(...)`:

```python
# --- emission-curve GHG override -------------------------------------------
_ch4_g_per_kwh = (
    self.emissions_g_per_kwh(EmissionType.CH4, load_ratio)
    if EmissionType.CH4 in self._emissions_per_kwh_interp
    else None
)
_n2o_g_per_kwh = (
    self.emissions_g_per_kwh(EmissionType.N2O, load_ratio)
    if EmissionType.N2O in self._emissions_per_kwh_interp
    else None
)
if _ch4_g_per_kwh is not None or _n2o_g_per_kwh is not None:
    fuel_consumption_component = fuel_consumption_component.with_emission_curve_ghg_overrides(
        ch4_factor_gch4_per_gfuel=(
            _ch4_g_per_kwh / bsfc_g_per_kwh if _ch4_g_per_kwh is not None else None
        ),
        n2o_factor_gn2o_per_gfuel=(
            _n2o_g_per_kwh / bsfc_g_per_kwh if _n2o_g_per_kwh is not None else None
        ),
    )
# ---------------------------------------------------------------------------
```

**`EngineDualFuel` is handled automatically** — it calls
`super().get_engine_run_point_from_power_out_kw()` for the main fuel. The pilot
fuel is a separate `Fuel` constructed without CH4/N2O curves, so it is unaffected.

---

## 5. Changes to `COGAS.get_gas_turbine_run_point_from_power_output_kw()`

**Location:** `feems/feems/components_model/component_mechanical.py`, `COGAS` class.

Insert after `fuel.mass_or_mass_fraction = fuel_consumption_kg_per_s` (line ~882)
and before constructing `COGASRunPoint`:

```python
# --- emission-curve GHG override -------------------------------------------
_ch4_g_per_kwh = (
    self.emissions_g_per_kwh(EmissionType.CH4, load_ratio)
    if EmissionType.CH4 in self._emissions_per_kwh_interp
    else None
)
_n2o_g_per_kwh = (
    self.emissions_g_per_kwh(EmissionType.N2O, load_ratio)
    if EmissionType.N2O in self._emissions_per_kwh_interp
    else None
)
if _ch4_g_per_kwh is not None or _n2o_g_per_kwh is not None:
    _power_kwh_per_s = power_kw / 3600
    _bsfc_eq_g_per_kwh = fuel_consumption_kg_per_s * 1000 / _power_kwh_per_s
    fuel = fuel.with_emission_curve_ghg_overrides(
        ch4_factor_gch4_per_gfuel=(
            _ch4_g_per_kwh / _bsfc_eq_g_per_kwh if _ch4_g_per_kwh is not None else None
        ),
        n2o_factor_gn2o_per_gfuel=(
            _n2o_g_per_kwh / _bsfc_eq_g_per_kwh if _n2o_g_per_kwh is not None else None
        ),
    )
# ---------------------------------------------------------------------------
```

---

## 6. Unit Tests

**Location:** `feems/tests/test_fuel.py` (new test functions at end of file).

### 6.1 Helper fixture

```python
def _make_engine_with_emission_curves(
    bsfc_flat: float,
    ch4_g_per_kwh: Optional[float] = None,
    n2o_g_per_kwh: Optional[float] = None,
) -> Engine:
    """Engine with flat BSFC and optional flat emission curves for CH4/N2O."""
    curves = []
    if ch4_g_per_kwh is not None:
        curves.append(EmissionCurve(
            points_per_kwh=[EmissionCurvePoint(0.0, ch4_g_per_kwh),
                            EmissionCurvePoint(1.0, ch4_g_per_kwh)],
            emission=EmissionType.CH4,
        ))
    if n2o_g_per_kwh is not None:
        curves.append(EmissionCurve(
            points_per_kwh=[EmissionCurvePoint(0.0, n2o_g_per_kwh),
                            EmissionCurvePoint(1.0, n2o_g_per_kwh)],
            emission=EmissionType.N2O,
        ))
    return Engine(
        type_=TypeComponent.MAIN_ENGINE,
        nox_calculation_method=NOxCalculationMethod.TIER_3,
        rated_power=1000.0,
        rated_speed=1000.0,
        bsfc_curve=np.array([[0.0, bsfc_flat], [1.0, bsfc_flat]]),
        fuel_type=TypeFuel.DIESEL,
        fuel_origin=FuelOrigin.FOSSIL,
        emissions_curves=curves or None,
    )
```

### 6.2 Test cases

| Test | What it verifies |
|------|-----------------|
| `test_ch4_curve_overrides_ghg_factor` | CH4 curve present → `ch4_factor` in the run-point Fuel equals `CH4_g_per_kwh / BSFC`; `c_slip_percent == 0`; N2O factor unchanged |
| `test_n2o_curve_overrides_ghg_factor` | N2O curve present → `n2o_factor` equals `N2O_g_per_kwh / BSFC`; CH4 factor and slip unchanged |
| `test_both_curves_override_ghg_factors` | Both curves → both factors overridden, slip zeroed |
| `test_no_curves_ghg_factor_unchanged` | No CH4/N2O curves → `ghg_emission_factor_tank_to_wake` unchanged (regression) |

Each test retrieves `engine_run_point.fuel_flow_rate_kg_per_s.fuels[0].ghg_emission_factor_tank_to_wake[0]`
and asserts the expected field values with `pytest.approx`.

### 6.3 `Fuel.with_emission_curve_ghg_overrides()` unit tests

| Test | What it verifies |
|------|-----------------|
| `test_with_emission_curve_ghg_overrides_ch4_only` | Only `ch4_factor` changes; `n2o_factor` stays; `c_slip_percent` → 0 |
| `test_with_emission_curve_ghg_overrides_n2o_only` | Only `n2o_factor` changes; `ch4_factor` stays; `c_slip_percent` unchanged |
| `test_with_emission_curve_ghg_overrides_no_args_returns_self` | Both None → returns same object (identity) |
| `test_with_emission_curve_ghg_overrides_preserves_co2_factor` | `co2_factor_gco2_per_gfuel` is never touched |
| `test_with_emission_curve_ghg_overrides_all_entries_updated` | Fuel with multiple `GhgEmissionFactorTankToWake` entries (EU fuel) → all entries updated |
| `test_with_emission_curve_ghg_overrides_original_unchanged` | Original `Fuel` object is not mutated |

---

## 7. Implementation Order

1. `fuel.py` — add `with_emission_curve_ghg_overrides()` method.
2. `component_mechanical.py` — apply override in `Engine` run-point.
3. `component_mechanical.py` — apply override in `COGAS` run-point.
4. `test_fuel.py` — all new tests.
5. `uv run pytest feems/tests/` — must pass green.

---

## 8. Non-Changes (Scope Boundary)

- Proto / MachSysS: emission curves already round-trip correctly; no change.
- `RunFEEMSSim`: calls `get_engine_run_point_from_power_out_kw()` unchanged.
- WtT (well-to-tank) path: unaffected.
- FuelCell / battery / electric components: no CH4/N2O curves; unaffected.
- `Fuel.__init__` signature: unchanged.
- `GhgEmissionFactorTankToWake` class definition: unchanged (we use `dataclasses.replace`).
