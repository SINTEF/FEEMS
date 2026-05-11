import os
import sys
import unittest

# Ensure modules are importable
sys.path.append(os.getcwd())

from feems.fuel import FuelOrigin, TypeFuel
from MachSysS import system_structure_pb2 as proto
from MachSysS.convert_to_feems import convert_proto_propulsion_system_to_feems


class TestAvailableFuelOptionsProto(unittest.TestCase):
    def test_proto_conversion_fuels(self):
        proto_path = "/Users/keviny/Dev/FEEMS/feems/tests/test_system_mechanical_propulsion.pb"
        if not os.path.exists(proto_path):
            self.skipTest(f"Proto file not found at {proto_path}")

        # Load protobuf
        with open(proto_path, "rb") as f:
            proto_system = proto.MachinerySystem()
            proto_system.ParseFromString(f.read())

        # Convert to FEEMS
        feems_system = convert_proto_propulsion_system_to_feems(proto_system)

        # Check fuel options
        options = feems_system.available_fuel_options_by_converter

        # Helper to find option in list
        def find_option(opt_list, fuel_type, for_pilot, primary):
            for opt in opt_list:
                if (
                    opt.fuel_type == fuel_type
                    and opt.for_pilot == for_pilot
                    and opt.primary == primary
                ):
                    return opt
            return None

        # Custom check for Main Engine (VLSFO only)
        def check_main_engine(engine_options):
            lng = find_option(engine_options, TypeFuel.NATURAL_GAS, for_pilot=False, primary=True)
            self.assertIsNotNone(
                lng, f"Main Engine: LNG primary main fuel not found. Options: {engine_options}"
            )
            self.assertEqual(lng.fuel_origin, FuelOrigin.FOSSIL)

            # Diesel Pilot
            diesel = find_option(engine_options, TypeFuel.DIESEL, for_pilot=True, primary=True)
            self.assertIsNotNone(
                diesel, f"Genset: Diesel primary pilot fuel not found. Options: {engine_options}"
            )

            # VLSFO backup (primary=False)
            vlsfo = find_option(engine_options, TypeFuel.VLSFO, for_pilot=False, primary=False)
            self.assertIsNotNone(
                vlsfo, f"Genset: VLSFO backup fuel not found. Options: {engine_options}"
            )

        # Custom check for Genset (LNG/Diesel Dual Fuel + VLSFO backup?)
        # Based on error: [FuelOption(DIESEL, for_pilot=True, primary=True),
        # FuelOption(NATURAL_GAS, for_pilot=False, primary=True),
        # FuelOption(VLSFO, for_pilot=False, primary=False)]
        def check_genset(engine_options):
            # LNG primary
            lng = find_option(engine_options, TypeFuel.NATURAL_GAS, for_pilot=False, primary=True)
            self.assertIsNotNone(
                lng, f"Genset: LNG primary main fuel not found. Options: {engine_options}"
            )

            # Diesel Pilot
            diesel = find_option(engine_options, TypeFuel.DIESEL, for_pilot=True, primary=True)
            self.assertIsNotNone(
                diesel, f"Genset: Diesel primary pilot fuel not found. Options: {engine_options}"
            )

            # VLSFO backup (primary=False)
            vlsfo = find_option(engine_options, TypeFuel.VLSFO, for_pilot=False, primary=False)
            self.assertIsNotNone(
                vlsfo, f"Genset: VLSFO backup fuel not found. Options: {engine_options}"
            )

        if "main_engine" in options:
            check_main_engine(options["main_engine"])

        if "genset" in options:
            check_genset(options["genset"])


if __name__ == "__main__":
    unittest.main()
