# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: system_structure.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x16system_structure.proto\x12\x18machinerySystemStructure"\x1d\n\x05Point\x12\t\n\x01x\x18\x01 \x01(\x01\x12\t\n\x01y\x18\x02 \x01(\x01":\n\x07\x43urve1D\x12/\n\x06points\x18\x01 \x03(\x0b\x32\x1f.machinerySystemStructure.Point"_\n\tBSFCCurve\x12\x0f\n\x07x_label\x18\x01 \x01(\t\x12\x0f\n\x07y_label\x18\x02 \x01(\t\x12\x30\n\x05\x63urve\x18\x03 \x01(\x0b\x32!.machinerySystemStructure.Curve1D"e\n\x0f\x45\x66\x66iciencyCurve\x12\x0f\n\x07x_label\x18\x01 \x01(\t\x12\x0f\n\x07y_label\x18\x02 \x01(\t\x12\x30\n\x05\x63urve\x18\x03 \x01(\x0b\x32!.machinerySystemStructure.Curve1D"X\n\x04\x42SFC\x12\x32\n\x05\x63urve\x18\x01 \x01(\x0b\x32#.machinerySystemStructure.BSFCCurve\x12\x12\n\x05value\x18\x02 \x01(\x01H\x00\x88\x01\x01\x42\x08\n\x06_value"s\n\nEfficiency\x12=\n\x05\x63urve\x18\x01 \x01(\x0b\x32).machinerySystemStructure.EfficiencyCurveH\x00\x88\x01\x01\x12\x12\n\x05value\x18\x02 \x01(\x01H\x01\x88\x01\x01\x42\x08\n\x06_curveB\x08\n\x06_value"`\n\nPowerCurve\x12\x0f\n\x07x_label\x18\x01 \x01(\t\x12\x0f\n\x07y_label\x18\x02 \x01(\t\x12\x30\n\x05\x63urve\x18\x03 \x01(\x0b\x32!.machinerySystemStructure.Curve1D"\x85\x01\n\x19PropulsionPowerTimeSeries\x12\x0f\n\x07x_label\x18\x01 \x01(\t\x12\x0f\n\x07y_label\x18\x02 \x01(\t\x12\x14\n\x0cpropulsor_id\x18\x03 \x01(\r\x12\x30\n\x05\x63urve\x18\x04 \x01(\x0b\x32!.machinerySystemStructure.Curve1D"\x85\x01\n\x17\x41uxiliaryLoadTimeSeries\x12\x0f\n\x07x_label\x18\x01 \x01(\t\x12\x0f\n\x07y_label\x18\x02 \x01(\t\x12\x16\n\x0eswitchboard_id\x18\x03 \x01(\r\x12\x30\n\x05\x63urve\x18\x04 \x01(\x0b\x32!.machinerySystemStructure.Curve1D"8\n\rAuxiliaryLoad\x12\x16\n\x0eswitchboard_id\x18\x01 \x01(\r\x12\x0f\n\x07load_kw\x18\x02 \x01(\x01"\xa2\x01\n\rEmissionCurve\x12\x0f\n\x07x_label\x18\x01 \x01(\t\x12\x0f\n\x07y_label\x18\x02 \x01(\t\x12\x30\n\x05\x63urve\x18\x03 \x01(\x0b\x32!.machinerySystemStructure.Curve1D\x12=\n\remission_type\x18\x04 \x01(\x0e\x32&.machinerySystemStructure.EmissionType"\xe5\x01\n\x04Gear\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x12\n\ngear_ratio\x18\x02 \x01(\x01\x12\x16\n\x0erated_power_kw\x18\x03 \x01(\x01\x12\x17\n\x0frated_speed_rpm\x18\x04 \x01(\x01\x12\x38\n\nefficiency\x18\x05 \x01(\x0b\x32$.machinerySystemStructure.Efficiency\x12+\n#order_from_switchboard_or_shaftline\x18\x06 \x01(\r\x12\x16\n\x0eunit_price_usd\x18\x07 \x01(\x01\x12\x0b\n\x03uid\x18\x08 \x01(\t"x\n\x04\x46uel\x12\x35\n\tfuel_type\x18\x01 \x01(\x0e\x32".machinerySystemStructure.FuelType\x12\x39\n\x0b\x66uel_origin\x18\x02 \x01(\x0e\x32$.machinerySystemStructure.FuelOrigin"\x92\x06\n\x06\x45ngine\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x16\n\x0erated_power_kw\x18\x02 \x01(\x01\x12\x17\n\x0frated_speed_rpm\x18\x03 \x01(\x01\x12,\n\x04\x62sfc\x18\x04 \x01(\x0b\x32\x1e.machinerySystemStructure.BSFC\x12\x31\n\tmain_fuel\x18\x05 \x01(\x0b\x32\x1e.machinerySystemStructure.Fuel\x12+\n#order_from_switchboard_or_shaftline\x18\x06 \x01(\r\x12\x32\n\npilot_bsfc\x18\x07 \x01(\x0b\x32\x1e.machinerySystemStructure.BSFC\x12\x32\n\npilot_fuel\x18\x08 \x01(\x0b\x32\x1e.machinerySystemStructure.Fuel\x12U\n\x16nox_calculation_method\x18\t \x01(\x0e\x32\x35.machinerySystemStructure.Engine.NOxCalculationMethod\x12@\n\x0f\x65mission_curves\x18\n \x03(\x0b\x32\'.machinerySystemStructure.EmissionCurve\x12K\n\x11\x65ngine_cycle_type\x18\x0b \x01(\x0e\x32\x30.machinerySystemStructure.Engine.EngineCycleType\x12\x16\n\x0eunit_price_usd\x18\x0c \x01(\x01\x12\x15\n\rstart_delay_s\x18\r \x01(\x01\x12\x19\n\x11turn_off_power_kw\x18\x0e \x01(\x01\x12\x0b\n\x03uid\x18\x0f \x01(\t"E\n\x14NOxCalculationMethod\x12\n\n\x06TIER_2\x10\x00\x12\n\n\x06TIER_1\x10\x01\x12\n\n\x06TIER_3\x10\x02\x12\t\n\x05\x43URVE\x10\x03"O\n\x0f\x45ngineCycleType\x12\x08\n\x04NONE\x10\x00\x12\n\n\x06\x44IESEL\x10\x01\x12\x08\n\x04OTTO\x10\x02\x12\x1c\n\x18LEAN_BURN_SPARK_IGNITION\x10\x03"\xdb\x04\n\x05\x43OGAS\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x16\n\x0erated_power_kw\x18\x02 \x01(\x01\x12\x17\n\x0frated_speed_rpm\x18\x03 \x01(\x01\x12\x38\n\nefficiency\x18\x04 \x01(\x0b\x32$.machinerySystemStructure.Efficiency\x12\x45\n\x17gas_turbine_power_curve\x18\x05 \x01(\x0b\x32$.machinerySystemStructure.PowerCurve\x12G\n\x19steam_turbine_power_curve\x18\x06 \x01(\x0b\x32$.machinerySystemStructure.PowerCurve\x12,\n\x04\x66uel\x18\x07 \x01(\x0b\x32\x1e.machinerySystemStructure.Fuel\x12+\n#order_from_switchboard_or_shaftline\x18\x08 \x01(\r\x12U\n\x16nox_calculation_method\x18\t \x01(\x0e\x32\x35.machinerySystemStructure.Engine.NOxCalculationMethod\x12@\n\x0f\x65mission_curves\x18\n \x03(\x0b\x32\'.machinerySystemStructure.EmissionCurve\x12\x16\n\x0eunit_price_usd\x18\x0b \x01(\x01\x12\x15\n\rstart_delay_s\x18\x0c \x01(\x01\x12\x19\n\x11turn_off_power_kw\x18\r \x01(\x01\x12\x0b\n\x03uid\x18\x0e \x01(\t"\xdc\x01\n\x0f\x45lectricMachine\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x16\n\x0erated_power_kw\x18\x02 \x01(\x01\x12\x17\n\x0frated_speed_rpm\x18\x03 \x01(\x01\x12\x38\n\nefficiency\x18\x04 \x01(\x0b\x32$.machinerySystemStructure.Efficiency\x12+\n#order_from_switchboard_or_shaftline\x18\x05 \x01(\r\x12\x16\n\x0eunit_price_usd\x18\x06 \x01(\x01\x12\x0b\n\x03uid\x18\x07 \x01(\t"\x8f\x03\n\x07\x42\x61ttery\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x1b\n\x13\x65nergy_capacity_kwh\x18\x02 \x01(\x01\x12\x1d\n\x15rated_charging_rate_c\x18\x03 \x01(\x01\x12 \n\x18rated_discharging_rate_c\x18\x04 \x01(\x01\x12\x1b\n\x13\x65\x66\x66iciency_charging\x18\x05 \x01(\x01\x12\x1e\n\x16\x65\x66\x66iciency_discharging\x18\x06 \x01(\x01\x12\x1f\n\x17initial_state_of_charge\x18\x07 \x01(\x01\x12+\n#order_from_switchboard_or_shaftline\x18\x08 \x01(\r\x12\x16\n\x0eunit_price_usd\x18\t \x01(\x01\x12&\n\x1eself_discharge_percent_per_day\x18\n \x01(\x01\x12\x1f\n\x17state_of_energy_minimum\x18\x0b \x01(\x01\x12\x1f\n\x17state_of_energy_maximum\x18\x0c \x01(\x01\x12\x0b\n\x03uid\x18\r \x01(\t"\xc5\x01\n\x11\x45lectricComponent\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x16\n\x0erated_power_kw\x18\x02 \x01(\x01\x12\x38\n\nefficiency\x18\x03 \x01(\x0b\x32$.machinerySystemStructure.Efficiency\x12+\n#order_from_switchboard_or_shaftline\x18\x04 \x01(\r\x12\x16\n\x0eunit_price_usd\x18\x05 \x01(\x01\x12\x0b\n\x03uid\x18\x06 \x01(\t"\xb9\x02\n\x08\x46uelCell\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x16\n\x0erated_power_kw\x18\x02 \x01(\x01\x12\x38\n\nefficiency\x18\x03 \x01(\x0b\x32$.machinerySystemStructure.Efficiency\x12+\n#order_from_switchboard_or_shaftline\x18\x05 \x01(\r\x12,\n\x04\x66uel\x18\x06 \x01(\x0b\x32\x1e.machinerySystemStructure.Fuel\x12\x16\n\x0eunit_price_usd\x18\x07 \x01(\x01\x12\x16\n\x0enumber_modules\x18\x08 \x01(\r\x12\x1e\n\x16power_minimum_specific\x18\t \x01(\x01\x12\x15\n\rstart_delay_s\x18\n \x01(\x01\x12\x0b\n\x03uid\x18\x0b \x01(\t"\xa3\x01\n\tPropeller\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x38\n\nefficiency\x18\x02 \x01(\x0b\x32$.machinerySystemStructure.Efficiency\x12\x14\n\x0cpropulsor_id\x18\x03 \x01(\r\x12+\n#order_from_switchboard_or_shaftline\x18\x05 \x01(\r\x12\x0b\n\x03uid\x18\x06 \x01(\t"$\n\nBusBreaker\x12\x16\n\x0eswitchboard_to\x18\x01 \x01(\x05"\x82\x02\n\x0eSuperCapacitor\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x1a\n\x12\x65nergy_capacity_wh\x18\x02 \x01(\x01\x12\x16\n\x0erated_power_kw\x18\x03 \x01(\x01\x12\x1b\n\x13\x65\x66\x66iciency_charging\x18\x04 \x01(\x01\x12\x1e\n\x16\x65\x66\x66iciency_discharging\x18\x05 \x01(\x01\x12\x1f\n\x17initial_state_of_charge\x18\x06 \x01(\x01\x12+\n#order_from_switchboard_or_shaftline\x18\x07 \x01(\r\x12\x16\n\x0eunit_price_usd\x18\x08 \x01(\x01\x12\x0b\n\x03uid\x18\t \x01(\t"\xc7\x01\n\x13MechanicalComponent\x12\x0c\n\x04name\x18\x01 \x01(\t\x12\x16\n\x0erated_power_kw\x18\x02 \x01(\x01\x12\x38\n\nefficiency\x18\x03 \x01(\x0b\x32$.machinerySystemStructure.Efficiency\x12+\n#order_from_switchboard_or_shaftline\x18\x04 \x01(\r\x12\x16\n\x0eunit_price_usd\x18\x05 \x01(\x01\x12\x0b\n\x03uid\x18\x06 \x01(\t"\x8d\x0e\n\tSubsystem\x12,\n\x04gear\x18\x01 \x01(\x0b\x32\x1e.machinerySystemStructure.Gear\x12\x30\n\x06\x65ngine\x18\x02 \x01(\x0b\x32 .machinerySystemStructure.Engine\x12\x43\n\x10\x65lectric_machine\x18\x03 \x01(\x0b\x32).machinerySystemStructure.ElectricMachine\x12@\n\x0btransformer\x18\x04 \x01(\x0b\x32+.machinerySystemStructure.ElectricComponent\x12?\n\nconverter1\x18\x05 \x01(\x0b\x32+.machinerySystemStructure.ElectricComponent\x12?\n\nconverter2\x18\x06 \x01(\x0b\x32+.machinerySystemStructure.ElectricComponent\x12\x32\n\x07\x62\x61ttery\x18\x07 \x01(\x0b\x32!.machinerySystemStructure.Battery\x12\x35\n\tfuel_cell\x18\x08 \x01(\x0b\x32".machinerySystemStructure.FuelCell\x12\x36\n\tpropeller\x18\t \x01(\x0b\x32#.machinerySystemStructure.Propeller\x12\x39\n\x0b\x62us_breaker\x18\n \x01(\x0b\x32$.machinerySystemStructure.BusBreaker\x12@\n\x0esupercapacitor\x18\x0b \x01(\x0b\x32(.machinerySystemStructure.SuperCapacitor\x12?\n\nother_load\x18\x0c \x01(\x0b\x32+.machinerySystemStructure.ElectricComponent\x12.\n\x05\x63ogas\x18\r \x01(\x0b\x32\x1f.machinerySystemStructure.COGAS\x12\x41\n\npower_type\x18\x0e \x01(\x0e\x32-.machinerySystemStructure.Subsystem.PowerType\x12I\n\x0e\x63omponent_type\x18\x0f \x01(\x0e\x32\x31.machinerySystemStructure.Subsystem.ComponentType\x12\x0c\n\x04name\x18\x10 \x01(\t\x12\x16\n\x0erated_power_kw\x18\x11 \x01(\x01\x12\x17\n\x0frated_speed_rpm\x18\x12 \x01(\x01\x12-\n%ramp_up_rate_limit_percent_per_second\x18\x13 \x01(\x01\x12/\n\'ramp_down_rate_limit_percent_per_second\x18\x14 \x01(\x01\x12\x17\n\x0f\x62\x61se_load_order\x18\x15 \x01(\r\x12\x0b\n\x03uid\x18\x16 \x01(\t"s\n\tPowerType\x12\t\n\x05NONE1\x10\x00\x12\x10\n\x0cPOWER_SOURCE\x10\x01\x12\x12\n\x0ePOWER_CONSUMER\x10\x02\x12\x0b\n\x07PTI_PTO\x10\x03\x12\x12\n\x0e\x45NERGY_STORAGE\x10\x04\x12\x14\n\x10SHORE_CONNECTION\x10\x05"\xbd\x04\n\rComponentType\x12\x08\n\x04NONE\x10\x00\x12\x0f\n\x0bMAIN_ENGINE\x10\x01\x12\x14\n\x10\x41UXILIARY_ENGINE\x10\x02\x12\r\n\tGENERATOR\x10\x03\x12\x14\n\x10PROPULSION_DRIVE\x10\x04\x12\x0e\n\nOTHER_LOAD\x10\x05\x12\x12\n\x0ePTI_PTO_SYSTEM\x10\x06\x12\x12\n\x0e\x42\x41TTERY_SYSTEM\x10\x07\x12\x14\n\x10\x46UEL_CELL_SYSTEM\x10\x08\x12\r\n\tRECTIFIER\x10\t\x12\x1c\n\x18MAIN_ENGINE_WITH_GEARBOX\x10\n\x12\x12\n\x0e\x45LECTRIC_MOTOR\x10\x0b\x12\n\n\x06GENSET\x10\x0c\x12\x0f\n\x0bTRANSFORMER\x10\r\x12\x0c\n\x08INVERTER\x10\x0e\x12\x13\n\x0f\x43IRCUIT_BREAKER\x10\x0f\x12\x14\n\x10\x41\x43TIVE_FRONT_END\x10\x10\x12\x13\n\x0fPOWER_CONVERTER\x10\x11\x12\x17\n\x13SYNCHRONOUS_MACHINE\x10\x12\x12\x15\n\x11INDUCTION_MACHINE\x10\x13\x12\x0b\n\x07GEARBOX\x10\x14\x12\r\n\tFUEL_CELL\x10\x15\x12\x12\n\x0ePROPELLER_LOAD\x10\x16\x12\x19\n\x15OTHER_MECHANICAL_LOAD\x10\x17\x12\x0b\n\x07\x42\x41TTERY\x10\x18\x12\x12\n\x0eSUPERCAPACITOR\x10\x19\x12\x19\n\x15SUPERCAPACITOR_SYSTEM\x10\x1a\x12\x0f\n\x0bSHORE_POWER\x10\x1b\x12\t\n\x05\x43OGAS\x10\x1c\x12\t\n\x05\x43OGES\x10\x1d"^\n\x0bSwitchboard\x12\x16\n\x0eswitchboard_id\x18\x01 \x01(\r\x12\x37\n\nsubsystems\x18\x02 \x03(\x0b\x32#.machinerySystemStructure.Subsystem"[\n\tShaftLine\x12\x15\n\rshaft_line_id\x18\x01 \x01(\r\x12\x37\n\nsubsystems\x18\x02 \x03(\x0b\x32#.machinerySystemStructure.Subsystem"L\n\x10MechanicalSystem\x12\x38\n\x0bshaft_lines\x18\x01 \x03(\x0b\x32#.machinerySystemStructure.ShaftLine"M\n\x0e\x45lectricSystem\x12;\n\x0cswitchboards\x18\x01 \x03(\x0b\x32%.machinerySystemStructure.Switchboard"Y\n\x0b\x46uelStorage\x12\x35\n\tfuel_type\x18\x01 \x01(\x0e\x32".machinerySystemStructure.FuelType\x12\x13\n\x0b\x63\x61pacity_kg\x18\x02 \x01(\x01"\xfe\x03\n\x0fMachinerySystem\x12\x0c\n\x04name\x18\x01 \x01(\t\x12Q\n\x0fpropulsion_type\x18\x02 \x01(\x0e\x32\x38.machinerySystemStructure.MachinerySystem.PropulsionType\x12;\n\x0c\x66uel_storage\x18\x03 \x03(\x0b\x32%.machinerySystemStructure.FuelStorage\x12.\n&maximum_allowed_genset_load_percentage\x18\x04 \x01(\x01\x12\x45\n\x11mechanical_system\x18\x05 \x01(\x0b\x32*.machinerySystemStructure.MechanicalSystem\x12\x41\n\x0f\x65lectric_system\x18\x06 \x01(\x0b\x32(.machinerySystemStructure.ElectricSystem\x12\x31\n)maximum_allowed_fuel_cell_load_percentage\x18\x07 \x01(\x01\x12$\n\x1c\x61verage_base_load_percentage\x18\x08 \x01(\x01":\n\x0ePropulsionType\x12\x0e\n\nMECHANICAL\x10\x00\x12\x0c\n\x08\x45LECTRIC\x10\x01\x12\n\n\x06HYBRID\x10\x02*T\n\x0c\x45missionType\x12\x08\n\x04NONE\x10\x00\x12\x07\n\x03SOX\x10\x01\x12\x07\n\x03NOX\x10\x02\x12\x06\n\x02\x43O\x10\x03\x12\x06\n\x02PM\x10\x04\x12\x06\n\x02HC\x10\x05\x12\x07\n\x03\x43H4\x10\x06\x12\x07\n\x03N2O\x10\x07*\xc6\x01\n\x08\x46uelType\x12\n\n\x06\x44IESEL\x10\x00\x12\x07\n\x03HFO\x10\x01\x12\x0f\n\x0bNATURAL_GAS\x10\x02\x12\x0c\n\x08HYDROGEN\x10\x03\x12\x0b\n\x07\x41MMONIA\x10\x04\x12\x0f\n\x0bLPG_PROPANE\x10\x05\x12\x0e\n\nLPG_BUTANE\x10\x06\x12\x0b\n\x07\x45THANOL\x10\x07\x12\x0c\n\x08METHANOL\x10\x08\x12\x07\n\x03LFO\x10\t\x12\x0e\n\nLSFO_CRUDE\x10\n\x12\x0e\n\nLSFO_BLEND\x10\x0b\x12\t\n\x05ULSFO\x10\x0c\x12\t\n\x05VLSFO\x10\r*C\n\nFuelOrigin\x12\t\n\x05NONE1\x10\x00\x12\n\n\x06\x46OSSIL\x10\x01\x12\x07\n\x03\x42IO\x10\x02\x12\x15\n\x11RENEWABLE_NON_BIO\x10\x03*E\n\x0f\x46uelSpecifiedBy\x12\t\n\x05NONE2\x10\x00\x12\x14\n\x10\x46UEL_EU_MARITIME\x10\x01\x12\x07\n\x03IMO\x10\x02\x12\x08\n\x04USER\x10\x03\x62\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "system_structure_pb2", _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _globals["_EMISSIONTYPE"]._serialized_start = 7458
    _globals["_EMISSIONTYPE"]._serialized_end = 7542
    _globals["_FUELTYPE"]._serialized_start = 7545
    _globals["_FUELTYPE"]._serialized_end = 7743
    _globals["_FUELORIGIN"]._serialized_start = 7745
    _globals["_FUELORIGIN"]._serialized_end = 7812
    _globals["_FUELSPECIFIEDBY"]._serialized_start = 7814
    _globals["_FUELSPECIFIEDBY"]._serialized_end = 7883
    _globals["_POINT"]._serialized_start = 52
    _globals["_POINT"]._serialized_end = 81
    _globals["_CURVE1D"]._serialized_start = 83
    _globals["_CURVE1D"]._serialized_end = 141
    _globals["_BSFCCURVE"]._serialized_start = 143
    _globals["_BSFCCURVE"]._serialized_end = 238
    _globals["_EFFICIENCYCURVE"]._serialized_start = 240
    _globals["_EFFICIENCYCURVE"]._serialized_end = 341
    _globals["_BSFC"]._serialized_start = 343
    _globals["_BSFC"]._serialized_end = 431
    _globals["_EFFICIENCY"]._serialized_start = 433
    _globals["_EFFICIENCY"]._serialized_end = 548
    _globals["_POWERCURVE"]._serialized_start = 550
    _globals["_POWERCURVE"]._serialized_end = 646
    _globals["_PROPULSIONPOWERTIMESERIES"]._serialized_start = 649
    _globals["_PROPULSIONPOWERTIMESERIES"]._serialized_end = 782
    _globals["_AUXILIARYLOADTIMESERIES"]._serialized_start = 785
    _globals["_AUXILIARYLOADTIMESERIES"]._serialized_end = 918
    _globals["_AUXILIARYLOAD"]._serialized_start = 920
    _globals["_AUXILIARYLOAD"]._serialized_end = 976
    _globals["_EMISSIONCURVE"]._serialized_start = 979
    _globals["_EMISSIONCURVE"]._serialized_end = 1141
    _globals["_GEAR"]._serialized_start = 1144
    _globals["_GEAR"]._serialized_end = 1373
    _globals["_FUEL"]._serialized_start = 1375
    _globals["_FUEL"]._serialized_end = 1495
    _globals["_ENGINE"]._serialized_start = 1498
    _globals["_ENGINE"]._serialized_end = 2284
    _globals["_ENGINE_NOXCALCULATIONMETHOD"]._serialized_start = 2134
    _globals["_ENGINE_NOXCALCULATIONMETHOD"]._serialized_end = 2203
    _globals["_ENGINE_ENGINECYCLETYPE"]._serialized_start = 2205
    _globals["_ENGINE_ENGINECYCLETYPE"]._serialized_end = 2284
    _globals["_COGAS"]._serialized_start = 2287
    _globals["_COGAS"]._serialized_end = 2890
    _globals["_ELECTRICMACHINE"]._serialized_start = 2893
    _globals["_ELECTRICMACHINE"]._serialized_end = 3113
    _globals["_BATTERY"]._serialized_start = 3116
    _globals["_BATTERY"]._serialized_end = 3515
    _globals["_ELECTRICCOMPONENT"]._serialized_start = 3518
    _globals["_ELECTRICCOMPONENT"]._serialized_end = 3715
    _globals["_FUELCELL"]._serialized_start = 3718
    _globals["_FUELCELL"]._serialized_end = 4031
    _globals["_PROPELLER"]._serialized_start = 4034
    _globals["_PROPELLER"]._serialized_end = 4197
    _globals["_BUSBREAKER"]._serialized_start = 4199
    _globals["_BUSBREAKER"]._serialized_end = 4235
    _globals["_SUPERCAPACITOR"]._serialized_start = 4238
    _globals["_SUPERCAPACITOR"]._serialized_end = 4496
    _globals["_MECHANICALCOMPONENT"]._serialized_start = 4499
    _globals["_MECHANICALCOMPONENT"]._serialized_end = 4698
    _globals["_SUBSYSTEM"]._serialized_start = 4701
    _globals["_SUBSYSTEM"]._serialized_end = 6506
    _globals["_SUBSYSTEM_POWERTYPE"]._serialized_start = 5815
    _globals["_SUBSYSTEM_POWERTYPE"]._serialized_end = 5930
    _globals["_SUBSYSTEM_COMPONENTTYPE"]._serialized_start = 5933
    _globals["_SUBSYSTEM_COMPONENTTYPE"]._serialized_end = 6506
    _globals["_SWITCHBOARD"]._serialized_start = 6508
    _globals["_SWITCHBOARD"]._serialized_end = 6602
    _globals["_SHAFTLINE"]._serialized_start = 6604
    _globals["_SHAFTLINE"]._serialized_end = 6695
    _globals["_MECHANICALSYSTEM"]._serialized_start = 6697
    _globals["_MECHANICALSYSTEM"]._serialized_end = 6773
    _globals["_ELECTRICSYSTEM"]._serialized_start = 6775
    _globals["_ELECTRICSYSTEM"]._serialized_end = 6852
    _globals["_FUELSTORAGE"]._serialized_start = 6854
    _globals["_FUELSTORAGE"]._serialized_end = 6943
    _globals["_MACHINERYSYSTEM"]._serialized_start = 6946
    _globals["_MACHINERYSYSTEM"]._serialized_end = 7456
    _globals["_MACHINERYSYSTEM_PROPULSIONTYPE"]._serialized_start = 7398
    _globals["_MACHINERYSYSTEM_PROPULSIONTYPE"]._serialized_end = 7456
# @@protoc_insertion_point(module_scope)
