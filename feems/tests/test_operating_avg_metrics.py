"""Tests for the per-component operating-average metrics (issue #97).

Covers the four scalars exposed on every detail_result row:
- operating_avg_power_kw
- operating_avg_reversible_power_kw
- operating_avg_efficiency
- operating_avg_sfc_g_per_kwh

Averages are computed over each component's on-state timesteps only
(mask = power_output != 0, matching the existing running_hours_h semantics).
"""

from unittest import TestCase

import numpy as np
from feems.components_model.component_base import BasicComponent
from feems.components_model.component_mechanical import (
    Engine,
    MainEngineForMechanicalPropulsion,
    MainEngineWithGearBoxForMechanicalPropulsion,
)
from feems.components_model.node import (
    _efficiency_from_totals,
    _sfc_g_per_kwh,
    _time_weighted_avg_magnitude_kw,
    get_fuel_emission_energy_balance_for_component,
)
from feems.components_model.utility import IntegrationMethod
from feems.fuel import FuelOrigin, FuelSpecifiedBy, TypeFuel
from feems.types_for_feems import TypeComponent, TypePower

from tests.utility import NOxCalculationMethod, create_a_pti_pto

# ---------------- helpers ------------------------------------------------


def _bsfc_curve_constant(bsfc_g_per_kwh: float = 200.0) -> np.ndarray:
    """Flat BSFC curve so engine SFC is predictable across all loads."""
    return np.array(
        [
            [0.1, bsfc_g_per_kwh],
            [0.5, bsfc_g_per_kwh],
            [1.0, bsfc_g_per_kwh],
        ]
    )


def _make_main_engine(rated_power_kw: float = 1000.0) -> MainEngineForMechanicalPropulsion:
    engine = Engine(
        type_=TypeComponent.MAIN_ENGINE,
        name="me-test",
        rated_power=rated_power_kw,
        rated_speed=900.0,
        bsfc_curve=_bsfc_curve_constant(),
        nox_calculation_method=NOxCalculationMethod.TIER_2,
        fuel_type=TypeFuel.DIESEL,
        fuel_origin=FuelOrigin.FOSSIL,
    )
    return MainEngineForMechanicalPropulsion(name="ME", engine=engine)


# ---------------- tests --------------------------------------------------


class TestHelpers(TestCase):
    """Direct tests of the small numeric helpers (cheap, deterministic)."""

    def test_time_weighted_avg_scalar_dt_mean_over_mask(self):
        # 4 timesteps, mask selects 2 of them (the non-zero entries),
        # uniform dt → arithmetic mean of the selected magnitudes
        p = np.array([0.0, 100.0, 200.0, 0.0])
        mask = p != 0
        avg = _time_weighted_avg_magnitude_kw(p, time_interval_s=60.0, mask=mask)
        self.assertAlmostEqual(avg, 150.0)  # mean(|100|, |200|)

    def test_time_weighted_avg_array_dt(self):
        # Non-uniform dt: 200 kW for 100 s and 50 kW for 300 s ⇒ weighted mean = 87.5
        p = np.array([200.0, 50.0])
        dt = np.array([100.0, 300.0])
        mask = np.array([True, True])
        avg = _time_weighted_avg_magnitude_kw(p, time_interval_s=dt, mask=mask)
        self.assertAlmostEqual(avg, (200 * 100 + 50 * 300) / 400.0)

    def test_time_weighted_avg_empty_mask_is_zero(self):
        avg = _time_weighted_avg_magnitude_kw(
            np.array([100.0, 100.0]), time_interval_s=10.0, mask=np.array([False, False])
        )
        self.assertEqual(avg, 0.0)

    def test_time_weighted_avg_absolute_value(self):
        # Magnitudes only (negative input still produces positive average)
        p = np.array([-50.0, -50.0])
        mask = p != 0
        avg = _time_weighted_avg_magnitude_kw(p, time_interval_s=10.0, mask=mask)
        self.assertAlmostEqual(avg, 50.0)

    def test_efficiency_clamped_and_guarded(self):
        self.assertEqual(_efficiency_from_totals(10.0, 0.0), 0.0)
        self.assertEqual(_efficiency_from_totals(0.0, 10.0), 0.0)
        self.assertAlmostEqual(_efficiency_from_totals(4.0, 10.0), 0.4)
        # clamp to [0, 1] — efficiency > 1 should saturate
        self.assertEqual(_efficiency_from_totals(15.0, 10.0), 1.0)

    def test_sfc_zero_when_no_useful_energy(self):
        self.assertEqual(_sfc_g_per_kwh(1.0, 0.0), 0.0)
        self.assertAlmostEqual(_sfc_g_per_kwh(0.5, 1.0), 500.0)


