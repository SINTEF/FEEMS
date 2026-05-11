"""Tests for T1 (saturated steam table), T2 (SteamBoiler core),
T3 (curve normalisation), T4 (multi-fuel support), and T5 (FEEMSResult boiler fields).
"""

import numpy as np
import pytest
from feems.exceptions import InputError
from feems.fuel import FuelConsumption, FuelOrigin, TypeFuel
from feems.types_for_feems import EmissionCurve, EmissionCurvePoint, EmissionType, TypeComponent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flat_efficiency_curve(eta: float) -> np.ndarray:
    """Return a trivial [[load_ratio, eta]] curve (constant efficiency)."""
    return np.array([[0.25, eta], [0.50, eta], [0.75, eta], [1.00, eta]])


def _make_boiler(
    rated_kg_per_h: float = 10_000.0,
    pressure_barg: float = 6.0,
    eta: float = 0.85,
    feed_water_temp_c: float = 80.0,
    fuel_type: TypeFuel = TypeFuel.HFO,
    fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
    emissions_curves=None,
):
    from feems.components_model.component_mechanical import SteamBoiler

    return SteamBoiler(
        name="test boiler",
        rated_steam_production_kg_per_h=rated_kg_per_h,
        working_pressure_barg=pressure_barg,
        thermal_efficiency_curve=_flat_efficiency_curve(eta),
        fuel_type=fuel_type,
        fuel_origin=fuel_origin,
        feed_water_temperature_c=feed_water_temp_c,
        emissions_curves=emissions_curves,
    )


# ---------------------------------------------------------------------------
# T1 — Saturated steam lookup table
# ---------------------------------------------------------------------------


class TestSteamTable:
    def test_known_value_at_10_bar(self):
        from feems.constant import get_saturated_steam_h_g_kj_per_kg

        h_g = get_saturated_steam_h_g_kj_per_kg(10.0)
        assert abs(h_g - 2778.9) / 2778.9 < 0.001, f"h_g(10 bar) = {h_g}, expected ≈ 2778.9"

    def test_known_value_at_7_bar(self):
        from feems.constant import get_saturated_steam_h_g_kj_per_kg

        h_g = get_saturated_steam_h_g_kj_per_kg(7.0)
        assert abs(h_g - 2763.1) / 2763.1 < 0.001, f"h_g(7 bar) = {h_g}, expected ≈ 2763.1"

    def test_known_value_at_1_bar(self):
        from feems.constant import get_saturated_steam_h_g_kj_per_kg

        h_g = get_saturated_steam_h_g_kj_per_kg(1.0)
        assert abs(h_g - 2675.6) / 2675.6 < 0.001, f"h_g(1 bar) = {h_g}, expected ≈ 2675.6"

    def test_known_value_at_20_bar(self):
        from feems.constant import get_saturated_steam_h_g_kj_per_kg

        h_g = get_saturated_steam_h_g_kj_per_kg(20.0)
        assert abs(h_g - 2798.3) / 2798.3 < 0.001, f"h_g(20 bar) = {h_g}, expected ≈ 2798.3"

    def test_interpolated_value_increases_monotonically(self):
        from feems.constant import get_saturated_steam_h_g_kj_per_kg

        pressures = np.arange(1.0, 20.1, 0.5)
        values = np.array([get_saturated_steam_h_g_kj_per_kg(p) for p in pressures])
        # h_g should increase with pressure in this range
        assert np.all(np.diff(values) > 0), "h_g should be monotonically increasing with pressure"

    def test_out_of_range_low_raises_input_error(self):
        from feems.constant import get_saturated_steam_h_g_kj_per_kg

        with pytest.raises(InputError):
            get_saturated_steam_h_g_kj_per_kg(0.5)

    def test_out_of_range_high_raises_input_error(self):
        from feems.constant import get_saturated_steam_h_g_kj_per_kg

        with pytest.raises(InputError):
            get_saturated_steam_h_g_kj_per_kg(21.0)

    def test_exact_boundary_1_bar_is_valid(self):
        from feems.constant import get_saturated_steam_h_g_kj_per_kg

        h_g = get_saturated_steam_h_g_kj_per_kg(1.0)
        assert h_g > 0

    def test_exact_boundary_20_bar_is_valid(self):
        from feems.constant import get_saturated_steam_h_g_kj_per_kg

        h_g = get_saturated_steam_h_g_kj_per_kg(20.0)
        assert h_g > 0


# ---------------------------------------------------------------------------
# T2 — SteamBoiler core
# ---------------------------------------------------------------------------


class TestSteamBoilerTypeComponent:
    def test_steam_boiler_enum_value_is_30(self):
        assert TypeComponent.STEAM_BOILER.value == 30

    def test_steam_boiler_enum_name(self):
        assert TypeComponent(30).name == "STEAM_BOILER"


class TestSteamBoilerConstruction:
    def test_construction_sets_name(self):
        boiler = _make_boiler()
        assert boiler.name == "test boiler"

    def test_construction_sets_type(self):
        boiler = _make_boiler()
        assert boiler.type == TypeComponent.STEAM_BOILER

    def test_construction_sets_rated_steam_production(self):
        boiler = _make_boiler(rated_kg_per_h=12_000.0)
        assert boiler.rated_steam_production_kg_per_h == 12_000.0

    def test_construction_sets_working_pressure(self):
        boiler = _make_boiler(pressure_barg=9.0)
        assert boiler.working_pressure_barg == 9.0

    def test_construction_default_feed_water_temp(self):
        boiler = _make_boiler()
        assert boiler.feed_water_temperature_c == 80.0

    def test_construction_custom_feed_water_temp(self):
        boiler = _make_boiler(feed_water_temp_c=60.0)
        assert boiler.feed_water_temperature_c == 60.0

    def test_construction_computes_delta_h(self):
        # Δh = h_g(6 barg = 7 bara) - 4.18 * 80 = 2763.1 - 334.4 ≈ 2428.7 kJ/kg
        boiler = _make_boiler(pressure_barg=6.0, feed_water_temp_c=80.0)
        expected_delta_h = 2763.1 - 4.18 * 80.0
        assert abs(boiler.delta_h_kj_per_kg - expected_delta_h) / expected_delta_h < 0.001

    def test_construction_invalid_pressure_raises(self):
        from feems.components_model.component_mechanical import SteamBoiler

        with pytest.raises(InputError):
            SteamBoiler(
                name="bad boiler",
                rated_steam_production_kg_per_h=10_000.0,
                working_pressure_barg=24.0,
                thermal_efficiency_curve=_flat_efficiency_curve(0.85),
            )

    def test_construction_requires_curve(self):
        from feems.components_model.component_mechanical import SteamBoiler

        with pytest.raises((InputError, ValueError)):
            SteamBoiler(
                name="no curve boiler",
                rated_steam_production_kg_per_h=10_000.0,
                working_pressure_barg=6.0,
            )


