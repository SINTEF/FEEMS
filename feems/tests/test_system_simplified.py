import random
from datetime import datetime
from typing import Union
from unittest import TestCase

import numpy as np
from feems.components_model import (
    Battery,
    ElectricComponent,
    ElectricMachine,
    Engine,
    Genset,
)
from feems.components_model.component_electric import (
    FuelCell,
    FuelCellSystem,
    OrganicRankineCycle,
    ShorePowerConnection,
)
from feems.components_model.utility import (
    IntegrationMethod,
    integrate_multi_fuel_consumption,
)
from feems.exceptions import InputError
from feems.runsimulation import (
    BatteryFuelCellDieselHybridSimulationInterface,
    run_simulation,
)
from feems.simulation_interface import EnergySourceType
from feems.system_model import ElectricPowerSystem
from feems.types_for_feems import (
    NOxCalculationMethod,
    Power_kW,
    Speed_rpm,
    SwbId,
    TypeComponent,
    TypePower,
)

random.seed(10)


class TestElectricPowerSystem(TestCase):
    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        """
        Initialize with configuration for conventional, hybrid and diesel electric propulsion and
        power system variants.
        """
        super().__init__(*args, **kwargs)

        #: main engine and gearbox
        self.rated_power_aux_engine = Power_kW(1000)
        rated_speed_genset = Speed_rpm(1500)
        bsfc_curve = np.array(
            [[1.00, 0.75, 0.50, 0.25, 0.10], [193.66, 188.995, 194.47, 211.4, 250]]
        ).transpose()
        aux_engine_object = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            name="main engine",
            rated_power=Power_kW(self.rated_power_aux_engine),
            rated_speed=Speed_rpm(rated_speed_genset),
            bsfc_curve=bsfc_curve,
            nox_calculation_method=NOxCalculationMethod.TIER_2,
        )

        efficiency_generator = 0.9
        self.switchboard_id = SwbId(1)
        self.generator = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator",
            rated_power=Power_kW(1000),
            rated_speed=rated_speed_genset,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=self.switchboard_id,
            eff_curve=np.array([efficiency_generator]),
        )
        self.genset = Genset(name="genset", aux_engine=aux_engine_object, generator=self.generator)

        # Battery
        self.rated_capacity_battery_kwh = 1200.0
        self.battery = Battery(
            name="Battery 1",
            rated_capacity_kwh=self.rated_capacity_battery_kwh,
            charging_rate_c=1,
            discharge_rate_c=1,
            switchboard_id=self.switchboard_id,
        )

        # FuelCell
        self.rated_power_fuel_cell = Power_kW(1200)
        fuel_cell = FuelCell(
            name="Fuel cell 1",
            rated_power=self.rated_power_fuel_cell,
            eff_curve=np.array([0.5]),
        )
        converter = ElectricComponent(
            type_=TypeComponent.POWER_CONVERTER,
            name="Converter for fuel cell 1",
            rated_power=self.rated_power_fuel_cell,
            switchboard_id=self.switchboard_id,
        )
        self.fuel_cell_system = FuelCellSystem(
            name="Fuel cell system 1",
            fuel_cell_module=fuel_cell,
            converter=converter,
            switchboard_id=self.switchboard_id,
        )

        #: Other load
        self.rated_power_other_load = Power_kW(1000)
        self.other_load = ElectricComponent(
            type_=TypeComponent.OTHER_LOAD,
            name="other loads",
            power_type=TypePower.POWER_CONSUMER,
            rated_power=self.rated_power_other_load,
            rated_speed=Speed_rpm(0),
            eff_curve=np.array([1]),
            switchboard_id=self.switchboard_id,
        )

        #: Bus tie configuration
        bus_tie = []

        #: Configure the system
        self.power_system = ElectricPowerSystem(
            name="diesel electric system",
            power_plant_components=[
                self.genset,
                self.other_load,
                self.battery,
                self.fuel_cell_system,
            ],
            bus_tie_connections=bus_tie,
        )
        self.power_system.set_time_interval(
            time_interval_s=1, integration_method=IntegrationMethod.simpson
        )

    def test_power_balance_calculation(self) -> None:
        # Sets the load
        load_other = np.array([0.5, 0.5, 0.5]) * self.rated_power_other_load
        duration = np.array([1, 3, 2])
        self.other_load.set_power_input_from_output(load_other)
        no_data_points = len(load_other)
        on_vector = np.ones(no_data_points)
        off_vector = np.zeros(no_data_points)
        equal_load_sharing_vector = np.zeros(no_data_points)
        self.genset.status = on_vector
        self.genset.load_sharing_mode = equal_load_sharing_vector
        self.fuel_cell_system.status = off_vector
        self.fuel_cell_system.load_sharing_mode = equal_load_sharing_vector
        self.battery.status = off_vector
        self.battery.load_sharing_mode = equal_load_sharing_vector

        self.power_system.set_bus_tie_status_all(np.array([]))
        self.power_system.set_time_interval(
            time_interval_s=duration, integration_method=IntegrationMethod.sum_with_time
        )
        self.power_system.do_power_balance_calculation()

        dt = duration.sum()
        power_other = load_other[0]
        gen_shaft_power, _ = self.generator.get_shaft_power_load_from_electric_power(power_other)
        res_engine = self.genset.aux_engine.get_engine_run_point_from_power_out_kw(gen_shaft_power)
        fc_kg = res_engine.fuel_flow_rate_kg_per_s.total_fuel_consumption * dt
        res = self.power_system.get_fuel_energy_consumption_running_time()
        self.assertAlmostEqual(fc_kg, res.fuel_consumption_total_kg)
        self.assertIsInstance(res.running_hours_genset_total_hr, float)

    def test_run_simulation(self) -> None:
        # Sets the load
        load_other = np.array([0.5, 0.5, 0.5]) * self.rated_power_other_load
        duration = np.array([1, 3, 2])
        self.other_load.set_power_input_from_output(load_other)
        self.power_system.set_bus_tie_status_all(np.array([]))
        self.power_system.set_time_interval(
            time_interval_s=duration, integration_method=IntegrationMethod.sum_with_time
        )
        pms = BatteryFuelCellDieselHybridSimulationInterface()
        run_simulation(
            electric_power_system=self.power_system,
            simulation_interface=pms,
            energy_source_to_prioritize=EnergySourceType.BATTERY,
        )
        res = self.power_system.get_fuel_energy_consumption_running_time()
        self.assertEqual(res.fuel_consumption_total_kg, 0)
        energy_stored_battery = self.battery.get_energy_stored_kj(
            time_interval_s=self.power_system.time_interval_s,
            integration_method=self.power_system.integration_method,
        )
        self.assertEqual(res.energy_stored_total_mj, energy_stored_battery / 1000)

        run_simulation(
            electric_power_system=self.power_system,
            simulation_interface=pms,
            energy_source_to_prioritize=EnergySourceType.HYDROGEN,
        )
        res = self.power_system.get_fuel_energy_consumption_running_time()
        self.assertEqual(res.energy_stored_total_mj, 0)
        power_out_fuel_cell = self.fuel_cell_system.power_output
        fuel_cell_run_point = self.fuel_cell_system.get_fuel_cell_run_point(
            power_out_kw=power_out_fuel_cell
        )
        hyd_consumption = integrate_multi_fuel_consumption(
            fuel_consumption_kg_per_s=fuel_cell_run_point.fuel_flow_rate_kg_per_s,
            time_interval_s=self.power_system.time_interval_s,
            integration_method=self.power_system.integration_method,
        )
        self.assertEqual(res.fuel_consumption_total_kg, hyd_consumption.total_fuel_consumption)

        run_simulation(
            electric_power_system=self.power_system,
            simulation_interface=pms,
            energy_source_to_prioritize=EnergySourceType.LNG_DIESEL,
        )
        res = self.power_system.get_fuel_energy_consumption_running_time()
        self.assertEqual(res.energy_stored_total_mj, 0)
        fuel_cons_rate = (
            self.genset.get_fuel_cons_load_bsfc_from_power_out_generator_kw().engine.fuel_flow_rate_kg_per_s
        )
        fuel_cons = integrate_multi_fuel_consumption(
            fuel_consumption_kg_per_s=fuel_cons_rate,
            time_interval_s=self.power_system.time_interval_s,
            integration_method=self.power_system.integration_method,
        )
        self.assertEqual(res.fuel_consumption_total_kg, fuel_cons.total_fuel_consumption)

    def test_time_single_input_vs_multi_input(self) -> None:
        # Sets the load
        n = 1000
        load_other = np.random.rand(n) * self.rated_power_other_load
        duration = np.ones(shape=[n])
        start = datetime.now()
        self.sim_one_step(load_other, n)
        self.sim_one_step_part_two(load_other, n)
        end = datetime.now()
        print("one shot", end - start)
        start = datetime.now()
        self.sim_one_step(load_other=load_other[0], n=1)
        for each_load, each_duration in zip(load_other, duration):
            self.sim_one_step_part_two(load_other=each_load, n=1)

        end = datetime.now()
        print("multi shot", end - start)

    # noinspection PyUnusedLocal
    def sim_one_step(self, load_other: Union[float, np.ndarray], n: int) -> None:
        self.other_load.set_power_input_from_output(load_other)
        # Set the generators to always on
        on_vector = np.ones(n)
        off_vector = np.zeros(n)
        equal_load_sharing_vector = np.zeros(n)
        self.genset.status = on_vector
        self.genset.load_sharing_mode = equal_load_sharing_vector
        self.fuel_cell_system.status = off_vector
        self.fuel_cell_system.load_sharing_mode = equal_load_sharing_vector
        self.battery.status = off_vector
        self.battery.load_sharing_mode = equal_load_sharing_vector

    # noinspection PyUnusedLocal
    def sim_one_step_part_two(self, load_other: Union[float, np.ndarray], n: int) -> None:
        self.power_system.set_bus_tie_status_all(np.array([]))
        self.power_system.do_power_balance_calculation()


