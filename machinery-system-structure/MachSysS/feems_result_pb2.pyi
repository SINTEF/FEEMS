from . import system_structure_pb2 as _system_structure_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class FuelScalar(_message.Message):
    __slots__ = [
        "fuel_type",
        "fuel_origin",
        "fuel_specified_by",
        "mass_or_mass_fraction",
        "lhv_mj_per_g",
        "ghg_emission_factor_well_to_tank_gco2eq_per_mj",
        "ghg_emission_factor_tank_to_wake",
    ]
    FUEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    FUEL_ORIGIN_FIELD_NUMBER: _ClassVar[int]
    FUEL_SPECIFIED_BY_FIELD_NUMBER: _ClassVar[int]
    MASS_OR_MASS_FRACTION_FIELD_NUMBER: _ClassVar[int]
    LHV_MJ_PER_G_FIELD_NUMBER: _ClassVar[int]
    GHG_EMISSION_FACTOR_WELL_TO_TANK_GCO2EQ_PER_MJ_FIELD_NUMBER: _ClassVar[int]
    GHG_EMISSION_FACTOR_TANK_TO_WAKE_FIELD_NUMBER: _ClassVar[int]
    fuel_type: _system_structure_pb2.FuelType
    fuel_origin: _system_structure_pb2.FuelOrigin
    fuel_specified_by: _system_structure_pb2.FuelSpecifiedBy
    mass_or_mass_fraction: float
    lhv_mj_per_g: float
    ghg_emission_factor_well_to_tank_gco2eq_per_mj: float
    ghg_emission_factor_tank_to_wake: float
    def __init__(
        self,
        fuel_type: _Optional[_Union[_system_structure_pb2.FuelType, str]] = ...,
        fuel_origin: _Optional[_Union[_system_structure_pb2.FuelOrigin, str]] = ...,
        fuel_specified_by: _Optional[
            _Union[_system_structure_pb2.FuelSpecifiedBy, str]
        ] = ...,
        mass_or_mass_fraction: _Optional[float] = ...,
        lhv_mj_per_g: _Optional[float] = ...,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: _Optional[float] = ...,
        ghg_emission_factor_tank_to_wake: _Optional[float] = ...,
    ) -> None: ...

class FuelArray(_message.Message):
    __slots__ = [
        "fuel_type",
        "fuel_origin",
        "fuel_specified_by",
        "mass_or_mass_fraction",
        "lhv_mj_per_g",
        "ghg_emission_factor_well_to_tank_gco2eq_per_mj",
        "ghg_emission_factor_tank_to_wake",
    ]
    FUEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    FUEL_ORIGIN_FIELD_NUMBER: _ClassVar[int]
    FUEL_SPECIFIED_BY_FIELD_NUMBER: _ClassVar[int]
    MASS_OR_MASS_FRACTION_FIELD_NUMBER: _ClassVar[int]
    LHV_MJ_PER_G_FIELD_NUMBER: _ClassVar[int]
    GHG_EMISSION_FACTOR_WELL_TO_TANK_GCO2EQ_PER_MJ_FIELD_NUMBER: _ClassVar[int]
    GHG_EMISSION_FACTOR_TANK_TO_WAKE_FIELD_NUMBER: _ClassVar[int]
    fuel_type: _system_structure_pb2.FuelType
    fuel_origin: _system_structure_pb2.FuelOrigin
    fuel_specified_by: _system_structure_pb2.FuelSpecifiedBy
    mass_or_mass_fraction: _containers.RepeatedScalarFieldContainer[float]
    lhv_mj_per_g: float
    ghg_emission_factor_well_to_tank_gco2eq_per_mj: float
    ghg_emission_factor_tank_to_wake: float
    def __init__(
        self,
        fuel_type: _Optional[_Union[_system_structure_pb2.FuelType, str]] = ...,
        fuel_origin: _Optional[_Union[_system_structure_pb2.FuelOrigin, str]] = ...,
        fuel_specified_by: _Optional[
            _Union[_system_structure_pb2.FuelSpecifiedBy, str]
        ] = ...,
        mass_or_mass_fraction: _Optional[_Iterable[float]] = ...,
        lhv_mj_per_g: _Optional[float] = ...,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: _Optional[float] = ...,
        ghg_emission_factor_tank_to_wake: _Optional[float] = ...,
    ) -> None: ...