class TestSteamBoilerRunPoint:
    """
    Reference boiler:
      rated = 10 000 kg/h, P = 7 bar, η = 0.85, T_fw = 80°C, fuel = HFO fossil
      h_g(7 bar) ≈ 2763.1 kJ/kg
      Δh = 2763.1 - 4.18*80 = 2763.1 - 334.4 = 2428.7 kJ/kg
      HFO LHV = 40 200 kJ/kg
    """

    def setup_method(self):
        self.boiler = _make_boiler(
            rated_kg_per_h=10_000.0,
            pressure_barg=6.0,
            eta=0.85,
            feed_water_temp_c=80.0,
        )
        self.delta_h = self.boiler.delta_h_kj_per_kg
        self.lhv_kj_per_kg = 40_200.0  # HFO IMO

    def test_run_point_returns_boiler_run_point(self):
        from feems.components_model.component_mechanical import BoilerRunPoint

        rp = self.boiler.get_boiler_run_point(np.array([10_000.0]))
        assert isinstance(rp, BoilerRunPoint)

    def test_load_ratio_at_full_load(self):
        rp = self.boiler.get_boiler_run_point(np.array([10_000.0]))
        np.testing.assert_allclose(rp.load_ratio, np.array([1.0]), rtol=1e-6)

    def test_load_ratio_at_half_load(self):
        rp = self.boiler.get_boiler_run_point(np.array([5_000.0]))
        np.testing.assert_allclose(rp.load_ratio, np.array([0.5]), rtol=1e-6)

    def test_steam_production_matches_demand(self):
        demand_kg_per_h = np.array([10_000.0])
        rp = self.boiler.get_boiler_run_point(demand_kg_per_h)
        # steam_production_kg_per_s * 3600 should equal demand_kg_per_h
        np.testing.assert_allclose(
            rp.steam_production_kg_per_s * 3600.0,
            demand_kg_per_h,
            rtol=1e-6,
        )

    def test_energy_balance_holds(self):
        """fuel_power = steam_power / η_th  →  fuel_kg_s * LHV ≈ steam_kg_s * Δh / η"""
        demand_kg_per_h = np.array([10_000.0])
        rp = self.boiler.get_boiler_run_point(demand_kg_per_h)
        fuel_kg_per_s = rp.fuel_flow_rate_kg_per_s.total_fuel_consumption
        steam_kg_per_s = rp.steam_production_kg_per_s
        eta = rp.thermal_efficiency

        fuel_power_kw = fuel_kg_per_s * self.lhv_kj_per_kg
        steam_power_kw = steam_kg_per_s * self.delta_h / eta

        np.testing.assert_allclose(fuel_power_kw, steam_power_kw, rtol=1e-4)

    def test_fuel_consumption_is_fuel_consumption_type(self):
        rp = self.boiler.get_boiler_run_point(np.array([10_000.0]))
        assert isinstance(rp.fuel_flow_rate_kg_per_s, FuelConsumption)

    def test_fuel_type_is_hfo(self):
        rp = self.boiler.get_boiler_run_point(np.array([10_000.0]))
        assert len(rp.fuel_flow_rate_kg_per_s.fuels) == 1
        assert rp.fuel_flow_rate_kg_per_s.fuels[0].fuel_type == TypeFuel.HFO

    def test_zero_demand_gives_zero_fuel(self):
        rp = self.boiler.get_boiler_run_point(np.array([0.0]))
        assert rp.fuel_flow_rate_kg_per_s.total_fuel_consumption == pytest.approx(0.0, abs=1e-10)

    def test_zero_demand_gives_zero_steam(self):
        rp = self.boiler.get_boiler_run_point(np.array([0.0]))
        np.testing.assert_allclose(rp.steam_production_kg_per_s, np.array([0.0]), atol=1e-10)

    def test_thermal_efficiency_matches_curve(self):
        rp = self.boiler.get_boiler_run_point(np.array([10_000.0]))
        np.testing.assert_allclose(rp.thermal_efficiency, np.array([0.85]), rtol=1e-6)

    def test_run_point_with_array_input(self):
        demands = np.array([2_500.0, 5_000.0, 7_500.0, 10_000.0])
        rp = self.boiler.get_boiler_run_point(demands)
        assert rp.load_ratio.shape == (4,)
        assert rp.steam_production_kg_per_s.shape == (4,)
        np.testing.assert_allclose(rp.load_ratio, np.array([0.25, 0.50, 0.75, 1.00]), rtol=1e-6)

    def test_fuel_consumption_increases_with_demand(self):
        demands = np.array([2_500.0, 5_000.0, 7_500.0, 10_000.0])
        rp = self.boiler.get_boiler_run_point(demands)
        fuel_per_step = rp.fuel_flow_rate_kg_per_s.total_fuel_consumption
        assert np.all(np.diff(fuel_per_step) > 0), "Fuel consumption must increase with demand"


class TestSteamBoilerEmissions:
    def test_no_emissions_curves_gives_empty_emissions(self):
        boiler = _make_boiler(emissions_curves=None)
        rp = boiler.get_boiler_run_point(np.array([10_000.0]))
        assert rp.emissions_g_per_s == {}

    def test_nox_emission_curve_tracked(self):
        nox_curve = EmissionCurve(
            points_per_kwh=[
                EmissionCurvePoint(load_ratio=0.25, emission_g_per_kwh=2.0),
                EmissionCurvePoint(load_ratio=0.50, emission_g_per_kwh=2.0),
                EmissionCurvePoint(load_ratio=0.75, emission_g_per_kwh=2.0),
                EmissionCurvePoint(load_ratio=1.00, emission_g_per_kwh=2.0),
            ],
            emission=EmissionType.NOX,
        )
        boiler = _make_boiler(emissions_curves=[nox_curve])
        rp = boiler.get_boiler_run_point(np.array([10_000.0]))
        assert EmissionType.NOX in rp.emissions_g_per_s
        assert rp.emissions_g_per_s[EmissionType.NOX] > 0


# ---------------------------------------------------------------------------
# T3 — Curve normalisation
# ---------------------------------------------------------------------------
#
# Reference boiler: rated=10 000 kg/h, P=7 bar, η=0.85, T_fw=80°C, HFO fossil
#   Δh ≈ 2428.7 kJ/kg   (2763.1 − 4.18×80)
#   HFO LHV = 40 200 kJ/kg
#   sfc = Δh / (η × LHV) = 2428.7 / (0.85 × 40 200) ≈ 0.071077 kg_fuel/kg_steam
#   kg_fuel_per_h at load x = sfc × x × 10 000
# ---------------------------------------------------------------------------

_RATED_KG_PER_H = 10_000.0
_ETA = 0.85
_LOAD_RATIOS = np.array([0.25, 0.50, 0.75, 1.00])


