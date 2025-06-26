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

class GymirResult(_message.Message):
    __slots__ = ["name", "auxiliary_load_kw", "result"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    AUXILIARY_LOAD_KW_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    name: str
    auxiliary_load_kw: float
    result: _containers.RepeatedCompositeFieldContainer[SimulationInstance]
    def __init__(
        self,
        name: _Optional[str] = ...,
        auxiliary_load_kw: _Optional[float] = ...,
        result: _Optional[_Iterable[_Union[SimulationInstance, _Mapping]]] = ...,
    ) -> None: ...

class SimulationInstance(_message.Message):
    __slots__ = [
        "epoch_s",
        "task_type",
        "task_name",
        "latitude_deg",
        "longitude_deg",
        "heading_deg",
        "wave_height_significant_m",
        "wave_peak_period_s",
        "wave_dir_rel_north_deg",
        "wave_dir_rel_vessel_deg",
        "wind_speed_mps",
        "wind_dir_rel_north_deg",
        "wind_dir_rel_vessel_deg",
        "weather_source",
        "speed_over_ground_kn",
        "speed_through_water_kn",
        "current_speed_mps",
        "current_dir_rel_north_deg",
        "power_kw",
        "torque_k_nm",
        "thrust_k_n",
        "total_resistance_k_n",
    ]
    EPOCH_S_FIELD_NUMBER: _ClassVar[int]
    TASK_TYPE_FIELD_NUMBER: _ClassVar[int]
    TASK_NAME_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_DEG_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_DEG_FIELD_NUMBER: _ClassVar[int]
    HEADING_DEG_FIELD_NUMBER: _ClassVar[int]
    WAVE_HEIGHT_SIGNIFICANT_M_FIELD_NUMBER: _ClassVar[int]
    WAVE_PEAK_PERIOD_S_FIELD_NUMBER: _ClassVar[int]
    WAVE_DIR_REL_NORTH_DEG_FIELD_NUMBER: _ClassVar[int]
    WAVE_DIR_REL_VESSEL_DEG_FIELD_NUMBER: _ClassVar[int]
    WIND_SPEED_MPS_FIELD_NUMBER: _ClassVar[int]
    WIND_DIR_REL_NORTH_DEG_FIELD_NUMBER: _ClassVar[int]
    WIND_DIR_REL_VESSEL_DEG_FIELD_NUMBER: _ClassVar[int]
    WEATHER_SOURCE_FIELD_NUMBER: _ClassVar[int]
    SPEED_OVER_GROUND_KN_FIELD_NUMBER: _ClassVar[int]
    SPEED_THROUGH_WATER_KN_FIELD_NUMBER: _ClassVar[int]
    CURRENT_SPEED_MPS_FIELD_NUMBER: _ClassVar[int]
    CURRENT_DIR_REL_NORTH_DEG_FIELD_NUMBER: _ClassVar[int]
    POWER_KW_FIELD_NUMBER: _ClassVar[int]
    TORQUE_K_NM_FIELD_NUMBER: _ClassVar[int]
    THRUST_K_N_FIELD_NUMBER: _ClassVar[int]
    TOTAL_RESISTANCE_K_N_FIELD_NUMBER: _ClassVar[int]
    epoch_s: float
    task_type: str
    task_name: str
    latitude_deg: float
    longitude_deg: float
    heading_deg: float
    wave_height_significant_m: float
    wave_peak_period_s: float
    wave_dir_rel_north_deg: float
    wave_dir_rel_vessel_deg: float
    wind_speed_mps: float
    wind_dir_rel_north_deg: float
    wind_dir_rel_vessel_deg: float
    weather_source: str
    speed_over_ground_kn: float
    speed_through_water_kn: float
    current_speed_mps: float
    current_dir_rel_north_deg: float
    power_kw: float
    torque_k_nm: float
    thrust_k_n: float
    total_resistance_k_n: float
    def __init__(
        self,
        epoch_s: _Optional[float] = ...,
        task_type: _Optional[str] = ...,
        task_name: _Optional[str] = ...,
        latitude_deg: _Optional[float] = ...,
        longitude_deg: _Optional[float] = ...,
        heading_deg: _Optional[float] = ...,
        wave_height_significant_m: _Optional[float] = ...,
        wave_peak_period_s: _Optional[float] = ...,
        wave_dir_rel_north_deg: _Optional[float] = ...,
        wave_dir_rel_vessel_deg: _Optional[float] = ...,
        wind_speed_mps: _Optional[float] = ...,
        wind_dir_rel_north_deg: _Optional[float] = ...,
        wind_dir_rel_vessel_deg: _Optional[float] = ...,
        weather_source: _Optional[str] = ...,
        speed_over_ground_kn: _Optional[float] = ...,
        speed_through_water_kn: _Optional[float] = ...,
        current_speed_mps: _Optional[float] = ...,
        current_dir_rel_north_deg: _Optional[float] = ...,
        power_kw: _Optional[float] = ...,
        torque_k_nm: _Optional[float] = ...,
        thrust_k_n: _Optional[float] = ...,
        total_resistance_k_n: _Optional[float] = ...,
    ) -> None: ...

class PropulsionPowerInstance(_message.Message):
    __slots__ = ["epoch_s", "propulsion_power_kw", "auxiliary_power_kw"]
    EPOCH_S_FIELD_NUMBER: _ClassVar[int]
    PROPULSION_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    AUXILIARY_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    epoch_s: float
    propulsion_power_kw: float
    auxiliary_power_kw: float
    def __init__(
        self,
        epoch_s: _Optional[float] = ...,
        propulsion_power_kw: _Optional[float] = ...,
        auxiliary_power_kw: _Optional[float] = ...,
    ) -> None: ...

class PropulsionPowerInstanceForMultiplePropulsors(_message.Message):
    __slots__ = ["epoch_s", "propulsion_power_kw", "auxiliary_power_kw"]
    EPOCH_S_FIELD_NUMBER: _ClassVar[int]
    PROPULSION_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    AUXILIARY_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    epoch_s: float
    propulsion_power_kw: _containers.RepeatedScalarFieldContainer[float]
    auxiliary_power_kw: float
    def __init__(
        self,
        epoch_s: _Optional[float] = ...,
        propulsion_power_kw: _Optional[_Iterable[float]] = ...,
        auxiliary_power_kw: _Optional[float] = ...,
    ) -> None: ...

class OperationProfilePoint(_message.Message):
    __slots__ = ["epoch_s", "speed_kn", "draft_m"]
    EPOCH_S_FIELD_NUMBER: _ClassVar[int]
    SPEED_KN_FIELD_NUMBER: _ClassVar[int]
    DRAFT_M_FIELD_NUMBER: _ClassVar[int]
    epoch_s: float
    speed_kn: float
    draft_m: float
    def __init__(
        self,
        epoch_s: _Optional[float] = ...,
        speed_kn: _Optional[float] = ...,
        draft_m: _Optional[float] = ...,
    ) -> None: ...

class TimeSeriesResult(_message.Message):
    __slots__ = [
        "propulsion_power_timeseries",
        "auxiliary_power_kw",
        "operation_profile",
    ]
    PROPULSION_POWER_TIMESERIES_FIELD_NUMBER: _ClassVar[int]
    AUXILIARY_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    OPERATION_PROFILE_FIELD_NUMBER: _ClassVar[int]
    propulsion_power_timeseries: _containers.RepeatedCompositeFieldContainer[
        PropulsionPowerInstance
    ]
    auxiliary_power_kw: float
    operation_profile: _containers.RepeatedCompositeFieldContainer[
        OperationProfilePoint
    ]
    def __init__(
        self,
        propulsion_power_timeseries: _Optional[
            _Iterable[_Union[PropulsionPowerInstance, _Mapping]]
        ] = ...,
        auxiliary_power_kw: _Optional[float] = ...,
        operation_profile: _Optional[
            _Iterable[_Union[OperationProfilePoint, _Mapping]]
        ] = ...,
    ) -> None: ...

class TimeSeriesResultForMultiplePropulsors(_message.Message):
    __slots__ = [
        "propulsion_power_timeseries",
        "propulsor_names",
        "auxiliary_power_kw",
        "operation_profile",
    ]
    PROPULSION_POWER_TIMESERIES_FIELD_NUMBER: _ClassVar[int]
    PROPULSOR_NAMES_FIELD_NUMBER: _ClassVar[int]
    AUXILIARY_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    OPERATION_PROFILE_FIELD_NUMBER: _ClassVar[int]
    propulsion_power_timeseries: _containers.RepeatedCompositeFieldContainer[
        PropulsionPowerInstanceForMultiplePropulsors
    ]
    propulsor_names: _containers.RepeatedScalarFieldContainer[str]
    auxiliary_power_kw: float
    operation_profile: _containers.RepeatedCompositeFieldContainer[
        OperationProfilePoint
    ]
    def __init__(
        self,
        propulsion_power_timeseries: _Optional[
            _Iterable[_Union[PropulsionPowerInstanceForMultiplePropulsors, _Mapping]]
        ] = ...,
        propulsor_names: _Optional[_Iterable[str]] = ...,
        auxiliary_power_kw: _Optional[float] = ...,
        operation_profile: _Optional[
            _Iterable[_Union[OperationProfilePoint, _Mapping]]
        ] = ...,
    ) -> None: ...
