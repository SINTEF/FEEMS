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



class TestConvertOrganicRankineCycle(unittest.TestCase):
    """Main engine ORC (switchboard_id > 0) becomes a feems power source on that switchboard."""

    def _system_with_main_engine_orc(self, switchboard_id=None):
        current_dir = os.path.dirname(__file__)
        system_proto = retrieve_machinery_system_from_file(
            os.path.join(current_dir, "mechanical_propulsion_with_electric_system.mss")
        )
        main_engine_subsystem = next(
            subsystem
            for shaft_line in system_proto.mechanical_system.shaft_lines
            for subsystem in shaft_line.subsystems
            if subsystem.HasField("engine")
        )
        orc = main_engine_subsystem.engine.orc
        orc.name = "ORC main engine"
        orc.uid = "main_engine_orc"
        orc.rated_power_kw = 300.0
        orc.switchboard_id = (
            system_proto.electric_system.switchboards[0].switchboard_id
            if switchboard_id is None
            else switchboard_id
        )
        return system_proto

    def _orc_power_sources(self, system_feems):
        return [
            component
            for component in system_feems.electric_system.power_sources
            if component.type == TypeComponent.ORGANIC_RANKINE_CYCLE
        ]

    def test_main_engine_orc_becomes_power_source(self):
        system_proto = self._system_with_main_engine_orc()
        orc_power_sources = self._orc_power_sources(convert_proto_propulsion_system_to_feems(system_proto))
        self.assertEqual(len(orc_power_sources), 1)
        self.assertEqual(orc_power_sources[0].uid, "main_engine_orc")
        self.assertEqual(orc_power_sources[0].name, "ORC main engine")
        self.assertEqual(orc_power_sources[0].rated_power, 300.0)
        self.assertEqual(
            orc_power_sources[0].switchboard_id,
            system_proto.electric_system.switchboards[0].switchboard_id,
        )

    def test_main_engine_orc_without_switchboard_raises(self):
        system_proto = self._system_with_main_engine_orc(switchboard_id=0)
        with self.assertRaisesRegex(ValueError, "switchboard_id 0"):
            convert_proto_propulsion_system_to_feems(system_proto)

    def test_main_engine_points_at_its_orc(self):
        system_feems = convert_proto_propulsion_system_to_feems(self._system_with_main_engine_orc())
        orc = self._orc_power_sources(system_feems)[0]
        engines_with_orc = [
            main_engine.engine
            for main_engine in system_feems.mechanical_system.main_engines
            if main_engine.engine.orc is not None
        ]
        self.assertEqual(len(engines_with_orc), 1)
        self.assertIs(engines_with_orc[0].orc, orc)

    def test_orc_without_rated_power_is_not_converted(self):
        system_proto = self._system_with_main_engine_orc()
        for shaft_line in system_proto.mechanical_system.shaft_lines:
            for subsystem in shaft_line.subsystems:
                if subsystem.HasField("engine"):
                    subsystem.engine.orc.rated_power_kw = 0.0
        self.assertEqual(self._orc_power_sources(convert_proto_propulsion_system_to_feems(system_proto)), [])

    def test_orc_on_unknown_switchboard_raises(self):
        system_proto = self._system_with_main_engine_orc(switchboard_id=99)
        with self.assertRaises(ValueError):
            convert_proto_propulsion_system_to_feems(system_proto)

    def test_conversion_back_to_proto_skips_orc_component(self):
        system_proto = self._system_with_main_engine_orc()
        system_feems = convert_proto_propulsion_system_to_feems(system_proto)
        system_proto_reconverted = convert_mechanical_propulsion_system_with_electric_system_to_protobuf(
            system_feems
        )
        component_types = [
            subsystem.component_type
            for switchboard in system_proto_reconverted.electric_system.switchboards
            for subsystem in switchboard.subsystems
        ]
        self.assertNotIn(TypeComponent.ORGANIC_RANKINE_CYCLE.value, component_types)

    def test_main_engine_orc_survives_round_trip(self):
        system_proto = self._system_with_main_engine_orc()
        system_proto_reconverted = convert_mechanical_propulsion_system_with_electric_system_to_protobuf(
            convert_proto_propulsion_system_to_feems(system_proto)
        )
        assert_orc_equal(self, _main_engine_orc(system_proto_reconverted), _main_engine_orc(system_proto))


def _main_engine_orc(system_proto):
    return next(
        subsystem.engine.orc
        for shaft_line in system_proto.mechanical_system.shaft_lines
        for subsystem in shaft_line.subsystems
        if subsystem.HasField("engine") and subsystem.engine.HasField("orc")
    )


def _set_orc(orc, name, uid, rated_power_kw=150.0):
    orc.name = name
    orc.uid = uid
    orc.rated_power_kw = rated_power_kw
    orc.rated_efficiency = 0.095
    orc.waste_heat_fraction = 0.3
    orc.unit_price_usd = 1350.0 * rated_power_kw
    for x, y in [(0.0, 0.0), (0.2, 0.0), (0.3, 0.8), (1.0, 1.0)]:
        orc.relative_efficiency_curve.points.add(x=x, y=y)