def _equivalent_boilers():
    """Return three SteamBoiler instances built from three equivalent curve representations."""
    from feems.components_model.component_mechanical import SteamBoiler
    from feems.constant import get_saturated_steam_h_g_kj_per_kg
    from feems.fuel import Fuel, FuelOrigin, FuelSpecifiedBy, TypeFuel

    delta_h = get_saturated_steam_h_g_kj_per_kg(7.0) - 4.18 * 80.0
    ref = Fuel(
        fuel_type=TypeFuel.HFO,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.IMO,
        mass_or_mass_fraction=0.0,
    )
    lhv = ref.lhv_mj_per_g * 1e6
    sfc = delta_h / (_ETA * lhv)  # kg_fuel / kg_steam

    eta_curve = np.column_stack([_LOAD_RATIOS, np.full(len(_LOAD_RATIOS), _ETA)])
    sfc_curve = np.column_stack([_LOAD_RATIOS, np.full(len(_LOAD_RATIOS), sfc)])
    kg_per_h_vals = sfc * _LOAD_RATIOS * _RATED_KG_PER_H
    kg_per_h_curve = np.column_stack([_LOAD_RATIOS, kg_per_h_vals])

    common = dict(
        rated_steam_production_kg_per_h=_RATED_KG_PER_H,
        working_pressure_barg=6.0,
        fuel_type=TypeFuel.HFO,
        fuel_origin=FuelOrigin.FOSSIL,
        feed_water_temperature_c=80.0,
    )
    boiler_eta = SteamBoiler(**common, thermal_efficiency_curve=eta_curve)
    boiler_sfc = SteamBoiler(**common, kg_fuel_per_kg_steam_curve=sfc_curve)
    boiler_kph = SteamBoiler(**common, kg_fuel_per_h_curve=kg_per_h_curve)
    return boiler_eta, boiler_sfc, boiler_kph


class TestCurveNormalisation:
    def test_three_equivalent_curves_give_same_fuel_flow_at_half_load(self):
        boiler_eta, boiler_sfc, boiler_kph = _equivalent_boilers()
        demand = np.array([5_000.0])
        rp_eta = boiler_eta.get_boiler_run_point(demand)
        rp_sfc = boiler_sfc.get_boiler_run_point(demand)
        rp_kph = boiler_kph.get_boiler_run_point(demand)
        ref = rp_eta.fuel_flow_rate_kg_per_s.total_fuel_consumption
        np.testing.assert_allclose(
            rp_sfc.fuel_flow_rate_kg_per_s.total_fuel_consumption, ref, rtol=1e-4
        )
        np.testing.assert_allclose(
            rp_kph.fuel_flow_rate_kg_per_s.total_fuel_consumption, ref, rtol=1e-4
        )

    def test_three_equivalent_curves_give_same_fuel_flow_at_full_load(self):
        boiler_eta, boiler_sfc, boiler_kph = _equivalent_boilers()
        demand = np.array([10_000.0])
        rp_eta = boiler_eta.get_boiler_run_point(demand)
        rp_sfc = boiler_sfc.get_boiler_run_point(demand)
        rp_kph = boiler_kph.get_boiler_run_point(demand)
        ref = rp_eta.fuel_flow_rate_kg_per_s.total_fuel_consumption
        np.testing.assert_allclose(
            rp_sfc.fuel_flow_rate_kg_per_s.total_fuel_consumption, ref, rtol=1e-4
        )
        np.testing.assert_allclose(
            rp_kph.fuel_flow_rate_kg_per_s.total_fuel_consumption, ref, rtol=1e-4
        )

    def test_input_error_if_two_curve_types_provided(self):
        from feems.components_model.component_mechanical import SteamBoiler
        from feems.exceptions import InputError

        eta_curve = _flat_efficiency_curve(0.85)
        sfc_val = (2763.1 - 4.18 * 80.0) / (0.85 * 40_200.0)
        sfc_curve = np.column_stack([_LOAD_RATIOS, np.full(4, sfc_val)])
        with pytest.raises(InputError):
            SteamBoiler(
                rated_steam_production_kg_per_h=10_000.0,
                working_pressure_barg=6.0,
                thermal_efficiency_curve=eta_curve,
                kg_fuel_per_kg_steam_curve=sfc_curve,
            )

    def test_input_error_if_no_curve_provided(self):
        from feems.components_model.component_mechanical import SteamBoiler
        from feems.exceptions import InputError

        with pytest.raises((InputError, ValueError)):
            SteamBoiler(
                rated_steam_production_kg_per_h=10_000.0,
                working_pressure_barg=6.0,
            )


# ---------------------------------------------------------------------------
# T4 — Multi-fuel support
# ---------------------------------------------------------------------------

def _make_multi_fuel_boiler(eta_hfo: float = 0.85, eta_lng: float = 0.85):
    """Two-mode boiler: HFO fossil and LNG fossil, each with a flat efficiency curve."""
    from feems.components_model.component_mechanical import FuelCharacteristics, SteamBoiler
    from feems.fuel import FuelOrigin, TypeFuel

    hfo_mode = FuelCharacteristics()
    hfo_mode.main_fuel_type = TypeFuel.HFO
    hfo_mode.main_fuel_origin = FuelOrigin.FOSSIL
    hfo_mode.eff_curve = _flat_efficiency_curve(eta_hfo)

    lng_mode = FuelCharacteristics()
    lng_mode.main_fuel_type = TypeFuel.NATURAL_GAS
    lng_mode.main_fuel_origin = FuelOrigin.FOSSIL
    lng_mode.eff_curve = _flat_efficiency_curve(eta_lng)

    return SteamBoiler(
        name="multi-fuel boiler",
        rated_steam_production_kg_per_h=10_000.0,
        working_pressure_barg=6.0,
        multi_fuel_characteristics=[hfo_mode, lng_mode],
    )


