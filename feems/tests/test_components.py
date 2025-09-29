import os
import random
from typing import List, cast
from unittest import TestCase

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

from feems.components_model.component_base import BasicComponent, SerialSystem
from feems.components_model.component_electric import (
    COGES,
    ElectricMachine,
    ElectricComponent,
    PTIPTO,
    Genset,
    SerialSystemElectric,
    FuelCell,
    FuelCellSystem,
)
from feems.components_model.component_mechanical import (
    COGAS,
    Engine,
    EngineDualFuel,
    EngineMultiFuel,
    FuelCharacteristics,
    MainEngineForMechanicalPropulsion,
    MainEngineWithGearBoxForMechanicalPropulsion,
)
from feems.components_model.node import Node
from feems.components_model.utility import (
    get_efficiency_curve_from_points,
    get_efficiency_curve_from_dataframe,
)
from feems.fuel import FuelByMassFraction, TypeFuel, Fuel, FuelSpecifiedBy, FuelOrigin
from feems.types_for_feems import EmissionType, Speed_rpm, NOxCalculationMethod, SwbId
from feems.types_for_feems import TypeNode, TypeComponent, TypePower, Power_kW
from tests.utility import (
    create_cogas_system,
    create_components,
    create_random_monotonic_eff_curve,
    create_basic_components,
    create_dataframe_save_and_return,
    create_engine_component,
    ELECTRIC_MACHINE_EFF_CURVE,
    create_electric_components_for_switchboard,
)
from feems.constant import nox_factor_imo_medium_speed_g_hWh

CONVERTER_EFF = np.array([[1.00, 0.75, 0.50, 0.25], [0.98, 0.972, 0.97, 0.96]]).transpose()


def create_multi_fuel_characteristics_sample() -> List[FuelCharacteristics]:
    return [
        FuelCharacteristics(
            main_fuel_type=TypeFuel.NATURAL_GAS,
            main_fuel_origin=FuelOrigin.FOSSIL,
            pilot_fuel_type=TypeFuel.DIESEL,
            pilot_fuel_origin=FuelOrigin.FOSSIL,
            bsfc_curve=np.array([[0.0, 180.0], [1.0, 180.0]], dtype=float),
            bpsfc_curve=np.array([[0.0, 10.0], [1.0, 10.0]], dtype=float),
        ),
        FuelCharacteristics(
            main_fuel_type=TypeFuel.DIESEL,
            main_fuel_origin=FuelOrigin.FOSSIL,
            pilot_fuel_type=None,
            pilot_fuel_origin=None,
            bsfc_curve=np.array([[0.0, 210.0], [1.0, 210.0]], dtype=float),
        ),
    ]


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
        diesel_consumption_kg_per_s = engine_run_point.bpsfc_g_per_kWh * power / 3600 / 1000
        assert np.allclose(
            engine_run_point.fuel_flow_rate_kg_per_s.fuels[1].mass_or_mass_fraction,
            diesel_consumption_kg_per_s,
        )
        print(engine_run_point)
        print(engine_run_point.fuel_flow_rate_kg_per_s.__dict__)

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
                bpsfc_curve=pilot_bsfc_dual,
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

        lng_run_point = engine.get_engine_run_point_from_power_out_kw(
            power_kw=power_kw,
            fuel_type=TypeFuel.NATURAL_GAS,
            fuel_origin=FuelOrigin.FOSSIL,
        )

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
        np.testing.assert_allclose(lng_run_point.bpsfc_g_per_kWh, expected_pilot_bsfc)
        self.assertEqual(pilot_fuel.fuel_type, TypeFuel.DIESEL)
        self.assertEqual(pilot_fuel.origin, FuelOrigin.FOSSIL)
        np.testing.assert_allclose(pilot_fuel.mass_or_mass_fraction, expected_pilot_consumption)
        np.testing.assert_allclose(
            lng_run_point.fuel_flow_rate_kg_per_s.total_fuel_consumption,
            expected_main_consumption + expected_pilot_consumption,
        )

        diesel_run_point = engine.get_engine_run_point_from_power_out_kw(
            power_kw=power_kw,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
        )

        expected_diesel_bsfc = np.full_like(expected_load, 210.0, dtype=float)
        expected_diesel_consumption = expected_diesel_bsfc * (power_kw / 3600.0) / 1000.0

        np.testing.assert_allclose(diesel_run_point.load_ratio, expected_load)
        np.testing.assert_allclose(diesel_run_point.bsfc_g_per_kWh, expected_diesel_bsfc)
        self.assertIsNone(diesel_run_point.bpsfc_g_per_kWh)
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

        default_expected = engine_for_expected.get_engine_run_point_from_power_out_kw(
            power_kw=power_kw,
            fuel_type=TypeFuel.NATURAL_GAS,
            fuel_origin=FuelOrigin.FOSSIL,
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
        diesel_expected = engine_for_expected.get_engine_run_point_from_power_out_kw(
            power_kw=power_kw,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
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
        expected = engine_for_expected.get_engine_run_point_from_power_out_kw(
            power_kw=power_kw / gearbox_eff,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
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
        expected_default = aux_engine_expected.get_engine_run_point_from_power_out_kw(
            power_kw=shaft_power_expected,
            fuel_type=TypeFuel.NATURAL_GAS,
            fuel_origin=FuelOrigin.FOSSIL,
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
        expected_diesel = aux_engine_expected.get_engine_run_point_from_power_out_kw(
            power_kw=shaft_power_expected,
            fuel_type=TypeFuel.DIESEL,
            fuel_origin=FuelOrigin.FOSSIL,
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

    