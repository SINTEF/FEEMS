from functools import reduce
from typing import Tuple, List, NamedTuple

from scipy import integrate

from feems.components_model.utility import IntegrationMethod
from .test_system import TestMechanicalPropulsionSystemSetup
from feems.types_for_feems import TypePower
import numpy as np
import random


class PowerSeries(NamedTuple):
    total_power_load_kw: np.ndarray
    total_power_pti_pto: np.ndarray = None
    full_pti_pto_mode: np.ndarray = None


class TestMechanicalPropulsionSystemSimulation(TestMechanicalPropulsionSystemSetup):
    def _set_power_input_and_status_no_pti_pto(self, number_points) -> PowerSeries:
        """Set power input and status for the mechanical system"""
        total_power_kw = 0
        for each_shaft_line in self.system.shaft_line:
            # Set power load on the consumer
            power_load_kw = np.random.random(number_points) * 1000
            total_power_kw += power_load_kw
            for propeller_load in each_shaft_line.component_by_power_type[
                TypePower.POWER_CONSUMER
            ]:
                propeller_load.set_power_input_from_output(power_load_kw)
            for pti_pto in each_shaft_line.component_by_power_type[TypePower.PTI_PTO]:
                pti_pto.set_power_input_from_output(np.zeros_like(power_load_kw))
                pti_pto.full_pti_mode = np.zeros(number_points).astype(bool)
            # Set status and load sharing mode for the engines
            for comp in (
                each_shaft_line.component_by_power_type[TypePower.POWER_SOURCE]
                + each_shaft_line.component_by_power_type[TypePower.PTI_PTO]
            ):
                comp.status = np.ones(number_points).astype(bool)
        return PowerSeries(total_power_load_kw=np.atleast_1d(total_power_kw))

    def _set_power_input_output_with_pti_pto(self, number_points) -> PowerSeries:
        """Set power input and output for the mechanical system"""
        power_series = self._set_power_input_and_status_no_pti_pto(number_points)
        total_power_pti_pto_mechanical_kw = np.zeros_like(power_series.total_power_load_kw)
        full_pti_mode = np.zeros_like(power_series.total_power_load_kw).astype(bool)
        for pti_pto in self.system.pti_ptos:
            power_pti_pto_electric_kw = (np.random.random(number_points) - 0.5) * 2000
            total_power_pti_pto_mechanical_kw += pti_pto.set_power_output_from_input(
                power_pti_pto_electric_kw
            )[0]
        for each_shaft_line in self.system.shaft_line:
            total_power_load_shaftline = reduce(
                lambda acc, load: acc + load.power_input,
                each_shaft_line.component_by_power_type[TypePower.POWER_CONSUMER],
                0,
            )
            total_power_pti_pto_mechanical_shaftline = reduce(
                lambda acc, pti_pto: acc + pti_pto.power_output,
                each_shaft_line.component_by_power_type[TypePower.PTI_PTO],
                0,
            )
            full_pti_mode = np.bitwise_or(
                full_pti_mode,
                total_power_load_shaftline < total_power_pti_pto_mechanical_shaftline,
            )
        total_power_pti_pto_mechanical_kw[full_pti_mode] = 0
        for pti_pto in self.system.pti_ptos:
            pti_pto.full_pti_mode = full_pti_mode
        return PowerSeries(
            total_power_load_kw=power_series.total_power_load_kw,
            total_power_pti_pto=np.atleast_1d(total_power_pti_pto_mechanical_kw),
            full_pti_pto_mode=full_pti_mode,
        )

    def test_run_simulation_without_pti_pto(self):
        """Test running simulation for the mechanical system with a single point"""
        tests = [
            dict(
                name="Test running simulation for the mechanical system with a single point",
                number_points=1,
            ),
            dict(
                name="Test running simulation for the mechanical system with multiple points",
                number_points=random.randint(10, 100),
            ),
        ]
        for test in tests:
            with self.subTest(test["name"]):
                number_points = test["number_points"]
                total_power_kw = self._set_power_input_and_status_no_pti_pto(
                    number_points
                ).total_power_load_kw
                time_interval_s = 60
                self.system.do_power_balance()

                # Check if the main engine has been correctly loaded
                for shaft_line in self.system.shaft_line:
                    main_engines = shaft_line.component_by_power_type[TypePower.POWER_SOURCE]
                    loads = shaft_line.component_by_power_type[TypePower.POWER_CONSUMER]
                    total_rated_power = np.array(
                        [each.rated_power * each.status for each in main_engines]
                    ).sum(axis=0)
                    total_power_consumption = reduce(
                        lambda acc, load: acc + load.power_input, loads, 0
                    )
                    for power_source in main_engines:
                        power_output_calc = (
                            power_source.status
                            * total_power_consumption
                            * power_source.rated_power
                            / total_rated_power
                        ).sum()
                        self.assertAlmostEqual(power_source.power_output.sum(), power_output_calc)
                self.system.set_time_interval(
                    time_interval_s=time_interval_s,
                    integration_method=IntegrationMethod.simpson,
                )
                feems_result = self.system.get_fuel_energy_consumption_running_time()

                # Check if the fuel consumption is not 0 even though the integration
                # method is simpson method
                if number_points == 1:
                    self.assertNotAlmostEqual(feems_result.fuel_consumption_total_kg, 0)

                # Check if the BSFC is in the sane range
                total_energy_kj = (
                    integrate.simpson(total_power_kw, dx=time_interval_s)
                    if len(total_power_kw) > 1
                    else total_power_kw * time_interval_s
                )
                average_bsfc = (
                    feems_result.fuel_consumption_total_kg * 1000 / (total_energy_kj / 3600)
                )
                self.assertTrue(300 > average_bsfc > 180)

    def test_run_simulation_with_incorrect_config(self):
        """Test running simulation for the mechanical system with incorrect configuration"""
        # Set the load time series
        total_power_kw = 0
        number_points = random.randint(10, 50)
        for comp in self.system.mechanical_loads + self.system.pti_ptos:
            power_load_kw = np.random.random(number_points) * 3000
            total_power_kw += power_load_kw
            comp.set_power_input_from_output(power_load_kw)
        for comp in self.system.main_engines + self.system.pti_ptos:
            comp.status = np.ones(number_points).astype(bool)
        for comp in self.system.pti_ptos:
            comp.full_pti_mode = np.ones(number_points).astype(bool)

        with self.subTest("Test for inconsistent number of points for power inputs"):
            component_with_wrong_input = random.choice(self.system.mechanical_loads)
            wrong_power_input = (
                np.random.random(number_points - random.randint(1, number_points - 1)) * 2000
            )
            component_with_wrong_input.set_power_input_from_output(wrong_power_input)

            # Test validation
            self.assertFalse(self.system.validate_inputs_before_power_balance_calculation())
            for err_msg in self.system.errors_simulation_inputs:
                print(err_msg)
            component_with_wrong_input.set_power_input_from_output(
                np.random.random(number_points) * 2000
            )

        with self.subTest(
            "Test for inconsistent number of points for status for PTI/PTO and main engines"
        ):
            components = [
                random.choice(self.system.pti_ptos),
                random.choice(self.system.main_engines),
            ]
            for comp in components:
                wrong_status = np.ones(
                    number_points - random.randint(1, number_points - 1)
                ).astype(bool)
                comp.status = wrong_status

                # Test validation
                self.assertFalse(self.system.validate_inputs_before_power_balance_calculation())
                for err_msg in self.system.errors_simulation_inputs:
                    print(err_msg)
                comp.status = np.ones(number_points).astype(bool)

        with self.subTest("Test for inconsistent number of points of full pti pto mode"):
            component_with_wrong_input = random.choice(self.system.pti_ptos)
            wrong_full_pti_mode = np.ones(
                number_points - random.randint(1, number_points - 1)
            ).astype(bool)
            component_with_wrong_input.full_pti_mode = wrong_full_pti_mode

            # Test validation
            self.assertFalse(self.system.validate_inputs_before_power_balance_calculation())
            for err_msg in self.system.errors_simulation_inputs:
                print(err_msg)
            component_with_wrong_input.full_pti_mode = np.ones(number_points).astype(bool)

    def test_run_simulation_with_pti_pto(self):
        """Test running simulation for the mechanical system with a single point"""
        number_points = random.randint(10, 100)
        power_series = self._set_power_input_output_with_pti_pto(number_points)
        time_interval_s = 60
        self.system.set_time_interval(
            time_interval_s=time_interval_s,
            integration_method=IntegrationMethod.simpson,
        )
        self.system.do_power_balance()

        # Check if the pti pto power output is correct for non-full pti mode
        total_power_pti_pto = reduce(
            lambda acc, pti_pto: acc + pti_pto.power_output,
            self.system.pti_ptos,
            np.zeros(number_points),
        )
        non_full_pti_pto_mode = np.bitwise_not(power_series.full_pti_pto_mode)
        self.assertTrue(
            np.allclose(
                total_power_pti_pto[non_full_pti_pto_mode],
                power_series.total_power_pti_pto[non_full_pti_pto_mode],
            )
        )

        # Check if the main engine has been correctly loaded
        for shaft_line in self.system.shaft_line:
            main_engines = shaft_line.component_by_power_type[TypePower.POWER_SOURCE]
            loads = shaft_line.component_by_power_type[TypePower.POWER_CONSUMER]
            pti_ptos = shaft_line.component_by_power_type[TypePower.PTI_PTO]
            total_rated_power = np.array(
                [each.rated_power * each.status for each in main_engines]
            ).sum(axis=0)
            total_power_consumption = reduce(lambda acc, load: acc + load.power_input, loads, 0)
            total_pti_pto_power = reduce(
                lambda acc, pti_pto: acc + pti_pto.power_output, pti_ptos, 0
            )
            total_power_on_engines = total_power_consumption - total_pti_pto_power
            for power_source in main_engines:
                index = total_rated_power == 0
                power_output_calc = np.zeros_like(power_source.power_output)
                power_output_calc[~index] = +(
                    power_source.status.astype(float)[~index]
                    * total_power_on_engines[~index]
                    * power_source.rated_power
                    / total_rated_power[~index]
                )
                self.assertAlmostEqual(power_source.power_output.sum(), power_output_calc.sum())