class TestMultiFuelSteamBoiler:
    def test_default_fuel_is_first_mode(self):
        from feems.fuel import FuelOrigin, TypeFuel

        boiler = _make_multi_fuel_boiler()
        assert boiler.fuel_type == TypeFuel.HFO
        assert boiler.fuel_origin == FuelOrigin.FOSSIL

    def test_set_fuel_in_use_switches_to_lng(self):
        from feems.fuel import FuelOrigin, TypeFuel

        boiler = _make_multi_fuel_boiler()
        boiler.set_fuel_in_use(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)
        assert boiler.fuel_type == TypeFuel.NATURAL_GAS

    def test_set_fuel_in_use_unknown_raises_value_error(self):
        from feems.fuel import FuelOrigin, TypeFuel

        boiler = _make_multi_fuel_boiler()
        with pytest.raises(ValueError):
            boiler.set_fuel_in_use(TypeFuel.METHANOL, FuelOrigin.FOSSIL)

    def test_set_fuel_in_use_none_resets_to_first(self):
        from feems.fuel import FuelOrigin, TypeFuel

        boiler = _make_multi_fuel_boiler()
        boiler.set_fuel_in_use(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)
        boiler.set_fuel_in_use()
        assert boiler.fuel_type == TypeFuel.HFO

    def test_fuel_type_reflected_in_run_point(self):
        from feems.fuel import FuelOrigin, TypeFuel

        boiler = _make_multi_fuel_boiler()
        demand = np.array([10_000.0])
        rp_hfo = boiler.get_boiler_run_point(demand)
        assert rp_hfo.fuel_flow_rate_kg_per_s.fuels[0].fuel_type == TypeFuel.HFO

        boiler.set_fuel_in_use(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)
        rp_lng = boiler.get_boiler_run_point(demand)
        assert rp_lng.fuel_flow_rate_kg_per_s.fuels[0].fuel_type == TypeFuel.NATURAL_GAS

    def test_fuel_flow_changes_proportionally_to_lhv_ratio(self):
        """Same η → fuel_flow ratio equals LHV_HFO / LHV_LNG."""
        from feems.fuel import FuelOrigin, TypeFuel

        boiler = _make_multi_fuel_boiler(eta_hfo=0.85, eta_lng=0.85)
        demand = np.array([10_000.0])

        rp_hfo = boiler.get_boiler_run_point(demand)
        boiler.set_fuel_in_use(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)
        rp_lng = boiler.get_boiler_run_point(demand)

        fuel_hfo = rp_hfo.fuel_flow_rate_kg_per_s.total_fuel_consumption
        fuel_lng = rp_lng.fuel_flow_rate_kg_per_s.total_fuel_consumption

        lhv_hfo = 40_200.0
        lhv_lng = 48_000.0
        expected_ratio = lhv_hfo / lhv_lng
        actual_ratio = float((fuel_lng / fuel_hfo).item())
        assert abs(actual_ratio - expected_ratio) / expected_ratio < 1e-4

    def test_single_fuel_boiler_unaffected(self):
        """Single-fuel SteamBoiler behaviour is unchanged after T4 addition."""
        boiler = _make_boiler()
        boiler.set_fuel_in_use()  # no-op for single-fuel
        demand = np.array([5_000.0])
        rp = boiler.get_boiler_run_point(demand)
        assert rp.fuel_flow_rate_kg_per_s.total_fuel_consumption > 0


# ---------------------------------------------------------------------------
# T5 — FEEMSResult new boiler fields + __merge
# ---------------------------------------------------------------------------


def _make_feems_result(running_hr=0.0, steam_kg=0.0, fuel_kg=0.0):
    """Build a minimal FEEMSResult with boiler fields set."""
    from feems.fuel import Fuel, FuelOrigin, FuelSpecifiedBy, TypeFuel
    from feems.types_for_feems import FEEMSResult

    if fuel_kg > 0:
        fuel = Fuel(
            fuel_type=TypeFuel.HFO,
            origin=FuelOrigin.FOSSIL,
            fuel_specified_by=FuelSpecifiedBy.IMO,
            mass_or_mass_fraction=fuel_kg,
        )
        boiler_fc = FuelConsumption(fuels=[fuel])
        total_fc = FuelConsumption(fuels=[fuel])
    else:
        boiler_fc = FuelConsumption()
        total_fc = FuelConsumption()

    return FEEMSResult(
        running_hours_boiler_total_hr=running_hr,
        steam_production_boiler_total_kg=steam_kg,
        fuel_consumption_boiler_total=boiler_fc,
        multi_fuel_consumption_total_kg=total_fc,
    )


class TestFEEMSResultBoilerFields:
    def test_default_running_hours_boiler_is_zero(self):
        from feems.types_for_feems import FEEMSResult

        r = FEEMSResult()
        assert r.running_hours_boiler_total_hr == 0.0

    def test_default_steam_production_boiler_is_zero(self):
        from feems.types_for_feems import FEEMSResult

        r = FEEMSResult()
        assert r.steam_production_boiler_total_kg == 0.0

    def test_default_fuel_consumption_boiler_is_empty(self):
        from feems.types_for_feems import FEEMSResult

        r = FEEMSResult()
        assert isinstance(r.fuel_consumption_boiler_total, FuelConsumption)
        assert r.fuel_consumption_boiler_total.total_fuel_consumption == 0.0

    def test_sum_and_extend_duration_sums_running_hours(self):
        r1 = _make_feems_result(running_hr=1.0)
        r2 = _make_feems_result(running_hr=2.0)
        merged = r1.sum_and_extend_duration(r2)
        assert merged.running_hours_boiler_total_hr == pytest.approx(3.0)

    def test_sum_and_extend_duration_sums_steam_production(self):
        r1 = _make_feems_result(steam_kg=10_000.0)
        r2 = _make_feems_result(steam_kg=5_000.0)
        merged = r1.sum_and_extend_duration(r2)
        assert merged.steam_production_boiler_total_kg == pytest.approx(15_000.0)

    def test_sum_and_extend_duration_sums_boiler_fuel(self):
        r1 = _make_feems_result(fuel_kg=100.0)
        r2 = _make_feems_result(fuel_kg=50.0)
        merged = r1.sum_and_extend_duration(r2)
        assert merged.fuel_consumption_boiler_total.total_fuel_consumption == pytest.approx(150.0)

    def test_sum_and_extend_duration_includes_boiler_fuel_in_multi_fuel(self):
        r1 = _make_feems_result(fuel_kg=100.0)
        r2 = _make_feems_result(fuel_kg=50.0)
        merged = r1.sum_and_extend_duration(r2)
        assert merged.multi_fuel_consumption_total_kg.total_fuel_consumption == pytest.approx(150.0)

    def test_sum_with_freeze_duration_sums_running_hours(self):
        from feems.types_for_feems import FEEMSResult

        r1 = FEEMSResult(duration_s=3600.0, running_hours_boiler_total_hr=1.0)
        r2 = FEEMSResult(duration_s=3600.0, running_hours_boiler_total_hr=0.5)
        merged = r1.sum_with_freeze_duration(r2)
        assert merged.running_hours_boiler_total_hr == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# T6 — MachinerySystem._calculate_boiler_result
# ---------------------------------------------------------------------------


def _make_machinery_system_with_boiler():
    """Return a (MachinerySystem instance, SteamBoiler, time_interval_s, integration_method) tuple."""
    from feems.components_model.component_mechanical import SteamBoiler
    from feems.components_model.utility import IntegrationMethod
    from feems.system_model import MachinerySystem

    boiler = SteamBoiler(
        name="test boiler",
        rated_steam_production_kg_per_h=10_000.0,
        working_pressure_barg=6.0,
        thermal_efficiency_curve=_flat_efficiency_curve(0.85),
    )

    sys = MachinerySystem()
    time_interval_s = 3600.0
    integration_method = IntegrationMethod.sum_with_time
    return sys, boiler, time_interval_s, integration_method


