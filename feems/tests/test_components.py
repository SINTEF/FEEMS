import os
import random
from typing import cast
from unittest import TestCase

import numpy as np
import pandas as pd
from feems.components_model.component_base import BasicComponent, SerialSystem
from feems.components_model.component_electric import (
    COGES,
    PTIPTO,
    ElectricComponent,
    ElectricMachine,
    FuelCell,
    FuelCellSystem,
    Genset,
    SerialSystemElectric,
)
from feems.components_model.component_mechanical import (
    Engine,
    EngineDualFuel,
    EngineMultiFuel,
    FuelCharacteristics,
    MainEngineForMechanicalPropulsion,
    MainEngineWithGearBoxForMechanicalPropulsion,
)
from feems.components_model.node import Node, get_fuel_emission_energy_balance_for_component
from feems.components_model.utility import (
    IntegrationMethod,
    get_efficiency_curve_from_dataframe,
    get_efficiency_curve_from_points,
)
from feems.constant import nox_factor_imo_medium_speed_g_hWh
from feems.fuel import (
    Fuel,
    FuelConsumerClassFuelEUMaritime,
    FuelOrigin,
    FuelSpecifiedBy,
    GhgEmissionFactorTankToWake,
    TypeFuel,
)
from feems.types_for_feems import (
    EmissionType,
    NOxCalculationMethod,
    Power_kW,
    Speed_rpm,
    SwbId,
    TypeComponent,
    TypeNode,
    TypePower,
)
from scipy.interpolate import PchipInterpolator

from tests.utility import (
    ELECTRIC_MACHINE_EFF_CURVE,
    create_basic_components,
    create_cogas_system,
    create_components,
    create_dataframe_save_and_return,
    create_electric_components_for_switchboard,
    create_engine_component,
    create_multi_fuel_characteristics_sample,
    create_random_monotonic_eff_curve,
)

CONVERTER_EFF = np.array([[1.00, 0.75, 0.50, 0.25], [0.98, 0.972, 0.97, 0.96]]).transpose()


