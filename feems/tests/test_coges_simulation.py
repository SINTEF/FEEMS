"""Tests for COGES simulation support: BRAYTON cycle, CH4/N2O defaults, multi-fuel modes,
node.py forwarding, and proto round-trip (issue #89)."""

import pytest
import numpy as np

from feems.types_for_feems import EngineCycleType
from feems.fuel import (
    Fuel,
    FuelConsumerClassFuelEUMaritime,
    FuelOrigin,
    FuelSpecifiedBy,
    TypeFuel,
    GhgEmissionFactorTankToWake,
)
from feems.components_model.component_mechanical import (
    COGAS,
    FuelCharacteristics,
    _DEFAULT_BRAYTON_C_SLIP_PERCENT,
    _DEFAULT_BRAYTON_CH4_GFUEL,
    _DEFAULT_BRAYTON_N2O_GFUEL,
)

from .utility import create_cogas_system, create_random_monotonic_eff_curve


# ---------------------------------------------------------------------------
# 4.1  with_emission_curve_ghg_overrides — backward compatibility
# ---------------------------------------------------------------------------

def _make_fuel_with_slip(c_slip: float = 1.7) -> Fuel:
    ttw = GhgEmissionFactorTankToWake(
        co2_factor_gco2_per_gfuel=2.75,
        ch4_factor_gch4_per_gfuel=0.0,
        n2o_factor_gn2o_per_gfuel=0.00011,
        c_slip_percent=c_slip,
    )
    return Fuel(
        fuel_type=TypeFuel.NATURAL_GAS,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.USER,
        name="test_lng",
        lhv_mj_per_g=0.048,
        ghg_emission_factor_tank_to_wake=[ttw],
        ghg_emission_factor_well_to_tank_gco2eq_per_mj=18.5,
    )


class TestWithEmissionCurveGhgOverridesBackwardCompat:
    def test_ch4_given_zeroes_c_slip(self):
        fuel = _make_fuel_with_slip(1.7)
        updated = fuel.with_emission_curve_ghg_overrides(ch4_factor_gch4_per_gfuel=0.0005)
        assert updated.ghg_emission_factor_tank_to_wake[0].c_slip_percent == pytest.approx(0.0)

    def test_n2o_only_leaves_c_slip_unchanged(self):
        fuel = _make_fuel_with_slip(1.7)
        updated = fuel.with_emission_curve_ghg_overrides(n2o_factor_gn2o_per_gfuel=0.0002)
        assert updated.ghg_emission_factor_tank_to_wake[0].c_slip_percent == pytest.approx(1.7)

    def test_no_args_returns_self(self):
        fuel = _make_fuel_with_slip(1.7)
        assert fuel.with_emission_curve_ghg_overrides() is fuel


# ---------------------------------------------------------------------------
# 4.2  with_emission_curve_ghg_overrides — explicit c_slip_percent parameter
# ---------------------------------------------------------------------------

class TestWithEmissionCurveGhgOverridesExplicitSlip:
    def test_ch4_and_explicit_c_slip_both_stored(self):
        fuel = _make_fuel_with_slip(1.7)
        updated = fuel.with_emission_curve_ghg_overrides(
            ch4_factor_gch4_per_gfuel=0.000192,
            c_slip_percent=0.01,
        )
        ttw = updated.ghg_emission_factor_tank_to_wake[0]
        assert ttw.ch4_factor_gch4_per_gfuel == pytest.approx(0.000192)
        assert ttw.c_slip_percent == pytest.approx(0.01)

    def test_c_slip_only_updates_slip(self):
        fuel = _make_fuel_with_slip(1.7)
        updated = fuel.with_emission_curve_ghg_overrides(c_slip_percent=0.05)
        ttw = updated.ghg_emission_factor_tank_to_wake[0]
        assert ttw.c_slip_percent == pytest.approx(0.05)
        assert ttw.ch4_factor_gch4_per_gfuel == pytest.approx(0.0)

    def test_n2o_and_c_slip_does_not_zero_slip(self):
        fuel = _make_fuel_with_slip(1.7)
        updated = fuel.with_emission_curve_ghg_overrides(
            n2o_factor_gn2o_per_gfuel=0.000048,
            c_slip_percent=0.01,
        )
        assert updated.ghg_emission_factor_tank_to_wake[0].c_slip_percent == pytest.approx(0.01)


