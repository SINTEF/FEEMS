import os
import random
import unittest

import MachSysS.system_structure_pb2 as sys_structure_pb2
import numpy as np
from feems.fuel import FuelSpecifiedBy
from feems.types_for_feems import TypePower
from MachSysS.convert_feems_result_to_proto import FEEMSResultConverter
from MachSysS.convert_to_feems import convert_proto_propulsion_system_to_feems
from MachSysS.gymir_result_pb2 import GymirResult, SimulationInstance, TimeSeriesResult
from MachSysS.system_structure_pb2 import MachinerySystem
from MachSysS.utility import retrieve_machinery_system_from_file

# Check if RunFeemsSim is available
try:
    from RunFeemsSim.machinery_calculation import MachineryCalculation
except ImportError:
    MachineryCalculation = None

class TestConvertFEEMSResultToProto(unittest.TestCase):
    def setUp(self):
        if MachineryCalculation is None:
            self.skipTest("RunFeemsSim not available")
            
        self.test_dir = os.path.dirname(__file__)
        self.system_proto_path = os.path.join(self.test_dir, "system_proto.mss")
        
        # Load system_proto
        with open(self.system_proto_path, "rb") as file:
            self.system_proto = MachinerySystem()
            self.system_proto.ParseFromString(file.read())

    def create_gymir_result(self) -> GymirResult:
        return GymirResult(
            name="test",
            auxiliary_load_kw=500 * random.random(),
            result=[
                SimulationInstance(epoch_s=100 * index + 1, power_kw=1000 * random.random())
                for index, _ in enumerate(range(10))
            ],
        )

    def test_fuel_specification_conversion(self):
        for each_fuel_specification in FuelSpecifiedBy:
            if each_fuel_specification in [FuelSpecifiedBy.NONE, FuelSpecifiedBy.USER]:
                continue
            # print("Testing fuel specification: ", each_fuel_specification)
            
            system_feems = convert_proto_propulsion_system_to_feems(self.system_proto)
            machinery_calculation = MachineryCalculation(
                feems_system=system_feems, maximum_allowed_power_source_load_percentage=80
            )
            gymir_result = self.create_gymir_result()
            res = machinery_calculation.calculate_machinery_system_output_from_gymir_result(
                gymir_result=gymir_result,
                fuel_specified_by=each_fuel_specification,
            )
            # print(res)
            feems_result_converter = FEEMSResultConverter(
                feems_result=res, system_feems=machinery_calculation.system_feems
            )
            number_sources = len(system_feems.power_sources)
            number_batteries = len(system_feems.energy_storage)
            feems_result_proto = feems_result_converter.get_feems_result_proto(
                include_time_series_for_components=True
            )
            self.assertEqual(number_sources + number_batteries, len(
                feems_result_converter._time_series_data_for_electric_component
            ))
            
            number_points = len(system_feems.power_sources[0].power_output)
            for each_time_series, component in zip(
                feems_result_converter._time_series_data_for_electric_component,
                system_feems.power_sources + system_feems.energy_storage,
            ):
                self.assertEqual(each_time_series.get("name"), component.name)
                self.assertEqual(len(each_time_series.get("data").time), number_points)
                self.assertTrue(np.all(np.diff(each_time_series.get("data").time) > 0))
                self.assertEqual(len(each_time_series.get("data").power_output_kw), number_points)
                if component.power_type == TypePower.POWER_SOURCE:
                    fuel_consumption = each_time_series.get("data").fuel_consumption_kg_per_s
                    for fuel in fuel_consumption.fuels:
                        self.assertEqual(len(fuel.mass_or_mass_fraction), number_points)
            
            self.assertIsNotNone(feems_result_proto)
            
            feems_result_proto_no_ts = feems_result_converter.get_feems_result_proto(
                include_time_series_for_components=False
            )
            self.assertIsNotNone(feems_result_proto_no_ts)

    def test_no_ice_case(self):
        # Test for the case of no ICE in the system
        path = os.path.join(self.test_dir, "electric_propulsion_system.mss")
        system_proto = retrieve_machinery_system_from_file(path)
        system_proto_copy = sys_structure_pb2.MachinerySystem()
        system_proto_copy.CopyFrom(system_proto)
        
        # Remove genset from the system
        for switchboard_idx, switchboard in enumerate(system_proto.electric_system.switchboards):
            for subsystem in switchboard.subsystems:
                if subsystem.component_type == sys_structure_pb2.Subsystem.ComponentType.GENSET:
                    # print(f"removing genset: {subsystem.name}")
                    system_proto_copy.electric_system.switchboards[switchboard_idx].subsystems.remove(
                        subsystem
                    )
        
        system_feems = convert_proto_propulsion_system_to_feems(system_proto_copy)
        
        # Import the time series data
        path = os.path.join(self.test_dir, "time_series_result.pb")
        time_series_pb = TimeSeriesResult()
        with open(path, "rb") as file:
            time_series_pb.ParseFromString(file.read())

        # Create a machinery calculation object
        machinery_calculation = MachineryCalculation(
            feems_system=system_feems, maximum_allowed_power_source_load_percentage=80
        )
        res = machinery_calculation.calculate_machinery_system_output_from_time_series_result(
            time_series=time_series_pb,
        )
        res_converter = FEEMSResultConverter(
            feems_result=res, system_feems=system_feems, time_series_input=time_series_pb
        )
        res_proto = res_converter.get_feems_result_proto()
        self.assertIsNotNone(res_proto)

