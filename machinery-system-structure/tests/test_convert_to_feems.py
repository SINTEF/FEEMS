import os
import unittest

import MachSysS.system_structure_pb2 as proto
from feems.fuel import FuelOrigin, TypeFuel
from feems.types_for_feems import TypeComponent
from MachSysS.convert_to_feems import (
    convert_proto_propulsion_system_to_feems,
    convert_proto_switchboard_to_feems,
)
from MachSysS.convert_to_protobuf import (
    convert_electric_system_to_protobuf_machinery_system,
    convert_hybrid_propulsion_system_to_protobuf,
    convert_mechanical_propulsion_system_with_electric_system_to_protobuf,
    convert_switchboard_to_protobuf,
)
from MachSysS.utility import retrieve_machinery_system_from_file

# Adjust import for utility based on execution context
try:
    from tests.utility import create_switchboard_with_components
    from tests.utility_compare_proto import compare_proto_machinery_system
except ImportError:
    from utility import create_switchboard_with_components
    from utility_compare_proto import compare_proto_machinery_system

class TestConvertToFeems(unittest.TestCase):
    def test_switchboard_conversion(self):
        switchboard_feems = create_switchboard_with_components(
            switchboard_id=1,
            rated_power_available_total=10000,
            no_power_sources=2,
            no_power_consumer=3,
        )
        switchboard_proto = convert_switchboard_to_protobuf(switchboard_feems)
        switchboard_feems_converted = convert_proto_switchboard_to_feems(switchboard_proto)
        self.assertEqual(len(switchboard_feems.components), len(switchboard_feems_converted.components))

        # Replace one genset with a multi-fuel engine genset
        multi_fuel_engine = proto.MultiFuelEngine(
            name="Multi fuel engine",
            rated_power_kw=1000,
            rated_speed_rpm=600,
            fuel_modes=[
                proto.MultiFuelEngine.FuelMode(
                    main_fuel=proto.Fuel(
                        fuel_type=TypeFuel.VLSFO.value, fuel_origin=FuelOrigin.FOSSIL.value
                    ),
                    main_bsfc=proto.BSFC(value=180),
                    engine_cycle_type=proto.Engine.EngineCycleType.DIESEL,
                    nox_calculation_method=proto.Engine.NOxCalculationMethod.TIER_2,
                ),
                proto.MultiFuelEngine.FuelMode(
                    main_fuel=proto.Fuel(
                        fuel_type=TypeFuel.NATURAL_GAS.value,
                        fuel_origin=FuelOrigin.FOSSIL.value,
                    ),
                    pilot_fuel=proto.Fuel(
                        fuel_type=TypeFuel.DIESEL.value, fuel_origin=FuelOrigin.FOSSIL.value
                    ),
                    main_bsfc=proto.BSFC(value=200),
                    pilot_bsfc=proto.BSFC(value=4),
                    engine_cycle_type=proto.Engine.EngineCycleType.OTTO,
                    nox_calculation_method=proto.Engine.NOxCalculationMethod.TIER_3,
                ),
            ],
        )
        # find a genset and replace the engine
        for subsystem in switchboard_proto.subsystems:
            if subsystem.HasField("engine"):
                print(f"Replacing engine in subsystem {subsystem.name} with multi-fuel engine.")
                subsystem.ClearField("engine")
                subsystem.multi_fuel_engine.CopyFrom(multi_fuel_engine)
                break
        switchboard_feems_converted = convert_proto_switchboard_to_feems(switchboard_proto)
        self.assertEqual(len(switchboard_feems.components), len(switchboard_feems_converted.components))

    def test_electric_propulsion_system(self):
        # Determine path to MSS file
        current_dir = os.path.dirname(__file__)
        pathToMSSFile = os.path.join(current_dir, "electric_propulsion_system.mss")
        
        system_proto = retrieve_machinery_system_from_file(pathToMSSFile)
        system_feems = convert_proto_propulsion_system_to_feems(system_proto)
        fuel_cells = list(
            filter(
                lambda component: component.type == TypeComponent.FUEL_CELL_SYSTEM,
                system_feems.power_sources,
            )
        )
        for fuel_cell in fuel_cells:
            fuel_cell.number_modules = 3
        system_proto_reconverted = convert_electric_system_to_protobuf_machinery_system(system_feems)
        diff = compare_proto_machinery_system(system_proto, system_proto_reconverted)
        
        self.assertEqual(len(diff.diff_electric_system.switchboards_added), 0)
        self.assertEqual(len(diff.diff_electric_system.switchboards_removed), 0)
        for (
            switchboard_id,
            diff_switchboard,
        ) in diff.diff_electric_system.switchboards_modified.items():
            self.assertEqual(len(diff_switchboard.subsystems_added), 0)
            self.assertEqual(len(diff_switchboard.subsystems_removed), 0)
            for key, diff_subsystem in diff_switchboard.subsystems_modified.items():
                self.assertEqual(len(diff_subsystem.diff_attributes), 0)
                self.assertEqual(len(diff_subsystem.components_removed), 0)
                self.assertEqual(len(diff_subsystem.components_added), 0)
                for component_key, diff_component in diff_subsystem.components_modified.items():
                    self.assertEqual(len(diff_component), 0,
                        f"subcomponent {component_key} for component {key} has been modified: "
                        f"{diff_component.__str__()}"
                    )

    def test_system_with_coges(self):
        current_dir = os.path.dirname(__file__)
        pathToMSSFile = os.path.join(current_dir, "system_proto_with_coges.mss")
        
        system_proto = retrieve_machinery_system_from_file(pathToMSSFile)
        system_feems = convert_proto_propulsion_system_to_feems(system_proto)
        fuel_cells = list(
            filter(
                lambda component: component.type == TypeComponent.FUEL_CELL_SYSTEM,
                system_feems.power_sources,
            )
        )
        for fuel_cell in fuel_cells:
            fuel_cell.number_modules = 3
        system_proto_reconverted = convert_electric_system_to_protobuf_machinery_system(system_feems)
        diff = compare_proto_machinery_system(system_proto, system_proto_reconverted)
        
        self.assertEqual(len(diff.diff_electric_system.switchboards_added), 0)
        self.assertEqual(len(diff.diff_electric_system.switchboards_removed), 0)
        for (
            switchboard_id,
            diff_switchboard,
        ) in diff.diff_electric_system.switchboards_modified.items():
            self.assertEqual(len(diff_switchboard.subsystems_added), 0)
            self.assertEqual(len(diff_switchboard.subsystems_removed), 0)
            for key, diff_subsystem in diff_switchboard.subsystems_modified.items():
                self.assertEqual(len(diff_subsystem.diff_attributes), 0)
                self.assertEqual(len(diff_subsystem.components_removed), 0)
                self.assertEqual(len(diff_subsystem.components_added), 0)
                for component_key, diff_component in diff_subsystem.components_modified.items():
                    self.assertEqual(len(diff_component), 0,
                        f"subcomponent {component_key} for component {key} has been modified: "
                        f"{diff_component.__str__()}"
                    )

    def test_mechanical_propulsion_system(self):
        current_dir = os.path.dirname(__file__)
        pathToMSSFile = os.path.join(current_dir, "mechanical_propulsion_with_electric_system.mss")
        
        system_proto = retrieve_machinery_system_from_file(pathToMSSFile)
        # print(system_proto)
        system_feems = convert_proto_propulsion_system_to_feems(system_proto)
        system_proto_reconverted = convert_mechanical_propulsion_system_with_electric_system_to_protobuf(
            system_feems
        )
        diff = compare_proto_machinery_system(system_proto, system_proto_reconverted)
        # Note: writing back to file is removed for test
        
        self.assertEqual(len(diff.diff_electric_system.switchboards_added), 0)
        self.assertEqual(len(diff.diff_electric_system.switchboards_removed), 0)
        self.assertEqual(len(diff.diff_mechanical_system.shaft_lines_added), 0)
        self.assertEqual(len(diff.diff_mechanical_system.shaft_lines_removed), 0)
        
        for (
            shaft_line_id,
            diff_shaft_line,
        ) in diff.diff_mechanical_system.shaft_lines_modified.items():
            self.assertEqual(len(diff_shaft_line.subsystems_added), 0)
            self.assertEqual(len(diff_shaft_line.subsystems_removed), 0)
            for key, diff_subsystem in diff_shaft_line.subsystems_modified.items():
                self.assertEqual(len(diff_subsystem.diff_attributes), 0)
                self.assertEqual(len(diff_subsystem.components_removed), 0)
                self.assertEqual(len(diff_subsystem.components_added), 0)
                for component_key, diff_component in diff_subsystem.components_modified.items():
                    self.assertEqual(len(diff_component), 0,
                        f"subcomponent {component_key} for component {key} has been modified: "
                        f"{diff_component.__str__()}"
                    )
                    
        for (
            switchboard_id,
            diff_switchboard,
        ) in diff.diff_electric_system.switchboards_modified.items():
            self.assertEqual(len(diff_switchboard.subsystems_added), 0)
            self.assertEqual(len(diff_switchboard.subsystems_removed), 0)
            for key, diff_subsystem in diff_switchboard.subsystems_modified.items():
                self.assertEqual(len(diff_subsystem.diff_attributes), 0)
                self.assertEqual(len(diff_subsystem.components_removed), 0)
                self.assertEqual(len(diff_subsystem.components_added), 0)
                for component_key, diff_component in diff_subsystem.components_modified.items():
                    self.assertEqual(len(diff_component), 0,
                        f"subcomponent {component_key} for component {key} has been modified: "
                        f"{diff_component.__str__()}"
                    )

    def test_hybrid_propulsion_system(self):
        current_dir = os.path.dirname(__file__)
        pathToMSSFile = os.path.join(current_dir, "hybrid_propulsion_system.mss")
        system_proto = retrieve_machinery_system_from_file(pathToMSSFile)
        system_feems = convert_proto_propulsion_system_to_feems(system_proto)
        # Make sure that the pti_pto of the electric system is the same instance as the pti_pto of the mechanical system
        # Assuming electric_system is not None and has pti_pto list
        self.assertEqual(system_feems.electric_system.pti_pto[0], system_feems.mechanical_system.pti_ptos[0])
        
        system_proto_reconverted = convert_hybrid_propulsion_system_to_protobuf(system_feems)
        diff = compare_proto_machinery_system(system_proto, system_proto_reconverted)
        
        self.assertEqual(len(diff.diff_electric_system.switchboards_added), 0)
        self.assertEqual(len(diff.diff_electric_system.switchboards_removed), 0)
        self.assertEqual(len(diff.diff_mechanical_system.shaft_lines_added), 0)
        self.assertEqual(len(diff.diff_mechanical_system.shaft_lines_removed), 0)
        
        for (
            shaft_line_id,
            diff_shaft_line,
        ) in diff.diff_mechanical_system.shaft_lines_modified.items():
            self.assertEqual(len(diff_shaft_line.subsystems_added), 0)
            self.assertEqual(len(diff_shaft_line.subsystems_removed), 0)
            for key, diff_subsystem in diff_shaft_line.subsystems_modified.items():
                self.assertEqual(len(diff_subsystem.diff_attributes), 0)
                self.assertEqual(len(diff_subsystem.components_removed), 0)
                self.assertEqual(len(diff_subsystem.components_added), 0)
                for component_key, diff_component in diff_subsystem.components_modified.items():
                    self.assertEqual(len(diff_component), 0,
                        f"subcomponent {component_key} for component "
                        f"{key} has been modified: {diff_component.__str__()}"
                    )
        
        for (
            switchboard_id,
            diff_switchboard,
        ) in diff.diff_electric_system.switchboards_modified.items():
            self.assertEqual(len(diff_switchboard.subsystems_added), 0)
            self.assertEqual(len(diff_switchboard.subsystems_removed), 0)
            for key, diff_subsystem in diff_switchboard.subsystems_modified.items():
                self.assertEqual(len(diff_subsystem.diff_attributes), 0)
                self.assertEqual(len(diff_subsystem.components_removed), 0)
                self.assertEqual(len(diff_subsystem.components_added), 0)
                for component_key, diff_component in diff_subsystem.components_modified.items():
                    self.assertEqual(len(diff_component), 0,
                        f"subcomponent {component_key} for component {key} "
                        f"has been modified: {diff_component.__str__()}"
                    )

if __name__ == '__main__':
    unittest.main()
