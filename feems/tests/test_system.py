import copy
import pprint
import random
from typing import List, Dict
from unittest import TestCase

from feems.components_model.component_electric import COGES, ElectricMachine, SerialSystemElectric
from feems.components_model.component_mechanical import COGAS
from feems.fuel import Fuel, FuelConsumption
import numpy as np

from feems.components_model import (
    BasicComponent,
    MainEngineWithGearBoxForMechanicalPropulsion,
    MechanicalPropulsionComponent,
    Engine,
    ElectricComponent,
    BatterySystem,
    Battery,
)
from feems.components_model.utility import IntegrationMethod
from feems.system_model import ElectricPowerSystem, BusId, MechanicalPropulsionSystem
from feems.types_for_feems import (
    SwbId,
    TypeComponent,
    TypePower,
    Power_kW,
    Speed_rpm,
    FEEMSResult,
    NOxCalculationMethod,
    EmissionType,
)

# import os
from tests.utility import (
    ELECTRIC_MACHINE_EFF_CURVE,
    create_a_pti_pto,
    create_a_propulsion_drive,
    create_cogas_system,
    create_genset_component,
)

random.seed(10)


def get_pti_pto(
    no_pti_pto: int,
    rated_power: float,
    rated_speed: float,
    switchboard_no: List[int],
    shaft_line_id: List[int],
):
    pti_pto = []
    for i in range(no_pti_pto):
        # noinspection PyTypeChecker
        pti_pto.append(
            create_a_pti_pto(
                name="PTI/PTO %i" % (i + 1),
                switchboard_id=switchboard_no[i],
                rated_power=rated_power,
                rated_speed=rated_speed,
                shaft_line_id=shaft_line_id[i],
            )
        )
    return pti_pto