class FuelConsumptionScalar(_message.Message):
    __slots__ = ["fuels"]
    FUELS_FIELD_NUMBER: _ClassVar[int]
    fuels: _containers.RepeatedCompositeFieldContainer[FuelScalar]
    def __init__(
        self, fuels: _Optional[_Iterable[_Union[FuelScalar, _Mapping]]] = ...
    ) -> None: ...

class FuelConsumptionRateArray(_message.Message):
    __slots__ = ["fuels"]
    FUELS_FIELD_NUMBER: _ClassVar[int]
    fuels: _containers.RepeatedCompositeFieldContainer[FuelArray]
    def __init__(
        self, fuels: _Optional[_Iterable[_Union[FuelArray, _Mapping]]] = ...
    ) -> None: ...

class TimeSeriesResultForComponent(_message.Message):
    __slots__ = ["time", "power_output_kw", "fuel_consumption_kg_per_s"]
    TIME_FIELD_NUMBER: _ClassVar[int]
    POWER_OUTPUT_KW_FIELD_NUMBER: _ClassVar[int]
    FUEL_CONSUMPTION_KG_PER_S_FIELD_NUMBER: _ClassVar[int]
    time: _containers.RepeatedScalarFieldContainer[float]
    power_output_kw: _containers.RepeatedScalarFieldContainer[float]
    fuel_consumption_kg_per_s: FuelConsumptionRateArray
    def __init__(
        self,
        time: _Optional[_Iterable[float]] = ...,
        power_output_kw: _Optional[_Iterable[float]] = ...,
        fuel_consumption_kg_per_s: _Optional[
            _Union[FuelConsumptionRateArray, _Mapping]
        ] = ...,
    ) -> None: ...

class GHGEmissions(_message.Message):
    __slots__ = [
        "well_to_tank",
        "tank_to_wake",
        "well_to_wake",
        "tank_to_wake_without_slip",
        "well_to_wake_without_slip",
        "tank_to_wake_from_green_fuel",
        "tank_to_wake_without_slip_from_green_fuel",
    ]
    WELL_TO_TANK_FIELD_NUMBER: _ClassVar[int]
    TANK_TO_WAKE_FIELD_NUMBER: _ClassVar[int]
    WELL_TO_WAKE_FIELD_NUMBER: _ClassVar[int]
    TANK_TO_WAKE_WITHOUT_SLIP_FIELD_NUMBER: _ClassVar[int]
    WELL_TO_WAKE_WITHOUT_SLIP_FIELD_NUMBER: _ClassVar[int]
    TANK_TO_WAKE_FROM_GREEN_FUEL_FIELD_NUMBER: _ClassVar[int]
    TANK_TO_WAKE_WITHOUT_SLIP_FROM_GREEN_FUEL_FIELD_NUMBER: _ClassVar[int]
    well_to_tank: float
    tank_to_wake: float
    well_to_wake: float
    tank_to_wake_without_slip: float
    well_to_wake_without_slip: float
    tank_to_wake_from_green_fuel: float
    tank_to_wake_without_slip_from_green_fuel: float
    def __init__(
        self,
        well_to_tank: _Optional[float] = ...,
        tank_to_wake: _Optional[float] = ...,
        well_to_wake: _Optional[float] = ...,
        tank_to_wake_without_slip: _Optional[float] = ...,
        well_to_wake_without_slip: _Optional[float] = ...,
        tank_to_wake_from_green_fuel: _Optional[float] = ...,
        tank_to_wake_without_slip_from_green_fuel: _Optional[float] = ...,
    ) -> None: ...