class TestConvertCOGESResultToProto(unittest.TestCase):
    """COGES branch in FEEMSResultConverter: build a minimal EPS with a single COGES,
    run the energy-balance calculation, and round-trip through get_feems_result_proto."""

    def _build_eps_with_coges(self):
        from feems.components_model.component_electric import COGES, ElectricMachine
        from feems.components_model.component_mechanical import COGAS
        from feems.components_model.utility import IntegrationMethod
        from feems.fuel import FuelOrigin, TypeFuel
        from feems.system_model import ElectricPowerSystem
        from feems.types_for_feems import TypeComponent, TypePower

        cogas = COGAS(
            name="COGAS",
            rated_power=5000.0,
            rated_speed=3600.0,
            eff_curve=np.array([[0.1, 0.30], [0.5, 0.40], [1.0, 0.42]]),
            fuel_type=TypeFuel.NATURAL_GAS,
            fuel_origin=FuelOrigin.FOSSIL,
        )
        generator = ElectricMachine(
            type_=TypeComponent.SYNCHRONOUS_MACHINE,
            name="generator",
            rated_power=cogas.rated_power * 0.9,
            rated_speed=cogas.rated_speed,
            power_type=TypePower.POWER_SOURCE,
            eff_curve=np.array([[0.1, 0.97], [1.0, 0.97]]),
            switchboard_id=1,
        )
        coges = COGES(name="COGES", cogas=cogas, generator=generator)
        coges.power_output = np.array([2000.0, 3000.0])

        system = ElectricPowerSystem(
            name="test EPS with COGES",
            power_plant_components=[coges],
            bus_tie_connections=[],
        )
        system.set_time_interval(
            time_interval_s=np.array([3600.0, 3600.0]),
            integration_method=IntegrationMethod.sum_with_time,
        )
        return system, coges

    def test_coges_time_series_has_fuel_consumption(self):
        """The new COGES branch should populate fuel_consumption_kg_per_s.fuels in the
        per-component time-series proto (regression for missing TypeComponent.COGES handling)."""
        system, coges = self._build_eps_with_coges()
        res = system.get_fuel_energy_consumption_running_time(
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )

        converter = FEEMSResultConverter(
            feems_result=res,
            system_feems=system,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        proto_result = converter.get_feems_result_proto(include_time_series_for_components=True)

        self.assertIsNotNone(proto_result)
        # The converter must have recorded a time-series entry for the COGES power source.
        ts_entries = converter._time_series_data_for_electric_component
        self.assertEqual(len(ts_entries), 1)
        coges_entry = ts_entries[0]
        self.assertEqual(coges_entry["name"], coges.name)
        self.assertEqual(coges_entry["node_id"], coges.switchboard_id)

        # Fuel consumption array must be populated by the new branch.
        fuels = coges_entry["data"].fuel_consumption_kg_per_s.fuels
        self.assertGreater(len(fuels), 0, "COGES fuel array is empty — branch did not run")
        for fuel in fuels:
            self.assertEqual(len(fuel.mass_or_mass_fraction), len(coges.power_output))
            self.assertTrue(
                np.all(np.asarray(fuel.mass_or_mass_fraction) > 0),
                "COGES fuel flow must be strictly positive at non-zero power output",
            )

    def test_coges_detail_result_joined_to_time_series(self):
        """detail_result row for the COGES must be matched on (name, switchboard_id)
        so that result_time_series is attached on the per-component proto."""
        system, coges = self._build_eps_with_coges()
        res = system.get_fuel_energy_consumption_running_time(
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )

        converter = FEEMSResultConverter(
            feems_result=res,
            system_feems=system,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
        proto_result = converter.get_feems_result_proto(include_time_series_for_components=True)

        detailed = list(proto_result.electric_system.detailed_result)
        coges_rows = [row for row in detailed if row.component_name == coges.name]
        self.assertEqual(len(coges_rows), 1)
        coges_row = coges_rows[0]
        # The join at convert_feems_result_to_proto.py should have populated result_time_series.
        self.assertGreater(
            len(coges_row.result_time_series.power_output_kw),
            0,
            "COGES detail row has no joined time-series — (name, switchboard_id) mismatch",
        )
        self.assertEqual(
            len(coges_row.result_time_series.power_output_kw),
            len(coges.power_output),
        )


if __name__ == '__main__':
    unittest.main()
