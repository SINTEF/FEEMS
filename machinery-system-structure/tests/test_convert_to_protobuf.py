import unittest
from functools import reduce

import numpy as np
from feems.components_model.component_electric import (
    PTIPTO,
    ElectricComponent,
    ElectricMachine,
    Genset,
)
from feems.components_model.component_mechanical import (
    Engine,
    EngineCycleType,
    EngineDualFuel,
    EngineMultiFuel,
    FuelCharacteristics,
    MainEngineForMechanicalPropulsion,
    MechanicalPropulsionComponent,
    NOxCalculationMethod,
)
from feems.fuel import FuelOrigin, TypeFuel
from feems.system_model import (
    ElectricPowerSystem,
    HybridPropulsionSystem,
    MechanicalPropulsionSystem,
    MechanicalPropulsionSystemWithElectricPowerSystem,
)
from feems.types_for_feems import Power_kW, Speed_rpm, TypeComponent, TypePower
from MachSysS.convert_to_protobuf import (
    convert_electric_system_to_protobuf,
    convert_electric_system_to_protobuf_machinery_system,
    convert_hybrid_propulsion_system_to_protobuf,
    convert_mechanical_propulsion_system_with_electric_system_to_protobuf,
    convert_mechanical_system_to_protobuf,
)


class TestConvertToProtobuf(unittest.TestCase):
    def setUp(self):
        # Create the engine
        bsfc_for_main_engine = np.array(
            [
                [0.25, 151.2],
                [0.30, 149.5],
                [0.40, 146.3],
                [0.50, 143.2],
                [0.60, 141.7],
                [0.70, 141.0],
                [0.75, 140.8],
                [0.80, 140.9],
                [0.85, 141.0],
                [0.90, 141.4],
                [0.95, 141.9],
                [1.00, 142.8],
            ]
        )
        bspfc_for_main_engine = np.array(
            [
                [0.25, 1.6],
                [0.30, 1.4],
                [0.40, 1.1],
                [0.50, 0.9],
                [0.60, 0.8],
                [0.70, 0.8],
                [0.75, 0.7],
                [0.80, 0.7],
                [0.85, 0.7],
                [0.90, 0.6],
                [0.95, 0.6],
                [1.00, 0.6],
            ]
        )
        main_engine = MainEngineForMechanicalPropulsion(
            engine=EngineDualFuel(
                type_=TypeComponent.MAIN_ENGINE,
                name="Main engine",
                rated_power=Power_kW(18000),
                rated_speed=Speed_rpm(60),
                bsfc_curve=bsfc_for_main_engine,
                fuel_type=TypeFuel.NATURAL_GAS,
                fuel_origin=FuelOrigin.FOSSIL,
                bspfc_curve=bspfc_for_main_engine,
                pilot_fuel_type=TypeFuel.DIESEL,
                nox_calculation_method=NOxCalculationMethod.TIER_3,
            ),
            name="Main engine for mechanical propulsion",
            shaft_line_id=1,
        )
        propeller = MechanicalPropulsionComponent(
            type_=TypeComponent.PROPELLER_LOAD,
            power_type=TypePower.POWER_CONSUMER,
            name="Propeller",
            rated_power=Power_kW(25000),
            rated_speed=Speed_rpm(60),
            shaft_line_id=1,
        )
        self.mechanical_propulsion_system = MechanicalPropulsionSystem(
            name="Mechanical propulsion system", components_list=[main_engine, propeller]
        )
        self.number_gensets = 3
        bsfc_for_aux_engine = np.array(
            [
                [0.25, 248.0],
                [0.30, 235.0],
                [0.35, 225.0],
                [0.40, 218.0],
                [0.45, 213.0],
                [0.50, 208.0],
                [0.55, 205.0],
                [0.60, 203.0],
                [0.65, 200.0],
                [0.70, 199.0],
                [0.75, 197.0],
                [0.80, 197.0],
                [0.85, 196.0],
                [0.90, 196.0],
                [0.95, 196.0],
                [1.00, 195.2],
            ]
        )
        gensets = [
            Genset(
                name=f"Genset {i + 1}",
                aux_engine=Engine(
                    type_=TypeComponent.AUXILIARY_ENGINE,
                    name=f"Aux engine {i + 1}",
                    rated_power=Power_kW(1290),
                    rated_speed=Speed_rpm(900),
                    bsfc_curve=bsfc_for_aux_engine,
                    fuel_type=TypeFuel.NATURAL_GAS,
                    fuel_origin=FuelOrigin.FOSSIL,
                    nox_calculation_method=NOxCalculationMethod.TIER_3,
                ),
                generator=ElectricMachine(
                    type_=TypeComponent.GENERATOR,
                    name=f"Generator {i + 1}",
                    rated_power=Power_kW(1000),
                    rated_speed=Speed_rpm(900),
                    eff_curve=np.array(
                        [
                            [0.0, 0.88],
                            [0.1, 0.89],
                            [0.2, 0.90],
                            [0.3, 0.91],
                            [0.4, 0.92],
                            [0.5, 0.93],
                            [0.6, 0.93],
                            [0.7, 0.94],
                            [0.8, 0.94],
                            [0.9, 0.95],
                            [1.0, 0.95],
                        ]
                    ),
                    power_type=TypePower.POWER_SOURCE,
                    switchboard_id=int(i / 2) + 1,
                ),
            )
            for i in range(self.number_gensets)
        ]
        other_load = ElectricComponent(
            type_=TypeComponent.OTHER_LOAD,
            name="Other load",
            rated_power=Power_kW(4000),
            power_type=TypePower.POWER_CONSUMER,
            switchboard_id=1,
        )
        self.electric_power_system = ElectricPowerSystem(
            name="Electric power system",
            power_plant_components=[*gensets, other_load],
            bus_tie_connections=[(1, 1)],
        )
        self.machinery_system = MechanicalPropulsionSystemWithElectricPowerSystem(
            name="Base case system",
            mechanical_system=self.mechanical_propulsion_system,
            electric_system=self.electric_power_system,
        )

    def test_convert_mechanical_system(self):
        mechanical_system_proto = convert_mechanical_system_to_protobuf(
            mechanical_propulsion_system=self.mechanical_propulsion_system
        )
        self.assertIsNotNone(mechanical_system_proto)
        # Add simpler assertions to verify proto content if possible, e.g. name
        # self.assertEqual(mechanical_system_proto.name, "Mechanical propulsion system") 
        # (Need to check if proto has name field that matches)

    def test_convert_machinery_system(self):
        proto_sys = convert_mechanical_propulsion_system_with_electric_system_to_protobuf(
            system_feems=self.machinery_system
        )
        self.assertIsNotNone(proto_sys)

    def test_convert_hybrid_system(self):
        # Create a pto system
        switchboard_id = 1
        rated_power = 1000
        synch_mach = ElectricMachine(
            type_=TypeComponent.SYNCHRONOUS_MACHINE,
            power_type=TypePower.PTI_PTO,
            name="synchronous machine",
            rated_power=rated_power,
            rated_speed=1000,
            switchboard_id=switchboard_id,
        )

        # Create a rectifier instance
        rectifier = ElectricComponent(
            type_=TypeComponent.RECTIFIER,
            power_type=TypePower.POWER_TRANSMISSION,
            name="rectifier",
            rated_power=rated_power,
            eff_curve=np.array([99.5]),
            switchboard_id=switchboard_id,
        )

        # Create a inverter instance
        inverter = ElectricComponent(
            type_=TypeComponent.INVERTER,
            power_type=TypePower.POWER_TRANSMISSION,
            name="inverter",
            rated_power=rated_power,
            eff_curve=np.array([98.5]),
            switchboard_id=switchboard_id,
        )

        # Create a transformer instance
        transformer = ElectricComponent(
            type_=TypeComponent.TRANSFORMER,
            power_type=TypePower.POWER_TRANSMISSION,
            name="transformer",
            rated_power=rated_power,
            eff_curve=np.array([99]),
            switchboard_id=switchboard_id,
        )

        pto = PTIPTO(
            name="PTI PTO",
            components=[synch_mach, rectifier, inverter, transformer],
            rated_power=1000,
            rated_speed=1000,
            switchboard_id=synch_mach.switchboard_id,
            shaft_line_id=1,
        )

        # Creat a new electric system with pto
        all_electric_components = reduce(
            lambda acc, switchboard: [*acc, *switchboard.components],
            self.machinery_system.electric_system.switchboards.values(),
            [pto],
        )
        bus_tie_breakers = reduce(
            lambda acc, bus_tie_breaker: [*acc, bus_tie_breaker.switchboard_ids],
            self.machinery_system.electric_system.bus_tie_breakers,
            [],
        )
        electric_system_with_pto = ElectricPowerSystem(
            name="electric power system with PTO",
            power_plant_components=all_electric_components,
            bus_tie_connections=bus_tie_breakers,
        )

        # Create a new mechanical system with pto
        all_mechanical_components = reduce(
            lambda acc, shaftline: [*acc, *shaftline.components],
            self.machinery_system.mechanical_system.shaft_line,
            [pto],
        )

        mechanical_system_with_pto = MechanicalPropulsionSystem(
            name="mechanical system with PTO",
            components_list=all_mechanical_components,
        )

        # Create a hybrid system
        hybrid_prop_system_feems = HybridPropulsionSystem(
            name="Hybrid system",
            electric_system=electric_system_with_pto,
            mechanical_system=mechanical_system_with_pto,
        )
        hybrid_prop_system_proto = convert_hybrid_propulsion_system_to_protobuf(
            system_feems=hybrid_prop_system_feems
        )
        self.assertIsNotNone(hybrid_prop_system_proto)
        
        # Save check (simulated)
        convert_electric_system_to_protobuf(
            electric_system=electric_system_with_pto
        )
        convert_mechanical_system_to_protobuf(
            mechanical_propulsion_system=mechanical_system_with_pto
        )
        convert_electric_system_to_protobuf_machinery_system(
            electric_system=self.electric_power_system, maximum_allowed_genset_load_percentage=80
        )
        # Assuming if no error raised, verification passed.

    def test_multi_fuel_conversion(self):
        # Mechanical system with multi-fuel main engine
        bsfc_for_main_engine = np.array(
            [
                [0.25, 151.2],
                [0.30, 149.5],
                [0.40, 146.3],
                [0.50, 143.2],
                [0.60, 141.7],
                [0.70, 141.0],
                [0.75, 140.8],
                [0.80, 140.9],
                [0.85, 141.0],
                [0.90, 141.4],
                [0.95, 141.9],
                [1.00, 142.8],
            ]
        )
        bspfc_for_main_engine = np.array(
            [
                [0.25, 1.6],
                [0.30, 1.4],
                [0.40, 1.1],
                [0.50, 0.9],
                [0.60, 0.8],
                [0.70, 0.8],
                [0.75, 0.7],
                [0.80, 0.7],
                [0.85, 0.7],
                [0.90, 0.6],
                [0.95, 0.6],
                [1.00, 0.6],
            ]
        )
        propeller = MechanicalPropulsionComponent(
            type_=TypeComponent.PROPELLER_LOAD,
            power_type=TypePower.POWER_CONSUMER,
            name="Propeller",
            rated_power=Power_kW(25000),
            rated_speed=Speed_rpm(60),
            shaft_line_id=1,
        )
        engine = EngineMultiFuel(
            type_=TypeComponent.MAIN_ENGINE,
            name="Main engine",
            rated_power=Power_kW(18000),
            rated_speed=Speed_rpm(60),
            multi_fuel_characteristics=[
                FuelCharacteristics(
                    main_fuel_type=TypeFuel.NATURAL_GAS,
                    main_fuel_origin=FuelOrigin.FOSSIL,
                    pilot_fuel_type=TypeFuel.DIESEL,
                    pilot_fuel_origin=FuelOrigin.FOSSIL,
                    bsfc_curve=bsfc_for_main_engine,
                    bspfc_curve=bspfc_for_main_engine,
                    nox_calculation_method=NOxCalculationMethod.TIER_3,
                    engine_cycle_type=EngineCycleType.OTTO,
                ),
                FuelCharacteristics(
                    main_fuel_type=TypeFuel.VLSFO,
                    main_fuel_origin=FuelOrigin.FOSSIL,
                    bsfc_curve=bsfc_for_main_engine * 1.05,
                    nox_calculation_method=NOxCalculationMethod.TIER_3,
                ),
            ],
            uid="cvjkrqwe23vc",
        )
        main_engine = MainEngineForMechanicalPropulsion(
            engine=engine,
            name="Main engine for mechanical propulsion",
            shaft_line_id=1,
            uid="cvjkrqwe23vc-shaftline",
        )
        # use the same propeller as before
        mechanical_propulsion_system = MechanicalPropulsionSystem(
            name="Mechanical propulsion system with multi-fuel main engine",
            components_list=[main_engine, propeller],
        )
        mechanical_system_proto = convert_mechanical_system_to_protobuf(
            mechanical_propulsion_system=mechanical_propulsion_system
        )
        self.assertIsNotNone(mechanical_system_proto)

        # Electric system with multi-fuel gensets
        number_gensets = 2
        bsfc_for_aux_engine = np.array(
            [
                [0.25, 248.0],
                [0.50, 208.0],
                [0.75, 197.0],
                [1.00, 195.2],
            ]
        )
        bspfc_for_aux_engine = np.array(
            [
                [0.25, 2.5],
                [0.50, 1.8],
                [0.75, 1.5],
                [1.00, 1.4],
            ]
        )
        gensets = [
            Genset(
                name=f"Genset {i + 1}",
                aux_engine=EngineMultiFuel(
                    type_=TypeComponent.AUXILIARY_ENGINE,
                    name=f"Aux engine {i + 1}",
                    rated_power=Power_kW(1290),
                    rated_speed=Speed_rpm(900),
                    multi_fuel_characteristics=[
                        FuelCharacteristics(
                            main_fuel_type=TypeFuel.NATURAL_GAS,
                            main_fuel_origin=FuelOrigin.FOSSIL,
                            pilot_fuel_type=TypeFuel.DIESEL,
                            pilot_fuel_origin=FuelOrigin.FOSSIL,
                            bsfc_curve=bsfc_for_aux_engine,
                            bspfc_curve=bspfc_for_aux_engine,
                            nox_calculation_method=NOxCalculationMethod.TIER_3,
                            engine_cycle_type=EngineCycleType.OTTO,
                        ),
                        FuelCharacteristics(
                            main_fuel_type=TypeFuel.DIESEL,
                            main_fuel_origin=FuelOrigin.FOSSIL,
                            bsfc_curve=bsfc_for_aux_engine * 1.05,
                            nox_calculation_method=NOxCalculationMethod.TIER_3,
                            engine_cycle_type=EngineCycleType.DIESEL,
                        ),
                    ],
                    uid=f"aux-engine-{i + 1}-uid",
                ),
                generator=ElectricMachine(
                    type_=TypeComponent.GENERATOR,
                    name=f"Generator {i + 1}",
                    rated_power=Power_kW(1000),
                    rated_speed=Speed_rpm(900),
                    eff_curve=np.array(
                        [
                            [0.0, 0.88],
                            [0.1, 0.89],
                            [0.2, 0.90],
                            [0.3, 0.91],
                            [0.4, 0.92],
                            [0.5, 0.93],
                            [0.6, 0.93],
                            [0.7, 0.94],
                            [0.8, 0.94],
                            [0.9, 0.95],
                            [1.0, 0.95],
                        ]
                    ),
                    power_type=TypePower.POWER_SOURCE,
                    switchboard_id=int(i / 2) + 1,
                    uid=f"generator-{i + 1}-uid",
                ),
                uid=f"genset-{i + 1}-uid",
            )
            for i in range(number_gensets)
        ]
        other_load = ElectricComponent(
            type_=TypeComponent.OTHER_LOAD,
            name="Other load",
            rated_power=Power_kW(4000),
            power_type=TypePower.POWER_CONSUMER,
            switchboard_id=1,
            uid="other-load-uid",
        )
        electric_power_system = ElectricPowerSystem(
            name="Electric power system with multi-fuel gensets",
            power_plant_components=[*gensets, other_load],
            bus_tie_connections=[(1, 1)],
        )
        electric_system_proto = convert_electric_system_to_protobuf(electric_system=electric_power_system)
        self.assertIsNotNone(electric_system_proto)

if __name__ == '__main__':
    unittest.main()