class ResultPerComponent(_message.Message):
    __slots__ = [
        "component_name",
        "multi_fuel_consumption_kg",
        "electric_energy_consumption_mj",
        "mechanical_energy_consumption_mj",
        "energy_stored_mj",
        "running_hours_h",
        "co2_emissions_kg",
        "nox_emissions_kg",
        "component_type",
        "rated_capacity",
        "rated_capacity_unit",
        "switchboard_id",
        "shaftline_id",
        "result_time_series",
        "fuel_consumer_type",
    ]
    COMPONENT_NAME_FIELD_NUMBER: _ClassVar[int]
    MULTI_FUEL_CONSUMPTION_KG_FIELD_NUMBER: _ClassVar[int]
    ELECTRIC_ENERGY_CONSUMPTION_MJ_FIELD_NUMBER: _ClassVar[int]
    MECHANICAL_ENERGY_CONSUMPTION_MJ_FIELD_NUMBER: _ClassVar[int]
    ENERGY_STORED_MJ_FIELD_NUMBER: _ClassVar[int]
    RUNNING_HOURS_H_FIELD_NUMBER: _ClassVar[int]
    CO2_EMISSIONS_KG_FIELD_NUMBER: _ClassVar[int]
    NOX_EMISSIONS_KG_FIELD_NUMBER: _ClassVar[int]
    COMPONENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    RATED_CAPACITY_FIELD_NUMBER: _ClassVar[int]
    RATED_CAPACITY_UNIT_FIELD_NUMBER: _ClassVar[int]
    SWITCHBOARD_ID_FIELD_NUMBER: _ClassVar[int]
    SHAFTLINE_ID_FIELD_NUMBER: _ClassVar[int]
    RESULT_TIME_SERIES_FIELD_NUMBER: _ClassVar[int]
    FUEL_CONSUMER_TYPE_FIELD_NUMBER: _ClassVar[int]
    component_name: str
    multi_fuel_consumption_kg: FuelConsumptionScalar
    electric_energy_consumption_mj: float
    mechanical_energy_consumption_mj: float
    energy_stored_mj: float
    running_hours_h: float
    co2_emissions_kg: GHGEmissions
    nox_emissions_kg: float
    component_type: str
    rated_capacity: float
    rated_capacity_unit: str
    switchboard_id: int
    shaftline_id: int
    result_time_series: TimeSeriesResultForComponent
    fuel_consumer_type: str
    def __init__(
        self,
        component_name: _Optional[str] = ...,
        multi_fuel_consumption_kg: _Optional[
            _Union[FuelConsumptionScalar, _Mapping]
        ] = ...,
        electric_energy_consumption_mj: _Optional[float] = ...,
        mechanical_energy_consumption_mj: _Optional[float] = ...,
        energy_stored_mj: _Optional[float] = ...,
        running_hours_h: _Optional[float] = ...,
        co2_emissions_kg: _Optional[_Union[GHGEmissions, _Mapping]] = ...,
        nox_emissions_kg: _Optional[float] = ...,
        component_type: _Optional[str] = ...,
        rated_capacity: _Optional[float] = ...,
        rated_capacity_unit: _Optional[str] = ...,
        switchboard_id: _Optional[int] = ...,
        shaftline_id: _Optional[int] = ...,
        result_time_series: _Optional[
            _Union[TimeSeriesResultForComponent, _Mapping]
        ] = ...,
        fuel_consumer_type: _Optional[str] = ...,
    ) -> None: ...