# ---------------------------------------------------------------------------
# 4.3  GAS_TURBINE FuelEU table lookup
# ---------------------------------------------------------------------------

class TestGasTurbineFuelEUTable:
    def test_lng_fossil_gas_turbine_row_exists(self):
        fuel = Fuel(
            fuel_type=TypeFuel.NATURAL_GAS,
            origin=FuelOrigin.FOSSIL,
            fuel_specified_by=FuelSpecifiedBy.FUEL_EU_MARITIME,
        )
        ttw_gas_turbine = next(
            (
                e
                for e in fuel.ghg_emission_factor_tank_to_wake
                if e.fuel_consumer_class == FuelConsumerClassFuelEUMaritime.GAS_TURBINE
            ),
            None,
        )
        assert ttw_gas_turbine is not None
        assert ttw_gas_turbine.c_slip_percent == pytest.approx(0.01)
        assert ttw_gas_turbine.ch4_factor_gch4_per_gfuel == pytest.approx(0.000192)
        assert ttw_gas_turbine.n2o_factor_gn2o_per_gfuel == pytest.approx(0.000048)

    def test_brayton_enum_value(self):
        assert EngineCycleType.BRAYTON.value == 4

    def test_gas_turbine_enum_value(self):
        assert FuelConsumerClassFuelEUMaritime.GAS_TURBINE.value == 7


# ---------------------------------------------------------------------------
# 4.4  BRAYTON IPCC defaults applied in run-point calculation
# ---------------------------------------------------------------------------

class TestBraytonDefaultsInRunPoint:
    def test_ipcc_defaults_applied_via_imo(self):
        cogas = create_cogas_system()
        cogas.power_output = np.array([cogas.rated_power * 0.75])
        run_point = cogas.get_gas_turbine_run_point_from_power_output_kw(
            fuel_specified_by=FuelSpecifiedBy.IMO
        )
        fuel_obj = run_point.fuel_flow_rate_kg_per_s.fuels[0]
        ttw = fuel_obj.ghg_emission_factor_tank_to_wake[0]
        assert ttw.ch4_factor_gch4_per_gfuel == pytest.approx(_DEFAULT_BRAYTON_CH4_GFUEL)
        assert ttw.n2o_factor_gn2o_per_gfuel == pytest.approx(_DEFAULT_BRAYTON_N2O_GFUEL)
        assert ttw.c_slip_percent == pytest.approx(_DEFAULT_BRAYTON_C_SLIP_PERCENT)

    def test_custom_scalars_override_defaults(self):
        cogas = create_cogas_system(
            ch4_factor_gch4_per_gfuel=0.0003,
            n2o_factor_gn2o_per_gfuel=0.0001,
            c_slip_percent=0.05,
        )
        cogas.power_output = np.array([cogas.rated_power * 0.5])
        run_point = cogas.get_gas_turbine_run_point_from_power_output_kw(
            fuel_specified_by=FuelSpecifiedBy.IMO
        )
        ttw = run_point.fuel_flow_rate_kg_per_s.fuels[0].ghg_emission_factor_tank_to_wake[0]
        assert ttw.ch4_factor_gch4_per_gfuel == pytest.approx(0.0003)
        assert ttw.n2o_factor_gn2o_per_gfuel == pytest.approx(0.0001)
        assert ttw.c_slip_percent == pytest.approx(0.05)

    def test_fuel_eu_maritime_does_not_raise(self):
        cogas = create_cogas_system()
        cogas.power_output = np.array([cogas.rated_power * 0.5])
        # Should no longer raise ValueError
        run_point = cogas.get_gas_turbine_run_point_from_power_output_kw(
            fuel_specified_by=FuelSpecifiedBy.FUEL_EU_MARITIME
        )
        assert run_point is not None

    def test_fuel_consumer_type_returns_gas_turbine(self):
        cogas = create_cogas_system()
        assert cogas.fuel_consumer_type_fuel_eu_maritime == FuelConsumerClassFuelEUMaritime.GAS_TURBINE