class TestOrganicRankineCycle(TestCase):
    """Organic Rankine cycle as a fuel-free power source with a fixed setpoint."""

    number_of_points = 3

    def _system(self, with_battery: bool = False):
        self.orc = OrganicRankineCycle(
            name="ORC", rated_power=Power_kW(300), switchboard_id=SwbId(1), uid="orc"
        )
        # fuel-free symmetric source as load-balancing unit keeps the test free of engine data
        self.balancing_source = ShorePowerConnection(
            name="balancing source", rated_power=Power_kW(2000), switchboard_id=SwbId(1)
        )
        self.auxiliary_load = ElectricComponent(
            type_=TypeComponent.OTHER_LOAD,
            name="auxiliary load",
            power_type=TypePower.POWER_CONSUMER,
            rated_power=Power_kW(2000),
            rated_speed=Speed_rpm(0),
            eff_curve=np.array([1]),
            switchboard_id=SwbId(1),
        )
        components = [self.orc, self.balancing_source, self.auxiliary_load]
        if with_battery:
            self.battery = Battery(
                name="battery",
                rated_capacity_kwh=1000.0,
                charging_rate_c=1,
                discharge_rate_c=1,
                switchboard_id=SwbId(1),
            )
            components.append(self.battery)
        return ElectricPowerSystem(
            name="orc test", power_plant_components=components, bus_tie_connections=[]
        )

    def _run_power_balance(self, system, auxiliary_load_kw, orc_setpoint_kw, balancing_source_on=True):
        self.auxiliary_load.set_power_input_from_output(auxiliary_load_kw)
        self.orc.status = orc_setpoint_kw != 0
        self.orc.load_sharing_mode = orc_setpoint_kw / self.orc.rated_power
        self.balancing_source.status = np.full(self.number_of_points, float(balancing_source_on))
        self.balancing_source.load_sharing_mode = np.zeros(self.number_of_points)
        system.set_bus_tie_status_all(np.array([]))
        system.set_time_interval(time_interval_s=1, integration_method=IntegrationMethod.simpson)
        system.do_power_balance_calculation()

    def test_orc_is_power_source(self):
        system = self._system()
        self.assertIn(self.orc, system.power_sources)

    def test_fixed_orc_setpoint_reduces_balancing_unit(self):
        system = self._system()
        auxiliary_load_kw = np.array([1000.0, 1000.0, 1000.0])
        orc_setpoint_kw = np.array([0.0, 150.0, 300.0])
        self._run_power_balance(system, auxiliary_load_kw, orc_setpoint_kw)
        np.testing.assert_allclose(self.orc.power_output, orc_setpoint_kw)
        np.testing.assert_allclose(self.balancing_source.power_output, auxiliary_load_kw - orc_setpoint_kw)

    def test_orc_burns_no_fuel_and_reports_recovered_energy(self):
        system = self._system()
        self._run_power_balance(system, np.full(3, 1000.0), np.full(3, 150.0))
        result = system.get_fuel_energy_consumption_running_time()
        self.assertEqual(result.fuel_consumption_total_kg, 0)
        # 150 kW over 2 s (3 points, 1 s apart) -> 0.3 MJ
        self.assertAlmostEqual(result.energy_input_waste_heat_recovery_total_mj, 150 * 2 / 1000)
        self.assertIn("ORC", result.detail_result.index)

    def test_orc_covering_load_up_to_rounding_gives_no_nan(self):
        # ORC exactly covers the load except for a rounding residual, no balancing power on,
        # battery symmetric and off: previously inf load ratio -> NaN battery power
        system = self._system(with_battery=True)
        self.battery.status = np.zeros(self.number_of_points)
        self.battery.load_sharing_mode = np.zeros(self.number_of_points)
        self.battery.power_input = np.zeros(self.number_of_points)
        auxiliary_load_kw = np.full(3, 0.1 + 0.2)  # 0.30000000000000004
        orc_setpoint_kw = np.full(3, 0.3)
        self._run_power_balance(system, auxiliary_load_kw, orc_setpoint_kw, balancing_source_on=False)
        self.assertFalse(np.isnan(self.battery.power_input).any())
        np.testing.assert_allclose(self.balancing_source.power_output, 0.0)

    def test_real_load_without_balancing_power_unchanged(self):
        # a real load with no balancing power is still not silently set to zero
        system = self._system(with_battery=True)
        self.battery.status = np.zeros(self.number_of_points)
        self.battery.load_sharing_mode = np.zeros(self.number_of_points)
        self.battery.power_input = np.zeros(self.number_of_points)
        self._run_power_balance(system, np.full(3, 500.0), np.zeros(3), balancing_source_on=False)
        self.assertFalse(np.isfinite(self.battery.power_input).all())

    def test_setpoint_above_bus_load_is_curtailed_with_balancing_source(self):
        # 300 kW setpoint on a 200 kW load: the balancing source must not go negative
        system = self._system()
        self._run_power_balance(system, np.full(3, 200.0), np.full(3, 300.0))
        np.testing.assert_allclose(self.orc.power_output, 200.0)
        np.testing.assert_allclose(self.balancing_source.power_output, 0.0, atol=1e-9)

    def test_setpoint_above_bus_load_is_curtailed_without_balancing_source(self):
        system = self._system()
        self._run_power_balance(
            system, np.full(3, 200.0), np.full(3, 300.0), balancing_source_on=False
        )
        np.testing.assert_allclose(self.orc.power_output, 200.0)
        np.testing.assert_allclose(self.balancing_source.power_output, 0.0, atol=1e-9)

    def test_orc_as_balancing_unit_is_rejected(self):
        system = self._system()
        self.auxiliary_load.set_power_input_from_output(np.full(3, 200.0))
        self.orc.status = np.ones(3)
        self.orc.load_sharing_mode = np.zeros(3)
        self.balancing_source.status = np.ones(3)
        self.balancing_source.load_sharing_mode = np.zeros(3)
        system.set_bus_tie_status_all(np.array([]))
        system.set_time_interval(time_interval_s=1, integration_method=IntegrationMethod.simpson)
        with self.assertRaisesRegex(InputError, "cannot balance the bus"):
            system.do_power_balance_calculation()

    def test_orc_running_hours(self):
        system = self._system()
        # ORC on at 2 of 3 points, 1 s apart -> 2 s
        self._run_power_balance(system, np.full(3, 1000.0), np.array([0.0, 150.0, 150.0]))
        result = system.get_fuel_energy_consumption_running_time()
        self.assertAlmostEqual(result.running_hours_orc_total_hr, 2 / 3600)
        self.assertAlmostEqual(result.detail_result.loc["ORC", "running hours [h]"], 2 / 3600)