class FeemsResult(_message.Message):
    __slots__ = [
        "duration_s",
        "multi_fuel_consumption_total_kg",
        "energy_consumption_electric_total_mj",
        "energy_consumption_mechanical_total_mj",
        "energy_stored_total_mj",
        "running_hours_main_engines_hr",
        "running_hours_genset_total_hr",
        "running_hours_fuel_cell_total_hr",
        "running_hours_pti_pto_total_hr",
        "co2_emission_total_kg",
        "nox_emission_total_kg",
        "detailed_result",
        "energy_input_mechanical_total_mj",
        "energy_input_electric_total_mj",
        "energy_consumption_propulsion_total_mj",
        "energy_consumption_auxiliary_total_mj",
    ]
    DURATION_S_FIELD_NUMBER: _ClassVar[int]
    MULTI_FUEL_CONSUMPTION_TOTAL_KG_FIELD_NUMBER: _ClassVar[int]
    ENERGY_CONSUMPTION_ELECTRIC_TOTAL_MJ_FIELD_NUMBER: _ClassVar[int]
    ENERGY_CONSUMPTION_MECHANICAL_TOTAL_MJ_FIELD_NUMBER: _ClassVar[int]
    ENERGY_STORED_TOTAL_MJ_FIELD_NUMBER: _ClassVar[int]
    RUNNING_HOURS_MAIN_ENGINES_HR_FIELD_NUMBER: _ClassVar[int]
    RUNNING_HOURS_GENSET_TOTAL_HR_FIELD_NUMBER: _ClassVar[int]
    RUNNING_HOURS_FUEL_CELL_TOTAL_HR_FIELD_NUMBER: _ClassVar[int]
    RUNNING_HOURS_PTI_PTO_TOTAL_HR_FIELD_NUMBER: _ClassVar[int]
    CO2_EMISSION_TOTAL_KG_FIELD_NUMBER: _ClassVar[int]
    NOX_EMISSION_TOTAL_KG_FIELD_NUMBER: _ClassVar[int]
    DETAILED_RESULT_FIELD_NUMBER: _ClassVar[int]
    ENERGY_INPUT_MECHANICAL_TOTAL_MJ_FIELD_NUMBER: _ClassVar[int]
    ENERGY_INPUT_ELECTRIC_TOTAL_MJ_FIELD_NUMBER: _ClassVar[int]
    ENERGY_CONSUMPTION_PROPULSION_TOTAL_MJ_FIELD_NUMBER: _ClassVar[int]
    ENERGY_CONSUMPTION_AUXILIARY_TOTAL_MJ_FIELD_NUMBER: _ClassVar[int]
    duration_s: float
    multi_fuel_consumption_total_kg: FuelConsumptionScalar
    energy_consumption_electric_total_mj: float
    energy_consumption_mechanical_total_mj: float
    energy_stored_total_mj: float
    running_hours_main_engines_hr: float
    running_hours_genset_total_hr: float
    running_hours_fuel_cell_total_hr: float
    running_hours_pti_pto_total_hr: float
    co2_emission_total_kg: GHGEmissions
    nox_emission_total_kg: float
    detailed_result: _containers.RepeatedCompositeFieldContainer[ResultPerComponent]
    energy_input_mechanical_total_mj: float
    energy_input_electric_total_mj: float
    energy_consumption_propulsion_total_mj: float
    energy_consumption_auxiliary_total_mj: float
    def __init__(
        self,
        duration_s: _Optional[float] = ...,
        multi_fuel_consumption_total_kg: _Optional[
            _Union[FuelConsumptionScalar, _Mapping]
        ] = ...,
        energy_consumption_electric_total_mj: _Optional[float] = ...,
        energy_consumption_mechanical_total_mj: _Optional[float] = ...,
        energy_stored_total_mj: _Optional[float] = ...,
        running_hours_main_engines_hr: _Optional[float] = ...,
        running_hours_genset_total_hr: _Optional[float] = ...,
        running_hours_fuel_cell_total_hr: _Optional[float] = ...,
        running_hours_pti_pto_total_hr: _Optional[float] = ...,
        co2_emission_total_kg: _Optional[_Union[GHGEmissions, _Mapping]] = ...,
        nox_emission_total_kg: _Optional[float] = ...,
        detailed_result: _Optional[
            _Iterable[_Union[ResultPerComponent, _Mapping]]
        ] = ...,
        energy_input_mechanical_total_mj: _Optional[float] = ...,
        energy_input_electric_total_mj: _Optional[float] = ...,
        energy_consumption_propulsion_total_mj: _Optional[float] = ...,
        energy_consumption_auxiliary_total_mj: _Optional[float] = ...,
    ) -> None: ...

class FeemsResultForMachinerySystem(_message.Message):
    __slots__ = ["electric_system", "mechanical_system"]
    ELECTRIC_SYSTEM_FIELD_NUMBER: _ClassVar[int]
    MECHANICAL_SYSTEM_FIELD_NUMBER: _ClassVar[int]
    electric_system: FeemsResult
    mechanical_system: FeemsResult
    def __init__(
        self,
        electric_system: _Optional[_Union[FeemsResult, _Mapping]] = ...,
        mechanical_system: _Optional[_Union[FeemsResult, _Mapping]] = ...,
    ) -> None: ...
