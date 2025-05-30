# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: feems_result.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from . import system_structure_pb2 as system__structure__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x12\x66\x65\x65ms_result.proto\x12\x0b\x66\x65\x65msResult\x1a\x16system_structure.proto"\xdb\x02\n\nFuelScalar\x12\x35\n\tfuel_type\x18\x01 \x01(\x0e\x32".machinerySystemStructure.FuelType\x12\x39\n\x0b\x66uel_origin\x18\x02 \x01(\x0e\x32$.machinerySystemStructure.FuelOrigin\x12\x44\n\x11\x66uel_specified_by\x18\x03 \x01(\x0e\x32).machinerySystemStructure.FuelSpecifiedBy\x12\x1d\n\x15mass_or_mass_fraction\x18\x04 \x01(\x01\x12\x14\n\x0clhv_mj_per_g\x18\x05 \x01(\x01\x12\x36\n.ghg_emission_factor_well_to_tank_gco2eq_per_mj\x18\x06 \x01(\x01\x12(\n ghg_emission_factor_tank_to_wake\x18\x07 \x01(\x01"\xda\x02\n\tFuelArray\x12\x35\n\tfuel_type\x18\x01 \x01(\x0e\x32".machinerySystemStructure.FuelType\x12\x39\n\x0b\x66uel_origin\x18\x02 \x01(\x0e\x32$.machinerySystemStructure.FuelOrigin\x12\x44\n\x11\x66uel_specified_by\x18\x03 \x01(\x0e\x32).machinerySystemStructure.FuelSpecifiedBy\x12\x1d\n\x15mass_or_mass_fraction\x18\x04 \x03(\x01\x12\x14\n\x0clhv_mj_per_g\x18\x05 \x01(\x01\x12\x36\n.ghg_emission_factor_well_to_tank_gco2eq_per_mj\x18\x06 \x01(\x01\x12(\n ghg_emission_factor_tank_to_wake\x18\x07 \x01(\x01"?\n\x15\x46uelConsumptionScalar\x12&\n\x05\x66uels\x18\x01 \x03(\x0b\x32\x17.feemsResult.FuelScalar"A\n\x18\x46uelConsumptionRateArray\x12%\n\x05\x66uels\x18\x01 \x03(\x0b\x32\x16.feemsResult.FuelArray"\x8f\x01\n\x1cTimeSeriesResultForComponent\x12\x0c\n\x04time\x18\x01 \x03(\x01\x12\x17\n\x0fpower_output_kw\x18\x02 \x03(\x01\x12H\n\x19\x66uel_consumption_kg_per_s\x18\x03 \x01(\x0b\x32%.feemsResult.FuelConsumptionRateArray"\xef\x01\n\x0cGHGEmissions\x12\x14\n\x0cwell_to_tank\x18\x01 \x01(\x01\x12\x14\n\x0ctank_to_wake\x18\x02 \x01(\x01\x12\x14\n\x0cwell_to_wake\x18\x03 \x01(\x01\x12!\n\x19tank_to_wake_without_slip\x18\x04 \x01(\x01\x12!\n\x19well_to_wake_without_slip\x18\x05 \x01(\x01\x12$\n\x1ctank_to_wake_from_green_fuel\x18\x06 \x01(\x01\x12\x31\n)tank_to_wake_without_slip_from_green_fuel\x18\x07 \x01(\x01"\xa5\x04\n\x12ResultPerComponent\x12\x16\n\x0e\x63omponent_name\x18\x01 \x01(\t\x12\x45\n\x19multi_fuel_consumption_kg\x18\x02 \x01(\x0b\x32".feemsResult.FuelConsumptionScalar\x12&\n\x1e\x65lectric_energy_consumption_mj\x18\x03 \x01(\x01\x12(\n mechanical_energy_consumption_mj\x18\x04 \x01(\x01\x12\x18\n\x10\x65nergy_stored_mj\x18\x05 \x01(\x01\x12\x17\n\x0frunning_hours_h\x18\x06 \x01(\x01\x12\x33\n\x10\x63o2_emissions_kg\x18\x07 \x01(\x0b\x32\x19.feemsResult.GHGEmissions\x12\x18\n\x10nox_emissions_kg\x18\x08 \x01(\x01\x12\x16\n\x0e\x63omponent_type\x18\t \x01(\t\x12\x16\n\x0erated_capacity\x18\n \x01(\x01\x12\x1b\n\x13rated_capacity_unit\x18\x0b \x01(\t\x12\x16\n\x0eswitchboard_id\x18\x0c \x01(\r\x12\x14\n\x0cshaftline_id\x18\r \x01(\r\x12\x45\n\x12result_time_series\x18\x0e \x01(\x0b\x32).feemsResult.TimeSeriesResultForComponent\x12\x1a\n\x12\x66uel_consumer_type\x18\x0f \x01(\t"\xd0\x05\n\x0b\x46\x65\x65msResult\x12\x12\n\nduration_s\x18\x01 \x01(\x01\x12K\n\x1fmulti_fuel_consumption_total_kg\x18\x02 \x01(\x0b\x32".feemsResult.FuelConsumptionScalar\x12,\n$energy_consumption_electric_total_mj\x18\x03 \x01(\x01\x12.\n&energy_consumption_mechanical_total_mj\x18\x04 \x01(\x01\x12\x1e\n\x16\x65nergy_stored_total_mj\x18\x05 \x01(\x01\x12%\n\x1drunning_hours_main_engines_hr\x18\x06 \x01(\x01\x12%\n\x1drunning_hours_genset_total_hr\x18\x07 \x01(\x01\x12(\n running_hours_fuel_cell_total_hr\x18\x08 \x01(\x01\x12&\n\x1erunning_hours_pti_pto_total_hr\x18\t \x01(\x01\x12\x38\n\x15\x63o2_emission_total_kg\x18\n \x01(\x0b\x32\x19.feemsResult.GHGEmissions\x12\x1d\n\x15nox_emission_total_kg\x18\x0b \x01(\x01\x12\x38\n\x0f\x64\x65tailed_result\x18\x0c \x03(\x0b\x32\x1f.feemsResult.ResultPerComponent\x12(\n energy_input_mechanical_total_mj\x18\r \x01(\x01\x12&\n\x1e\x65nergy_input_electric_total_mj\x18\x0e \x01(\x01\x12.\n&energy_consumption_propulsion_total_mj\x18\x0f \x01(\x01\x12-\n%energy_consumption_auxiliary_total_mj\x18\x10 \x01(\x01"\x87\x01\n\x1d\x46\x65\x65msResultForMachinerySystem\x12\x31\n\x0f\x65lectric_system\x18\x01 \x01(\x0b\x32\x18.feemsResult.FeemsResult\x12\x33\n\x11mechanical_system\x18\x02 \x01(\x0b\x32\x18.feemsResult.FeemsResultb\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "feems_result_pb2", _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _globals["_FUELSCALAR"]._serialized_start = 60
    _globals["_FUELSCALAR"]._serialized_end = 407
    _globals["_FUELARRAY"]._serialized_start = 410
    _globals["_FUELARRAY"]._serialized_end = 756
    _globals["_FUELCONSUMPTIONSCALAR"]._serialized_start = 758
    _globals["_FUELCONSUMPTIONSCALAR"]._serialized_end = 821
    _globals["_FUELCONSUMPTIONRATEARRAY"]._serialized_start = 823
    _globals["_FUELCONSUMPTIONRATEARRAY"]._serialized_end = 888
    _globals["_TIMESERIESRESULTFORCOMPONENT"]._serialized_start = 891
    _globals["_TIMESERIESRESULTFORCOMPONENT"]._serialized_end = 1034
    _globals["_GHGEMISSIONS"]._serialized_start = 1037
    _globals["_GHGEMISSIONS"]._serialized_end = 1276
    _globals["_RESULTPERCOMPONENT"]._serialized_start = 1279
    _globals["_RESULTPERCOMPONENT"]._serialized_end = 1828
    _globals["_FEEMSRESULT"]._serialized_start = 1831
    _globals["_FEEMSRESULT"]._serialized_end = 2551
    _globals["_FEEMSRESULTFORMACHINERYSYSTEM"]._serialized_start = 2554
    _globals["_FEEMSRESULTFORMACHINERYSYSTEM"]._serialized_end = 2689
# @@protoc_insertion_point(module_scope)