def assert_orc_equal(test_case, orc_after, orc_before):
    test_case.assertEqual(orc_after.name, orc_before.name)
    test_case.assertEqual(orc_after.uid, orc_before.uid)
    test_case.assertEqual(orc_after.rated_power_kw, orc_before.rated_power_kw)
    test_case.assertEqual(orc_after.rated_efficiency, orc_before.rated_efficiency)
    test_case.assertEqual(orc_after.waste_heat_fraction, orc_before.waste_heat_fraction)
    test_case.assertEqual(orc_after.unit_price_usd, orc_before.unit_price_usd)
    test_case.assertEqual(
        list(orc_after.relative_efficiency_curve.points),
        list(orc_before.relative_efficiency_curve.points),
    )


class TestConvertGensetAndFuelCellOrganicRankineCycle(unittest.TestCase):
    """Genset and fuel-cell ORCs become feems power sources on their host's switchboard."""

    def _electric_system(self):
        current_dir = os.path.dirname(__file__)
        return retrieve_machinery_system_from_file(
            os.path.join(current_dir, "electric_propulsion_system.mss")
        )

    def _first_genset(self, system_proto):
        return next(
            subsystem
            for switchboard in system_proto.electric_system.switchboards
            for subsystem in switchboard.subsystems
            if subsystem.component_type == proto.Subsystem.ComponentType.GENSET
        )

    def _system_with_genset_orc(self, switchboard_id=0):
        system_proto = self._electric_system()
        orc = self._first_genset(system_proto).engine.orc
        _set_orc(orc, "ORC genset", "genset_orc")
        orc.switchboard_id = switchboard_id
        return system_proto

    def _system_with_fuel_cell_orc(self, fuel_cells_on_one_switchboard=True):
        system_proto = self._electric_system()
        if fuel_cells_on_one_switchboard:
            for switchboard in system_proto.electric_system.switchboards[1:]:
                fuel_cells = [
                    subsystem
                    for subsystem in switchboard.subsystems
                    if subsystem.component_type == proto.Subsystem.ComponentType.FUEL_CELL_SYSTEM
                ]
                for fuel_cell in fuel_cells:
                    switchboard.subsystems.remove(fuel_cell)
        _set_orc(system_proto.fuel_cell_orc, "ORC fuel cells", "fuel_cell_orc")
        return system_proto

    def _orcs(self, system_feems):
        return [
            component
            for component in system_feems.power_sources
            if component.type == TypeComponent.ORGANIC_RANKINE_CYCLE
        ]

    def test_genset_orc_on_genset_switchboard(self):
        system_feems = convert_proto_propulsion_system_to_feems(self._system_with_genset_orc())
        orcs = self._orcs(system_feems)
        gensets_with_orc = [
            component
            for component in system_feems.power_sources
            if component.type == TypeComponent.GENSET and component.aux_engine.orc is not None
        ]
        self.assertEqual(len(orcs), 1)
        self.assertEqual(len(gensets_with_orc), 1)
        self.assertIs(gensets_with_orc[0].aux_engine.orc, orcs[0])
        self.assertEqual(orcs[0].switchboard_id, gensets_with_orc[0].switchboard_id)
        self.assertEqual(orcs[0].rated_efficiency, 0.095)
        self.assertEqual(orcs[0].relative_efficiency_curve.shape, (4, 2))

    def test_genset_orc_with_its_own_switchboard_id_is_accepted(self):
        system_proto = self._system_with_genset_orc(switchboard_id=1)
        self.assertEqual(len(self._orcs(convert_proto_propulsion_system_to_feems(system_proto))), 1)

    def test_genset_orc_on_other_switchboard_raises(self):
        with self.assertRaisesRegex(ValueError, "feeds its host's switchboard"):
            convert_proto_propulsion_system_to_feems(self._system_with_genset_orc(switchboard_id=2))

    def test_genset_orc_survives_round_trip(self):
        system_proto = self._system_with_genset_orc()
        system_proto_reconverted = convert_electric_system_to_protobuf_machinery_system(
            convert_proto_propulsion_system_to_feems(system_proto)
        )
        orc_after = self._first_genset(system_proto_reconverted).engine.orc
        assert_orc_equal(self, orc_after, self._first_genset(system_proto).engine.orc)
        self.assertEqual(orc_after.switchboard_id, 1)

    def test_fuel_cell_orc_on_fuel_cell_switchboard(self):
        system_feems = convert_proto_propulsion_system_to_feems(self._system_with_fuel_cell_orc())
        orcs = self._orcs(system_feems)
        self.assertEqual(len(orcs), 1)
        self.assertIs(system_feems.fuel_cell_orc, orcs[0])
        self.assertEqual(orcs[0].switchboard_id, 1)

    def test_fuel_cell_orc_with_fuel_cells_on_two_switchboards_raises(self):
        system_proto = self._system_with_fuel_cell_orc(fuel_cells_on_one_switchboard=False)
        with self.assertRaisesRegex(ValueError, "all fuel cells on one switchboard"):
            convert_proto_propulsion_system_to_feems(system_proto)

    def test_fuel_cell_orc_survives_round_trip(self):
        system_proto = self._system_with_fuel_cell_orc()
        system_proto_reconverted = convert_electric_system_to_protobuf_machinery_system(
            convert_proto_propulsion_system_to_feems(system_proto)
        )
        self.assertTrue(system_proto_reconverted.HasField("fuel_cell_orc"))
        assert_orc_equal(self, system_proto_reconverted.fuel_cell_orc, system_proto.fuel_cell_orc)


if __name__ == '__main__':
    unittest.main()