class TestElectricPowerSystem(TestCase):
    # noinspection DuplicatedCode
    def setUp(self) -> None:
        """
        Initialize with configuration for conventional, hybrid and diesel electric propulsion and
        power system variants.
        """
        self.power_balance_test_complete = False
        self.no_points_to_test = 1000

        # main engine and gearbox
        self.no_main_engines_for_conventional = 1
        self.no_main_engines_for_hybrid = 2
        self.no_main_engines_for_diesel_electric = 0
        bsfc_curve_for_main_engine = np.array(
            [[1, 0.75, 0.50, 0.25, 0.10], [193.66, 188.995, 194.47, 211.4, 250]]
        ).transpose()
        main_engine_object = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            name="main engine",
            rated_power=Power_kW(4000),
            rated_speed=Speed_rpm(750),
            bsfc_curve=bsfc_curve_for_main_engine,
            nox_calculation_method=NOxCalculationMethod.TIER_2,
        )
        self.main_engine_for_conventional = []
        for i in range(self.no_main_engines_for_conventional):
            self.main_engine_for_conventional.append(copy.deepcopy(main_engine_object))
            self.main_engine_for_conventional[i].name = "main engine {}".format(i + 1)
        self.main_engine_for_hybrid = []
        for i in range(self.no_main_engines_for_hybrid):
            self.main_engine_for_hybrid.append(
                MainEngineWithGearBoxForMechanicalPropulsion(
                    "main engine {}".format(i),
                    copy.deepcopy(main_engine_object),
                    BasicComponent(
                        type_=TypeComponent.GEARBOX,
                        power_type=TypePower.POWER_TRANSMISSION,
                        name="gearbox {}".format(i),
                        rated_power=Power_kW(4000),
                        rated_speed=Speed_rpm(4000),
                        eff_curve=np.array([1]),
                    ),
                )
            )
        self.main_engine_for_diesel_electric = []

        # auxiliary engines and generators
        bsfc_curve_for_aux_engine = np.array(
            [[1.00, 0.75, 0.50, 0.25, 0.10], [205, 195, 202, 210, 290]]
        ).transpose()
        efficiency_curve_for_generator_motor = np.array(
            [[1.00, 0.75, 0.50, 0.25], [0.96, 0.961, 0.96, 0.94]]
        ).transpose()
        no_of_genset_per_switchboard = 1
        no_of_genset_per_switchboard_diesel_electric = 2
        self.no_gensets_for_conventional = int(np.round(np.random.rand() * 3)) + 1
        self.no_gensets_for_hybrid = int(np.round(np.random.rand() * 3)) + 1
        self.no_gensets_for_diesel_electric = (int(np.round(np.random.rand() * 3)) + 2) * 2
        self.rated_power_aux_engine = Power_kW(2700)
        self.rated_power_generator = Power_kW(2500)
        self.rated_speed_genset = Speed_rpm(1500)
        self.gensets_for_conventional = TestElectricPowerSystem.get_gensets(
            self.no_gensets_for_conventional,
            self.rated_power_generator,
            self.rated_speed_genset,
            bsfc_curve_for_aux_engine,
            efficiency_curve_for_generator_motor,
            no_of_genset_per_switchboard,
        )
        self.no_switchboard_conventional = self.gensets_for_conventional[-1].switchboard_id
        self.gensets_for_hybrid = TestElectricPowerSystem.get_gensets(
            self.no_gensets_for_hybrid,
            self.rated_power_generator,
            self.rated_speed_genset,
            bsfc_curve_for_aux_engine,
            efficiency_curve_for_generator_motor,
            no_of_genset_per_switchboard,
        )
        self.no_switchboard_hybrid = self.gensets_for_hybrid[-1].switchboard_id
        self.gensets_for_diesel_electric = TestElectricPowerSystem.get_gensets(
            self.no_gensets_for_diesel_electric,
            self.rated_power_generator,
            self.rated_speed_genset,
            bsfc_curve_for_aux_engine,
            efficiency_curve_for_generator_motor,
            no_of_genset_per_switchboard_diesel_electric,
        )
        self.no_switchboard_diesel_electric = self.gensets_for_diesel_electric[-1].switchboard_id

        # PTI PTO
        self.no_pti_pto = 1
        self.rated_power_pti_pto = 2500
        self.rated_speed_pti_pto = 500
        self.switchboard_id_pti_pto = [
            int(np.ceil(np.random.rand() * self.no_switchboard_hybrid))
            for _ in range(self.no_pti_pto)
        ]
        self.pti_pto = get_pti_pto(
            no_pti_pto=self.no_pti_pto,
            rated_power=self.rated_power_pti_pto,
            rated_speed=self.rated_speed_pti_pto,
            switchboard_no=self.switchboard_id_pti_pto,
            shaft_line_id=[1],
        )

        # Energy Storage
        self.rated_power_energy_storage = 1000
        self.switchboard_id_energy_storage = 1
        energy_storage_for_hybrid = Battery(
            name="Battery System",
            rated_capacity_kwh=1000,
            charging_rate_c=1,
            discharge_rate_c=1,
            switchboard_id=self.switchboard_id_energy_storage,
        )
        energy_storage_for_diesel_electric = copy.deepcopy(energy_storage_for_hybrid)
        energy_storage_for_conventional = copy.deepcopy(energy_storage_for_hybrid)
        
        # Thruster
        self.no_thruster = 2
        self.no_thruster_diesel_electric = self.no_switchboard_diesel_electric
        self.rated_power_thruster = 1080
        self.rated_speed_thruster = 150
        self.switchboard_id_thrusters_for_hybrid = []
        for i in range(self.no_thruster):
            self.switchboard_id_thrusters_for_hybrid.append(
                int(np.ceil(self.no_switchboard_hybrid * np.random.rand()))
            )
        self.switchboard_id_thrusters_for_conventional = []
        for i in range(self.no_thruster):
            self.switchboard_id_thrusters_for_conventional.append(
                int(np.ceil(self.no_switchboard_conventional * np.random.rand()))
            )
        self.switchboard_id_thrusters_for_diesel_electric = np.arange(
            1, self.no_switchboard_diesel_electric + 1
        ).tolist()
        self.propulsion_drives_for_hybrid = TestElectricPowerSystem.get_propulsion_drives(
            self.no_thruster,
            self.rated_power_thruster,
            self.rated_speed_thruster,
            self.switchboard_id_thrusters_for_hybrid,
        )
        self.propulsion_drives_for_conventional = TestElectricPowerSystem.get_propulsion_drives(
            self.no_thruster,
            self.rated_power_thruster,
            self.rated_speed_thruster,
            self.switchboard_id_thrusters_for_conventional,
        )
        self.propulsion_drives_for_diesel_electric = TestElectricPowerSystem.get_propulsion_drives(
            self.no_thruster_diesel_electric,
            self.rated_power_thruster,
            self.rated_speed_thruster,
            self.switchboard_id_thrusters_for_diesel_electric,
        )

        # Other load
        self.rated_power_other_load = 1000
        self.switchboard_id_other_load = 1
        other_load_for_hybrid = ElectricComponent(
            type_=TypeComponent.OTHER_LOAD,
            name="other loads",
            power_type=TypePower.POWER_CONSUMER,
            rated_power=Power_kW(self.rated_power_other_load),
            rated_speed=Speed_rpm(0),
            eff_curve=np.array([1]),
            switchboard_id=self.switchboard_id_other_load,
        )
        other_load_for_diesel_electric = copy.deepcopy(other_load_for_hybrid)
        other_load_for_conventional = copy.deepcopy(other_load_for_diesel_electric)

        # Bus tie configuration
        self.bus_tie_connections_conventional = []
        for i in range(self.no_switchboard_conventional - 1):
            self.bus_tie_connections_conventional.append((i + 1, i + 2))
        self.bus_tie_connections_hybrid = []
        for i in range(self.no_switchboard_hybrid - 1):
            self.bus_tie_connections_hybrid.append((i + 1, i + 2))
        self.bus_tie_connections_diesel_electric = []
        for i in range(self.no_switchboard_diesel_electric - 1):
            self.bus_tie_connections_diesel_electric.append((i + 1, i + 2))

        # Configure the system
        # noinspection PyTypeChecker
        self.power_system_for_hybrid_propulsion_system = ElectricPowerSystem(
            name="hybrid propulsion system",
            power_plant_components=self.gensets_for_hybrid
            + self.propulsion_drives_for_hybrid
            + self.pti_pto
            + [other_load_for_hybrid]
            + [energy_storage_for_hybrid],
            bus_tie_connections=self.bus_tie_connections_hybrid,
        )
        self.power_system_for_hybrid_propulsion_system.set_time_interval(
            time_interval_s=1, integration_method=IntegrationMethod.simpson
        )

        # noinspection PyTypeChecker
        self.power_system_for_diesel_electric_system = ElectricPowerSystem(
            name="diesel electric propulsion system",
            power_plant_components=self.gensets_for_diesel_electric
            + self.propulsion_drives_for_diesel_electric
            + [other_load_for_diesel_electric]
            + [energy_storage_for_diesel_electric],
            bus_tie_connections=self.bus_tie_connections_diesel_electric,
        )
        self.power_system_for_diesel_electric_system.set_time_interval(
            time_interval_s=1, integration_method=IntegrationMethod.simpson
        )

        # noinspection PyTypeChecker
        self.power_system_for_conventional_system = ElectricPowerSystem(
            name="mechanical drive propulsion and power system",
            power_plant_components=self.gensets_for_conventional
            + self.propulsion_drives_for_conventional
            + [other_load_for_conventional]
            + [energy_storage_for_conventional],
            bus_tie_connections=self.bus_tie_connections_conventional,
        )
        self.power_system_for_conventional_system.set_time_interval(
            time_interval_s=1, integration_method=IntegrationMethod.simpson
        )

    def test_system_with_components_of_invalid_power_type(self):
        other_load = ElectricComponent(
            type_=TypeComponent.OTHER_LOAD,
            rated_power=1000,
            rated_speed=1000,
            switchboard_id=1,
        )

        def set_system():
            return ElectricPowerSystem(
                name="System with errors",
                power_plant_components=[*self.gensets_for_diesel_electric, other_load],
                bus_tie_connections=[(1, 2)],
            )

        self.assertRaises(TypeError, set_system)

    @staticmethod
    def get_gensets(
        no_gensets: int,
        rated_power_gen: Power_kW,
        rated_speed: Speed_rpm,
        bsfc_curve,
        efficiency_curve,
        no_gensets_per_switchboard,
    ):
        gensets = []
        for i in range(no_gensets):
            gensets.append(
                create_genset_component(
                    name="genset %s" % i,
                    rated_power=rated_power_gen,
                    rated_speed=rated_speed,
                    switchboard_id=int(np.ceil((i + 1) / no_gensets_per_switchboard)),
                    bsfc_curve=bsfc_curve,
                    eff_curve_gen=efficiency_curve,
                )
            )
        return gensets

    @staticmethod
    def get_propulsion_drives(
        no_thrusters: int,
        rated_power: float,
        rated_speed: float,
        switchboard_no: List[int],
    ):
        propulsion_drives = []
        for i in range(no_thrusters):
            propulsion_drives.append(
                create_a_propulsion_drive(
                    name="propulsion drive for thruster %s" % (i + 1),
                    rated_power=rated_power,
                    rated_speed=rated_speed,
                    switchboard_id=switchboard_no[i],
                )
            )
        return propulsion_drives

    @staticmethod
    def get_components_numbers_electric_system(
        system: ElectricPowerSystem,
    ) -> (int, int, int, int, int):
        no_power_sources = system.no_power_sources
        no_propulsion_drive = system.no_propulsion_units
        no_other_load = system.no_other_load
        no_pti_pto = system.no_pti_pto
        no_energy_storage = system.no_energy_storage
        return (
            no_power_sources,
            no_propulsion_drive,
            no_other_load,
            no_pti_pto,
            no_energy_storage,
        )

    # noinspection DuplicatedCode
    def test_configuration(self):
        # Test for the conventional system
        # # : Check if all the components are included
        (
            no_power_sources,
            no_propulsion_drive,
            no_other_load,
            no_pti_pto,
            no_energy_storage,
        ) = TestElectricPowerSystem.get_components_numbers_electric_system(
            self.power_system_for_conventional_system
        )
        self.assertEqual(no_power_sources, self.no_gensets_for_conventional)
        self.assertEqual(
            [genset.switchboard_id for genset in self.gensets_for_conventional],
            self.power_system_for_conventional_system.switchboard_id,
        )
        self.assertEqual(no_propulsion_drive, self.no_thruster)
        self.assertEqual(no_other_load, 1)
        self.assertEqual(no_pti_pto, 0)
        self.assertEqual(no_energy_storage, 1)
        for genset in self.gensets_for_conventional:
            self.assertTrue(
                genset
                in self.power_system_for_conventional_system.switchboards[
                    genset.switchboard_id
                ].component_by_power_type[TypePower.POWER_SOURCE.value]
            )
        for propulsion_drive in self.propulsion_drives_for_conventional:
            self.assertTrue(
                propulsion_drive
                in self.power_system_for_conventional_system.switchboards[
                    propulsion_drive.switchboard_id
                ].component_by_power_type[TypePower.POWER_CONSUMER.value]
            )
        # # Check for the bus breaker
        for i, bus_tie_breaker in enumerate(
            self.power_system_for_conventional_system.bus_tie_breakers
        ):
            for switchboard_id in bus_tie_breaker.switchboard_ids:
                self.assertTrue(switchboard_id in self.bus_tie_connections_conventional[i])

        # Test for the hybrid system
        # # Check if the components are all included in the system
        (
            no_power_sources,
            no_propulsion_drive,
            no_other_load,
            no_pti_pto,
            no_energy_storage,
        ) = TestElectricPowerSystem.get_components_numbers_electric_system(
            self.power_system_for_hybrid_propulsion_system
        )
        self.assertEqual(no_power_sources, self.no_gensets_for_hybrid)
        self.assertEqual(no_propulsion_drive, self.no_thruster)
        self.assertEqual(no_other_load, 1)
        self.assertEqual(no_pti_pto, self.no_pti_pto)
        self.assertEqual(no_energy_storage, 1)
        for pti_pto in self.pti_pto:
            self.assertTrue(
                pti_pto
                in self.power_system_for_hybrid_propulsion_system.switchboards[
                    pti_pto.switchboard_id
                ].component_by_power_type[TypePower.PTI_PTO.value]
            )
        for genset in self.gensets_for_hybrid:
            self.assertTrue(
                genset
                in self.power_system_for_hybrid_propulsion_system.switchboards[
                    genset.switchboard_id
                ].component_by_power_type[TypePower.POWER_SOURCE.value]
            )
        for propulsion_drive in self.propulsion_drives_for_hybrid:
            self.assertTrue(
                propulsion_drive
                in self.power_system_for_hybrid_propulsion_system.switchboards[
                    propulsion_drive.switchboard_id
                ].component_by_power_type[TypePower.POWER_CONSUMER.value]
            )
        # # Test for the bus configuration
        for i, bus_tie_breaker in enumerate(
            self.power_system_for_hybrid_propulsion_system.bus_tie_breakers
        ):
            for switchboard_id in bus_tie_breaker.switchboard_ids:
                self.assertTrue(switchboard_id in self.bus_tie_connections_hybrid[i])

        # Test for the diesel electric system
        # # Check if all the components are included in the system
        (
            no_power_sources,
            no_propulsion_drive,
            no_other_load,
            no_pti_pto,
            no_energy_storage,
        ) = TestElectricPowerSystem.get_components_numbers_electric_system(
            self.power_system_for_diesel_electric_system
        )
        self.assertEqual(no_power_sources, self.no_gensets_for_diesel_electric)
        self.assertEqual(no_propulsion_drive, self.no_thruster_diesel_electric)
        self.assertEqual(no_other_load, 1)
        self.assertEqual(no_pti_pto, 0)
        self.assertEqual(no_energy_storage, 1)
        for genset in self.gensets_for_diesel_electric:
            self.assertTrue(
                genset
                in self.power_system_for_diesel_electric_system.switchboards[
                    genset.switchboard_id
                ].component_by_power_type[TypePower.POWER_SOURCE.value]
            )
        for propulsion_drive in self.propulsion_drives_for_diesel_electric:
            self.assertTrue(
                propulsion_drive
                in self.power_system_for_diesel_electric_system.switchboards[
                    propulsion_drive.switchboard_id
                ].component_by_power_type[TypePower.POWER_CONSUMER.value]
            )
        # # Check the bus tie configuration
        for i, bus_tie_breaker in enumerate(
            self.power_system_for_diesel_electric_system.bus_tie_breakers
        ):
            for switchboard_id in bus_tie_breaker.switchboard_ids:
                self.assertTrue(switchboard_id in self.bus_tie_connections_diesel_electric[i])

    def test_power_balance_calculation(self):
        if self.power_balance_test_complete:
            return 0
        else:
            self.power_balance_test_complete = True

        # Generate a random number of the number different bus-tie configuration for the test
        no_different_bus_tie_configuration = int(
            np.random.rand() * 0.5 * self.no_points_to_test + 2
        )

        # First generate the array of bus tie configuration with all bus tie closed (True)
        bus_tie_configuration = np.ones(
            [
                self.no_points_to_test,
                self.power_system_for_diesel_electric_system.no_bus_tie_breakers,
            ]
        ).astype(bool)

        # Prepare an array that will only contain the bus tie configuration for at the point
        # when it has changed
        bus_tie_configuration_at_change = np.ones(
            [
                no_different_bus_tie_configuration,
                self.power_system_for_diesel_electric_system.no_bus_tie_breakers,
            ]
        ).astype(bool)

        switch2bus_configuration = []
        no_buses = []
        index_bus_config_change = []
        for i in range(no_different_bus_tie_configuration):
            switch2bus_configuration.append([])
            while True:
                switch2bus_configuration[i] = [1]
                for j in range(self.power_system_for_diesel_electric_system.no_switchboard - 1):
                    bus_tie_configuration_at_change[i, j] = bool(random.getrandbits(1))
                    switch2bus_configuration[i].append(
                        int(not (bus_tie_configuration_at_change[i, j]))
                        + switch2bus_configuration[i][j]
                    )
                if i == 0:
                    break
                elif switch2bus_configuration[i - 1] != switch2bus_configuration[i]:
                    break
            no_buses.append(switch2bus_configuration[i][-1])
            while True:
                if i == 0:
                    index_bus_config_change.append(0)
                    break
                else:
                    index_next = int(
                        np.random.rand()
                        * 1
                        / no_different_bus_tie_configuration
                        * self.no_points_to_test
                        + (i - 1) * self.no_points_to_test / no_different_bus_tie_configuration
                    )
                    if index_next != index_bus_config_change[i - 1]:
                        index_bus_config_change.append(index_next)
                        break
            if i > 0:
                bus_tie_configuration[
                    index_bus_config_change[i - 1] : index_bus_config_change[i], :
                ] = bus_tie_configuration_at_change[i - 1, :]
        # noinspection PyUnboundLocalVariable
        bus_tie_configuration[index_bus_config_change[i] :] = bus_tie_configuration_at_change[i]
        self.power_system_for_diesel_electric_system.set_bus_tie_status_all(bus_tie_configuration)
        self.assertEqual(
            self.power_system_for_diesel_electric_system.bus_configuration_change_index,
            index_bus_config_change,
        )
        for actual_s2b, expected_s2b in zip(
            self.power_system_for_diesel_electric_system.switchboard2bus,
            switch2bus_configuration,
        ):
            for i, expected_bus in enumerate(expected_s2b):
                # Actual uses 1 based index, while expected uses 0 based
                self.assertEqual(
                    actual_s2b[i + 1],
                    expected_bus,
                    "Bus (%s) not as expected (%s)" % (actual_s2b, expected_s2b),
                )

        # In this section of test, we will generate a random percentage load of a bus.
        # Then we will also generate power inputs for power consumer components so that
        # the total power inputs will result in the bus load percentage generated.
        # Set the power for the power consumers from the random percentage of load for each bus
        sum_power_output_rated_bus = self.power_system_for_diesel_electric_system.get_sum_power_out_rated_buses_by_power_type(
            TypePower.POWER_CONSUMER
        )
        load_perc_power_output_bus = np.random.rand(
            self.no_points_to_test,
            self.power_system_for_diesel_electric_system.no_switchboard,
        )
        sum_power_output_buses = {}
        for swb in range(self.power_system_for_diesel_electric_system.no_switchboard):
            sum_power_output_buses[swb + 1] = np.zeros(self.no_points_to_test)

        for i, switchboard2bus in enumerate(
            self.power_system_for_diesel_electric_system.switchboard2bus
        ):
            index_start = (
                self.power_system_for_diesel_electric_system.bus_configuration_change_index[i]
            )
            if i + 1 < self.power_system_for_diesel_electric_system.no_bus_configuration_change:
                index_end = (
                    self.power_system_for_diesel_electric_system.bus_configuration_change_index[
                        i + 1
                    ]
                )
            else:
                index_end = self.no_points_to_test
            for _, bus_id in switchboard2bus.items():
                sum_power_output_buses[bus_id][index_start:index_end] = (
                    sum_power_output_rated_bus[bus_id][i]
                    * load_perc_power_output_bus[index_start:index_end, bus_id - 1]
                )
        sum_power_input = 0
        sum_power_input_switchboard = 0
        for (
            _,
            switchboard,
        ) in self.power_system_for_diesel_electric_system.switchboards.items():
            for component in switchboard.component_by_power_type[TypePower.POWER_CONSUMER.value]:
                first_loading = True
                for i, switchboard2bus in enumerate(
                    self.power_system_for_diesel_electric_system.switchboard2bus
                ):
                    bus_id = switchboard2bus[switchboard.id]
                    index_start = self.power_system_for_diesel_electric_system.bus_configuration_change_index[
                        i
                    ]
                    index_end = (
                        self.power_system_for_diesel_electric_system.bus_configuration_change_index[
                            i + 1
                        ]
                        if i + 1
                        < self.power_system_for_diesel_electric_system.no_bus_configuration_change
                        else self.no_points_to_test
                    )

                    if first_loading:
                        self.power_system_for_diesel_electric_system.set_power_input_from_power_output_by_switchboard_id_type_name(
                            power_output=np.zeros(self.no_points_to_test),
                            switchboard_id=switchboard.id,
                            type_=TypePower.POWER_CONSUMER,
                            name=component.name,
                        )
                    power_output = component.power_output
                    load_perc_power_output = load_perc_power_output_bus[
                        index_start:index_end, bus_id - 1
                    ]
                    power_output[index_start:index_end] += (
                        component.rated_power * load_perc_power_output
                    )
                    self.power_system_for_diesel_electric_system.set_power_input_from_power_output_by_switchboard_id_type_name(
                        power_output=power_output,
                        switchboard_id=switchboard.id,
                        type_=TypePower.POWER_CONSUMER,
                        name=component.name,
                    )
                    first_loading = False
                sum_power_input += component.power_input
            sum_power_input_switchboard += switchboard.get_sum_power_input_by_power_type(
                TypePower.POWER_CONSUMER
            )

        # Test the energy conservation and methods for summing the power input/output for buses
        sum_power_input_buses_comp_tmp = (
            self.power_system_for_diesel_electric_system.get_sum_power_in_buses_by_power_type(
                TypePower.POWER_CONSUMER
            )
        )
        sum_power_input_buses_comp = self.sum_bus(sum_power_input_buses_comp_tmp)

        sum_power_output_buses_comp = (
            self.power_system_for_diesel_electric_system.get_sum_power_output_buses_by_power_type(
                TypePower.POWER_CONSUMER
            )
        )
        self.assertAlmostEqual(np.abs(sum_power_input - sum_power_input_switchboard).sum(), 0)
        self.assertAlmostEqual(
            np.abs(sum_power_input_switchboard - sum_power_input_buses_comp).sum(), 0
        )
        for bus in sum_power_output_buses:
            # noinspection PyTypeChecker
            np.array_equal(sum_power_output_buses[bus], sum_power_output_buses_comp[bus])
            # noinspection PyTypeChecker
            self.assertAlmostEqual(
                np.abs(sum_power_output_buses[bus] - sum_power_output_buses_comp[bus]).sum(),
                0,
            )

        # Set the load sharing mode and status for the power sources and energy storage devices
        for (
            _,
            switchboard,
        ) in self.power_system_for_diesel_electric_system.switchboards.items():
            status_power_source = np.round(
                np.random.rand(self.no_points_to_test, switchboard.no_power_sources)
            ).astype(bool)
            index_all_off = np.bitwise_not(status_power_source.all(axis=1))
            status_power_source[index_all_off, 0] = True
            load_sharing_mode_power_source = np.zeros(
                [self.no_points_to_test, switchboard.no_power_sources]
            )
            switchboard.set_load_sharing_mode_components_by_power_type(
                TypePower.POWER_SOURCE, load_sharing_mode_power_source
            )

            switchboard.set_status_components_by_power_type(
                TypePower.POWER_SOURCE, status_power_source
            )
            load_sharing_mode_energy_storage = np.ones(
                (self.no_points_to_test, switchboard.no_energy_storage)
            )
            status_energy_storage = np.round(
                np.random.rand(self.no_points_to_test, switchboard.no_energy_storage)
            ).astype(bool)
            switchboard.set_status_components_by_power_type(
                TypePower.ENERGY_STORAGE, status_energy_storage
            )
            switchboard.set_load_sharing_mode_components_by_power_type(
                TypePower.ENERGY_STORAGE, load_sharing_mode_energy_storage
            )

            for energy_storage_component in switchboard.component_by_power_type[
                TypePower.ENERGY_STORAGE.value
            ]:
                energy_storage_component.power_input = (
                    np.random.randn(self.no_points_to_test)
                    * energy_storage_component.rated_power
                    * energy_storage_component.status
                    * 0.1
                )

        # Sum all the power input for the buses
        sum_power_input_buses_comp = (
            self.power_system_for_diesel_electric_system.get_sum_power_in_buses_by_power_type(
                TypePower.POWER_CONSUMER
            )
        )

        sum_power_input_buses_comp = self.add_bus(
            sum_power_input_buses_comp,
            self.power_system_for_diesel_electric_system.get_sum_power_in_buses_by_power_type(
                TypePower.PTI_PTO
            ),
        )

        sum_power_input_buses_comp = self.add_bus(
            sum_power_input_buses_comp,
            self.power_system_for_diesel_electric_system.get_sum_power_in_buses_by_power_type(
                TypePower.ENERGY_STORAGE
            ),
        )

        # Do the power balancing calculation (assigning the equal load for the gensets
        # and energy storage devices
        # at symmetric load sharing mode
        self.power_system_for_diesel_electric_system.do_power_balance_calculation()
        sum_power_output_power_sources_buses = {}
        for bus_id in sum_power_input_buses_comp:
            sum_power_output_power_sources_buses[bus_id] = np.zeros(
                sum_power_input_buses_comp[bus_id].shape
            )

        sum_power_output_power_sources_switchboards = {}
        for (
            _,
            switchboard,
        ) in self.power_system_for_diesel_electric_system.switchboards.items():
            sum_power_output_power_sources_switchboards[switchboard.id] = (
                switchboard.get_sum_power_output_by_power_type(TypePower.POWER_SOURCE)
            )

        for i, switchboard2bus in enumerate(
            self.power_system_for_diesel_electric_system.switchboard2bus
        ):
            index_start = (
                self.power_system_for_diesel_electric_system.bus_configuration_change_index[i]
            )
            if i + 1 < self.power_system_for_diesel_electric_system.no_bus_configuration_change:
                index_end = (
                    self.power_system_for_diesel_electric_system.bus_configuration_change_index[
                        i + 1
                    ]
                )
            else:
                index_end = self.no_points_to_test
            for swb_id, bus_id in switchboard2bus.items():
                sum_power_output_power_sources_buses[bus_id][
                    index_start:index_end
                ] += sum_power_output_power_sources_switchboards[swb_id][index_start:index_end]
        for bus_id in sum_power_output_power_sources_buses:
            self.assertAlmostEqual(
                np.abs(
                    sum_power_input_buses_comp[bus_id]
                    - sum_power_output_power_sources_buses[bus_id]
                ).sum(),
                0,
            )

    @staticmethod
    def sum_bus(bus_dict: Dict[BusId, np.ndarray]) -> np.ndarray:
        sum_vec = None
        for _, bus_power in bus_dict.items():
            if sum_vec is None:
                sum_vec = bus_power
            else:
                sum_vec += bus_power
        return sum_vec

    @staticmethod
    def add_bus(
        bus_dict: Dict[BusId, np.ndarray], bus_dict2: Dict[BusId, np.ndarray]
    ) -> Dict[BusId, np.ndarray]:
        assert len(bus_dict) == len(bus_dict2)
        for bus_id in bus_dict:
            bus_dict[bus_id] += bus_dict2[bus_id]
        return bus_dict

    def test_fuel_consumption_calculation(self):
        if not self.power_balance_test_complete:
            self.test_power_balance_calculation()
        result: FEEMSResult = (
            self.power_system_for_diesel_electric_system.get_fuel_energy_consumption_running_time()
        )
        print("Fuel consumption (kg): %s" % result.fuel_consumption_total_kg)
        print(
            "Mechanical energy consumption (kJ): %s"
            % result.energy_consumption_mechanical_total_mj
        )
        print("Electric energy consumption (kJ): %s" % result.energy_consumption_electric_total_mj)
        print("Running time (s):")
        print("\t" + "Gensets: %s" % result.running_hours_genset_total_hr)
        print("\t" + "Fuel cell: %s" % result.running_hours_fuel_cell_total_hr)
        print("\t" + "PTI PTO: %s" % result.running_hours_pti_pto_total_hr)
        print("CO2 emissions [kg]: %s" % result.co2_emission_total_kg)
        print("NOx emissions [kg]: %s" % result.total_emission_kg[EmissionType.NOX])

    def test_battery_only_configuration(self):
        number_points = 100
        rated_power_thruster = 1000 * random.random()
        rated_power_battery = rated_power_thruster * 1.5
        discharging_rate_battery = 3
        propulsion_drive = create_a_propulsion_drive(
            name="propulsion drive for thruster 1",
            rated_power=rated_power_thruster,
            rated_speed=750,
            switchboard_id=1,
        )
        battery = Battery(
            name="Battery",
            rated_capacity_kwh=rated_power_battery / discharging_rate_battery,
            charging_rate_c=discharging_rate_battery,
            discharge_rate_c=discharging_rate_battery,
            switchboard_id=1,
        )
        # noinspection PyTypeChecker
        converter = ElectricComponent(
            name="Converter for battery",
            rated_power=rated_power_battery,
            power_type=TypePower.POWER_TRANSMISSION,
            type_=TypeComponent.POWER_CONVERTER,
            switchboard_id=1,
        )
        battery_system = BatterySystem(
            name="Battery system",
            battery=battery,
            converter=converter,
            switchboard_id=battery.switchboard_id,
        )
        electric_system = ElectricPowerSystem(
            name="Battery only",
            power_plant_components=[propulsion_drive, battery_system],
            bus_tie_connections=[],
        )
        power_output_thruster = np.random.random(number_points) * rated_power_thruster
        electric_system.set_power_input_from_power_output_by_switchboard_id_type_name(
            power_output=power_output_thruster,
            switchboard_id=1,
            type_=TypePower.POWER_CONSUMER,
            name=propulsion_drive.name,
        )
        battery_status = np.ones([number_points, 1])
        electric_system.set_status_by_switchboard_id_power_type(
            switchboard_id=1, power_type=TypePower.ENERGY_STORAGE, status=battery_status
        )
        battery_load_sharing_mode = np.zeros([number_points, 1])
        electric_system.set_load_sharing_mode_power_sources_by_switchboard_id_power_type(
            switchboard_id=1,
            power_type=TypePower.ENERGY_STORAGE,
            load_sharing_mode=battery_load_sharing_mode,
        )

        electric_system.set_bus_tie_status_all(np.array([]))
        electric_system.set_time_interval(
            time_interval_s=1.0, integration_method=IntegrationMethod.trapezoid
        )

        electric_system.do_power_balance_calculation()
        self.assertAlmostEqual(
            np.power(battery_system.power_input + propulsion_drive.power_input, 2).sum(),
            0,
            5,
        )

        with self.subTest("Check aggregated values"):
            result = electric_system.get_fuel_energy_consumption_running_time()
            self.assertLess(result.energy_stored_total_mj, 0)