class TestCalculateBoilerResult:
    def test_running_hours_equals_one_for_single_hour(self):
        sys, boiler, tis, im = _make_machinery_system_with_boiler()
        boiler.steam_out_kg_per_h = np.array([10_000.0])
        res = sys._calculate_boiler_result(boiler, tis, im)
        assert res.running_hours_boiler_total_hr == pytest.approx(1.0)

    def test_steam_production_matches_demand_for_single_step(self):
        sys, boiler, tis, im = _make_machinery_system_with_boiler()
        boiler.steam_out_kg_per_h = np.array([10_000.0])
        res = sys._calculate_boiler_result(boiler, tis, im)
        # steam_kg_per_s * 3600 s = 10 000 kg
        assert res.steam_production_boiler_total_kg == pytest.approx(10_000.0, rel=1e-3)

    def test_boiler_fuel_consumption_is_nonzero(self):
        sys, boiler, tis, im = _make_machinery_system_with_boiler()
        boiler.steam_out_kg_per_h = np.array([10_000.0])
        res = sys._calculate_boiler_result(boiler, tis, im)
        assert float(np.sum(res.fuel_consumption_boiler_total.total_fuel_consumption)) > 0

    def test_multi_fuel_total_includes_boiler_fuel(self):
        sys, boiler, tis, im = _make_machinery_system_with_boiler()
        boiler.steam_out_kg_per_h = np.array([10_000.0])
        res = sys._calculate_boiler_result(boiler, tis, im)
        boiler_fc = float(np.sum(res.fuel_consumption_boiler_total.total_fuel_consumption))
        total_fc = float(np.sum(res.multi_fuel_consumption_total_kg.total_fuel_consumption))
        assert total_fc == pytest.approx(boiler_fc)

    def test_zero_demand_gives_zero_running_hours(self):
        sys, boiler, tis, im = _make_machinery_system_with_boiler()
        boiler.steam_out_kg_per_h = np.array([0.0])
        res = sys._calculate_boiler_result(boiler, tis, im)
        assert res.running_hours_boiler_total_hr == pytest.approx(0.0)

    def test_no_boiler_on_system_gives_zero_boiler_hours(self):
        """System with no boiler set returns zero boiler running hours."""
        from feems.components_model.utility import IntegrationMethod
        from feems.system_model import MechanicalPropulsionSystem

        system = MechanicalPropulsionSystem(name="test mech", components_list=[])
        system.set_time_interval(3600.0, IntegrationMethod.sum_with_time)
        assert system.boiler is None
        res = system.get_fuel_energy_consumption_running_time()
        assert res.running_hours_boiler_total_hr == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# T7 — System model integration smoke tests
# ---------------------------------------------------------------------------


def _make_boiler_for_system():
    from feems.components_model.component_mechanical import SteamBoiler

    return SteamBoiler(
        name="ship boiler",
        rated_steam_production_kg_per_h=10_000.0,
        working_pressure_barg=6.0,
        thermal_efficiency_curve=_flat_efficiency_curve(0.85),
    )


class TestMechanicalPropulsionSystemBoiler:
    def test_boiler_running_hours_nonzero_in_result(self):
        """MechanicalPropulsionSystem with boiler and no shaft lines returns boiler data."""
        from feems.components_model.utility import IntegrationMethod
        from feems.system_model import MechanicalPropulsionSystem

        system = MechanicalPropulsionSystem(name="test mech", components_list=[])
        system.set_time_interval(time_interval_s=3600.0, integration_method=IntegrationMethod.sum_with_time)

        boiler = _make_boiler_for_system()
        system.boiler = boiler
        system.boiler.steam_out_kg_per_h = np.array([10_000.0])
        res = system.get_fuel_energy_consumption_running_time()
        assert res.running_hours_boiler_total_hr == pytest.approx(1.0)

    def test_no_boilers_returns_existing_result_unchanged(self):
        """Calling without boiler set does not affect running hours boiler field."""
        from feems.components_model.utility import IntegrationMethod
        from feems.system_model import MechanicalPropulsionSystem

        system = MechanicalPropulsionSystem(name="test mech", components_list=[])
        system.set_time_interval(time_interval_s=3600.0, integration_method=IntegrationMethod.sum_with_time)
        res = system.get_fuel_energy_consumption_running_time()
        assert res.running_hours_boiler_total_hr == pytest.approx(0.0)


def _make_electric_system_with_shore_power():
    """Minimal ElectricPowerSystem — shore power only, no fuel consumption."""
    from feems.components_model.component_electric import ShorePowerConnection
    from feems.components_model.utility import IntegrationMethod
    from feems.system_model import ElectricPowerSystem
    from feems.types_for_feems import Power_kW, SwbId

    shore = ShorePowerConnection(name="Shore", rated_power=Power_kW(1000.0), switchboard_id=SwbId(1))
    system = ElectricPowerSystem(name="test elec", power_plant_components=[shore], bus_tie_connections=[])
    system.set_time_interval(time_interval_s=3600.0, integration_method=IntegrationMethod.sum_with_time)
    return system


class TestElectricPowerSystemBoiler:
    def test_boiler_running_hours_nonzero_in_result(self):
        """ElectricPowerSystem with boiler accumulates boiler running hours."""
        system = _make_electric_system_with_shore_power()
        boiler = _make_boiler_for_system()
        system.boiler = boiler
        system.boiler.steam_out_kg_per_h = np.array([10_000.0])
        res = system.get_fuel_energy_consumption_running_time()
        assert res.running_hours_boiler_total_hr == pytest.approx(1.0)

    def test_boiler_fuel_consumption_nonzero_in_result(self):
        system = _make_electric_system_with_shore_power()
        boiler = _make_boiler_for_system()
        system.boiler = boiler
        system.boiler.steam_out_kg_per_h = np.array([10_000.0])
        res = system.get_fuel_energy_consumption_running_time()
        assert float(np.sum(res.fuel_consumption_boiler_total.total_fuel_consumption)) > 0

    def test_no_boiler_gives_zero_boiler_hours(self):
        system = _make_electric_system_with_shore_power()
        res = system.get_fuel_energy_consumption_running_time()
        assert res.running_hours_boiler_total_hr == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# T8 — Multi-step (N > 1) integration: running_hr crash regression
# ---------------------------------------------------------------------------


