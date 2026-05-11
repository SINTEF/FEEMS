"""T9 — SteamBoiler proto converter round-trip tests."""

import os

import numpy as np
import pytest
from feems.components_model.component_mechanical import FuelCharacteristics, SteamBoiler
from feems.fuel import FuelOrigin, TypeFuel
from MachSysS.convert_to_feems import convert_proto_propulsion_system_to_feems, proto_to_steam_boiler
from MachSysS.convert_to_protobuf import (
    convert_electric_system_to_protobuf_machinery_system,
    convert_hybrid_propulsion_system_to_protobuf,
    convert_mechanical_propulsion_system_with_electric_system_to_protobuf,
    steam_boiler_to_proto,
)
from MachSysS.utility import retrieve_machinery_system_from_file

_TEST_DIR = os.path.dirname(__file__)


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


# ---------------------------------------------------------------------------
# T10 — MachinerySystem-level boiler round-trip
# ---------------------------------------------------------------------------


class TestMachinerySystemBoilerRoundTrip:
    """Verify that a boiler attached to a full machinery system survives proto serialisation."""

    @pytest.fixture()
    def boiler(self):
        return _make_single_fuel_boiler()

    def _check_boiler_preserved(self, original_boiler, restored_system) -> None:
        b = restored_system.boiler
        assert b is not None, "boiler was not restored from proto"
        assert b.name == original_boiler.name
        assert b.rated_steam_production_kg_per_h == pytest.approx(
            original_boiler.rated_steam_production_kg_per_h
        )
        assert b.working_pressure_barg == pytest.approx(original_boiler.working_pressure_barg)
        assert b.feed_water_temperature_c == pytest.approx(original_boiler.feed_water_temperature_c)
        assert b.fuel_type == original_boiler.fuel_type
        assert b.fuel_origin == original_boiler.fuel_origin

    def test_electric_system_with_boiler_round_trip(self, boiler):
        mss_path = os.path.join(_TEST_DIR, "electric_propulsion_system.mss")
        system_proto = retrieve_machinery_system_from_file(mss_path)
        system = convert_proto_propulsion_system_to_feems(system_proto)
        system.boiler = boiler

        restored = convert_proto_propulsion_system_to_feems(
            convert_electric_system_to_protobuf_machinery_system(system)
        )
        self._check_boiler_preserved(boiler, restored)

    def test_electric_system_without_boiler_has_no_boiler(self):
        mss_path = os.path.join(_TEST_DIR, "electric_propulsion_system.mss")
        system_proto = retrieve_machinery_system_from_file(mss_path)
        system = convert_proto_propulsion_system_to_feems(system_proto)
        assert system.boiler is None

        restored = convert_proto_propulsion_system_to_feems(
            convert_electric_system_to_protobuf_machinery_system(system)
        )
        assert restored.boiler is None

    def test_mechanical_system_with_boiler_round_trip(self, boiler):
        mss_path = os.path.join(_TEST_DIR, "mechanical_propulsion_with_electric_system.mss")
        system_proto = retrieve_machinery_system_from_file(mss_path)
        system = convert_proto_propulsion_system_to_feems(system_proto)
        system.boiler = boiler

        restored = convert_proto_propulsion_system_to_feems(
            convert_mechanical_propulsion_system_with_electric_system_to_protobuf(system)
        )
        self._check_boiler_preserved(boiler, restored)

    def test_hybrid_system_with_boiler_round_trip(self, boiler):
        mss_path = os.path.join(_TEST_DIR, "hybrid_propulsion_system.mss")
        system_proto = retrieve_machinery_system_from_file(mss_path)
        system = convert_proto_propulsion_system_to_feems(system_proto)
        system.boiler = boiler

        restored = convert_proto_propulsion_system_to_feems(
            convert_hybrid_propulsion_system_to_protobuf(system)
        )
        self._check_boiler_preserved(boiler, restored)

    def test_multi_fuel_boiler_preserved_in_system(self):
        mss_path = os.path.join(_TEST_DIR, "electric_propulsion_system.mss")
        system_proto = retrieve_machinery_system_from_file(mss_path)
        system = convert_proto_propulsion_system_to_feems(system_proto)
        system.boiler = _make_multi_fuel_boiler()

        restored = convert_proto_propulsion_system_to_feems(
            convert_electric_system_to_protobuf_machinery_system(system)
        )
        assert restored.boiler is not None
        assert len(restored.boiler.multi_fuel_characteristics) == 2
        assert restored.boiler.multi_fuel_characteristics[0].main_fuel_type == TypeFuel.HFO
        assert restored.boiler.multi_fuel_characteristics[1].main_fuel_type == TypeFuel.NATURAL_GAS
