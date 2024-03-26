import random
from typing import Union, NamedTuple, cast
from unittest import TestCase

import numpy as np
from scipy.integrate import simpson

from feems.components_model import (
    ElectricComponent,
    Genset,
    BasicComponent,
    MainEngineWithGearBoxForMechanicalPropulsion,
    MechanicalPropulsionComponent,
    ShaftLine,
)
from feems.components_model.component_electric import FuelCellSystem
from feems.components_model.utility import (
    get_list_random_distribution_numbers_for_total_number,
)
from feems.types_for_feems import TypePower, TypeComponent
from tests.utility import (
    create_switchboard_with_components,
    set_random_power_input_consumer_pti_pto_energy_storage,
    create_engine_component,
    create_a_pti_pto,
)


class LoadSharingModeSummary(NamedTuple):
    load_sharing_mode_power_source: np.ndarray
    load_sharing_mode_pti_pto: np.ndarray
    load_sharing_mode_energy_storage: np.ndarray


class StatusSummary(NamedTuple):
    status_power_source: np.ndarray
    status_pti_pto: np.ndarray
    status_energy_storage: np.ndarray


class TestSwitchboard(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        number_of_components = 20
        self.no_points_to_test = 10000
        power_avail_total = 3000

        #: Distribute number of components by types
        number_of_components_list = get_list_random_distribution_numbers_for_total_number(
            4, number_of_components
        )
        self.switchboard = create_switchboard_with_components(
            1,
            power_avail_total,
            no_power_sources=number_of_components_list[0],
            no_power_consumer=number_of_components_list[1],
            no_pti_ptos=number_of_components_list[2],
            no_energy_storage=number_of_components_list[3],
        )

    def set_load_sharing_mode(self) -> LoadSharingModeSummary:
        # Set load sharing mode
        load_sharing_mode_power_source = np.random.rand(
            self.no_points_to_test, self.switchboard.no_power_sources
        )
        load_sharing_mode_power_source[load_sharing_mode_power_source < 0.7] = 0
        self.switchboard.set_load_sharing_mode_components_by_power_type(
            TypePower.POWER_SOURCE, load_sharing_mode_power_source
        )
        load_sharing_mode_pti_pto = np.random.rand(
            self.no_points_to_test, self.switchboard.no_pti_pto
        )
        load_sharing_mode_pti_pto[load_sharing_mode_pti_pto < 0.1] = 0
        load_sharing_mode_pti_pto[load_sharing_mode_pti_pto >= 0.1] = 1
        self.switchboard.set_load_sharing_mode_components_by_power_type(
            type_=TypePower.PTI_PTO, load_sharing_mode=load_sharing_mode_pti_pto
        )
        load_sharing_mode_energy_storage = np.random.rand(
            self.no_points_to_test, self.switchboard.no_energy_storage
        )
        load_sharing_mode_energy_storage[load_sharing_mode_energy_storage < 0.1] = 0
        load_sharing_mode_energy_storage[load_sharing_mode_energy_storage >= 0.1] = 1
        self.switchboard.set_load_sharing_mode_components_by_power_type(
            type_=TypePower.ENERGY_STORAGE,
            load_sharing_mode=load_sharing_mode_energy_storage,
        )
        return LoadSharingModeSummary(
            load_sharing_mode_power_source=load_sharing_mode_power_source,
            load_sharing_mode_pti_pto=load_sharing_mode_pti_pto,
            load_sharing_mode_energy_storage=load_sharing_mode_energy_storage,
        )

    def set_status(self) -> StatusSummary:
        status_new_power_source = np.round(
            np.random.rand(self.no_points_to_test, self.switchboard.no_power_sources)
        ).astype(bool)
        index_all_power_source_off = np.bitwise_not(status_new_power_source).all(axis=1)
        status_new_power_source[index_all_power_source_off, 0] = (
            True  # Make sure at least one power source is on
        )
        self.switchboard.set_status_components_by_power_type(
            type_=TypePower.POWER_SOURCE, status=status_new_power_source
        )
        status_new_pti_pto = np.round(
            np.random.rand(self.no_points_to_test, self.switchboard.no_pti_pto)
        ).astype(bool)
        self.switchboard.set_status_components_by_power_type(
            type_=TypePower.PTI_PTO, status=status_new_pti_pto
        )
        status_new_energy_storage = np.round(
            np.random.rand(self.no_points_to_test, self.switchboard.no_energy_storage)
        ).astype(bool)
        self.switchboard.set_status_components_by_power_type(
            type_=TypePower.ENERGY_STORAGE, status=status_new_energy_storage
        )
        return StatusSummary(
            status_power_source=status_new_power_source,
            status_pti_pto=status_new_pti_pto,
            status_energy_storage=status_new_energy_storage,
        )

    def test_initialization(self):
        power_types = [component.power_type for component in self.switchboard.components]

        # Test initialization
        self.assertEqual(
            power_types.count(TypePower.POWER_SOURCE), self.switchboard.no_power_sources
        )
        self.assertEqual(
            power_types.count(TypePower.POWER_CONSUMER), self.switchboard.no_consumers
        )
        self.assertEqual(
            power_types.count(TypePower.ENERGY_STORAGE),
            self.switchboard.no_energy_storage,
        )
        self.assertEqual(power_types.count(TypePower.PTI_PTO), self.switchboard.no_pti_pto)

    def test_setting_and_getting_status_power_source(self):
        # Test setting and getting the status of the power source
        status_power_source = self.switchboard.get_status_component_by_power_type(
            TypePower.POWER_SOURCE
        )
        self.assertEqual(
            np.array(status_power_source).all(),
            np.ones([self.switchboard.no_power_sources, 1]).astype(bool).all(),
        )
        new_status = self.set_status()
        status_power_source = self.switchboard.get_status_component_by_power_type(
            TypePower.POWER_SOURCE
        )
        status_pti_pto = self.switchboard.get_status_component_by_power_type(TypePower.PTI_PTO)
        status_energy_storage = self.switchboard.get_status_component_by_power_type(
            TypePower.ENERGY_STORAGE
        )
        self.assertTrue(
            np.equal(
                np.array(status_power_source).transpose(),
                new_status.status_power_source,
            ).all()
        )
        self.assertTrue(
            np.equal(np.array(status_pti_pto).transpose(), new_status.status_pti_pto).all()
        )
        self.assertTrue(
            np.equal(
                np.array(status_energy_storage).transpose(),
                new_status.status_energy_storage,
            ).all()
        )

    def test_setting_getting_the_load_sharing_status(self):
        # Test setting and getting the load sharing status of the power source
        load_sharing_status = self.switchboard.get_load_sharing_mode_components_by_power_type(
            TypePower.POWER_SOURCE
        )
        self.assertEqual(np.abs(np.array(load_sharing_status)).sum(), 0)
        load_sharing_summary = self.set_load_sharing_mode()

        load_sharing_status = self.switchboard.get_load_sharing_mode_components_by_power_type(
            TypePower.POWER_SOURCE
        )
        self.assertTrue(
            np.equal(
                np.array(load_sharing_status).transpose(),
                load_sharing_summary.load_sharing_mode_power_source,
            ).all()
        )

        load_sharing_status = self.switchboard.get_load_sharing_mode_components_by_power_type(
            TypePower.PTI_PTO
        )
        self.assertTrue(
            np.equal(
                np.array(load_sharing_status).transpose(),
                load_sharing_summary.load_sharing_mode_pti_pto,
            ).all()
        )

        load_sharing_status = self.switchboard.get_load_sharing_mode_components_by_power_type(
            TypePower.ENERGY_STORAGE
        )
        self.assertTrue(
            np.equal(
                np.array(load_sharing_status).transpose(),
                load_sharing_summary.load_sharing_mode_energy_storage,
            ).all()
        )

    def test_get_power_avail_component_by_power_type(self):
        # Test getting the available rated power
        rated_power_list = []
        for component in self.switchboard.components:
            if component.power_type == TypePower.POWER_SOURCE:
                rated_power_list.append(component.rated_power * component.status)
        rated_power_list_from_class = self.switchboard.get_power_avail_component_by_power_type(
            TypePower.POWER_SOURCE
        )
        rated_power_array = np.array(rated_power_list).transpose()
        rated_power_array_from_class = np.array(rated_power_list_from_class).transpose()
        self.assertEqual(np.sum(np.abs(rated_power_array - rated_power_array_from_class)), 0)

    # noinspection PyTypeChecker
    def test_set_power_load_component_from_power_output_by_type_and_name(self):
        # Test setting power input of the component from the given output.

        # Gets a random component which is not a power source
        component: ElectricComponent = random.choice(self.switchboard.components)
        while isinstance(component, (Genset, FuelCellSystem)):
            component = cast(ElectricComponent, random.choice(self.switchboard.components))
        power_output_ref = np.random.rand(self.no_points_to_test) * component.rated_power
        power_input_ref, load = component.get_power_input_from_bidirectional_output(
            power_output_ref
        )
        self.switchboard.set_power_load_component_from_power_output_by_type_and_name(
            component.name, component.power_type, power_output_ref
        )
        self.assertTrue(np.equal(power_input_ref, component.power_input).all())

    def test_get_sum_power_input_by_power_type(self):
        """Test getting the switchboard load (sum of the power input of the power consumers)"""
        # Set status
        self.set_status()
        self.set_load_sharing_mode()

        power_summary = set_random_power_input_consumer_pti_pto_energy_storage(
            self.no_points_to_test, self.switchboard
        )
        sum_power_input = [
            power_summary.sum_power_input_power_consumer,
            power_summary.sum_power_input_pti_pto,
            power_summary.sum_power_input_energy_storage,
        ]
        for i, type_ in enumerate(
            [TypePower.POWER_CONSUMER, TypePower.PTI_PTO, TypePower.ENERGY_STORAGE]
        ):
            self.assertAlmostEqual(
                np.sum(self.switchboard.get_sum_power_input_by_power_type(type_=type_)),
                np.sum(sum_power_input[i]),
            )

    def test_power_source_load_calculation(self):
        """Test power source load calculation"""
        # Set power
        self.set_status()
        self.set_load_sharing_mode()

        power_summary = set_random_power_input_consumer_pti_pto_energy_storage(
            self.no_points_to_test, self.switchboard
        )

        load_perc_symm_power_source_ref = np.zeros(self.no_points_to_test)
        sum_power_avail_for_power_sources_symmetric = (
            self.switchboard.get_sum_power_avail_for_power_sources_symmetric()
        )
        power_is_available = sum_power_avail_for_power_sources_symmetric > 0

        load_perc_symm_power_source_ref[power_is_available] = (
            self.switchboard.get_sum_load_kw_sources_symmetric()[power_is_available]
            / sum_power_avail_for_power_sources_symmetric[power_is_available]
        )

        load_perc_symm_power_source = power_summary.load_perc_symmetric_loaded_power_source
        load_perc_symm_power_source_ref[np.isinf(load_perc_symm_power_source_ref)] = 0
        load_perc_symm_power_source[np.isinf(load_perc_symm_power_source)] = 0
        load_perc_symm_power_source_ref[np.isnan(load_perc_symm_power_source_ref)] = 0
        load_perc_symm_power_source[np.isnan(load_perc_symm_power_source)] = 0
        self.assertTrue(np.allclose(load_perc_symm_power_source, load_perc_symm_power_source_ref))

        time_step = 1.0
        self.switchboard.set_power_out_power_sources(load_perc_symm_power_source)
        result = self.switchboard.get_fuel_energy_consumption_running_time(time_step)
        for power_source in self.switchboard.component_by_power_type[TypePower.POWER_SOURCE.value]:
            index = power_source.load_sharing_mode > 0
            power_output = power_source.rated_power * load_perc_symm_power_source
            power_output *= power_source.status
            power_output[index] = power_source.rated_power * power_source.load_sharing_mode[index]
            power_output[index] = power_output[index] * power_source.status[index]
            self.assertTrue(
                np.equal(np.round(power_output, 3), np.round(power_source.power_output, 3)).all()
            )

        results2 = self.switchboard.get_fuel_energy_consumption_running_time_without_details(
            time_step
        )
        for key in results2.__dict__:
            if key == "detail_result":
                continue
            if key == "multi_fuel_consumption_total_kg":
                self.assertAlmostEqual(
                    result.__getattribute__(key).total_fuel_consumption,
                    results2.__getattribute__(key).total_fuel_consumption,
                    places=5,
                    msg="Values not matching for '%s'" % key,
                )
                continue
            with self.subTest("Test get fuel... without_details, %s" % key):
                self.assertAlmostEqual(
                    result.__getattribute__(key),
                    results2.__getattribute__(key),
                    places=5,
                    msg="Values not matching for '%s'" % key,
                )


class TestShaftLine(TestCase):
    def test_shaft_line(self):

        time_step = 1
        number_test_points = 100
        number_main_engines = random.randint(1, 4)
        rated_speed = 700

        main_engines = []
        total_rated_power_main_engine = 0

        #: Create main engine components with gear boxes
        for i in range(number_main_engines):
            #: Maximum random rated power (1500 ~ 3000 kW)
            rated_power_max = 3000

            engine_id = i + 1
            main_engine = create_engine_component(
                "main engine %i" % engine_id,
                rated_power_max,
                rated_speed,
            )
            rated_power = main_engine.rated_power

            #: Get total rated power of main engines
            total_rated_power_main_engine += rated_power

            #: Create a gearbox instance
            gearbox = BasicComponent(
                type_=TypeComponent.GEARBOX,
                name="gearbox",
                power_type=TypePower.POWER_TRANSMISSION,
                rated_power=rated_power,
                rated_speed=150,
                eff_curve=np.array([98.0]),
            )

            #: Create a main engine with a gear box instance and collect it in the list
            main_engines.append(
                MainEngineWithGearBoxForMechanicalPropulsion(
                    "main engine %i" % engine_id, main_engine, gearbox, 1
                )
            )

        #: Create a pti/pto
        pti_pto = create_a_pti_pto("PTI/PTO", rated_power=1000)

        #: Create a propeller load
        rated_power_propeller = (
            0.5 * (random.random() + 1) * (total_rated_power_main_engine + pti_pto.rated_power)
        )
        propeller_load = MechanicalPropulsionComponent(
            TypeComponent.PROPELLER_LOAD,
            TypePower.POWER_CONSUMER,
            "propeller 1",
            rated_power_propeller,
            np.array([1]),
            rated_speed=150,
            shaft_line_id=1,
        )

        # Create a shaftline with only main_engines and a propeller load
        # noinspection PyTypeChecker
        ShaftLine("Shaft line with only engines", 1, main_engines + [propeller_load])

        #: Create a shaft line component
        shaft_line = ShaftLine("shaft line 1", 1, main_engines + [pti_pto, propeller_load])

        #: Test pure mechanical propulsion mode
        while True:
            #: Set the power input for the propeller load
            propeller_load.power_input = np.random.rand(number_test_points) * (
                propeller_load.rated_power - pti_pto.rated_power
            )

            #: Set the main engine status so that total available power is greater than
            #: The load.
            status = np.random.rand(number_test_points, len(main_engines)) > 0.5
            total_power_available = 0
            for _ in range(2):
                total_power_available = 0
                for i, main_engine in enumerate(main_engines):
                    total_power_available += status[:, i] * main_engine.rated_power
                    main_engine.status = status[:, i]
                index = total_power_available < propeller_load.power_input
                if index.any():
                    status[index, :] = True
                else:
                    break
            if (total_power_available > propeller_load.power_input).all():
                break

        #: Get total power available and total running hours for reference
        total_power_available = 0
        total_running_hours_ref = 0
        for main_engine in main_engines:
            total_power_available += main_engine.rated_power * main_engine.status
            total_running_hours_ref += main_engine.status
        # noinspection PyUnresolvedReferences
        total_running_hours_ref = total_running_hours_ref.sum() * time_step / 3600
        total_load_percentage_ref = propeller_load.power_input / total_power_available

        #: Calculate the reference fuel consumption
        fuel_consumption_rate_ref = 0
        for main_engine in main_engines:
            fuel_consumption_rate_temp = main_engine.get_engine_run_point_from_power_out_kw(
                main_engine.rated_power * total_load_percentage_ref * main_engine.status
            ).fuel_flow_rate_kg_per_s.total_fuel_consumption
            fuel_consumption_rate_ref += fuel_consumption_rate_temp
        fuel_consumption_ref = simpson(fuel_consumption_rate_ref) * time_step

        #: Set the PTI/PTO power 0
        pti_pto.power_input = pti_pto.set_power_output_from_input(np.zeros(number_test_points))
        pti_pto.full_pti_mode = np.zeros(number_test_points).astype(bool)
        #: Do the power balance calculation
        shaft_line.do_power_balance()

        #: Calculate fuel calculation
        result = shaft_line.get_fuel_calculation_running_hours(time_step)

        #: Check the result
        self.assertAlmostEqual(result.running_hours_main_engines_hr, total_running_hours_ref)
        self.assertAlmostEqual(result.fuel_consumption_total_kg, fuel_consumption_ref)

        #: Test the hybrid propulsion
        while True:
            #: Set the power input for the propeller load
            propeller_load.power_input = (
                np.random.rand(number_test_points) * propeller_load.rated_power
            )

            #: Set the main engine status so that total available power is greater than the load.
            status = np.random.rand(number_test_points, len(main_engines)) > 0.5
            total_power_available = 0
            for _ in range(2):
                total_power_available = 0
                for i, main_engine in enumerate(main_engines):
                    total_power_available += status[:, i] * main_engine.rated_power
                    main_engine.status = status[:, i]
                total_power_available += pti_pto.rated_power
                index = total_power_available < propeller_load.power_input
                if index.any():
                    status[index, :] = True
                else:
                    break
            if (total_power_available > propeller_load.power_input).all():
                break
        total_power_available_main_engines = total_power_available - pti_pto.rated_power

        #: Generate power output for PTI/PTO. Negative means PTO, positive means PTI
        power_output_pti_pto = (np.random.rand(100) * 2 - 1) * pti_pto.rated_power

        #: Check power balance
        max_power_output_pti_pto = propeller_load.power_input
        power_output_pti_pto = np.minimum(power_output_pti_pto, max_power_output_pti_pto)
        min_power_output_pti_pto = -(
            total_power_available_main_engines - propeller_load.power_input
        )
        power_output_pti_pto = np.maximum(power_output_pti_pto, min_power_output_pti_pto)
        pti_pto.full_pti_mode = power_output_pti_pto == max_power_output_pti_pto

        #: Get the reference value for running hours and fuel consumption
        total_power_output_main_engines = propeller_load.power_input - power_output_pti_pto
        status = total_power_output_main_engines > 0
        total_load_percentage_ref = np.zeros(number_test_points)
        total_load_percentage_ref[status] = (
            total_power_output_main_engines[status] / total_power_available_main_engines[status]
        )
        total_running_hours_ref = 0
        fuel_consumption_ref = 0
        for engine in main_engines:
            engine.status[np.bitwise_not(status)] = False
            engine.power_output = total_load_percentage_ref * engine.rated_power * engine.status
            res_engine = engine.get_engine_run_point_from_power_out_kw()
            fuel_consumption_ref += (
                simpson(res_engine.fuel_flow_rate_kg_per_s.total_fuel_consumption) * time_step
            )
            total_running_hours_ref += engine.status.sum() * time_step / 3600

        #: Set the PTI/PTO power
        pti_pto.set_power_input_from_output(power_output_pti_pto)

        #: Calculate PTI/PTO running hours
        total_running_hours_ref += (pti_pto.power_output != 0).sum() * time_step / 3600

        #: Do the power balance calculation
        shaft_line.do_power_balance()

        #: Get fuel calculation
        result = shaft_line.get_fuel_calculation_running_hours(time_step)
        self.assertAlmostEqual(result.fuel_consumption_total_kg, fuel_consumption_ref)
        self.assertAlmostEqual(
            result.running_hours_main_engines_hr + result.running_hours_pti_pto_total_hr,
            total_running_hours_ref,
        )