class TestMultiStepBoilerResult:
    """Regression guard for the running_hr np.dot crash on N > 1 time arrays."""

    def setup_method(self):
        from feems.components_model.component_mechanical import SteamBoiler
        from feems.components_model.utility import IntegrationMethod
        from feems.system_model import MachinerySystem

        self.boiler = SteamBoiler(
            name="multi-step boiler",
            rated_steam_production_kg_per_h=10_000.0,
            working_pressure_barg=6.0,
            thermal_efficiency_curve=_flat_efficiency_curve(0.85),
        )
        self.sys = MachinerySystem()
        self.im = IntegrationMethod.sum_with_time

    def test_running_hours_multi_step_all_active(self):
        """4 × 1-hour steps at full load → 4 running hours."""
        self.boiler.steam_out_kg_per_h = np.array([10_000.0, 10_000.0, 10_000.0, 10_000.0])
        time_interval_s = np.array([3600.0, 3600.0, 3600.0, 3600.0])
        res = self.sys._calculate_boiler_result(self.boiler, time_interval_s, self.im)
        assert res.running_hours_boiler_total_hr == pytest.approx(4.0)

    def test_running_hours_multi_step_partial_active(self):
        """4 steps: first two at zero demand, last two at full load → 2 running hours."""
        self.boiler.steam_out_kg_per_h = np.array([0.0, 0.0, 10_000.0, 10_000.0])
        time_interval_s = np.array([3600.0, 3600.0, 3600.0, 3600.0])
        res = self.sys._calculate_boiler_result(self.boiler, time_interval_s, self.im)
        assert res.running_hours_boiler_total_hr == pytest.approx(2.0)

    def test_steam_production_multi_step(self):
        """Full load for two 1-hour steps → 20 000 kg steam total."""
        self.boiler.steam_out_kg_per_h = np.array([10_000.0, 10_000.0])
        time_interval_s = np.array([3600.0, 3600.0])
        res = self.sys._calculate_boiler_result(self.boiler, time_interval_s, self.im)
        assert res.steam_production_boiler_total_kg == pytest.approx(20_000.0, rel=1e-3)

    def test_fuel_consumption_multi_step_doubles_vs_single_step(self):
        """Two identical steps should produce twice the fuel of one step."""
        self.boiler.steam_out_kg_per_h = np.array([10_000.0])
        res_1 = self.sys._calculate_boiler_result(self.boiler, np.array([3600.0]), self.im)
        self.boiler.steam_out_kg_per_h = np.array([10_000.0, 10_000.0])
        res_2 = self.sys._calculate_boiler_result(self.boiler, np.array([3600.0, 3600.0]), self.im)
        fc_1 = float(np.sum(res_1.fuel_consumption_boiler_total.total_fuel_consumption))
        fc_2 = float(np.sum(res_2.fuel_consumption_boiler_total.total_fuel_consumption))
        assert fc_2 == pytest.approx(2.0 * fc_1, rel=1e-4)


# ---------------------------------------------------------------------------
# T9 — Input validation
# ---------------------------------------------------------------------------


class TestSteamBoilerInputValidation:
    def test_zero_rated_production_raises_input_error(self):
        from feems.components_model.component_mechanical import SteamBoiler

        with pytest.raises(InputError):
            SteamBoiler(
                name="bad",
                rated_steam_production_kg_per_h=0.0,
                working_pressure_barg=6.0,
                thermal_efficiency_curve=_flat_efficiency_curve(0.85),
            )

    def test_negative_rated_production_raises_input_error(self):
        from feems.components_model.component_mechanical import SteamBoiler

        with pytest.raises(InputError):
            SteamBoiler(
                name="bad",
                rated_steam_production_kg_per_h=-1.0,
                working_pressure_barg=6.0,
                thermal_efficiency_curve=_flat_efficiency_curve(0.85),
            )

    def test_feed_water_temp_too_high_raises_input_error(self):
        """feed_water_temperature_c higher than saturation temp → delta_h <= 0."""
        from feems.components_model.component_mechanical import SteamBoiler

        with pytest.raises(InputError):
            SteamBoiler(
                name="bad",
                rated_steam_production_kg_per_h=10_000.0,
                working_pressure_barg=6.0,
                thermal_efficiency_curve=_flat_efficiency_curve(0.85),
                feed_water_temperature_c=700.0,  # far above saturation (~165 °C at 7 bar)
            )

    def test_negative_steam_demand_raises_value_error(self):
        boiler = _make_boiler()
        with pytest.raises(ValueError):
            boiler.get_boiler_run_point(np.array([-100.0]))

    def test_nan_steam_demand_raises_value_error(self):
        boiler = _make_boiler()
        with pytest.raises(ValueError):
            boiler.get_boiler_run_point(np.array([float("nan")]))

    def test_inf_steam_demand_raises_value_error(self):
        boiler = _make_boiler()
        with pytest.raises(ValueError):
            boiler.get_boiler_run_point(np.array([float("inf")]))


# ---------------------------------------------------------------------------
# T10 — Emission accumulation in _calculate_boiler_result
# ---------------------------------------------------------------------------


class TestCalculateBoilerResultEmissions:
    def setup_method(self):
        from feems.components_model.component_mechanical import SteamBoiler
        from feems.components_model.utility import IntegrationMethod
        from feems.system_model import MachinerySystem

        nox_curve = EmissionCurve(
            points_per_kwh=[
                EmissionCurvePoint(load_ratio=0.25, emission_g_per_kwh=2.0),
                EmissionCurvePoint(load_ratio=0.50, emission_g_per_kwh=2.0),
                EmissionCurvePoint(load_ratio=0.75, emission_g_per_kwh=2.0),
                EmissionCurvePoint(load_ratio=1.00, emission_g_per_kwh=2.0),
            ],
            emission=EmissionType.NOX,
        )
        self.boiler = SteamBoiler(
            name="emission boiler",
            rated_steam_production_kg_per_h=10_000.0,
            working_pressure_barg=6.0,
            thermal_efficiency_curve=_flat_efficiency_curve(0.85),
            emissions_curves=[nox_curve],
        )
        self.sys = MachinerySystem()
        self.im = IntegrationMethod.sum_with_time

    def test_nox_emission_kg_nonzero(self):
        self.boiler.steam_out_kg_per_h = np.array([10_000.0])
        res = self.sys._calculate_boiler_result(self.boiler, 3600.0, self.im)
        assert res.total_emission_kg is not None
        assert res.total_emission_kg[EmissionType.NOX] > 0

    def test_nox_doubles_for_two_steps(self):
        self.boiler.steam_out_kg_per_h = np.array([10_000.0])
        res_1 = self.sys._calculate_boiler_result(self.boiler, 3600.0, self.im)
        self.boiler.steam_out_kg_per_h = np.array([10_000.0, 10_000.0])
        res_2 = self.sys._calculate_boiler_result(self.boiler, np.array([3600.0, 3600.0]), self.im)
        nox_1 = res_1.total_emission_kg[EmissionType.NOX]
        nox_2 = res_2.total_emission_kg[EmissionType.NOX]
        assert nox_2 == pytest.approx(2.0 * nox_1, rel=1e-4)

    def test_zero_demand_gives_no_emissions(self):
        self.boiler.steam_out_kg_per_h = np.array([0.0])
        res = self.sys._calculate_boiler_result(self.boiler, 3600.0, self.im)
        if res.total_emission_kg is not None:
            assert res.total_emission_kg[EmissionType.NOX] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# T11 — fuel_option applied to boiler in _calculate_boiler_result
# ---------------------------------------------------------------------------