# ---------------------------------------------------------------------------
# 4.5  Emission curve overrides scalar defaults (issue #85 path)
# ---------------------------------------------------------------------------

class TestEmissionCurveOverridesScalarDefaults:
    def test_ch4_emission_curve_overrides_ipcc_default(self):
        from feems.types_for_feems import EmissionCurve, EmissionCurvePoint, EmissionType

        ch4_g_per_kwh = 0.5
        emission_curve = EmissionCurve(
            emission=EmissionType.CH4,
            points_per_kwh=[
                EmissionCurvePoint(load_ratio=0.0, emission_g_per_kwh=ch4_g_per_kwh),
                EmissionCurvePoint(load_ratio=1.0, emission_g_per_kwh=ch4_g_per_kwh),
            ],
        )
        cogas = create_cogas_system(emissions_curves=[emission_curve])
        cogas.power_output = np.array([cogas.rated_power * 0.5])
        run_point = cogas.get_gas_turbine_run_point_from_power_output_kw(
            fuel_specified_by=FuelSpecifiedBy.IMO
        )
        fuel_obj = run_point.fuel_flow_rate_kg_per_s.fuels[0]
        ttw = fuel_obj.ghg_emission_factor_tank_to_wake[0]

        # Emission curve path: c_slip should be zeroed (legacy double-count prevention)
        assert ttw.c_slip_percent == pytest.approx(0.0)
        # CH4 factor should come from the emission curve, not the IPCC default
        assert ttw.ch4_factor_gch4_per_gfuel != pytest.approx(_DEFAULT_BRAYTON_CH4_GFUEL, rel=0.01)


# ---------------------------------------------------------------------------
# 4.6  Multi-fuel mode switching
# ---------------------------------------------------------------------------

class TestMultiFuelModeSwitch:
    def _make_cogas_multi(self):
        eff_lng = np.array([[0.1, 0.32], [0.5, 0.44], [1.0, 0.42]])
        eff_h2 = np.array([[0.1, 0.30], [0.5, 0.42], [1.0, 0.40]])
        lng_mode = FuelCharacteristics(
            main_fuel_type=TypeFuel.NATURAL_GAS,
            main_fuel_origin=FuelOrigin.FOSSIL,
            eff_curve=eff_lng,
            engine_cycle_type=EngineCycleType.BRAYTON,
        )
        h2_mode = FuelCharacteristics(
            main_fuel_type=TypeFuel.HYDROGEN,
            main_fuel_origin=FuelOrigin.FOSSIL,
            eff_curve=eff_h2,
            engine_cycle_type=EngineCycleType.BRAYTON,
        )
        return COGAS(
            name="multi_cogas",
            rated_power=1000.0,
            rated_speed=3000.0,
            multi_fuel_characteristics=[lng_mode, h2_mode],
        )

    def test_initial_mode_is_first(self):
        cogas = self._make_cogas_multi()
        assert cogas.fuel_type == TypeFuel.NATURAL_GAS

    def test_switch_to_hydrogen(self):
        cogas = self._make_cogas_multi()
        cogas.set_fuel_in_use(TypeFuel.HYDROGEN, FuelOrigin.FOSSIL)
        assert cogas.fuel_type == TypeFuel.HYDROGEN

    def test_switch_back_to_lng(self):
        cogas = self._make_cogas_multi()
        cogas.set_fuel_in_use(TypeFuel.HYDROGEN, FuelOrigin.FOSSIL)
        cogas.set_fuel_in_use(TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL)
        assert cogas.fuel_type == TypeFuel.NATURAL_GAS

    def test_unknown_fuel_raises(self):
        cogas = self._make_cogas_multi()
        with pytest.raises(ValueError):
            cogas.set_fuel_in_use(TypeFuel.AMMONIA, FuelOrigin.FOSSIL)

    def test_set_fuel_in_use_none_resets_to_first(self):
        cogas = self._make_cogas_multi()
        cogas.set_fuel_in_use(TypeFuel.HYDROGEN, FuelOrigin.FOSSIL)
        cogas.set_fuel_in_use(None, None)
        assert cogas.fuel_type == TypeFuel.NATURAL_GAS

    def test_no_multi_fuel_set_fuel_in_use_noop(self):
        cogas = create_cogas_system()
        cogas.set_fuel_in_use(TypeFuel.HYDROGEN, FuelOrigin.FOSSIL)  # Should not raise
        assert cogas.fuel_type == TypeFuel.NATURAL_GAS  # Unchanged

    def test_secondary_fuel_type_alias(self):
        fc = FuelCharacteristics(
            main_fuel_type=TypeFuel.NATURAL_GAS,
            engine_cycle_type=EngineCycleType.BRAYTON,
        )
        fc.secondary_fuel_type = TypeFuel.HYDROGEN
        assert fc.pilot_fuel_type == TypeFuel.HYDROGEN
        assert fc.secondary_fuel_type == TypeFuel.HYDROGEN