class TestOrganicRankineCycleHeatModel(TestCase):
    def test_power_from_waste_heat(self):
        orc = OrganicRankineCycle(
            name="ORC",
            rated_power=Power_kW(300),
            rated_efficiency=0.095,
            waste_heat_fraction=0.3,
            relative_efficiency_curve=np.array([[0.0, 0.0], [0.15, 0.0], [0.5, 0.93], [1.0, 1.0]]),
        )
        design_heat_input_kw = 300 / (0.095 * 0.3)
        self.assertAlmostEqual(orc.design_heat_input_kw, design_heat_input_kw)
        np.testing.assert_allclose(
            orc.get_power_output_from_waste_heat_kw(
                [0.0, 0.1 * design_heat_input_kw, design_heat_input_kw, 2 * design_heat_input_kw]
            ),
            [0.0, 0.0, 300.0, 300.0],
        )
        # half the design heat: rated efficiency x 0.93 (part-load curve) x half the heat
        self.assertAlmostEqual(
            float(orc.get_power_output_from_waste_heat_kw(0.5 * design_heat_input_kw)), 0.93 * 150.0
        )

    def test_without_curve_runs_at_rated_efficiency(self):
        orc = OrganicRankineCycle(
            name="ORC", rated_power=Power_kW(300), rated_efficiency=0.095, waste_heat_fraction=0.3
        )
        waste_heat_kw = 0.1 * orc.design_heat_input_kw
        self.assertAlmostEqual(
            float(orc.get_power_output_from_waste_heat_kw(waste_heat_kw)), 0.095 * 0.3 * waste_heat_kw
        )

    def test_without_heat_parameters_gives_zero(self):
        orc = OrganicRankineCycle(name="ORC", rated_power=Power_kW(300))
        np.testing.assert_allclose(orc.get_power_output_from_waste_heat_kw([1000.0]), [0.0])