class TestBoilerFuelOption:
    def setup_method(self):
        from feems.components_model.component_mechanical import FuelCharacteristics, SteamBoiler
        from feems.components_model.utility import IntegrationMethod
        from feems.fuel import FuelOrigin, TypeFuel
        from feems.system_model import MachinerySystem

        hfo_mode = FuelCharacteristics()
        hfo_mode.main_fuel_type = TypeFuel.HFO
        hfo_mode.main_fuel_origin = FuelOrigin.FOSSIL
        hfo_mode.eff_curve = _flat_efficiency_curve(0.85)

        lng_mode = FuelCharacteristics()
        lng_mode.main_fuel_type = TypeFuel.NATURAL_GAS
        lng_mode.main_fuel_origin = FuelOrigin.FOSSIL
        lng_mode.eff_curve = _flat_efficiency_curve(0.87)

        self.boiler_multi = SteamBoiler(
            name="multi-fuel boiler",
            rated_steam_production_kg_per_h=10_000.0,
            working_pressure_barg=6.0,
            multi_fuel_characteristics=[hfo_mode, lng_mode],
        )
        self.boiler_single = _make_boiler()  # HFO single-fuel
        self.sys = MachinerySystem()
        self.im = IntegrationMethod.sum_with_time

    def test_matching_fuel_option_switches_boiler_to_lng(self):
        from feems.fuel import FuelOrigin, TypeFuel
        from feems.system_model import FuelOption

        self.boiler_multi.steam_out_kg_per_h = np.array([10_000.0])
        option = FuelOption(fuel_type=TypeFuel.NATURAL_GAS, fuel_origin=FuelOrigin.FOSSIL)
        self.sys._calculate_boiler_result(self.boiler_multi, 3600.0, self.im, fuel_option=option)
        assert self.boiler_multi.fuel_type == TypeFuel.NATURAL_GAS

    def test_non_matching_fuel_option_leaves_single_fuel_boiler_unchanged(self):
        """A single-fuel HFO boiler ignores any fuel_option — no error raised."""
        from feems.fuel import FuelOrigin, TypeFuel
        from feems.system_model import FuelOption

        self.boiler_single.steam_out_kg_per_h = np.array([10_000.0])
        option = FuelOption(fuel_type=TypeFuel.NATURAL_GAS, fuel_origin=FuelOrigin.FOSSIL)
        self.sys._calculate_boiler_result(self.boiler_single, 3600.0, self.im, fuel_option=option)
        assert self.boiler_single.fuel_type == TypeFuel.HFO

    def test_fuel_option_not_in_boiler_modes_keeps_current_fuel(self):
        """Multi-fuel boiler with HFO+LNG: passing METHANOL option keeps current fuel."""
        from feems.fuel import FuelOrigin, TypeFuel
        from feems.system_model import FuelOption

        self.boiler_multi.steam_out_kg_per_h = np.array([10_000.0])
        option = FuelOption(fuel_type=TypeFuel.METHANOL, fuel_origin=FuelOrigin.FOSSIL)
        self.sys._calculate_boiler_result(self.boiler_multi, 3600.0, self.im, fuel_option=option)
        assert self.boiler_multi.fuel_type == TypeFuel.HFO  # default first mode unchanged

    def test_no_fuel_option_leaves_boiler_on_current_fuel(self):
        self.boiler_multi.steam_out_kg_per_h = np.array([10_000.0])
        self.sys._calculate_boiler_result(self.boiler_multi, 3600.0, self.im)
        assert self.boiler_multi.fuel_type == TypeFuel.HFO  # first mode, unchanged


# ---------------------------------------------------------------------------
# T12 — fuel_option applied through full get_fuel_energy_consumption_running_time
# ---------------------------------------------------------------------------


def _make_multi_fuel_genset(switchboard_id: int = 1):
    """Genset with EngineMultiFuel (LNG primary / Diesel secondary) on the given switchboard."""
    from feems.components_model.component_electric import ElectricMachine, Genset
    from feems.components_model.component_mechanical import EngineMultiFuel, FuelCharacteristics
    from feems.fuel import FuelOrigin, TypeFuel
    from feems.types_for_feems import Power_kW, Speed_rpm, SwbId, TypeComponent, TypePower

    lng_mode = FuelCharacteristics(
        main_fuel_type=TypeFuel.NATURAL_GAS,
        main_fuel_origin=FuelOrigin.FOSSIL,
        bsfc_curve=np.array([[0.0, 180.0], [1.0, 180.0]], dtype=float),
    )
    hfo_mode = FuelCharacteristics(
        main_fuel_type=TypeFuel.HFO,
        main_fuel_origin=FuelOrigin.FOSSIL,
        bsfc_curve=np.array([[0.0, 210.0], [1.0, 210.0]], dtype=float),
    )
    engine = EngineMultiFuel(
        type_=TypeComponent.MAIN_ENGINE,
        name="multi-fuel engine",
        rated_power=Power_kW(1000.0),
        rated_speed=Speed_rpm(750.0),
        multi_fuel_characteristics=[lng_mode, hfo_mode],
    )
    generator = ElectricMachine(
        type_=TypeComponent.GENERATOR,
        name="generator",
        rated_power=Power_kW(900.0),
        rated_speed=Speed_rpm(750.0),
        power_type=TypePower.POWER_SOURCE,
        switchboard_id=SwbId(switchboard_id),
        eff_curve=np.array([[0.1, 0.95], [1.0, 0.95]]),
    )
    genset = Genset("multi-fuel genset", engine, generator)
    genset.switchboard_id = SwbId(switchboard_id)
    genset.power_output = np.array([500.0])
    return genset


def _make_multi_fuel_boiler_hfo_lng():
    """SteamBoiler with HFO as first mode and LNG as second mode."""
    from feems.components_model.component_mechanical import FuelCharacteristics, SteamBoiler
    from feems.fuel import FuelOrigin, TypeFuel

    hfo_mode = FuelCharacteristics()
    hfo_mode.main_fuel_type = TypeFuel.HFO
    hfo_mode.main_fuel_origin = FuelOrigin.FOSSIL
    hfo_mode.eff_curve = _flat_efficiency_curve(0.85)

    lng_mode = FuelCharacteristics()
    lng_mode.main_fuel_type = TypeFuel.NATURAL_GAS
    lng_mode.main_fuel_origin = FuelOrigin.FOSSIL
    lng_mode.eff_curve = _flat_efficiency_curve(0.87)

    return SteamBoiler(
        name="multi-fuel boiler",
        rated_steam_production_kg_per_h=10_000.0,
        working_pressure_barg=6.0,
        multi_fuel_characteristics=[hfo_mode, lng_mode],
    )