class TestCOGESSystem(TestCase):
    def setUp(self) -> None:
        # Create COGES systems
        self.coges: List[COGES] = []
        self.propulsion_drive: List[SerialSystemElectric] = []
        self.other_load = ElectricComponent(
            type_=TypeComponent.OTHER_LOAD,
            name="other loads",
            power_type=TypePower.POWER_CONSUMER,
            rated_power=Power_kW(1000),
            eff_curve=np.array([1]),
            switchboard_id=1,
        )
        for i in range(1, 3):
            cogas = create_cogas_system()
            generator = ElectricMachine(
                type_=TypeComponent.GENERATOR,
                name=f"generator {i}",
                rated_power=cogas.rated_power * 0.9,
                rated_speed=cogas.rated_speed,
                power_type=TypePower.POWER_SOURCE,
                switchboard_id=SwbId(i),
                number_poles=4,
                eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
            )
            self.coges.append(COGES(
                name=f"COGES {i}",
                cogas=cogas,
                generator=generator,
            ))
            # Create a propulsion drive
            self.propulsion_drive.append(create_a_propulsion_drive(
                name=f"propulsion drive {i}",
                rated_power=600,
                rated_speed=750,
                switchboard_id=i,
            ))
        self.system = ElectricPowerSystem(
            name="COGES system",
            power_plant_components=[
                *self.coges, *self.propulsion_drive, self.other_load
            ],
            bus_tie_connections=[(1, 2)],
        )
    
    def test_configuration(self):
        # Test the configuration
        self.assertEqual(self.system.no_power_sources, len(self.coges))
        self.assertEqual(self.system.no_propulsion_units, len(self.propulsion_drive))
        self.assertEqual(self.system.no_other_load, 1)
        self.assertEqual(self.system.no_energy_storage, 0)
        self.assertEqual(self.system.no_pti_pto, 0)
        self.assertEqual(self.system.no_bus_tie_breakers, 1)
        self.assertEqual(self.system.no_bus_configuration_change, 1)
        self.assertEqual(self.system.no_switchboard, 2)
        self.assertEqual(self.system.no_bus, [1])
        
    def test_get_fuel_consumption(self):
        propulsion_loads = [propulsion_drive.rated_power * np.random.random(1) for propulsion_drive in self.propulsion_drive]
        other_loads = np.array([400 * np.random.random()])
        
        # Set the power input for the propulsion drives and other loads
        for propulsion_drive, load in zip(self.propulsion_drive, propulsion_loads):
            propulsion_drive.set_power_input_from_output(load)
        self.other_load.set_power_input_from_output(other_loads)
        
        # Set the bus tie status
        self.system.bus_tie_breakers[0].status = np.ones(1).astype(bool)
        
        # Set the status and load sharing mode for the power sources
        for coges in self.coges:
            coges.status = np.ones(1).astype(bool)
            coges.load_sharing_mode = np.zeros(1)
            
        # Set time interval
        self.system.set_time_interval(time_interval_s=3600, integration_method=IntegrationMethod.sum_with_time)        
        
        # Do power balance
        self.system.do_power_balance_calculation()
        
        # Calculate the fuel consumption manually
        cogas_fuel_consumption = 0
        for coges in self.coges:
            cogas_power_output, _ = coges.generator.get_power_input_from_bidirectional_output(coges.power_output)
            cogas_efficiency = coges.cogas.get_efficiency_from_load_percentage(
                cogas_power_output / coges.cogas.rated_power
            )
            lhv_fuel_mj_per_g = Fuel(
                fuel_type=coges.cogas.fuel_type,
                origin=coges.cogas.fuel_origin,
            ).lhv_mj_per_g
            cogas_fuel_consumption_rate = cogas_power_output / cogas_efficiency / (lhv_fuel_mj_per_g * 1000) / 1000
            cogas_fuel_consumption += cogas_fuel_consumption_rate * 3600
        
        # Get the fuel consumption
        result = self.system.get_fuel_energy_consumption_running_time()
        fuel_consumption_result = result.fuel_consumption_total_kg
        # Compare the results
        self.assertAlmostEqual(cogas_fuel_consumption[0], fuel_consumption_result, 5)
        