# ---------------------------------------------------------------------------
# 4.7  node.py COGES branch forwarding
# ---------------------------------------------------------------------------

class TestNodeCogesBranchForwarding:
    def _make_coges_system(self, multi_fuel: bool = False):
        from feems.components_model.component_electric import COGES, ElectricMachine
        from feems.types_for_feems import TypeComponent, TypePower

        if multi_fuel:
            eff_lng = np.array([[0.1, 0.32], [0.5, 0.44], [1.0, 0.42]])
            eff_h2 = np.array([[0.1, 0.30], [0.5, 0.42], [1.0, 0.40]])
            lng_mode = FuelCharacteristics(
                main_fuel_type=TypeFuel.NATURAL_GAS,
                main_fuel_origin=FuelOrigin.FOSSIL,
                eff_curve=eff_lng,
                engine_cycle_type=EngineCycleType.BRAYTON,
            )
            h2_mode = FuelCharacteristics(
                main_fuel_type=TypeFuel.HYDROGEN,
                main_fuel_origin=FuelOrigin.FOSSIL,
                eff_curve=eff_h2,
                engine_cycle_type=EngineCycleType.BRAYTON,
            )
            cogas = COGAS(
                name="COGAS",
                rated_power=5000.0,
                rated_speed=3000.0,
                multi_fuel_characteristics=[lng_mode, h2_mode],
            )
        else:
            cogas = create_cogas_system(rated_power_kw=5000.0)

        generator = ElectricMachine(
            name="generator",
            type_=TypeComponent.SYNCHRONOUS_MACHINE,
            power_type=TypePower.POWER_SOURCE,
            rated_power=cogas.rated_power * 0.9,
            rated_speed=cogas.rated_speed,
            eff_curve=np.array([[0.1, 0.97], [1.0, 0.97]]),
            switchboard_id=1,
        )
        return COGES(name="COGES", cogas=cogas, generator=generator)

    def test_fuel_consumer_class_resolved_via_node(self):
        from feems.components_model.node import get_fuel_emission_energy_balance_for_component
        from feems.components_model.utility import IntegrationMethod

        coges = self._make_coges_system(multi_fuel=False)
        coges.power_output = np.array([coges.rated_power * 0.5])
        result = get_fuel_emission_energy_balance_for_component(
            component=coges,
            time_interval_s=np.array([1.0]),
            integration_method=IntegrationMethod.trapezoid,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        assert result.multi_fuel_consumption_total_kg is not None

    def test_multi_fuel_coges_fuel_type_forwarded(self):
        from feems.components_model.node import get_fuel_emission_energy_balance_for_component
        from feems.components_model.utility import IntegrationMethod

        coges = self._make_coges_system(multi_fuel=True)
        coges.power_output = np.array([coges.rated_power * 0.5])
        get_fuel_emission_energy_balance_for_component(
            component=coges,
            time_interval_s=np.array([1.0]),
            integration_method=IntegrationMethod.trapezoid,
            fuel_specified_by=FuelSpecifiedBy.IMO,
            fuel_type=TypeFuel.HYDROGEN,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        assert coges.cogas.fuel_type == TypeFuel.HYDROGEN


# ---------------------------------------------------------------------------
# 4.8  Proto round-trip
# ---------------------------------------------------------------------------

class TestProtoRoundTrip:
    def test_scalar_fields_round_trip(self):
        import sys
        sys.path.insert(0, "machinery-system-structure")
        from MachSysS.convert_to_protobuf import convert_cogas_component_to_protobuf
        from MachSysS.convert_to_feems import convert_proto_cogas_to_feems

        original = create_cogas_system(
            rated_power_kw=5000.0,
            rated_speed_rpm=3600.0,
            fuel_type=TypeFuel.NATURAL_GAS,
            fuel_origin=FuelOrigin.FOSSIL,
            ch4_factor_gch4_per_gfuel=0.000192,
            n2o_factor_gn2o_per_gfuel=0.000048,
            c_slip_percent=0.01,
        )
        proto_msg = convert_cogas_component_to_protobuf(original)
        restored = convert_proto_cogas_to_feems(proto_msg)

        assert restored.ch4_factor_gch4_per_gfuel == pytest.approx(0.000192)
        assert restored.n2o_factor_gn2o_per_gfuel == pytest.approx(0.000048)
        assert restored.c_slip_percent == pytest.approx(0.01)

    def test_multi_fuel_modes_round_trip(self):
        import sys
        sys.path.insert(0, "machinery-system-structure")
        from MachSysS.convert_to_protobuf import convert_cogas_component_to_protobuf
        from MachSysS.convert_to_feems import convert_proto_cogas_to_feems

        eff_lng = np.array([[0.1, 0.32], [0.5, 0.44], [1.0, 0.42]])
        eff_h2 = np.array([[0.1, 0.30], [0.5, 0.42], [1.0, 0.40]])
        modes = [
            FuelCharacteristics(
                main_fuel_type=TypeFuel.NATURAL_GAS,
                main_fuel_origin=FuelOrigin.FOSSIL,
                eff_curve=eff_lng,
                engine_cycle_type=EngineCycleType.BRAYTON,
            ),
            FuelCharacteristics(
                main_fuel_type=TypeFuel.HYDROGEN,
                main_fuel_origin=FuelOrigin.FOSSIL,
                eff_curve=eff_h2,
                engine_cycle_type=EngineCycleType.BRAYTON,
            ),
        ]
        original = create_cogas_system(
            rated_power_kw=5000.0,
            rated_speed_rpm=3600.0,
            multi_fuel_characteristics=modes,
        )
        proto_msg = convert_cogas_component_to_protobuf(original)
        restored = convert_proto_cogas_to_feems(proto_msg)

        assert restored.multi_fuel_characteristics is not None
        assert len(restored.multi_fuel_characteristics) == 2
        assert restored.multi_fuel_characteristics[0].main_fuel_type == TypeFuel.NATURAL_GAS
        assert restored.multi_fuel_characteristics[1].main_fuel_type == TypeFuel.HYDROGEN
        assert restored.multi_fuel_characteristics[0].eff_curve is not None
        np.testing.assert_allclose(restored.multi_fuel_characteristics[0].eff_curve, eff_lng)
