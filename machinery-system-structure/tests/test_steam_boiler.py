"""T9 — SteamBoiler proto converter round-trip tests."""

import numpy as np
import pytest
from feems.components_model.component_mechanical import FuelCharacteristics, SteamBoiler
from feems.fuel import FuelOrigin, TypeFuel
from MachSysS.convert_to_feems import proto_to_steam_boiler
from MachSysS.convert_to_protobuf import steam_boiler_to_proto


def _flat_eta_curve(eta: float) -> np.ndarray:
    return np.array([[0.25, eta], [0.50, eta], [0.75, eta], [1.00, eta]])


def _make_single_fuel_boiler(**kwargs) -> SteamBoiler:
    defaults = dict(
        name="test boiler",
        rated_steam_production_kg_per_h=10_000.0,
        working_pressure_barg=6.0,
        thermal_efficiency_curve=_flat_eta_curve(0.85),
        fuel_type=TypeFuel.HFO,
        fuel_origin=FuelOrigin.FOSSIL,
        feed_water_temperature_c=80.0,
        uid="boiler-uid-001",
    )
    defaults.update(kwargs)
    return SteamBoiler(**defaults)


def _make_multi_fuel_boiler() -> SteamBoiler:
    hfo_mode = FuelCharacteristics()
    hfo_mode.main_fuel_type = TypeFuel.HFO
    hfo_mode.main_fuel_origin = FuelOrigin.FOSSIL
    hfo_mode.eff_curve = _flat_eta_curve(0.85)

    lng_mode = FuelCharacteristics()
    lng_mode.main_fuel_type = TypeFuel.NATURAL_GAS
    lng_mode.main_fuel_origin = FuelOrigin.FOSSIL
    lng_mode.eff_curve = _flat_eta_curve(0.87)

    return SteamBoiler(
        name="multi boiler",
        rated_steam_production_kg_per_h=10_000.0,
        working_pressure_barg=6.0,
        multi_fuel_characteristics=[hfo_mode, lng_mode],
        uid="boiler-uid-002",
    )


class TestSingleFuelRoundTrip:
    def test_rated_steam_production_preserved(self):
        original = _make_single_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))
        assert restored.rated_steam_production_kg_per_h == pytest.approx(10_000.0)

    def test_working_pressure_preserved(self):
        original = _make_single_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))
        assert restored.working_pressure_barg == pytest.approx(6.0)

    def test_feed_water_temperature_preserved(self):
        original = _make_single_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))
        assert restored.feed_water_temperature_c == pytest.approx(80.0)

    def test_fuel_type_preserved(self):
        original = _make_single_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))
        assert restored.fuel_type == TypeFuel.HFO

    def test_fuel_origin_preserved(self):
        original = _make_single_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))
        assert restored.fuel_origin == FuelOrigin.FOSSIL

    def test_name_preserved(self):
        original = _make_single_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))
        assert restored.name == "test boiler"

    def test_uid_preserved(self):
        original = _make_single_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))
        assert restored.uid == "boiler-uid-001"

    def test_run_point_fuel_flow_matches_within_tolerance(self):
        """Round-trip boiler produces same fuel flow as original (within 0.01%)."""
        original = _make_single_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))

        demand = np.array([10_000.0])
        rp_orig = original.get_boiler_run_point(demand)
        rp_rest = restored.get_boiler_run_point(demand)

        fuel_orig = float(np.sum(rp_orig.fuel_flow_rate_kg_per_s.total_fuel_consumption))
        fuel_rest = float(np.sum(rp_rest.fuel_flow_rate_kg_per_s.total_fuel_consumption))
        assert abs(fuel_rest - fuel_orig) / fuel_orig < 1e-4

    def test_run_point_at_half_load_matches(self):
        original = _make_single_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))

        demand = np.array([5_000.0])
        rp_orig = original.get_boiler_run_point(demand)
        rp_rest = restored.get_boiler_run_point(demand)

        fuel_orig = float(np.sum(rp_orig.fuel_flow_rate_kg_per_s.total_fuel_consumption))
        fuel_rest = float(np.sum(rp_rest.fuel_flow_rate_kg_per_s.total_fuel_consumption))
        assert abs(fuel_rest - fuel_orig) / fuel_orig < 1e-4


class TestMultiFuelRoundTrip:
    def test_multi_fuel_mode_count_preserved(self):
        original = _make_multi_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))
        assert len(restored.multi_fuel_characteristics) == 2

    def test_first_fuel_mode_type_preserved(self):
        original = _make_multi_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))
        assert restored.multi_fuel_characteristics[0].main_fuel_type == TypeFuel.HFO

    def test_second_fuel_mode_type_preserved(self):
        original = _make_multi_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))
        assert restored.multi_fuel_characteristics[1].main_fuel_type == TypeFuel.NATURAL_GAS

    def test_multi_fuel_run_point_hfo_matches(self):
        original = _make_multi_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))

        demand = np.array([10_000.0])
        rp_orig = original.get_boiler_run_point(demand)
        rp_rest = restored.get_boiler_run_point(demand)

        fuel_orig = float(np.sum(rp_orig.fuel_flow_rate_kg_per_s.total_fuel_consumption))
        fuel_rest = float(np.sum(rp_rest.fuel_flow_rate_kg_per_s.total_fuel_consumption))
        assert abs(fuel_rest - fuel_orig) / fuel_orig < 1e-4

    def test_multi_fuel_run_point_lng_matches_after_switch(self):
        original = _make_multi_fuel_boiler()
        restored = proto_to_steam_boiler(steam_boiler_to_proto(original))

        original.set_fuel_in_use(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)
        restored.set_fuel_in_use(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)

        demand = np.array([10_000.0])
        rp_orig = original.get_boiler_run_point(demand)
        rp_rest = restored.get_boiler_run_point(demand)

        fuel_orig = float(np.sum(rp_orig.fuel_flow_rate_kg_per_s.total_fuel_consumption))
        fuel_rest = float(np.sum(rp_rest.fuel_flow_rate_kg_per_s.total_fuel_consumption))
        assert abs(fuel_rest - fuel_orig) / fuel_orig < 1e-4