class TestComponent(TestCase):
    def setUp(self):
        """Create a serial system for testing for a pti/pto system with 5 components."""
        gearbox = BasicComponent(
            type_=TypeComponent.GEARBOX,
            name="gearbox",
            power_type=TypePower.POWER_TRANSMISSION,
            rated_power=3000,
            rated_speed=150,
            eff_curve=np.array([98.0]),
        )
        synch_mach = ElectricMachine(
            type_=TypeComponent.SYNCHRONOUS_MACHINE,
            name="synchronous machine",
            rated_power=3000,
            rated_speed=150,
            eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
        )
        rectifier = ElectricComponent(
            type_=TypeComponent.RECTIFIER,
            name="rectifier",
            rated_power=3000,
            eff_curve=np.array([99.5]),
        )
        inverter = ElectricComponent(
            type_=TypeComponent.INVERTER,
            name="inverter",
            rated_power=3000,
            eff_curve=CONVERTER_EFF,
        )
        transformer = ElectricComponent(
            type_=TypeComponent.TRANSFORMER,
            name="transformer",
            rated_power=3000,
            eff_curve=np.array([99]),
        )

        self.components = [gearbox, synch_mach, rectifier, inverter, transformer]
        self.pti_pto = SerialSystem(
            TypeComponent.PTI_PTO_SYSTEM,
            TypePower.PTI_PTO,
            "PTIPTO 1",
            self.components,
            rated_power=transformer.rated_power,
            rated_speed=synch_mach.rated_speed,
        )

    def test_component(self):
        name = "component"
        component = create_components(name, 1, 1000, 1000)
        power = np.random.rand() * component.rated_power
        self.assertEqual(component.name, name)
        self.assertEqual(component.get_type_name(), component.type.name)
        self.assertEqual(component.get_load(power), power / component.rated_power)

    def test_get_efficiency_curve_from_points(self):
        eff_curve = create_random_monotonic_eff_curve()
        interp_function, curve = get_efficiency_curve_from_points(eff_curve)
        np.testing.assert_allclose(eff_curve[:, 1], interp_function(eff_curve[:, 0]))
        eff = np.random.rand(1)
        interp_function, curve = get_efficiency_curve_from_points(eff)
        self.assertEqual(eff, interp_function(np.random.rand()))
        columns = []
        for point in eff_curve[:, 0].tolist():
            columns.append("efficiency @{}%".format(point))
        df = pd.DataFrame(np.reshape(eff_curve[:, 1], (1, -1)), columns=columns)
        interp_function, curve = get_efficiency_curve_from_dataframe(df, "effic")
        np.testing.assert_allclose(eff_curve[:, 1], interp_function(eff_curve[:, 0]))

    def test_node(self):
        name = "node"
        type_ = TypeNode(np.ceil(np.random.rand() * (len(TypeNode.__members__) - 1)))
        components = create_components("component", 10, 1000, 1000)
        node = Node(name, type_, components)
        power_total = np.zeros(10)
        for component in components:
            component.power_input = np.random.rand(10) * component.rated_power
            power_total += component.power_input
        self.assertEqual(len(node.components), len(components))
        node.get_power_out()
        np.testing.assert_allclose(power_total, node.power_out)

    # noinspection DuplicatedCode
    def test_engine_bsfc_interpolation_with_points_input(self):
        #: Create an engine component with a arbitrary bsfc curve
        rated_power_max = 1000
        rated_speed_max = 1000
        bsfc_curve = np.append(
            np.reshape(np.arange(10, 101, 10), (-1, 1)),
            np.random.rand(10, 1) * 200,
            axis=1,
        )
        eng = create_engine_component(
            "main engine 1", rated_power_max, rated_speed_max, bsfc_curve
        )
        #: Make the bsfc interpolation function anc compare with the component method
        interp_func = PchipInterpolator(bsfc_curve[:, 0], bsfc_curve[:, 1], extrapolate=True)
        np.testing.assert_allclose(bsfc_curve, eng.specific_fuel_consumption_points)
        power = np.random.rand(4) * eng.rated_power
        load = eng.get_load(power)
        bsfc = interp_func(load)
        np.testing.assert_allclose(eng.specific_fuel_consumption_interp(load), bsfc)
        fuel_consumption = bsfc * power / 1000 / 3600
        engine_comp = eng.get_engine_run_point_from_power_out_kw(power)
        np.testing.assert_allclose(
            engine_comp.fuel_flow_rate_kg_per_s.total_fuel_consumption, fuel_consumption
        )
        np.testing.assert_allclose(engine_comp.load_ratio, load)
        np.testing.assert_allclose(engine_comp.bsfc_g_per_kWh, bsfc)

    def test_engine_bsfc_interpolation_with_a_single_point_input(self):
        #: Create an engine component with a arbitrary bsfc curve
        rated_power = Power_kW(cast(float, 1000.0 * np.random.rand()))
        rated_speed = Speed_rpm(cast(float, 1000.0 * np.random.rand()))
        bsfc_curve = np.random.rand(1) * 200
        eng = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            name="main engine 1",
            rated_power=rated_power,
            rated_speed=rated_speed,
            bsfc_curve=bsfc_curve,
            nox_calculation_method=NOxCalculationMethod.TIER_2,
        )
        self.assertEqual(eng.specific_fuel_consumption_interp(np.random.rand()), bsfc_curve[0])

    def test_engine_with_file_bsfc_curve(self):
        """
        Test the engine class with file input
        """
        #: Create a DataFrame and save it to csv
        name = "engine1"
        filename = "info.csv"
        columns = [
            "Rated Power",
            "Rated Speed",
            "BSFC @100%",
            "BSFC @75%",
            "BSFC @50%",
            "BSFC @25%",
            "BSFC @10%",
        ]
        df = create_dataframe_save_and_return(name, filename, columns)
        bsfc_function, bsfc = get_efficiency_curve_from_dataframe(df, "BSFC")

        #: Create an engine object and test_for_fuel_calculation_for_machinery_system
        eng = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            file_name=filename,
            nox_calculation_method=NOxCalculationMethod.TIER_2,
        )
        load_points = np.random.rand(5)
        # noinspection PyTypeChecker
        self.assertAlmostEqual(eng.name, name)
        self.assertAlmostEqual(eng.rated_speed, df["Rated Speed"].values[0])
        self.assertAlmostEqual(eng.rated_power, df["Rated Power"].values[0])
        np.testing.assert_allclose(eng.specific_fuel_consumption_points, bsfc)
        np.testing.assert_allclose(
            eng.specific_fuel_consumption_interp(load_points),
            bsfc_function(load_points),
        )
        os.unlink(filename)

    def test_engine_with_file_bsfc_point(self):
        #: Create a DataFrame and save it to csv
        name = "engine1"
        filename = "info.csv"
        columns = ["Rated Power", "Rated Speed", "BSFC"]
        df = create_dataframe_save_and_return(name, filename, columns)
        bsfc_curve, bsfc = get_efficiency_curve_from_dataframe(df, "BSFC")

        #: Create an engine object and test_for_fuel_calculation_for_machinery_system
        eng = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            file_name=filename,
            nox_calculation_method=NOxCalculationMethod.TIER_2,
        )
        load_point = np.random.rand(5)
        np.testing.assert_allclose(eng.specific_fuel_consumption_points, bsfc)
        np.testing.assert_allclose(eng.specific_fuel_consumption_interp(load_point), bsfc[0, 1])
        os.unlink(filename)

    def test_basic_component(self):
        #: efficiency curve fitting test_for_fuel_calculation_for_machinery_system
        name = "basic_component"
        rated_power_max = 1000
        rated_speed_max = 500
        basic_component = create_basic_components(name, 1, rated_power_max, rated_speed_max)
        interp_func = PchipInterpolator(
            basic_component._efficiency_points[:, 0],
            basic_component._efficiency_points[:, 1],
            extrapolate=True,
        )
        # self.assertAlmostEqual((eff_curve - basic_component._efficiency_points).sum(), 0)
        load_perc = np.random.rand(5)
        np.testing.assert_allclose(
            basic_component.get_efficiency_from_load_percentage(load_perc),
            interp_func(load_perc),
        )

        #: test the power conversions, forward power
        no_of_pts_to_test = 100000
        power_output = (2 * np.random.rand(no_of_pts_to_test) - 1) * basic_component.rated_power
        power_input = np.zeros(len(power_output))
        load_perc = basic_component.get_load(power_output)
        idx_forward_power = power_output > 0
        idx_reverse_power = np.bitwise_not(idx_forward_power)
        power_input[idx_reverse_power] = power_output[idx_reverse_power]
        power_input[idx_forward_power] = power_output[
            idx_forward_power
        ] / basic_component.get_efficiency_from_load_percentage(load_perc[idx_forward_power])
        power_output[idx_reverse_power] = power_input[
            idx_reverse_power
        ] / basic_component.get_efficiency_from_load_percentage(load_perc[idx_reverse_power])
        (
            power_input_comp,
            load_perc,
        ) = basic_component.get_power_input_from_bidirectional_output(power_output)
        np.testing.assert_allclose(power_input_comp, power_input, atol=2)
        (
            power_output_comp,
            load_perc,
        ) = basic_component.get_power_output_from_bidirectional_input(power_input)
        np.testing.assert_allclose(power_output_comp, power_output, atol=2)

        #: single point efficiency value test_for_fuel_calculation_for_machinery_system
        eff_curve = np.clip(np.random.rand(1), 0.01, 1)
        basic_component = BasicComponent(
            type_=TypeComponent.NONE,
            name=name,
            power_type=random.choice([power_type for power_type in TypePower]),
            rated_power=rated_power_max,
            eff_curve=eff_curve,
            rated_speed=rated_speed_max,
        )
        np.testing.assert_allclose(
            basic_component.get_efficiency_from_load_percentage(load_perc), eff_curve[0]
        )

    def test_electric_component(self):
        #: switchboard id assignment test_for_fuel_calculation_for_machinery_system
        rated_power_max = 1000
        rated_speed_max = 100
        no_components = 100
        switchboard_id_list = np.random.randint(1, 11, no_components)
        electric_components = []
        type_power_list = [type_power for type_power in TypePower]
        for switchboard_id in switchboard_id_list:
            electric_components += create_electric_components_for_switchboard(
                random.choice(type_power_list),
                1,
                rated_power_max * random.random(),
                rated_speed_max,
                switchboard_id,
            )
        switchboard_id_list_to_compare = np.array(
            [electric_component.switchboard_id for electric_component in electric_components]
        )
        np.testing.assert_array_equal(switchboard_id_list, switchboard_id_list_to_compare)

    # noinspection DuplicatedCode
    def test_electric_machine(self):
        # Create a electric machine component as power source
        rated_power_max = 1000
        rated_speed_max = 1000
        rated_power = rated_power_max * (random.random() / 2 + 0.5)
        # noinspection PyTypeChecker
        electric_machine = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator",
            rated_power=rated_power,
            rated_speed=rated_speed_max * random.random(),
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=1,
            eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
        )
        # Test for power input from the shaft.
        number_of_point_to_test = 10000
        power_electric = (
            2 * np.random.rand(number_of_point_to_test) - 1
        ) * electric_machine.rated_power
        power_shaft = power_electric.copy()
        idx_generator = power_electric >= 0
        idx_motor = np.bitwise_not(idx_generator)
        load = electric_machine.get_load(power_electric)
        efficiency = electric_machine.get_efficiency_from_load_percentage(load)
        # noinspection DuplicatedCode
        power_shaft[idx_generator] = power_electric[idx_generator] / efficiency[idx_generator]
        power_electric[idx_motor] = power_shaft[idx_motor] / efficiency[idx_motor]
        # Test for power input from the mechanical side
        (
            power_electric_pred,
            load_pred,
        ) = electric_machine.get_electric_power_load_from_shaft_power(power_shaft)
        np.testing.assert_allclose(power_electric_pred, power_electric, rtol=2e-3)
        np.testing.assert_allclose(load, load_pred, rtol=2e-3)
        # Test for power input from the electric side
        (
            power_shaft_pred,
            load_pred,
        ) = electric_machine.get_shaft_power_load_from_electric_power(power_electric, True)
        np.testing.assert_allclose(power_shaft, power_shaft_pred)
        np.testing.assert_allclose(load, load_pred)

        # Test for power consumer and PTI/PTO
        rated_power = rated_power_max * (random.random() * 0.5 + 0.5)
        rated_speed = rated_speed_max * random.random()
        # noinspection PyTypeChecker
        electric_machine = ElectricMachine(
            type_=TypeComponent.ELECTRIC_MOTOR,
            name="electric_motor",
            rated_power=rated_power,
            rated_speed=rated_speed,
            power_type=TypePower.POWER_CONSUMER,
            switchboard_id=1,
            eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
        )
        # Test for power input from the shaft
        number_of_point_to_test = 10000
        power_shaft = (
            2 * np.random.rand(number_of_point_to_test) - 1
        ) * electric_machine.rated_power
        power_electric = power_shaft.copy()
        load = electric_machine.get_load(power_electric)
        efficiency = electric_machine.get_efficiency_from_load_percentage(load)
        idx_motor = power_shaft > 0
        idx_generator = np.bitwise_not(idx_motor)
        power_electric[idx_motor] = power_shaft[idx_motor] / efficiency[idx_motor]
        power_shaft[idx_generator] = power_electric[idx_generator] / efficiency[idx_generator]
        # Test for power input from the shaft side
        (
            power_electric_pred,
            load_pred,
        ) = electric_machine.get_electric_power_load_from_shaft_power(power_shaft)
        np.testing.assert_allclose(power_electric_pred, power_electric, rtol=2e-3)
        np.testing.assert_allclose(load, load_pred, rtol=2e-3)
        # Test for power input from the electric side
        (
            power_shaft_pred,
            load,
        ) = electric_machine.get_shaft_power_load_from_electric_power(power_electric, True)
        np.testing.assert_allclose(power_shaft, power_shaft_pred)
        np.testing.assert_allclose(load, load_pred, rtol=2e-3)

    def test_electric_component_efficiency_interpolation_with_a_single_point_input(
        self,
    ):
        efficiency = 0.45
        generator = ElectricComponent(
            name="generator",
            type_=TypeComponent.GENERATOR,
            rated_power=100,
            rated_speed=100,
            eff_curve=np.array([efficiency]),
        )
        self.assertAlmostEqual(generator.get_efficiency_from_load_percentage(0.45), efficiency)

    def test_electric_component_with_file_input(self):
        name = "generator 1"
        filename = "info.csv"
        columns = ["Switchboard No", "Rated Power", "Rated Speed"]
        df = create_dataframe_save_and_return(name, filename, columns)
        efficiency_function, efficiency = get_efficiency_curve_from_dataframe(df, "Efficiency")
        #: Create an engine object and test_for_fuel_calculation_for_machinery_system
        gen = ElectricComponent(
            type_=TypeComponent.GENERATOR,
            power_type=TypePower.POWER_SOURCE,
            file_name=filename,
        )
        load_point = np.random.rand()
        self.assertEqual(gen.name, name)
        self.assertAlmostEqual(gen.rated_speed, df["Rated Speed"].values[0])
        self.assertAlmostEqual(gen.rated_power, df["Rated Power"].values[0])
        np.testing.assert_allclose(gen._efficiency_points, efficiency)
        self.assertAlmostEqual(
            gen.get_efficiency_from_load_percentage(load_point),
            np.clip(efficiency_function(load_point), 0.01, 1),
        )
        os.unlink(filename)

    def test_serial_system(self):
        load_perc = 0.50  # np.random.rand() * 100
        efficiency = 1
        for component in self.components:
            efficiency *= component.get_efficiency_from_load_percentage(load_perc)
        self.assertAlmostEqual(
            self.pti_pto.get_efficiency_from_load_percentage(load_perc),
            efficiency,
            places=-1,
        )

    def test_pti_pto(self):
        #: Create a PTIPTO instance
        switchboard_id = 1
        shaft_line_id = 1
        pti_pto = PTIPTO(
            self.pti_pto.name,
            self.pti_pto.components,
            switchboard_id,
            self.pti_pto.rated_power,
            self.pti_pto.rated_speed,
            shaft_line_id,
        )
        self.assertEqual(shaft_line_id, pti_pto.shaft_line_id)

    def test_serial_system_electric(self):
        switchboard_no = 0
        power_type = TypePower.PTI_PTO
        # noinspection PyShadowingNames
        pti_pto_electric = SerialSystemElectric(
            self.pti_pto.type,
            self.pti_pto.name,
            power_type,
            self.pti_pto.components,
            switchboard_no,
            self.pti_pto.rated_power,
            self.pti_pto.rated_speed,
        )
        self.assertEqual(pti_pto_electric.switchboard_id, switchboard_no)
        self.assertEqual(pti_pto_electric.power_type, power_type)

    # noinspection DuplicatedCode
    def test_main_engine_with_gear_box(self):
        engine = create_engine_component("main_engine 1", 1000, 1000)
        gearbox = BasicComponent(
            type_=TypeComponent.GEARBOX,
            name="gearbox",
            power_type=TypePower.POWER_TRANSMISSION,
            rated_power=engine.rated_power,
            rated_speed=engine.rated_speed,
            eff_curve=np.array([98]),
        )
        main_engine_with_gearbox = MainEngineWithGearBoxForMechanicalPropulsion(
            "main engine with GB", engine, gearbox
        )
        power_at_gearbox_out = np.random.rand(5) * gearbox.rated_power
        load = gearbox.get_load(power_at_gearbox_out)
        eff_gearbox = gearbox.get_efficiency_from_load_percentage(load)
        power_at_engine_shaft = power_at_gearbox_out / eff_gearbox
        engine_run_point = engine.get_engine_run_point_from_power_out_kw(power_at_engine_shaft)
        engine_run_point_comp = main_engine_with_gearbox.get_engine_run_point_from_power_out_kw(
            power_at_gearbox_out
        )
        np.testing.assert_allclose(
            engine_run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            engine_run_point_comp.fuel_flow_rate_kg_per_s.total_fuel_consumption,
        )
        np.testing.assert_allclose(engine_run_point.load_ratio, engine_run_point_comp.load_ratio)
        np.testing.assert_allclose(
            engine_run_point.bsfc_g_per_kWh, engine_run_point_comp.bsfc_g_per_kWh
        )

    def test_genset(self):
        #: Create an engine component
        engine = create_engine_component("auxiliary engine 1", 1000, 1000)
        #: Create a generator component
        generator = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator 1",
            rated_power=engine.rated_power * 0.9,
            rated_speed=engine.rated_speed,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=SwbId(0),
            number_poles=4,
            eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
        )
        rectifier = ElectricComponent(
            type_=TypeComponent.RECTIFIER,
            name="rectifier 1",
            rated_power=generator.rated_power,
            eff_curve=np.array([99]),
        )
        genset_ac = Genset("genset 1", engine, generator)
        genset_dc = Genset("genset 1", engine, generator, rectifier)
        power_electric = np.random.rand(5) * genset_ac.rated_power
        load_at_genset = generator.get_load(power_electric)
        power_dc_at_generator = power_electric / rectifier.get_efficiency_from_load_percentage(
            load_at_genset
        )
        power_shaft_ac, load_perc = generator.get_shaft_power_load_from_electric_power(
            power_electric
        )
        power_shaft_dc, load_perc = generator.get_shaft_power_load_from_electric_power(
            power_dc_at_generator
        )
        res_engine_ac = engine.get_engine_run_point_from_power_out_kw(power_shaft_ac)
        res_engine_dc = engine.get_engine_run_point_from_power_out_kw(power_shaft_dc)
        res_genset_ac = genset_ac.get_fuel_cons_load_bsfc_from_power_out_generator_kw(
            power_electric
        )
        res_genset_dc = genset_dc.get_fuel_cons_load_bsfc_from_power_out_generator_kw(
            power_electric
        )
        np.testing.assert_allclose(
            res_engine_ac.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            res_genset_ac.engine.fuel_flow_rate_kg_per_s.total_fuel_consumption,
        )
        np.testing.assert_allclose(
            res_engine_dc.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            res_genset_dc.engine.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            rtol=1e-2,
        )

    def test_dual_fuel_engine(self):
        """Test dual fuel engine"""
        engine = EngineDualFuel(
            type_=TypeComponent.MAIN_ENGINE,
            nox_calculation_method=NOxCalculationMethod.TIER_3,
            name="main engine 1",
            rated_power=1000,
            rated_speed=1000,
            bsfc_curve=np.append(
                np.reshape(np.arange(0.1, 1.1, 0.1), (-1, 1)),
                np.random.rand(10, 1) * 200,
                axis=1,
            ),
            fuel_type=TypeFuel.NATURAL_GAS,
            bspfc_curve=np.append(
                np.reshape(np.arange(0.1, 1.1, 0.1), (-1, 1)),
                np.random.rand(10, 1) * 10,
                axis=1,
            ),
            pilot_fuel_type=TypeFuel.DIESEL,
        )
        power = np.random.rand(5) * engine.rated_power
        engine_run_point = engine.get_engine_run_point_from_power_out_kw(power)
        natual_gas_consumption_kg_per_s = engine_run_point.bsfc_g_per_kWh * power / 3600 / 1000
        assert np.allclose(
            engine_run_point.fuel_flow_rate_kg_per_s.fuels[0].mass_or_mass_fraction,
            natual_gas_consumption_kg_per_s,
        )
        diesel_consumption_kg_per_s = engine_run_point.bspfc_g_per_kWh * power / 3600 / 1000
        assert np.allclose(
            engine_run_point.fuel_flow_rate_kg_per_s.fuels[1].mass_or_mass_fraction,
            diesel_consumption_kg_per_s,
        )
        print(engine_run_point)
        print(engine_run_point.fuel_flow_rate_kg_per_s.__dict__)

        # Test the same with pilot fuel being the same as main fuel
        engine_same_fuel = EngineDualFuel(
            type_=TypeComponent.MAIN_ENGINE,
            nox_calculation_method=NOxCalculationMethod.TIER_3,
            name="main engine 2",
            rated_power=1000,
            rated_speed=1000,
            bsfc_curve=np.append(
                np.reshape(np.arange(0.1, 1.1, 0.1), (-1, 1)),
                np.random.rand(10, 1) * 200,
                axis=1,
            ),
            fuel_type=TypeFuel.DIESEL,
            bspfc_curve=np.append(
                np.reshape(np.arange(0.1, 1.1, 0.1), (-1, 1)),
                np.random.rand(10, 1) * 10,
                axis=1,
            ),
            pilot_fuel_type=TypeFuel.DIESEL,
        )
        engine_run_point_same_fuel = engine_same_fuel.get_engine_run_point_from_power_out_kw(power)
        total_consumption_kg_per_s = (
            (
                engine_run_point_same_fuel.bsfc_g_per_kWh
                + engine_run_point_same_fuel.bspfc_g_per_kWh
            )
            * power
            / 3600
            / 1000
        )
        assert len(engine_run_point_same_fuel.fuel_flow_rate_kg_per_s.fuels) == 1
        assert np.allclose(
            engine_run_point_same_fuel.fuel_flow_rate_kg_per_s.fuels[0].mass_or_mass_fraction,
            total_consumption_kg_per_s,
        )

    def test_engine_multi_fuel(self):
        rated_power = 1000.0
        rated_speed = 1000.0
        power_kw = np.array([rated_power * 0.5])

        main_bsfc_dual = np.array([[0.0, 180.0], [1.0, 180.0]])
        pilot_bsfc_dual = np.array([[0.0, 10.0], [1.0, 10.0]])
        diesel_bsfc_single = np.array([[0.0, 210.0], [1.0, 210.0]])

        multi_fuel_characteristics = [
            FuelCharacteristics(
                main_fuel_type=TypeFuel.NATURAL_GAS,
                main_fuel_origin=FuelOrigin.FOSSIL,
                pilot_fuel_type=TypeFuel.DIESEL,
                pilot_fuel_origin=FuelOrigin.FOSSIL,
                bsfc_curve=main_bsfc_dual,
                bspfc_curve=pilot_bsfc_dual,
            ),
            FuelCharacteristics(
                main_fuel_type=TypeFuel.DIESEL,
                main_fuel_origin=FuelOrigin.FOSSIL,
                pilot_fuel_type=None,
                pilot_fuel_origin=None,
                bsfc_curve=diesel_bsfc_single,
            ),
        ]

        engine = EngineMultiFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="multi-fuel engine",
            rated_power=rated_power,
            rated_speed=rated_speed,
            multi_fuel_characteristics=multi_fuel_characteristics,
        )

        expected_load = power_kw / rated_power
        engine.set_fuel_in_use(fuel_type=TypeFuel.NATURAL_GAS, fuel_origin=FuelOrigin.FOSSIL)

        lng_run_point = engine.get_engine_run_point_from_power_out_kw(power_kw=power_kw)

        expected_main_bsfc = np.full_like(expected_load, 180.0, dtype=float)
        expected_main_consumption = expected_main_bsfc * (power_kw / 3600.0) / 1000.0
        expected_pilot_bsfc = np.full_like(expected_load, 10.0, dtype=float)
        expected_pilot_consumption = expected_pilot_bsfc * (power_kw / 3600.0) / 1000.0

        np.testing.assert_allclose(lng_run_point.load_ratio, expected_load)
        np.testing.assert_allclose(lng_run_point.bsfc_g_per_kWh, expected_main_bsfc)
        self.assertEqual(len(lng_run_point.fuel_flow_rate_kg_per_s.fuels), 2)
        main_fuel = lng_run_point.fuel_flow_rate_kg_per_s.fuels[0]
        pilot_fuel = lng_run_point.fuel_flow_rate_kg_per_s.fuels[1]
        self.assertEqual(main_fuel.fuel_type, TypeFuel.NATURAL_GAS)
        self.assertEqual(main_fuel.origin, FuelOrigin.FOSSIL)
        np.testing.assert_allclose(main_fuel.mass_or_mass_fraction, expected_main_consumption)
        np.testing.assert_allclose(lng_run_point.bspfc_g_per_kWh, expected_pilot_bsfc)
        self.assertEqual(pilot_fuel.fuel_type, TypeFuel.DIESEL)
        self.assertEqual(pilot_fuel.origin, FuelOrigin.FOSSIL)
        np.testing.assert_allclose(pilot_fuel.mass_or_mass_fraction, expected_pilot_consumption)
        np.testing.assert_allclose(
            lng_run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            expected_main_consumption + expected_pilot_consumption,
        )

        engine.set_fuel_in_use(fuel_type=TypeFuel.DIESEL, fuel_origin=FuelOrigin.FOSSIL)
        diesel_run_point = engine.get_engine_run_point_from_power_out_kw(power_kw=power_kw)

        expected_diesel_bsfc = np.full_like(expected_load, 210.0, dtype=float)
        expected_diesel_consumption = expected_diesel_bsfc * (power_kw / 3600.0) / 1000.0

        np.testing.assert_allclose(diesel_run_point.load_ratio, expected_load)
        np.testing.assert_allclose(diesel_run_point.bsfc_g_per_kWh, expected_diesel_bsfc)
        self.assertIsNone(diesel_run_point.bspfc_g_per_kWh)
        self.assertEqual(len(diesel_run_point.fuel_flow_rate_kg_per_s.fuels), 1)
        diesel_fuel = diesel_run_point.fuel_flow_rate_kg_per_s.fuels[0]
        self.assertEqual(diesel_fuel.fuel_type, TypeFuel.DIESEL)
        self.assertEqual(diesel_fuel.origin, FuelOrigin.FOSSIL)
        np.testing.assert_allclose(
            diesel_fuel.mass_or_mass_fraction,
            expected_diesel_consumption,
        )
        np.testing.assert_allclose(
            diesel_run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            expected_diesel_consumption,
        )

    def test_main_engine_mechanical_with_engine_multi_fuel(self):
        rated_power = 1200.0
        rated_speed = 750.0
        power_kw = np.array([rated_power * 0.6])

        engine_for_component = EngineMultiFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="multi",
            rated_power=rated_power,
            rated_speed=rated_speed,
            multi_fuel_characteristics=create_multi_fuel_characteristics_sample(),
        )
        engine_for_expected = EngineMultiFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="multi-expected",
            rated_power=rated_power,
            rated_speed=rated_speed,
            multi_fuel_characteristics=create_multi_fuel_characteristics_sample(),
        )

        component = MainEngineForMechanicalPropulsion(
            name="main engine",
            engine=engine_for_component,
        )

        # Default fuel selection should use the first entry (natural gas)
        default_run_point = component.get_engine_run_point_from_power_out_kw(power=power_kw)
        self.assertEqual(
            default_run_point.fuel_flow_rate_kg_per_s.fuels[0].fuel_type,
            TypeFuel.NATURAL_GAS,
        )

        engine_for_expected.set_fuel_in_use(
            fuel_type=TypeFuel.NATURAL_GAS,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        default_expected = engine_for_expected.get_engine_run_point_from_power_out_kw(
            power_kw=power_kw,
        )
        np.testing.assert_allclose(default_run_point.load_ratio, default_expected.load_ratio)
        np.testing.assert_allclose(
            default_run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            default_expected.fuel_flow_rate_kg_per_s.total_fuel_consumption,
        )

        # Explicit fuel choice should be honoured
        diesel_run_point = component.get_engine_run_point_from_power_out_kw(
            power=power_kw,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        engine_for_expected.set_fuel_in_use(
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        diesel_expected = engine_for_expected.get_engine_run_point_from_power_out_kw(
            power_kw=power_kw,
        )
        np.testing.assert_allclose(diesel_run_point.load_ratio, diesel_expected.load_ratio)
        np.testing.assert_allclose(
            diesel_run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            diesel_expected.fuel_flow_rate_kg_per_s.total_fuel_consumption,
        )

    def test_main_engine_with_gearbox_multi_fuel_support(self):
        rated_power = 1500.0
        rated_speed = 900.0
        power_kw = np.array([rated_power * 0.4])
        gearbox_eff_curve = np.array([[0.0, 0.95], [1.0, 0.95]])

        engine_for_component = EngineMultiFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="gear-multi",
            rated_power=rated_power,
            rated_speed=rated_speed,
            multi_fuel_characteristics=create_multi_fuel_characteristics_sample(),
        )
        engine_for_expected = EngineMultiFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="gear-multi-expected",
            rated_power=rated_power,
            rated_speed=rated_speed,
            multi_fuel_characteristics=create_multi_fuel_characteristics_sample(),
        )

        gearbox = BasicComponent(
            type_=TypeComponent.GEARBOX,
            name="gearbox",
            power_type=TypePower.POWER_TRANSMISSION,
            rated_power=rated_power,
            rated_speed=rated_speed,
            eff_curve=gearbox_eff_curve,
        )

        component = MainEngineWithGearBoxForMechanicalPropulsion(
            name="main engine gearbox",
            engine=engine_for_component,
            gearbox=gearbox,
        )

        run_point = component.get_engine_run_point_from_power_out_kw(
            power=power_kw,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )

        load_ratio = component.get_load(power_kw)
        gearbox_eff = gearbox.get_efficiency_from_load_percentage(load_ratio)
        engine_for_expected.set_fuel_in_use(
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        expected = engine_for_expected.get_engine_run_point_from_power_out_kw(
            power_kw=power_kw / gearbox_eff,
        )

        np.testing.assert_allclose(run_point.load_ratio, expected.load_ratio)
        np.testing.assert_allclose(
            run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            expected.fuel_flow_rate_kg_per_s.total_fuel_consumption,
        )

    def test_main_engine_mechanical_single_fuel_mismatch_raises(self):
        rated_power = 800.0
        rated_speed = 600.0
        bsfc_curve = np.array([[0.0, 200.0], [1.0, 200.0]])
        engine = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            rated_power=rated_power,
            rated_speed=rated_speed,
            bsfc_curve=bsfc_curve,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        component = MainEngineForMechanicalPropulsion(name="single", engine=engine)
        with self.assertRaises(ValueError):
            component.get_engine_run_point_from_power_out_kw(
                power=np.array([rated_power * 0.5]),
                fuel_type=TypeFuel.NATURAL_GAS,
                fuel_origin=FuelOrigin.FOSSIL,
            )

    def test_main_engine_with_gearbox_single_fuel_mismatch_raises(self):
        rated_power = 900.0
        rated_speed = 700.0
        bsfc_curve = np.array([[0.0, 210.0], [1.0, 210.0]])
        engine = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            rated_power=rated_power,
            rated_speed=rated_speed,
            bsfc_curve=bsfc_curve,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        gearbox = BasicComponent(
            type_=TypeComponent.GEARBOX,
            name="gearbox",
            power_type=TypePower.POWER_TRANSMISSION,
            rated_power=rated_power,
            rated_speed=rated_speed,
            eff_curve=np.array([1.0]),
        )
        component = MainEngineWithGearBoxForMechanicalPropulsion(
            name="gear-single",
            engine=engine,
            gearbox=gearbox,
        )
        with self.assertRaises(ValueError):
            component.get_engine_run_point_from_power_out_kw(
                power=np.array([rated_power * 0.4]),
                fuel_type=TypeFuel.NATURAL_GAS,
                fuel_origin=FuelOrigin.FOSSIL,
            )

    def test_genset_multi_fuel_support(self):
        rated_power = 1000.0
        rated_speed = 900.0
        power_electric = np.array([rated_power * 0.5])

        aux_engine_component = EngineMultiFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="aux-multi",
            rated_power=rated_power,
            rated_speed=rated_speed,
            multi_fuel_characteristics=create_multi_fuel_characteristics_sample(),
        )
        aux_engine_expected = EngineMultiFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="aux-multi-expected",
            rated_power=rated_power,
            rated_speed=rated_speed,
            multi_fuel_characteristics=create_multi_fuel_characteristics_sample(),
        )

        generator_component = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator multi",
            rated_power=rated_power * 0.9,
            rated_speed=rated_speed,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=SwbId(0),
            number_poles=4,
            eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
        )
        generator_expected = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator expected",
            rated_power=rated_power * 0.9,
            rated_speed=rated_speed,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=SwbId(0),
            number_poles=4,
            eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
        )

        genset = Genset("genset multi", aux_engine_component, generator_component)

        result_default = genset.get_fuel_cons_load_bsfc_from_power_out_generator_kw(
            power=power_electric
        )
        self.assertEqual(
            result_default.engine.fuel_flow_rate_kg_per_s.fuels[0].fuel_type,
            TypeFuel.NATURAL_GAS,
        )
        shaft_power_expected, _ = generator_expected.get_shaft_power_load_from_electric_power(
            power_electric
        )
        aux_engine_expected.set_fuel_in_use(
            fuel_type=TypeFuel.NATURAL_GAS,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        expected_default = aux_engine_expected.get_engine_run_point_from_power_out_kw(
            power_kw=shaft_power_expected,
        )
        np.testing.assert_allclose(
            result_default.engine.load_ratio,
            expected_default.load_ratio,
        )
        for result_fuel, expected_fuel in zip(
            result_default.engine.fuel_flow_rate_kg_per_s.fuels,
            expected_default.fuel_flow_rate_kg_per_s.fuels,
        ):
            np.testing.assert_allclose(
                result_fuel.mass_or_mass_fraction,
                expected_fuel.mass_or_mass_fraction,
            )

        result_diesel = genset.get_fuel_cons_load_bsfc_from_power_out_generator_kw(
            power=power_electric,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        aux_engine_expected.set_fuel_in_use(
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        expected_diesel = aux_engine_expected.get_engine_run_point_from_power_out_kw(
            power_kw=shaft_power_expected,
        )
        np.testing.assert_allclose(
            result_diesel.engine.load_ratio,
            expected_diesel.load_ratio,
        )
        np.testing.assert_allclose(
            result_diesel.engine.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            expected_diesel.fuel_flow_rate_kg_per_s.total_fuel_consumption,
        )

    def test_genset_single_fuel_mismatch_raises(self):
        rated_power = 950.0
        rated_speed = 720.0
        bsfc_curve = np.array([[0.0, 205.0], [1.0, 205.0]])
        aux_engine = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            rated_power=rated_power,
            rated_speed=rated_speed,
            bsfc_curve=bsfc_curve,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        generator = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator single",
            rated_power=rated_power * 0.9,
            rated_speed=rated_speed,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=SwbId(0),
            number_poles=4,
            eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
        )
        genset = Genset("genset single", aux_engine, generator)
        with self.assertRaises(ValueError):
            genset.get_fuel_cons_load_bsfc_from_power_out_generator_kw(
                power=np.array([rated_power * 0.4]),
                fuel_type=TypeFuel.NATURAL_GAS,
                fuel_origin=FuelOrigin.FOSSIL,
            )

    def test_energy_balance_main_engine_with_engine_multi_fuel(self):
        rated_power = 1200.0
        rated_speed = 750.0
        power = np.array([rated_power * 0.6])
        main_engine_component = MainEngineForMechanicalPropulsion(
            name="main-multi",
            engine=EngineMultiFuel(
                type_=TypeComponent.MAIN_ENGINE,
                name="multi",
                rated_power=rated_power,
                rated_speed=rated_speed,
                multi_fuel_characteristics=create_multi_fuel_characteristics_sample(),
            ),
        )
        main_engine_component.power_output = power
        time_interval_s = np.array([3600.0])

        result = get_fuel_emission_energy_balance_for_component(
            component=main_engine_component,
            time_interval_s=time_interval_s,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )

        expected_run_point = main_engine_component.get_engine_run_point_from_power_out_kw()
        expected_total = (
            expected_run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption * time_interval_s[0]
        )

        self.assertIsNotNone(result.multi_fuel_consumption_total_kg)
        self.assertGreaterEqual(
            result.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel,
            0,
        )
        np.testing.assert_allclose(
            result.multi_fuel_consumption_total_kg.total_fuel_consumption,
            expected_total,
        )
        self.assertEqual(
            result.multi_fuel_consumption_total_kg.fuels[0].fuel_type,
            TypeFuel.NATURAL_GAS,
        )

    def test_energy_balance_genset_with_engine_multi_fuel(self):
        rated_power = 800.0
        rated_speed = 720.0
        power = np.array([rated_power * 0.5])
        aux_engine_multi = EngineMultiFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="genset-multi",
            rated_power=rated_power,
            rated_speed=rated_speed,
            multi_fuel_characteristics=create_multi_fuel_characteristics_sample(),
        )
        generator = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator",
            rated_power=rated_power * 0.9,
            rated_speed=rated_speed,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=SwbId(0),
            number_poles=4,
            eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
        )
        genset = Genset("genset-multi", aux_engine_multi, generator)
        genset.power_output = power
        time_interval_s = np.array([3600.0])

        result = get_fuel_emission_energy_balance_for_component(
            component=genset,
            time_interval_s=time_interval_s,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )

        expected_run_point = genset.get_fuel_cons_load_bsfc_from_power_out_generator_kw(
            power=power
        )
        expected_total = (
            expected_run_point.engine.fuel_flow_rate_kg_per_s.total_fuel_consumption
            * time_interval_s[0]
        )

        self.assertIsNotNone(result.multi_fuel_consumption_total_kg)
        self.assertGreaterEqual(
            result.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel,
            0,
        )
        np.testing.assert_allclose(
            result.multi_fuel_consumption_total_kg.total_fuel_consumption,
            expected_total,
        )
        self.assertEqual(
            result.multi_fuel_consumption_total_kg.fuels[0].fuel_type,
            TypeFuel.NATURAL_GAS,
        )

    def test_energy_balance_main_engine_with_multi_fuel_explicit_selection(self):
        rated_power = 1500.0
        rated_speed = 780.0
        power = np.array([rated_power * 0.55])
        main_engine_component = MainEngineForMechanicalPropulsion(
            name="main-multi-select",
            engine=EngineMultiFuel(
                type_=TypeComponent.MAIN_ENGINE,
                name="multi-select",
                rated_power=rated_power,
                rated_speed=rated_speed,
                multi_fuel_characteristics=create_multi_fuel_characteristics_sample(),
            ),
        )
        main_engine_component.power_output = power
        time_interval_s = np.array([3600.0])

        result = get_fuel_emission_energy_balance_for_component(
            component=main_engine_component,
            time_interval_s=time_interval_s,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )

        expected_run_point = main_engine_component.get_engine_run_point_from_power_out_kw(
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        expected_total = (
            expected_run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption * time_interval_s[0]
        )

        np.testing.assert_allclose(
            result.multi_fuel_consumption_total_kg.total_fuel_consumption,
            expected_total,
        )
        self.assertEqual(
            result.multi_fuel_consumption_total_kg.fuels[0].fuel_type,
            TypeFuel.DIESEL,
        )
        self.assertEqual(
            result.multi_fuel_consumption_total_kg.fuels[0].origin,
            FuelOrigin.FOSSIL,
        )

    def test_energy_balance_genset_with_multi_fuel_explicit_selection(self):
        rated_power = 950.0
        rated_speed = 800.0
        power = np.array([rated_power * 0.45])
        aux_engine_multi = EngineMultiFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="genset-multi-select",
            rated_power=rated_power,
            rated_speed=rated_speed,
            multi_fuel_characteristics=create_multi_fuel_characteristics_sample(),
        )
        generator = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator-select",
            rated_power=rated_power * 0.9,
            rated_speed=rated_speed,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=SwbId(0),
            number_poles=4,
            eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
        )
        genset = Genset("genset-multi-select", aux_engine_multi, generator)
        genset.power_output = power
        time_interval_s = np.array([3600.0])

        result = get_fuel_emission_energy_balance_for_component(
            component=genset,
            time_interval_s=time_interval_s,
            integration_method=IntegrationMethod.simpson,
            fuel_specified_by=FuelSpecifiedBy.IMO,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )

        expected_run_point = genset.get_fuel_cons_load_bsfc_from_power_out_generator_kw(
            power=power,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        expected_total = (
            expected_run_point.engine.fuel_flow_rate_kg_per_s.total_fuel_consumption
            * time_interval_s[0]
        )

        np.testing.assert_allclose(
            result.multi_fuel_consumption_total_kg.total_fuel_consumption,
            expected_total,
        )
        self.assertEqual(
            result.multi_fuel_consumption_total_kg.fuels[0].fuel_type,
            TypeFuel.DIESEL,
        )
        self.assertEqual(
            result.multi_fuel_consumption_total_kg.fuels[0].origin,
            FuelOrigin.FOSSIL,
        )

    def test_fuel_cell(self):
        """Test fuel cell"""
        fuel_cell = FuelCell(
            name="fuel cell 1",
            rated_power=1000,
            eff_curve=create_random_monotonic_eff_curve(),
            fuel_type=TypeFuel.HYDROGEN,
        )
        power = np.random.rand(5) * fuel_cell.rated_power
        fuel_cell_run_point = fuel_cell.get_fuel_cell_run_point(power_out_kw=power)
        fuel = Fuel(
            fuel_type=fuel_cell.fuel_type,
            origin=fuel_cell.fuel_origin,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        hydrogen_consumption_kg_per_s = (
            power / fuel_cell_run_point.efficiency / (fuel.lhv_mj_per_g * 1000) / 1000
        )
        assert np.allclose(
            fuel_cell_run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            hydrogen_consumption_kg_per_s,
        )

        fuel_cell.fuel_type = TypeFuel.NATURAL_GAS
        fuel_cell.fuel_origin = FuelOrigin.FOSSIL
        fuel_cell_run_point = fuel_cell.get_fuel_cell_run_point(power_out_kw=power)
        fuel = Fuel(
            fuel_type=fuel_cell.fuel_type,
            origin=fuel_cell.fuel_origin,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        natural_gas_consumption_kg_per_s = (
            power / fuel_cell_run_point.efficiency / (fuel.lhv_mj_per_g * 1000) / 1000
        )
        assert np.allclose(
            fuel_cell_run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            natural_gas_consumption_kg_per_s,
        )

        number_modules = 2
        converter = ElectricComponent(
            type_=TypeComponent.POWER_CONVERTER,
            name="converter",
            rated_power=fuel_cell.rated_power * number_modules * 1.05,
            eff_curve=create_random_monotonic_eff_curve(),
        )
        fuel_cell_system = FuelCellSystem(
            name="fuel cell system 1",
            fuel_cell_module=fuel_cell,
            converter=converter,
            switchboard_id=1,
            number_modules=2,
        )
        power = np.random.rand(5) * fuel_cell_system.rated_power
        power_after_converter, _ = converter.get_power_input_from_bidirectional_output(power)
        fuel_cell_system_run_point = fuel_cell_system.get_fuel_cell_run_point(power)
        fuel_cell_module_run_point = fuel_cell_system.fuel_cell.get_fuel_cell_run_point(
            power_out_kw=power_after_converter / number_modules,
        )
        assert np.allclose(
            fuel_cell_system_run_point.load_ratio,
            fuel_cell_module_run_point.load_ratio,
        )
        for fuel_con_system, fuel_con_module in zip(
            fuel_cell_system_run_point.fuel_flow_rate_kg_per_s.fuels,
            fuel_cell_module_run_point.fuel_flow_rate_kg_per_s.fuels,
        ):
            assert np.allclose(
                fuel_con_system.mass_or_mass_fraction,
                fuel_con_module.mass_or_mass_fraction * number_modules,
            )
        assert np.allclose(
            fuel_cell_system_run_point.efficiency,
            fuel_cell_module_run_point.efficiency,
        )

    def test_cogas(self):
        """Test combined gas and steam system - mechanical output"""
        cogas = create_cogas_system()
        power_output_kw = np.random.rand(5) * cogas.rated_power
        eff_cogas = cogas.get_efficiency_from_load_percentage(cogas.get_load(power_output_kw))
        fuel = Fuel(
            fuel_type=cogas.fuel_type,
            origin=cogas.fuel_origin,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        fuel_consumption_kg_per_s_ref = (
            power_output_kw / eff_cogas / (fuel.lhv_mj_per_g * 1000) / 1000
        )
        gas_turbine_run_point = cogas.get_gas_turbine_run_point_from_power_output_kw(
            power_output_kw
        )
        np.testing.assert_allclose(eff_cogas, gas_turbine_run_point.efficiency)
        np.testing.assert_allclose(
            fuel_consumption_kg_per_s_ref,
            gas_turbine_run_point.fuel_flow_rate_kg_per_s.fuels[0].mass_or_mass_fraction,
        )

        # Test if the default NOx emission curve is IMO Tier 3
        factor, exponent = nox_factor_imo_medium_speed_g_hWh[NOxCalculationMethod.TIER_3.value]
        nox_g_per_kwh = factor * np.power(cogas.rated_speed, exponent)
        np.testing.assert_equal(
            cogas._emissions_per_kwh_interp[EmissionType.NOX](np.random.rand()),
            nox_g_per_kwh,
        )

    def test_coges(self):
        #: Create an engine component
        cogas = create_cogas_system()
        #: Create a generator component
        generator = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator 1",
            rated_power=cogas.rated_power * 0.9,
            rated_speed=cogas.rated_speed,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=SwbId(0),
            number_poles=4,
            eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
        )
        coges = COGES(
            name="coges 1",
            cogas=cogas,
            generator=generator,
        )
        power_electric = np.random.rand(5) * coges.rated_power
        power_shaft, load_at_generator = generator.get_shaft_power_load_from_electric_power(
            power_electric
        )
        res_cogas = cogas.get_gas_turbine_run_point_from_power_output_kw(power_shaft)
        res_coges = coges.get_system_run_point_from_power_output_kw(power_electric)
        np.testing.assert_allclose(load_at_generator, res_coges.coges_load_ratio)
        np.testing.assert_allclose(
            res_coges.cogas.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            res_cogas.fuel_flow_rate_kg_per_s.total_fuel_consumption,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tests for user_defined_fuels threading through the component calculation stack
# ─────────────────────────────────────────────────────────────────────────────


class TestUserDefinedFuels(TestCase):
    """Verify that user_defined_fuels are correctly applied (or ignored when no
    match) at every layer of the fuel-consumption calculation stack."""

    _BSFC_CURVE = np.array([[0.25, 200.0], [0.5, 190.0], [0.75, 185.0], [1.0, 190.0]])

    def _make_user_fuel(
        self,
        fuel_type: TypeFuel = TypeFuel.DIESEL,
        origin: FuelOrigin = FuelOrigin.FOSSIL,
        name: str = "custom_blend",
        lhv_mj_per_g: float = 0.042,
        ghg_wtt: float = 1.5,
        co2_ttw: float = 3.1,
    ) -> Fuel:
        return Fuel(
            fuel_type=fuel_type,
            origin=origin,
            fuel_specified_by=FuelSpecifiedBy.USER,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_wtt,
            ghg_emission_factor_tank_to_wake=[
                GhgEmissionFactorTankToWake(
                    co2_factor_gco2_per_gfuel=co2_ttw,
                    ch4_factor_gch4_per_gfuel=0.0,
                    n2o_factor_gn2o_per_gfuel=0.0,
                    c_slip_percent=0.0,
                    fuel_consumer_class=None,
                )
            ],
            name=name,
        )

    def _make_engine(
        self,
        fuel_type: TypeFuel = TypeFuel.DIESEL,
        fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
        rated_power: float = 1000.0,
    ) -> Engine:
        return Engine(
            type_=TypeComponent.MAIN_ENGINE,
            name="test engine",
            rated_power=Power_kW(rated_power),
            rated_speed=Speed_rpm(750.0),
            bsfc_curve=self._BSFC_CURVE,
            nox_calculation_method=NOxCalculationMethod.TIER_2,
            fuel_type=fuel_type,
            fuel_origin=fuel_origin,
        )

    # ------------------------------------------------------------------
    # Engine
    # ------------------------------------------------------------------

    def test_engine_uses_user_defined_fuel_factors(self):
        """Engine uses user-defined LHV, WTT factor and name when a matching
        user fuel is provided."""
        engine = self._make_engine()
        user_fuel = self._make_user_fuel(
            fuel_type=TypeFuel.DIESEL,
            origin=FuelOrigin.FOSSIL,
            name="my_diesel_blend",
            lhv_mj_per_g=0.042,
            ghg_wtt=1.5,
        )
        power = np.array([500.0])
        run_point = engine.get_engine_run_point_from_power_out_kw(
            power_kw=power, user_defined_fuels=[user_fuel]
        )
        fuel_out = run_point.fuel_flow_rate_kg_per_s.fuels[0]

        self.assertEqual(fuel_out.fuel_specified_by, FuelSpecifiedBy.USER)
        self.assertAlmostEqual(fuel_out.lhv_mj_per_g, 0.042)
        self.assertAlmostEqual(fuel_out.ghg_emission_factor_well_to_tank_gco2eq_per_mj, 1.5)
        self.assertEqual(fuel_out.name, "my_diesel_blend")
        # Fuel consumption mass must still be correct (unaffected by emission-factor source)
        expected_mass = run_point.bsfc_g_per_kWh * power / 3600 / 1000
        np.testing.assert_allclose(fuel_out.mass_or_mass_fraction, expected_mass)

    def test_engine_falls_back_to_imo_when_no_user_fuel_match(self):
        """Engine falls back to IMO factors when user_defined_fuels contains no
        entry for the engine's (fuel_type, origin)."""
        engine = self._make_engine(fuel_type=TypeFuel.DIESEL, fuel_origin=FuelOrigin.FOSSIL)
        # Provide a user fuel for a *different* type — should not match
        user_fuel = self._make_user_fuel(
            fuel_type=TypeFuel.NATURAL_GAS,
            origin=FuelOrigin.FOSSIL,
            name="lng_blend",
        )
        power = np.array([500.0])
        run_point = engine.get_engine_run_point_from_power_out_kw(
            power_kw=power, user_defined_fuels=[user_fuel]
        )
        fuel_out = run_point.fuel_flow_rate_kg_per_s.fuels[0]

        self.assertEqual(fuel_out.fuel_type, TypeFuel.DIESEL)
        self.assertEqual(fuel_out.fuel_specified_by, FuelSpecifiedBy.IMO)

    # ------------------------------------------------------------------
    # EngineDualFuel
    # ------------------------------------------------------------------

    def test_dual_fuel_engine_applies_user_defined_fuels_to_main_and_pilot(self):
        """When user_defined_fuels covers both main and pilot types, both
        entries in the run-point must carry user-defined factors."""
        engine = EngineDualFuel(
            type_=TypeComponent.MAIN_ENGINE,
            nox_calculation_method=NOxCalculationMethod.TIER_2,
            name="df engine",
            rated_power=Power_kW(1000.0),
            rated_speed=Speed_rpm(750.0),
            bsfc_curve=np.array([[0.1, 180.0], [1.0, 180.0]]),
            fuel_type=TypeFuel.NATURAL_GAS,
            bspfc_curve=np.array([[0.1, 10.0], [1.0, 10.0]]),
            pilot_fuel_type=TypeFuel.DIESEL,
        )
        user_lng = self._make_user_fuel(
            fuel_type=TypeFuel.NATURAL_GAS, origin=FuelOrigin.FOSSIL, name="lng_custom"
        )
        user_diesel = self._make_user_fuel(
            fuel_type=TypeFuel.DIESEL, origin=FuelOrigin.FOSSIL, name="diesel_custom"
        )
        power = np.array([500.0])
        run_point = engine.get_engine_run_point_from_power_out_kw(
            power_kw=power, user_defined_fuels=[user_lng, user_diesel]
        )
        fuels = run_point.fuel_flow_rate_kg_per_s.fuels

        specified_by_values = {f.fuel_specified_by for f in fuels}
        self.assertEqual(specified_by_values, {FuelSpecifiedBy.USER})
        fuel_names = {f.name for f in fuels}
        self.assertIn("lng_custom", fuel_names)
        self.assertIn("diesel_custom", fuel_names)

    def test_dual_fuel_engine_pilot_falls_back_when_only_main_matched(self):
        """When only the main fuel matches user_defined_fuels, the pilot fuel
        must fall back to the default IMO factors."""
        engine = EngineDualFuel(
            type_=TypeComponent.MAIN_ENGINE,
            nox_calculation_method=NOxCalculationMethod.TIER_2,
            name="df engine 2",
            rated_power=Power_kW(1000.0),
            rated_speed=Speed_rpm(750.0),
            bsfc_curve=np.array([[0.1, 180.0], [1.0, 180.0]]),
            fuel_type=TypeFuel.NATURAL_GAS,
            bspfc_curve=np.array([[0.1, 10.0], [1.0, 10.0]]),
            pilot_fuel_type=TypeFuel.DIESEL,
        )
        # Only provide LNG — no diesel entry in the list
        user_lng = self._make_user_fuel(
            fuel_type=TypeFuel.NATURAL_GAS, origin=FuelOrigin.FOSSIL, name="lng_custom"
        )
        power = np.array([500.0])
        run_point = engine.get_engine_run_point_from_power_out_kw(
            power_kw=power, user_defined_fuels=[user_lng]
        )
        fuels_by_type = {f.fuel_type: f for f in run_point.fuel_flow_rate_kg_per_s.fuels}

        self.assertEqual(fuels_by_type[TypeFuel.NATURAL_GAS].fuel_specified_by, FuelSpecifiedBy.USER)
        self.assertEqual(fuels_by_type[TypeFuel.NATURAL_GAS].name, "lng_custom")
        self.assertEqual(fuels_by_type[TypeFuel.DIESEL].fuel_specified_by, FuelSpecifiedBy.IMO)

    # ------------------------------------------------------------------
    # FuelCell
    # ------------------------------------------------------------------

    def test_fuel_cell_uses_user_defined_fuel_factors(self):
        """FuelCell.get_fuel_cell_run_point applies user-defined factors when
        a fuel with the matching (fuel_type, origin) is provided."""
        fuel_cell = FuelCell(
            name="fc_test",
            rated_power=Power_kW(200.0),
            eff_curve=np.array([[0.25, 0.50], [0.5, 0.55], [0.75, 0.57], [1.0, 0.55]]),
            fuel_type=TypeFuel.HYDROGEN,
            fuel_origin=FuelOrigin.RENEWABLE_NON_BIO,
        )
        fuel_cell.power_output = np.array([100.0])
        user_h2 = self._make_user_fuel(
            fuel_type=TypeFuel.HYDROGEN,
            origin=FuelOrigin.RENEWABLE_NON_BIO,
            name="green_h2",
            lhv_mj_per_g=0.120,
            ghg_wtt=0.1,
        )
        run_point = fuel_cell.get_fuel_cell_run_point(user_defined_fuels=[user_h2])
        fuel_out = run_point.fuel_flow_rate_kg_per_s.fuels[0]

        self.assertEqual(fuel_out.fuel_specified_by, FuelSpecifiedBy.USER)
        self.assertAlmostEqual(fuel_out.lhv_mj_per_g, 0.120)
        self.assertEqual(fuel_out.name, "green_h2")

    def test_fuel_cell_falls_back_when_no_user_fuel_match(self):
        """FuelCell falls back to IMO factors when user_defined_fuels contains
        no entry for the cell's (fuel_type, origin)."""
        fuel_cell = FuelCell(
            name="fc_test2",
            rated_power=Power_kW(200.0),
            eff_curve=np.array([[0.25, 0.50], [0.5, 0.55], [0.75, 0.57], [1.0, 0.55]]),
            fuel_type=TypeFuel.HYDROGEN,
            fuel_origin=FuelOrigin.RENEWABLE_NON_BIO,
        )
        fuel_cell.power_output = np.array([100.0])
        # Diesel user fuel — does NOT match the H2 fuel cell
        user_diesel = self._make_user_fuel(
            fuel_type=TypeFuel.DIESEL, origin=FuelOrigin.FOSSIL, name="diesel_blend"
        )
        run_point = fuel_cell.get_fuel_cell_run_point(user_defined_fuels=[user_diesel])
        fuel_out = run_point.fuel_flow_rate_kg_per_s.fuels[0]

        self.assertEqual(fuel_out.fuel_type, TypeFuel.HYDROGEN)
        self.assertEqual(fuel_out.fuel_specified_by, FuelSpecifiedBy.IMO)

    # ------------------------------------------------------------------
    # Genset
    # ------------------------------------------------------------------

    def test_genset_passes_user_defined_fuels_to_engine(self):
        """Genset.get_fuel_cons_load_bsfc_from_power_out_generator_kw passes
        user_defined_fuels down to its underlying engine so the returned
        GensetRunPoint carries user-defined emission factors."""
        engine = self._make_engine(rated_power=2700.0)
        generator = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator",
            rated_power=Power_kW(2500.0),
            rated_speed=Speed_rpm(1500.0),
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=SwbId(1),
            eff_curve=np.array([[0.25, 0.94], [0.5, 0.96], [0.75, 0.961], [1.0, 0.96]]),
        )
        genset = Genset("test genset", engine, generator)
        user_fuel = self._make_user_fuel(
            fuel_type=TypeFuel.DIESEL,
            origin=FuelOrigin.FOSSIL,
            name="special_diesel",
            lhv_mj_per_g=0.041,
            ghg_wtt=2.0,
        )
        power = np.array([1250.0])
        run_point = genset.get_fuel_cons_load_bsfc_from_power_out_generator_kw(
            power=power, user_defined_fuels=[user_fuel]
        )
        fuel_out = run_point.engine.fuel_flow_rate_kg_per_s.fuels[0]

        self.assertEqual(fuel_out.fuel_specified_by, FuelSpecifiedBy.USER)
        self.assertAlmostEqual(fuel_out.lhv_mj_per_g, 0.041)
        self.assertEqual(fuel_out.name, "special_diesel")

    # ------------------------------------------------------------------
    # get_fuel_emission_energy_balance_for_component — by-component dict
    # ------------------------------------------------------------------

    def _make_ice_user_fuel(
        self,
        name: str = "custom_diesel",
        lhv_mj_per_g: float = 0.042,
        ghg_wtt: float = 1.5,
        co2_ttw: float = 3.1,
    ) -> Fuel:
        """Create a USER-specified diesel/fossil fuel with the ICE consumer class needed
        for CO2 calculation through get_fuel_emission_energy_balance_for_component."""
        return Fuel(
            fuel_type=TypeFuel.DIESEL,
            origin=FuelOrigin.FOSSIL,
            fuel_specified_by=FuelSpecifiedBy.USER,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_wtt,
            ghg_emission_factor_tank_to_wake=[
                GhgEmissionFactorTankToWake(
                    co2_factor_gco2_per_gfuel=co2_ttw,
                    ch4_factor_gch4_per_gfuel=0.0,
                    n2o_factor_gn2o_per_gfuel=0.0,
                    c_slip_percent=0.0,
                    fuel_consumer_class=FuelConsumerClassFuelEUMaritime.ICE,
                )
            ],
            name=name,
        )

    def _make_genset(self, name: str, rated_power: float = 2700.0) -> Genset:
        engine = Engine(
            type_=TypeComponent.MAIN_ENGINE,
            name=f"{name}_engine",
            rated_power=Power_kW(rated_power),
            rated_speed=Speed_rpm(750.0),
            bsfc_curve=self._BSFC_CURVE,
            nox_calculation_method=NOxCalculationMethod.TIER_2,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        generator = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name=f"{name}_gen",
            rated_power=Power_kW(rated_power),
            rated_speed=Speed_rpm(750.0),
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=SwbId(0),
            number_poles=4,
            eff_curve=np.array([[0.25, 0.95], [0.5, 0.96], [0.75, 0.97], [1.0, 0.96]]),
        )
        return Genset(name, engine, generator)

    def test_by_component_dict_overrides_for_named_component(self):
        """user_defined_fuels_by_component applies the per-component list when the
        component name is present in the dict."""
        genset = self._make_genset("genset_a")
        genset.power_output = np.array([1000.0])
        time_interval_s = np.array([3600.0])

        per_component_fuel = self._make_user_fuel(
            fuel_type=TypeFuel.DIESEL,
            origin=FuelOrigin.FOSSIL,
            name="per_component_diesel",
            lhv_mj_per_g=0.040,
            ghg_wtt=2.0,
        )
        result = get_fuel_emission_energy_balance_for_component(
            component=genset,
            time_interval_s=time_interval_s,
            integration_method=IntegrationMethod.simpson,
            user_defined_fuels_by_component={"genset_a": [per_component_fuel]},
        )

        fuel_out = result.multi_fuel_consumption_total_kg.fuels[0]
        self.assertEqual(fuel_out.fuel_specified_by, FuelSpecifiedBy.USER)
        self.assertAlmostEqual(fuel_out.lhv_mj_per_g, 0.040)
        self.assertEqual(fuel_out.name, "per_component_diesel")
        # CO2 pipeline should work for USER fuels regardless of consumer class
        self.assertGreater(result.co2_emission_total_kg.tank_to_wake_kg_or_gco2eq_per_gfuel, 0)

    def test_by_component_dict_falls_back_to_global_for_unmatched_component(self):
        """When a component name is NOT in user_defined_fuels_by_component, the
        global user_defined_fuels list is used."""
        genset = self._make_genset("genset_b")
        genset.power_output = np.array([1000.0])
        time_interval_s = np.array([3600.0])

        global_fuel = self._make_user_fuel(
            fuel_type=TypeFuel.DIESEL,
            origin=FuelOrigin.FOSSIL,
            name="global_diesel",
            lhv_mj_per_g=0.041,
            ghg_wtt=1.2,
        )
        # per-component dict has a different component name — should not match
        result = get_fuel_emission_energy_balance_for_component(
            component=genset,
            time_interval_s=time_interval_s,
            integration_method=IntegrationMethod.simpson,
            user_defined_fuels=[global_fuel],
            user_defined_fuels_by_component={"genset_other": []},
        )

        fuel_out = result.multi_fuel_consumption_total_kg.fuels[0]
        self.assertEqual(fuel_out.fuel_specified_by, FuelSpecifiedBy.USER)
        self.assertEqual(fuel_out.name, "global_diesel")
        self.assertAlmostEqual(fuel_out.lhv_mj_per_g, 0.041)

    def test_by_component_wins_over_global_for_named_component(self):
        """When both user_defined_fuels and user_defined_fuels_by_component are
        provided, the per-component entry wins for the named component while the
        global list applies to other components."""
        genset_named = self._make_genset("genset_named")
        genset_named.power_output = np.array([800.0])
        time_interval_s = np.array([3600.0])

        global_fuel = self._make_user_fuel(
            fuel_type=TypeFuel.DIESEL,
            origin=FuelOrigin.FOSSIL,
            name="global_fuel",
            lhv_mj_per_g=0.042,
            ghg_wtt=1.0,
        )
        per_component_fuel = self._make_user_fuel(
            fuel_type=TypeFuel.DIESEL,
            origin=FuelOrigin.FOSSIL,
            name="per_component_fuel",
            lhv_mj_per_g=0.039,
            ghg_wtt=3.0,
        )

        # Named component should use per-component fuel, not global
        result_named = get_fuel_emission_energy_balance_for_component(
            component=genset_named,
            time_interval_s=time_interval_s,
            integration_method=IntegrationMethod.simpson,
            user_defined_fuels=[global_fuel],
            user_defined_fuels_by_component={"genset_named": [per_component_fuel]},
        )
        fuel_named = result_named.multi_fuel_consumption_total_kg.fuels[0]
        self.assertEqual(fuel_named.name, "per_component_fuel")
        self.assertAlmostEqual(fuel_named.lhv_mj_per_g, 0.039)

        # Un-named component uses the global list
        genset_other = self._make_genset("genset_other")
        genset_other.power_output = np.array([800.0])
        result_other = get_fuel_emission_energy_balance_for_component(
            component=genset_other,
            time_interval_s=time_interval_s,
            integration_method=IntegrationMethod.simpson,
            user_defined_fuels=[global_fuel],
            user_defined_fuels_by_component={"genset_named": [per_component_fuel]},
        )
        fuel_other = result_other.multi_fuel_consumption_total_kg.fuels[0]
        self.assertEqual(fuel_other.name, "global_fuel")
        self.assertAlmostEqual(fuel_other.lhv_mj_per_g, 0.042)