class TestMechanicalPropulsionSystemSetup(TestCase):
    def setUp(self) -> None:
        """Set up the test case with default system configuration"""
        # Randomly generate the number of shaft lines between 1 and 5
        self.number_shaft_lines = np.random.randint(1, 5)

        # First create a component that represents each type
        # Main engine
        bsfc_curve_for_main_engine = np.array(
            [[1.00, 0.75, 0.50, 0.25, 0.10], [193.66, 188.995, 194.47, 211.4, 250]]
        ).transpose()
        main_engine = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            name="Main engine",
            rated_power=Power_kW(4000),
            rated_speed=Speed_rpm(750),
            bsfc_curve=bsfc_curve_for_main_engine,
            nox_calculation_method=NOxCalculationMethod.TIER_2,
        )

        # Gear box
        gearbox = BasicComponent(
            type_=TypeComponent.GEARBOX,
            name="gearbox",
            power_type=TypePower.POWER_TRANSMISSION,
            rated_power=main_engine.rated_power,
            rated_speed=main_engine.rated_speed,
            eff_curve=np.array([98]),
        )

        # Main engine with a gear box
        main_engine_ref = MainEngineWithGearBoxForMechanicalPropulsion(
            "main engine", main_engine, gearbox
        )

        # PTI/PTO
        pti_pto_ref = create_a_pti_pto(rated_power=3000)

        # Propeller_load
        propeller_load_ref = MechanicalPropulsionComponent(
            type_=TypeComponent.PROPELLER_LOAD,
            power_type=TypePower.POWER_CONSUMER,
            name="Propeller load",
            rated_power=Power_kW(6000),
            rated_speed=Speed_rpm(150),
            eff_curve=np.array([1.00]),
        )

        # Add components to the list
        self.main_engine_component = []
        self.pti_pto = []
        self.propeller_load = []
        for i in range(self.number_shaft_lines):

            shaft_line_id = i + 1

            # Generate random number of main engines for each shaft lines (1 ~ 2)
            number_main_engines = np.random.randint(1, 3)
            for j in range(number_main_engines):
                # Copy the reference component, make the name unique and assign the shaft line id
                main_engine = copy.deepcopy(main_engine_ref)
                main_engine.name = "main engine %i" % (j + 1)
                main_engine.shaft_line_id = shaft_line_id

                # Add the main engine component to the list
                self.main_engine_component.append(main_engine)

            # Add a pti pto
            pti_pto = copy.deepcopy(pti_pto_ref)
            pti_pto.shaft_line_id = shaft_line_id
            pti_pto.name = "PTI/PTO %i" % shaft_line_id
            self.pti_pto.append(pti_pto)

            # Add a propeller load
            propeller_load = copy.deepcopy(propeller_load_ref)
            propeller_load.shaft_line_id = shaft_line_id
            propeller_load.name = "propeller load %i" % shaft_line_id
            self.propeller_load.append(propeller_load)

        # noinspection PyTypeChecker
        self.components = self.main_engine_component + self.pti_pto + self.propeller_load
        # Create a system model
        self.system = MechanicalPropulsionSystem(
            name="Mechanical Propulsion", components_list=self.components
        )