class TestBoilerFuelOptionFullChain:
    """T12: fuel_option reaches the boiler through get_fuel_energy_consumption_running_time."""

    def setup_method(self):
        from feems.components_model.utility import IntegrationMethod
        from feems.system_model import ElectricPowerSystem

        self.genset = _make_multi_fuel_genset(switchboard_id=1)
        self.boiler = _make_multi_fuel_boiler_hfo_lng()

        self.system = ElectricPowerSystem(
            name="test system",
            power_plant_components=[self.genset],
            bus_tie_connections=[],
        )
        self.system.set_time_interval(
            time_interval_s=3600.0,
            integration_method=IntegrationMethod.sum_with_time,
        )
        self.system.boiler = self.boiler
        self.system.boiler.steam_out_kg_per_h = np.array([10_000.0])

    def test_fuel_option_lng_switches_boiler_to_lng(self):
        """fuel_option=LNG reaches the boiler and switches it away from the HFO default."""
        from feems.fuel import FuelOrigin, TypeFuel
        from feems.system_model import FuelOption

        option = FuelOption(fuel_type=TypeFuel.NATURAL_GAS, fuel_origin=FuelOrigin.FOSSIL)
        res = self.system.get_fuel_energy_consumption_running_time(fuel_option=option)
        assert self.boiler.fuel_type == TypeFuel.NATURAL_GAS
        assert res.running_hours_boiler_total_hr == pytest.approx(1.0)

    def test_no_fuel_option_leaves_boiler_on_default_hfo(self):
        """No fuel_option: boiler stays on HFO (its first configured mode)."""
        self.system.get_fuel_energy_consumption_running_time()
        assert self.boiler.fuel_type == TypeFuel.HFO

    def test_fuel_option_unsupported_by_boiler_keeps_current_fuel(self):
        """fuel_option for a fuel the boiler doesn't have leaves the boiler unchanged."""
        from feems.components_model.component_mechanical import FuelCharacteristics, SteamBoiler
        from feems.fuel import FuelOrigin, TypeFuel
        from feems.system_model import FuelOption

        # Replace boiler with one that only supports HFO and LNG;
        # pass METHANOL option (not in boiler, but genset supports LNG so validation passes)
        # Use the LNG option to satisfy validation, then give the boiler only HFO.
        hfo_only = FuelCharacteristics()
        hfo_only.main_fuel_type = TypeFuel.HFO
        hfo_only.main_fuel_origin = FuelOrigin.FOSSIL
        hfo_only.eff_curve = _flat_efficiency_curve(0.85)
        self.system.boiler = SteamBoiler(
            name="hfo-only boiler",
            rated_steam_production_kg_per_h=10_000.0,
            working_pressure_barg=6.0,
            multi_fuel_characteristics=[hfo_only],
        )
        self.system.boiler.steam_out_kg_per_h = np.array([10_000.0])

        # LNG option passes validation (genset supports it) but boiler only has HFO
        option = FuelOption(fuel_type=TypeFuel.NATURAL_GAS, fuel_origin=FuelOrigin.FOSSIL)
        self.system.get_fuel_energy_consumption_running_time(fuel_option=option)
        assert self.system.boiler.fuel_type == TypeFuel.HFO


# ---------------------------------------------------------------------------
# T13 — detail_result includes boiler row
# ---------------------------------------------------------------------------


class TestBoilerDetailResult:
    """Boiler row appears in FEEMSResult.detail_result after system calculation."""

    def setup_method(self):
        self.system = _make_electric_system_with_shore_power()
        self.boiler = _make_boiler_for_system()
        self.system.boiler = self.boiler
        self.boiler.steam_out_kg_per_h = np.array([10_000.0])
        self.res = self.system.get_fuel_energy_consumption_running_time()

    def test_boiler_row_present_in_detail_result(self):
        assert self.res.detail_result is not None
        assert self.boiler.name in self.res.detail_result.index

    def test_boiler_detail_running_hours(self):
        row = self.res.detail_result.loc[self.boiler.name]
        assert float(row["running hours [h]"]) == pytest.approx(1.0)

    def test_boiler_detail_component_type(self):
        row = self.res.detail_result.loc[self.boiler.name]
        assert row["component type"] == "STEAM_BOILER"

    def test_boiler_detail_rated_capacity(self):
        row = self.res.detail_result.loc[self.boiler.name]
        assert float(row["rated capacity"]) == pytest.approx(10_000.0)
        assert row["rated capacity unit"] == "kg/h"

    def test_boiler_detail_fuel_consumption_nonzero(self):
        from feems.fuel import FuelConsumption

        row = self.res.detail_result.loc[self.boiler.name]
        fc = row["multi fuel consumption [kg]"]
        assert isinstance(fc, FuelConsumption)
        assert fc.total_fuel_consumption > 0

    def test_boiler_co2_emission_in_result(self):
        from feems.fuel import GHGEmissions

        assert isinstance(self.res.co2_emission_total_kg, GHGEmissions)
        assert self.res.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel > 0

    def test_boiler_co2_emission_in_detail_row(self):
        from feems.fuel import GHGEmissions

        row = self.res.detail_result.loc[self.boiler.name]
        co2 = row["CO2 emission [kg]"]
        assert isinstance(co2, GHGEmissions)
        assert co2.tank_to_wake_kg_or_gco2eq_per_gfuel > 0


# ---------------------------------------------------------------------------
# T14 — fuel_option on boiler-only system (no multi-fuel engines)
# ---------------------------------------------------------------------------


class TestBoilerOnlyFuelOption:
    """fuel_option is allowed when the boiler (but no engine) supports the fuel."""

    def setup_method(self):
        from feems.components_model.component_mechanical import FuelCharacteristics, SteamBoiler

        lng_mode = FuelCharacteristics()
        lng_mode.main_fuel_type = TypeFuel.NATURAL_GAS
        lng_mode.main_fuel_origin = FuelOrigin.FOSSIL
        lng_mode.eff_curve = _flat_efficiency_curve(0.88)

        hfo_mode = FuelCharacteristics()
        hfo_mode.main_fuel_type = TypeFuel.HFO
        hfo_mode.main_fuel_origin = FuelOrigin.FOSSIL
        hfo_mode.eff_curve = _flat_efficiency_curve(0.85)

        self.system = _make_electric_system_with_shore_power()
        self.boiler = SteamBoiler(
            name="multi-fuel boiler",
            rated_steam_production_kg_per_h=10_000.0,
            working_pressure_barg=6.0,
            multi_fuel_characteristics=[hfo_mode, lng_mode],
        )
        self.system.boiler = self.boiler
        self.boiler.steam_out_kg_per_h = np.array([10_000.0])

    def test_matching_fuel_option_allowed_without_multi_fuel_engine(self):
        from feems.system_model import FuelOption

        option = FuelOption(fuel_type=TypeFuel.NATURAL_GAS, fuel_origin=FuelOrigin.FOSSIL)
        # Must not raise — boiler supports LNG even though there are no multi-fuel engines
        self.system.get_fuel_energy_consumption_running_time(fuel_option=option)
        assert self.boiler.fuel_type == TypeFuel.NATURAL_GAS

    def test_unsupported_fuel_option_still_raises_on_boiler_only_system(self):
        from feems.exceptions import InputError
        from feems.system_model import FuelOption

        # HYDROGEN is not in HFO/LNG boiler modes, and there are no multi-fuel engines
        option = FuelOption(fuel_type=TypeFuel.HYDROGEN, fuel_origin=FuelOrigin.RENEWABLE_NON_BIO)
        with pytest.raises(InputError):
            self.system.get_fuel_energy_consumption_running_time(fuel_option=option)