class TestMainEngineMetrics(TestCase):
    """Main engine: all four metrics populated; off-state excluded from average."""

    def test_constant_load_with_off_time(self):
        engine_comp = _make_main_engine(rated_power_kw=1000.0)
        # 4 timesteps × 60 s; 100 % load in [1, 2, 3], off in [0]
        power = np.array([0.0, 500.0, 500.0, 500.0])
        engine_comp.power_output = power
        engine_comp.engine.power_output = power
        engine_comp.engine.status = (power > 0).astype(bool)

        res = get_fuel_emission_energy_balance_for_component(
            component=engine_comp,
            time_interval_s=60.0,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )

        # avg power excludes the off step → mean of [500, 500, 500] = 500
        self.assertAlmostEqual(res.operating_avg_power_kw, 500.0, places=6)
        # SFC = total_fuel_g / shaft_kWh. With flat 200 g/kWh BSFC the integrated
        # SFC should equal 200 g/kWh up to integration error.
        self.assertGreater(res.operating_avg_sfc_g_per_kwh, 199.0)
        self.assertLess(res.operating_avg_sfc_g_per_kwh, 201.0)
        # η = shaft_MJ / fuel_MJ. With BSFC 200 and diesel LHV ≈ 0.0427 MJ/g,
        # η ≈ 3600 / (200 × 42.7) ≈ 0.42. Allow wide bracket.
        self.assertGreater(res.operating_avg_efficiency, 0.30)
        self.assertLess(res.operating_avg_efficiency, 0.50)
        # Reversible field is not used by engines.
        self.assertEqual(res.operating_avg_reversible_power_kw, 0.0)

    def test_engine_off_for_entire_run_reports_zeros(self):
        engine_comp = _make_main_engine(rated_power_kw=1000.0)
        n = 4
        engine_comp.power_output = np.zeros(n)
        engine_comp.engine.power_output = np.zeros(n)
        engine_comp.engine.status = np.zeros(n, dtype=bool)

        res = get_fuel_emission_energy_balance_for_component(
            component=engine_comp,
            time_interval_s=60.0,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        self.assertEqual(res.operating_avg_power_kw, 0.0)
        self.assertEqual(res.operating_avg_reversible_power_kw, 0.0)
        self.assertEqual(res.operating_avg_efficiency, 0.0)
        self.assertEqual(res.operating_avg_sfc_g_per_kwh, 0.0)

    def test_main_engine_with_gearbox_uses_delivered_shaft_power(self):
        """Regression for PR #98 Copilot review: MAIN_ENGINE_WITH_GEARBOX must
        use `component.power_output` (delivered shaft kW) for efficiency/SFC,
        NOT `component.engine.power_output` which is upstream of the gearbox
        (= power / eff_gearbox).
        """
        engine = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            name="inner",
            rated_power=1000.0,
            rated_speed=900.0,
            bsfc_curve=_bsfc_curve_constant(),
            nox_calculation_method=NOxCalculationMethod.TIER_2,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        gearbox = BasicComponent(
            type_=TypeComponent.GEARBOX,
            power_type=TypePower.POWER_TRANSMISSION,
            name="gearbox",
            rated_power=1000.0,
            rated_speed=900.0,
            eff_curve=np.array([0.95]),  # flat 95 % gearbox efficiency
        )
        me_gb = MainEngineWithGearBoxForMechanicalPropulsion(
            name="ME-with-gearbox", engine=engine, gearbox=gearbox
        )
        # Drive the delivered shaft at 500 kW; engine side will be 500/0.95 ≈ 526.3 kW
        delivered = np.array([0.0, 500.0, 500.0, 500.0])
        me_gb.power_output = delivered
        # Important: the dispatcher runs AFTER get_engine_run_point_from_power_out_kw
        # has set engine.power_output = power / eff_gearbox. Mirror that here.
        me_gb.get_engine_run_point_from_power_out_kw(power=delivered)

        res = get_fuel_emission_energy_balance_for_component(
            component=me_gb,
            time_interval_s=60.0,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )

        # operating_avg_power_kw uses component.power_output → 500 kW (delivered shaft)
        self.assertAlmostEqual(res.operating_avg_power_kw, 500.0, places=6)

        # Bug-before-fix: efficiency used engine.power_output (~526 kW), giving
        # eff = 526*dt / fuel_MJ. After fix, eff = 500*dt / fuel_MJ — strictly
        # smaller because the gearbox loss is now correctly debited.
        # Compute the "old" (buggy) efficiency for comparison:
        from feems.components_model.node import _integrate_kw_signal_to_mj

        buggy_shaft_mj = _integrate_kw_signal_to_mj(
            me_gb.engine.power_output, 60.0, IntegrationMethod.simpson
        )
        fixed_shaft_mj = _integrate_kw_signal_to_mj(
            me_gb.power_output, 60.0, IntegrationMethod.simpson
        )
        self.assertLess(fixed_shaft_mj, buggy_shaft_mj)  # by ~5 % (gearbox loss)
        # The reported efficiency must come from the fixed (smaller) shaft energy.
        self.assertLess(res.operating_avg_efficiency, buggy_shaft_mj / res.fuel_energy_total_mj)


class TestPTIPTOMetrics(TestCase):
    """PTI/PTO: bidirectional. Mixed-sign signal must populate both avg fields."""

    def test_mixed_pti_and_pto(self):
        pti_pto = create_a_pti_pto()
        # power_input convention (see node.py:284-331):
        #   power_input > 0  → PTI mode (electric in)
        #   power_input < 0  → PTO mode (electric out)
        # The signal below: 2 PTO steps at 200 kW, 1 off, 2 PTI steps at 100 kW.
        pti_pto.power_input = np.array([-200.0, -200.0, 0.0, 100.0, 100.0])
        pti_pto.power_output = np.array([-180.0, -180.0, 0.0, 90.0, 90.0])
        pti_pto.full_pti_mode = np.array([False, False, False, True, True])
        pti_pto.full_pto_mode = np.array([True, True, False, False, False])
        pti_pto.status = (pti_pto.power_input != 0).astype(bool)

        res = get_fuel_emission_energy_balance_for_component(
            component=pti_pto,
            time_interval_s=60.0,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        # PTO avg = mean(|200|, |200|) = 200; PTI avg = mean(|100|, |100|) = 100
        self.assertAlmostEqual(res.operating_avg_power_kw, 200.0, places=6)
        self.assertAlmostEqual(res.operating_avg_reversible_power_kw, 100.0, places=6)
        # Efficiency is a single scalar across both directions, in [0, 1].
        self.assertGreaterEqual(res.operating_avg_efficiency, 0.0)
        self.assertLessEqual(res.operating_avg_efficiency, 1.0)
        # PTI/PTO has no fuel.
        self.assertEqual(res.operating_avg_sfc_g_per_kwh, 0.0)

    def test_only_pto_mode_leaves_reversible_zero(self):
        pti_pto = create_a_pti_pto()
        pti_pto.power_input = np.array([-300.0, -300.0, 0.0, 0.0])
        pti_pto.power_output = np.array([-270.0, -270.0, 0.0, 0.0])
        pti_pto.full_pti_mode = np.zeros(4, dtype=bool)
        pti_pto.full_pto_mode = np.array([True, True, False, False])
        pti_pto.status = (pti_pto.power_input != 0).astype(bool)

        res = get_fuel_emission_energy_balance_for_component(
            component=pti_pto,
            time_interval_s=60.0,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        self.assertAlmostEqual(res.operating_avg_power_kw, 300.0, places=6)
        self.assertEqual(res.operating_avg_reversible_power_kw, 0.0)

    def test_pure_pto_has_nonzero_efficiency(self):
        """Regression for PR #98 Copilot review: PTI/PTO efficiency must be
        computed directly from power signals — not from res.energy_*_total_mj,
        which the existing branch populates differently depending on
        isSystemMechanical. A pure-PTO run called from a switchboard context
        (isSystemMechanical=False) used to report efficiency = 0.0.
        """
        pti_pto = create_a_pti_pto()
        # Pure PTO: electric out (power_input < 0), mech in (power_output > 0).
        pti_pto.power_input = np.array([-300.0, -300.0, -300.0, -300.0])
        pti_pto.power_output = np.array([330.0, 330.0, 330.0, 330.0])
        pti_pto.full_pti_mode = np.zeros(4, dtype=bool)
        pti_pto.full_pto_mode = np.ones(4, dtype=bool)
        pti_pto.status = np.ones(4, dtype=bool)

        # Switchboard context — would have left mech_total_mj unpopulated under
        # the old formula, giving energy_in = 0 → efficiency = 0.0.
        res = get_fuel_emission_energy_balance_for_component(
            component=pti_pto,
            time_interval_s=60.0,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
            isSystemMechanical=False,
        )
        # Useful out / required in = 300 / 330 ≈ 0.909 for this fixture.
        # The exact value depends on the test fixture's eff curves, but it
        # must be > 0 (the bug) and ≤ 1.
        self.assertGreater(res.operating_avg_efficiency, 0.0)
        self.assertLessEqual(res.operating_avg_efficiency, 1.0)


class TestNonFuelLoadMetrics(TestCase):
    """OTHER_LOAD: power load reported; efficiency + SFC stay at 0."""

    def test_other_load(self):
        # 100% efficiency so set_power_output_from_input is a no-op transform.
        load = BasicComponent(
            type_=TypeComponent.OTHER_LOAD,
            power_type=TypePower.POWER_CONSUMER,
            name="aux load",
            rated_power=500.0,
            eff_curve=np.array([1.0]),
        )
        load.power_input = np.array([0.0, 200.0, 200.0, 200.0])
        load.power_output = np.array([0.0, 200.0, 200.0, 200.0])
        load.status = (load.power_output != 0).astype(bool)

        res = get_fuel_emission_energy_balance_for_component(
            component=load,
            time_interval_s=60.0,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        self.assertAlmostEqual(res.operating_avg_power_kw, 200.0, places=6)
        self.assertEqual(res.operating_avg_reversible_power_kw, 0.0)
        self.assertEqual(res.operating_avg_efficiency, 0.0)
        self.assertEqual(res.operating_avg_sfc_g_per_kwh, 0.0)


class TestShoreInputMetrics(TestCase):
    """SHORE_POWER: averaging uses power_input."""

    def test_shore_power_uses_power_input(self):
        load = BasicComponent(
            type_=TypeComponent.SHORE_POWER,
            power_type=TypePower.POWER_SOURCE,
            name="shore",
            rated_power=500.0,
            eff_curve=np.array([1.0]),
        )
        # power_input is the meaningful side for shore power.
        load.power_input = np.array([0.0, 400.0, 400.0])
        load.power_output = np.array([0.0, 400.0, 400.0])
        load.status = (load.power_input != 0).astype(bool)

        res = get_fuel_emission_energy_balance_for_component(
            component=load,
            time_interval_s=60.0,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        self.assertAlmostEqual(res.operating_avg_power_kw, 400.0, places=6)
        self.assertEqual(res.operating_avg_efficiency, 0.0)
        self.assertEqual(res.operating_avg_sfc_g_per_kwh, 0.0)