class TestMechanicalPropulsionSystem(TestMechanicalPropulsionSystemSetup):
    def test_configuration(self):
        # Check if all the components are included in the right shaft line
        shaftline_list = []
        for component in self.components:
            shaftline_list.append(component.shaft_line_id)
            self.assertTrue(
                component in self.system.component_by_shaft_line_id[shaftline_list[-1]]
            )
            self.assertTrue(component in self.system.shaft_line[shaftline_list[-1] - 1].components)

        # make shaft line list unique
        number_shaft_line_given = len(list(dict.fromkeys(shaftline_list)))
        self.assertEqual(self.system.no_shaft_lines, number_shaft_line_given)
        self.assertEqual(len(self.system.shaft_line), number_shaft_line_given)

        # make sure the numbers of components in the system are correct
        self.assertEqual(self.system.no_main_engines, len(self.main_engine_component))
        self.assertEqual(self.system.no_pti_ptos, len(self.pti_pto))
        self.assertEqual(self.system.no_mechanical_loads, len(self.propeller_load))

    def test_get_component_by_name_shaft_line_id_power_type(self):
        for component in self.components:
            self.assertEqual(
                component,
                self.system.get_component_by_name_shaft_line_id_power_type(
                    component.name, component.shaft_line_id, component.power_type
                ),
            )

    def test_set_full_pti_mode_for_name_shaft_line_id(self):
        for pti_pto in self.pti_pto:
            number_points = np.random.randint(10, 10000)
            full_pti_pto_mode = np.random.random(number_points) > 0.7
            self.assertEqual(
                self.system.set_full_pti_mode_for_name_shaft_line_id(
                    pti_pto.name, pti_pto.shaft_line_id, full_pti_pto_mode
                ),
                1,
            )
            self.assertTrue(np.equal(pti_pto.full_pti_mode, full_pti_pto_mode).all())

    def test_set_power_input_output_pti_pto(self):
        for pti_pto in self.pti_pto:
            number_points = np.random.randint(10, 10000)
            power_output = (2 * np.random.random(number_points) - 1) * pti_pto.rated_power
            power_input, load = pti_pto.get_power_input_from_bidirectional_output(power_output)
            self.assertEqual(
                self.system.set_power_input_pti_pto_by_power_output_value_for_name_shaft_line_id(
                    pti_pto.name, pti_pto.shaft_line_id, power_output
                ),
                1,
            )
            self.assertTrue(np.equal(power_output, pti_pto.power_output).all())
            self.assertTrue(np.equal(power_input, pti_pto.power_input).all())
            self.assertEqual(
                self.system.set_power_input_pti_pto_by_value_for_name_shaft_line_id(
                    pti_pto.name, pti_pto.shaft_line_id, power_input
                ),
                1,
            )
            power_output, load = pti_pto.get_power_output_from_bidirectional_input(power_input)
            self.assertTrue(np.equal(power_input, pti_pto.power_input).all())
            self.assertTrue(np.equal(power_output, pti_pto.power_output).all())

    def test_set_power_consumer_load(self):
        for component in self.propeller_load:
            number_points = np.random.randint(10, 10000)
            power_output = (2 * np.random.random(number_points) - 1) * component.rated_power
            power_input, load = component.get_power_input_from_bidirectional_output(power_output)
            self.assertEqual(
                self.system.set_power_consumer_load_by_power_output_for_given_name_shaft_line_id(
                    component.name, component.shaft_line_id, power_output
                ),
                1,
            )
            self.assertTrue(np.equal(power_output, component.power_output).all())
            self.assertTrue(np.equal(power_input, component.power_input).all())
            self.assertEqual(
                self.system.set_power_consumer_load_by_value_for_given_name_shaft_line_id(
                    component.name, component.shaft_line_id, power_input
                ),
                1,
            )
            self.assertTrue(np.equal(power_input, component.power_input).all())
            self.assertTrue(
                np.equal(np.round(power_output, 3), np.round(component.power_output, 3)).all()
            )

    def test_set_status_main_engine_for_name_shaft_line_id(self):
        for main_engine in self.main_engine_component:
            number_points = np.random.randint(10, 10000)
            status = np.random.random(number_points) > 0.5
            self.assertEqual(
                self.system.set_status_main_engine_for_name_shaft_line_id(
                    main_engine.name, main_engine.shaft_line_id, status
                ),
                1,
            )
            self.assertTrue(np.equal(status, main_engine.status).all())

    def test_power_balance_and_fuel_calculation(self):
        pass
