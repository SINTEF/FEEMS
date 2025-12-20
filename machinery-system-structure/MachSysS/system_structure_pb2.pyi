from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
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

class EmissionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    NONE: _ClassVar[EmissionType]
    SOX: _ClassVar[EmissionType]
    NOX: _ClassVar[EmissionType]
    CO: _ClassVar[EmissionType]
    PM: _ClassVar[EmissionType]
    HC: _ClassVar[EmissionType]
    CH4: _ClassVar[EmissionType]
    N2O: _ClassVar[EmissionType]

class FuelType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    DIESEL: _ClassVar[FuelType]
    HFO: _ClassVar[FuelType]
    NATURAL_GAS: _ClassVar[FuelType]
    HYDROGEN: _ClassVar[FuelType]
    AMMONIA: _ClassVar[FuelType]
    LPG_PROPANE: _ClassVar[FuelType]
    LPG_BUTANE: _ClassVar[FuelType]
    ETHANOL: _ClassVar[FuelType]
    METHANOL: _ClassVar[FuelType]
    LFO: _ClassVar[FuelType]
    LSFO_CRUDE: _ClassVar[FuelType]
    LSFO_BLEND: _ClassVar[FuelType]
    ULSFO: _ClassVar[FuelType]
    VLSFO: _ClassVar[FuelType]
    NONE3: _ClassVar[FuelType]

class FuelOrigin(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    NONE1: _ClassVar[FuelOrigin]
    FOSSIL: _ClassVar[FuelOrigin]
    BIO: _ClassVar[FuelOrigin]
    RENEWABLE_NON_BIO: _ClassVar[FuelOrigin]

class FuelSpecifiedBy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    NONE2: _ClassVar[FuelSpecifiedBy]
    FUEL_EU_MARITIME: _ClassVar[FuelSpecifiedBy]
    IMO: _ClassVar[FuelSpecifiedBy]
    USER: _ClassVar[FuelSpecifiedBy]

NONE: EmissionType
SOX: EmissionType
NOX: EmissionType
CO: EmissionType
PM: EmissionType
HC: EmissionType
CH4: EmissionType
N2O: EmissionType
DIESEL: FuelType
HFO: FuelType
NATURAL_GAS: FuelType
HYDROGEN: FuelType
AMMONIA: FuelType
LPG_PROPANE: FuelType
LPG_BUTANE: FuelType
ETHANOL: FuelType
METHANOL: FuelType
LFO: FuelType
LSFO_CRUDE: FuelType
LSFO_BLEND: FuelType
ULSFO: FuelType
VLSFO: FuelType
NONE3: FuelType
NONE1: FuelOrigin
FOSSIL: FuelOrigin
BIO: FuelOrigin
RENEWABLE_NON_BIO: FuelOrigin
NONE2: FuelSpecifiedBy
FUEL_EU_MARITIME: FuelSpecifiedBy
IMO: FuelSpecifiedBy
USER: FuelSpecifiedBy

class Point(_message.Message):
    __slots__ = ["x", "y"]
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    def __init__(
        self, x: _Optional[float] = ..., y: _Optional[float] = ...
    ) -> None: ...

class Curve1D(_message.Message):
    __slots__ = ["points"]
    POINTS_FIELD_NUMBER: _ClassVar[int]
    points: _containers.RepeatedCompositeFieldContainer[Point]
    def __init__(
        self, points: _Optional[_Iterable[_Union[Point, _Mapping]]] = ...
    ) -> None: ...

class BSFCCurve(_message.Message):
    __slots__ = ["x_label", "y_label", "curve"]
    X_LABEL_FIELD_NUMBER: _ClassVar[int]
    Y_LABEL_FIELD_NUMBER: _ClassVar[int]
    CURVE_FIELD_NUMBER: _ClassVar[int]
    x_label: str
    y_label: str
    curve: Curve1D
    def __init__(
        self,
        x_label: _Optional[str] = ...,
        y_label: _Optional[str] = ...,
        curve: _Optional[_Union[Curve1D, _Mapping]] = ...,
    ) -> None: ...

class EfficiencyCurve(_message.Message):
    __slots__ = ["x_label", "y_label", "curve"]
    X_LABEL_FIELD_NUMBER: _ClassVar[int]
    Y_LABEL_FIELD_NUMBER: _ClassVar[int]
    CURVE_FIELD_NUMBER: _ClassVar[int]
    x_label: str
    y_label: str
    curve: Curve1D
    def __init__(
        self,
        x_label: _Optional[str] = ...,
        y_label: _Optional[str] = ...,
        curve: _Optional[_Union[Curve1D, _Mapping]] = ...,
    ) -> None: ...

class BSFC(_message.Message):
    __slots__ = ["curve", "value"]
    CURVE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    curve: BSFCCurve
    value: float
    def __init__(
        self,
        curve: _Optional[_Union[BSFCCurve, _Mapping]] = ...,
        value: _Optional[float] = ...,
    ) -> None: ...

class Efficiency(_message.Message):
    __slots__ = ["curve", "value"]
    CURVE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    curve: EfficiencyCurve
    value: float
    def __init__(
        self,
        curve: _Optional[_Union[EfficiencyCurve, _Mapping]] = ...,
        value: _Optional[float] = ...,
    ) -> None: ...

class PowerCurve(_message.Message):
    __slots__ = ["x_label", "y_label", "curve"]
    X_LABEL_FIELD_NUMBER: _ClassVar[int]
    Y_LABEL_FIELD_NUMBER: _ClassVar[int]
    CURVE_FIELD_NUMBER: _ClassVar[int]
    x_label: str
    y_label: str
    curve: Curve1D
    def __init__(
        self,
        x_label: _Optional[str] = ...,
        y_label: _Optional[str] = ...,
        curve: _Optional[_Union[Curve1D, _Mapping]] = ...,
    ) -> None: ...

class PropulsionPowerTimeSeries(_message.Message):
    __slots__ = ["x_label", "y_label", "propulsor_id", "curve"]
    X_LABEL_FIELD_NUMBER: _ClassVar[int]
    Y_LABEL_FIELD_NUMBER: _ClassVar[int]
    PROPULSOR_ID_FIELD_NUMBER: _ClassVar[int]
    CURVE_FIELD_NUMBER: _ClassVar[int]
    x_label: str
    y_label: str
    propulsor_id: int
    curve: Curve1D
    def __init__(
        self,
        x_label: _Optional[str] = ...,
        y_label: _Optional[str] = ...,
        propulsor_id: _Optional[int] = ...,
        curve: _Optional[_Union[Curve1D, _Mapping]] = ...,
    ) -> None: ...

class AuxiliaryLoadTimeSeries(_message.Message):
    __slots__ = ["x_label", "y_label", "switchboard_id", "curve"]
    X_LABEL_FIELD_NUMBER: _ClassVar[int]
    Y_LABEL_FIELD_NUMBER: _ClassVar[int]
    SWITCHBOARD_ID_FIELD_NUMBER: _ClassVar[int]
    CURVE_FIELD_NUMBER: _ClassVar[int]
    x_label: str
    y_label: str
    switchboard_id: int
    curve: Curve1D
    def __init__(
        self,
        x_label: _Optional[str] = ...,
        y_label: _Optional[str] = ...,
        switchboard_id: _Optional[int] = ...,
        curve: _Optional[_Union[Curve1D, _Mapping]] = ...,
    ) -> None: ...

class AuxiliaryLoad(_message.Message):
    __slots__ = ["switchboard_id", "load_kw"]
    SWITCHBOARD_ID_FIELD_NUMBER: _ClassVar[int]
    LOAD_KW_FIELD_NUMBER: _ClassVar[int]
    switchboard_id: int
    load_kw: float
    def __init__(
        self, switchboard_id: _Optional[int] = ..., load_kw: _Optional[float] = ...
    ) -> None: ...

class EmissionCurve(_message.Message):
    __slots__ = ["x_label", "y_label", "curve", "emission_type"]
    X_LABEL_FIELD_NUMBER: _ClassVar[int]
    Y_LABEL_FIELD_NUMBER: _ClassVar[int]
    CURVE_FIELD_NUMBER: _ClassVar[int]
    EMISSION_TYPE_FIELD_NUMBER: _ClassVar[int]
    x_label: str
    y_label: str
    curve: Curve1D
    emission_type: EmissionType
    def __init__(
        self,
        x_label: _Optional[str] = ...,
        y_label: _Optional[str] = ...,
        curve: _Optional[_Union[Curve1D, _Mapping]] = ...,
        emission_type: _Optional[_Union[EmissionType, str]] = ...,
    ) -> None: ...

class Gear(_message.Message):
    __slots__ = [
        "name",
        "gear_ratio",
        "rated_power_kw",
        "rated_speed_rpm",
        "efficiency",
        "order_from_switchboard_or_shaftline",
        "unit_price_usd",
        "uid",
    ]
    NAME_FIELD_NUMBER: _ClassVar[int]
    GEAR_RATIO_FIELD_NUMBER: _ClassVar[int]
    RATED_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    RATED_SPEED_RPM_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    UNIT_PRICE_USD_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    gear_ratio: float
    rated_power_kw: float
    rated_speed_rpm: float
    efficiency: Efficiency
    order_from_switchboard_or_shaftline: int
    unit_price_usd: float
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        gear_ratio: _Optional[float] = ...,
        rated_power_kw: _Optional[float] = ...,
        rated_speed_rpm: _Optional[float] = ...,
        efficiency: _Optional[_Union[Efficiency, _Mapping]] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        unit_price_usd: _Optional[float] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...

class Fuel(_message.Message):
    __slots__ = ["fuel_type", "fuel_origin"]
    FUEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    FUEL_ORIGIN_FIELD_NUMBER: _ClassVar[int]
    fuel_type: FuelType
    fuel_origin: FuelOrigin
    def __init__(
        self,
        fuel_type: _Optional[_Union[FuelType, str]] = ...,
        fuel_origin: _Optional[_Union[FuelOrigin, str]] = ...,
    ) -> None: ...

class Engine(_message.Message):
    __slots__ = [
        "name",
        "rated_power_kw",
        "rated_speed_rpm",
        "bsfc",
        "main_fuel",
        "order_from_switchboard_or_shaftline",
        "pilot_bsfc",
        "pilot_fuel",
        "nox_calculation_method",
        "emission_curves",
        "engine_cycle_type",
        "unit_price_usd",
        "start_delay_s",
        "turn_off_power_kw",
        "uid",
    ]

    class NOxCalculationMethod(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        TIER_2: _ClassVar[Engine.NOxCalculationMethod]
        TIER_1: _ClassVar[Engine.NOxCalculationMethod]
        TIER_3: _ClassVar[Engine.NOxCalculationMethod]
        CURVE: _ClassVar[Engine.NOxCalculationMethod]
    TIER_2: Engine.NOxCalculationMethod
    TIER_1: Engine.NOxCalculationMethod
    TIER_3: Engine.NOxCalculationMethod
    CURVE: Engine.NOxCalculationMethod

    class EngineCycleType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        NONE: _ClassVar[Engine.EngineCycleType]
        DIESEL: _ClassVar[Engine.EngineCycleType]
        OTTO: _ClassVar[Engine.EngineCycleType]
        LEAN_BURN_SPARK_IGNITION: _ClassVar[Engine.EngineCycleType]
    NONE: Engine.EngineCycleType
    DIESEL: Engine.EngineCycleType
    OTTO: Engine.EngineCycleType
    LEAN_BURN_SPARK_IGNITION: Engine.EngineCycleType
    NAME_FIELD_NUMBER: _ClassVar[int]
    RATED_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    RATED_SPEED_RPM_FIELD_NUMBER: _ClassVar[int]
    BSFC_FIELD_NUMBER: _ClassVar[int]
    MAIN_FUEL_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    PILOT_BSFC_FIELD_NUMBER: _ClassVar[int]
    PILOT_FUEL_FIELD_NUMBER: _ClassVar[int]
    NOX_CALCULATION_METHOD_FIELD_NUMBER: _ClassVar[int]
    EMISSION_CURVES_FIELD_NUMBER: _ClassVar[int]
    ENGINE_CYCLE_TYPE_FIELD_NUMBER: _ClassVar[int]
    UNIT_PRICE_USD_FIELD_NUMBER: _ClassVar[int]
    START_DELAY_S_FIELD_NUMBER: _ClassVar[int]
    TURN_OFF_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    rated_power_kw: float
    rated_speed_rpm: float
    bsfc: BSFC
    main_fuel: Fuel
    order_from_switchboard_or_shaftline: int
    pilot_bsfc: BSFC
    pilot_fuel: Fuel
    nox_calculation_method: Engine.NOxCalculationMethod
    emission_curves: _containers.RepeatedCompositeFieldContainer[EmissionCurve]
    engine_cycle_type: Engine.EngineCycleType
    unit_price_usd: float
    start_delay_s: float
    turn_off_power_kw: float
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        rated_power_kw: _Optional[float] = ...,
        rated_speed_rpm: _Optional[float] = ...,
        bsfc: _Optional[_Union[BSFC, _Mapping]] = ...,
        main_fuel: _Optional[_Union[Fuel, _Mapping]] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        pilot_bsfc: _Optional[_Union[BSFC, _Mapping]] = ...,
        pilot_fuel: _Optional[_Union[Fuel, _Mapping]] = ...,
        nox_calculation_method: _Optional[
            _Union[Engine.NOxCalculationMethod, str]
        ] = ...,
        emission_curves: _Optional[_Iterable[_Union[EmissionCurve, _Mapping]]] = ...,
        engine_cycle_type: _Optional[_Union[Engine.EngineCycleType, str]] = ...,
        unit_price_usd: _Optional[float] = ...,
        start_delay_s: _Optional[float] = ...,
        turn_off_power_kw: _Optional[float] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...

class COGAS(_message.Message):
    __slots__ = [
        "name",
        "rated_power_kw",
        "rated_speed_rpm",
        "efficiency",
        "gas_turbine_power_curve",
        "steam_turbine_power_curve",
        "fuel",
        "order_from_switchboard_or_shaftline",
        "nox_calculation_method",
        "emission_curves",
        "unit_price_usd",
        "start_delay_s",
        "turn_off_power_kw",
        "uid",
    ]
    NAME_FIELD_NUMBER: _ClassVar[int]
    RATED_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    RATED_SPEED_RPM_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_FIELD_NUMBER: _ClassVar[int]
    GAS_TURBINE_POWER_CURVE_FIELD_NUMBER: _ClassVar[int]
    STEAM_TURBINE_POWER_CURVE_FIELD_NUMBER: _ClassVar[int]
    FUEL_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    NOX_CALCULATION_METHOD_FIELD_NUMBER: _ClassVar[int]
    EMISSION_CURVES_FIELD_NUMBER: _ClassVar[int]
    UNIT_PRICE_USD_FIELD_NUMBER: _ClassVar[int]
    START_DELAY_S_FIELD_NUMBER: _ClassVar[int]
    TURN_OFF_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    rated_power_kw: float
    rated_speed_rpm: float
    efficiency: Efficiency
    gas_turbine_power_curve: PowerCurve
    steam_turbine_power_curve: PowerCurve
    fuel: Fuel
    order_from_switchboard_or_shaftline: int
    nox_calculation_method: Engine.NOxCalculationMethod
    emission_curves: _containers.RepeatedCompositeFieldContainer[EmissionCurve]
    unit_price_usd: float
    start_delay_s: float
    turn_off_power_kw: float
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        rated_power_kw: _Optional[float] = ...,
        rated_speed_rpm: _Optional[float] = ...,
        efficiency: _Optional[_Union[Efficiency, _Mapping]] = ...,
        gas_turbine_power_curve: _Optional[_Union[PowerCurve, _Mapping]] = ...,
        steam_turbine_power_curve: _Optional[_Union[PowerCurve, _Mapping]] = ...,
        fuel: _Optional[_Union[Fuel, _Mapping]] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        nox_calculation_method: _Optional[
            _Union[Engine.NOxCalculationMethod, str]
        ] = ...,
        emission_curves: _Optional[_Iterable[_Union[EmissionCurve, _Mapping]]] = ...,
        unit_price_usd: _Optional[float] = ...,
        start_delay_s: _Optional[float] = ...,
        turn_off_power_kw: _Optional[float] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...

class ElectricMachine(_message.Message):
    __slots__ = [
        "name",
        "rated_power_kw",
        "rated_speed_rpm",
        "efficiency",
        "order_from_switchboard_or_shaftline",
        "unit_price_usd",
        "uid",
    ]
    NAME_FIELD_NUMBER: _ClassVar[int]
    RATED_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    RATED_SPEED_RPM_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    UNIT_PRICE_USD_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    rated_power_kw: float
    rated_speed_rpm: float
    efficiency: Efficiency
    order_from_switchboard_or_shaftline: int
    unit_price_usd: float
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        rated_power_kw: _Optional[float] = ...,
        rated_speed_rpm: _Optional[float] = ...,
        efficiency: _Optional[_Union[Efficiency, _Mapping]] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        unit_price_usd: _Optional[float] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...

class Battery(_message.Message):
    __slots__ = [
        "name",
        "energy_capacity_kwh",
        "rated_charging_rate_c",
        "rated_discharging_rate_c",
        "efficiency_charging",
        "efficiency_discharging",
        "initial_state_of_charge",
        "order_from_switchboard_or_shaftline",
        "unit_price_usd",
        "self_discharge_percent_per_day",
        "state_of_energy_minimum",
        "state_of_energy_maximum",
        "uid",
    ]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ENERGY_CAPACITY_KWH_FIELD_NUMBER: _ClassVar[int]
    RATED_CHARGING_RATE_C_FIELD_NUMBER: _ClassVar[int]
    RATED_DISCHARGING_RATE_C_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_CHARGING_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_DISCHARGING_FIELD_NUMBER: _ClassVar[int]
    INITIAL_STATE_OF_CHARGE_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    UNIT_PRICE_USD_FIELD_NUMBER: _ClassVar[int]
    SELF_DISCHARGE_PERCENT_PER_DAY_FIELD_NUMBER: _ClassVar[int]
    STATE_OF_ENERGY_MINIMUM_FIELD_NUMBER: _ClassVar[int]
    STATE_OF_ENERGY_MAXIMUM_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    energy_capacity_kwh: float
    rated_charging_rate_c: float
    rated_discharging_rate_c: float
    efficiency_charging: float
    efficiency_discharging: float
    initial_state_of_charge: float
    order_from_switchboard_or_shaftline: int
    unit_price_usd: float
    self_discharge_percent_per_day: float
    state_of_energy_minimum: float
    state_of_energy_maximum: float
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        energy_capacity_kwh: _Optional[float] = ...,
        rated_charging_rate_c: _Optional[float] = ...,
        rated_discharging_rate_c: _Optional[float] = ...,
        efficiency_charging: _Optional[float] = ...,
        efficiency_discharging: _Optional[float] = ...,
        initial_state_of_charge: _Optional[float] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        unit_price_usd: _Optional[float] = ...,
        self_discharge_percent_per_day: _Optional[float] = ...,
        state_of_energy_minimum: _Optional[float] = ...,
        state_of_energy_maximum: _Optional[float] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...

class ElectricComponent(_message.Message):
    __slots__ = [
        "name",
        "rated_power_kw",
        "efficiency",
        "order_from_switchboard_or_shaftline",
        "unit_price_usd",
        "uid",
    ]
    NAME_FIELD_NUMBER: _ClassVar[int]
    RATED_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    UNIT_PRICE_USD_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    rated_power_kw: float
    efficiency: Efficiency
    order_from_switchboard_or_shaftline: int
    unit_price_usd: float
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        rated_power_kw: _Optional[float] = ...,
        efficiency: _Optional[_Union[Efficiency, _Mapping]] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        unit_price_usd: _Optional[float] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...

class FuelCell(_message.Message):
    __slots__ = [
        "name",
        "rated_power_kw",
        "efficiency",
        "order_from_switchboard_or_shaftline",
        "fuel",
        "unit_price_usd",
        "number_modules",
        "power_minimum_specific",
        "start_delay_s",
        "uid",
    ]
    NAME_FIELD_NUMBER: _ClassVar[int]
    RATED_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    FUEL_FIELD_NUMBER: _ClassVar[int]
    UNIT_PRICE_USD_FIELD_NUMBER: _ClassVar[int]
    NUMBER_MODULES_FIELD_NUMBER: _ClassVar[int]
    POWER_MINIMUM_SPECIFIC_FIELD_NUMBER: _ClassVar[int]
    START_DELAY_S_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    rated_power_kw: float
    efficiency: Efficiency
    order_from_switchboard_or_shaftline: int
    fuel: Fuel
    unit_price_usd: float
    number_modules: int
    power_minimum_specific: float
    start_delay_s: float
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        rated_power_kw: _Optional[float] = ...,
        efficiency: _Optional[_Union[Efficiency, _Mapping]] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        fuel: _Optional[_Union[Fuel, _Mapping]] = ...,
        unit_price_usd: _Optional[float] = ...,
        number_modules: _Optional[int] = ...,
        power_minimum_specific: _Optional[float] = ...,
        start_delay_s: _Optional[float] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...

class Propeller(_message.Message):
    __slots__ = [
        "name",
        "efficiency",
        "propulsor_id",
        "order_from_switchboard_or_shaftline",
        "uid",
    ]
    NAME_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_FIELD_NUMBER: _ClassVar[int]
    PROPULSOR_ID_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    efficiency: Efficiency
    propulsor_id: int
    order_from_switchboard_or_shaftline: int
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        efficiency: _Optional[_Union[Efficiency, _Mapping]] = ...,
        propulsor_id: _Optional[int] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...

class BusBreaker(_message.Message):
    __slots__ = ["switchboard_to"]
    SWITCHBOARD_TO_FIELD_NUMBER: _ClassVar[int]
    switchboard_to: int
    def __init__(self, switchboard_to: _Optional[int] = ...) -> None: ...

class SuperCapacitor(_message.Message):
    __slots__ = [
        "name",
        "energy_capacity_wh",
        "rated_power_kw",
        "efficiency_charging",
        "efficiency_discharging",
        "initial_state_of_charge",
        "order_from_switchboard_or_shaftline",
        "unit_price_usd",
        "uid",
    ]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ENERGY_CAPACITY_WH_FIELD_NUMBER: _ClassVar[int]
    RATED_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_CHARGING_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_DISCHARGING_FIELD_NUMBER: _ClassVar[int]
    INITIAL_STATE_OF_CHARGE_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    UNIT_PRICE_USD_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    energy_capacity_wh: float
    rated_power_kw: float
    efficiency_charging: float
    efficiency_discharging: float
    initial_state_of_charge: float
    order_from_switchboard_or_shaftline: int
    unit_price_usd: float
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        energy_capacity_wh: _Optional[float] = ...,
        rated_power_kw: _Optional[float] = ...,
        efficiency_charging: _Optional[float] = ...,
        efficiency_discharging: _Optional[float] = ...,
        initial_state_of_charge: _Optional[float] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        unit_price_usd: _Optional[float] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...

class MechanicalComponent(_message.Message):
    __slots__ = [
        "name",
        "rated_power_kw",
        "efficiency",
        "order_from_switchboard_or_shaftline",
        "unit_price_usd",
        "uid",
    ]
    NAME_FIELD_NUMBER: _ClassVar[int]
    RATED_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    UNIT_PRICE_USD_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    rated_power_kw: float
    efficiency: Efficiency
    order_from_switchboard_or_shaftline: int
    unit_price_usd: float
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        rated_power_kw: _Optional[float] = ...,
        efficiency: _Optional[_Union[Efficiency, _Mapping]] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        unit_price_usd: _Optional[float] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...

class Subsystem(_message.Message):
    __slots__ = [
        "gear",
        "engine",
        "electric_machine",
        "transformer",
        "converter1",
        "converter2",
        "battery",
        "fuel_cell",
        "propeller",
        "bus_breaker",
        "supercapacitor",
        "other_load",
        "cogas",
        "power_type",
        "component_type",
        "name",
        "rated_power_kw",
        "rated_speed_rpm",
        "ramp_up_rate_limit_percent_per_second",
        "ramp_down_rate_limit_percent_per_second",
        "base_load_order",
        "uid",
        "multi_fuel_engine",
    ]

    class PowerType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        NONE1: _ClassVar[Subsystem.PowerType]
        POWER_SOURCE: _ClassVar[Subsystem.PowerType]
        POWER_CONSUMER: _ClassVar[Subsystem.PowerType]
        PTI_PTO: _ClassVar[Subsystem.PowerType]
        ENERGY_STORAGE: _ClassVar[Subsystem.PowerType]
        SHORE_CONNECTION: _ClassVar[Subsystem.PowerType]
    NONE1: Subsystem.PowerType
    POWER_SOURCE: Subsystem.PowerType
    POWER_CONSUMER: Subsystem.PowerType
    PTI_PTO: Subsystem.PowerType
    ENERGY_STORAGE: Subsystem.PowerType
    SHORE_CONNECTION: Subsystem.PowerType

    class ComponentType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        NONE: _ClassVar[Subsystem.ComponentType]
        MAIN_ENGINE: _ClassVar[Subsystem.ComponentType]
        AUXILIARY_ENGINE: _ClassVar[Subsystem.ComponentType]
        GENERATOR: _ClassVar[Subsystem.ComponentType]
        PROPULSION_DRIVE: _ClassVar[Subsystem.ComponentType]
        OTHER_LOAD: _ClassVar[Subsystem.ComponentType]
        PTI_PTO_SYSTEM: _ClassVar[Subsystem.ComponentType]
        BATTERY_SYSTEM: _ClassVar[Subsystem.ComponentType]
        FUEL_CELL_SYSTEM: _ClassVar[Subsystem.ComponentType]
        RECTIFIER: _ClassVar[Subsystem.ComponentType]
        MAIN_ENGINE_WITH_GEARBOX: _ClassVar[Subsystem.ComponentType]
        ELECTRIC_MOTOR: _ClassVar[Subsystem.ComponentType]
        GENSET: _ClassVar[Subsystem.ComponentType]
        TRANSFORMER: _ClassVar[Subsystem.ComponentType]
        INVERTER: _ClassVar[Subsystem.ComponentType]
        CIRCUIT_BREAKER: _ClassVar[Subsystem.ComponentType]
        ACTIVE_FRONT_END: _ClassVar[Subsystem.ComponentType]
        POWER_CONVERTER: _ClassVar[Subsystem.ComponentType]
        SYNCHRONOUS_MACHINE: _ClassVar[Subsystem.ComponentType]
        INDUCTION_MACHINE: _ClassVar[Subsystem.ComponentType]
        GEARBOX: _ClassVar[Subsystem.ComponentType]
        FUEL_CELL: _ClassVar[Subsystem.ComponentType]
        PROPELLER_LOAD: _ClassVar[Subsystem.ComponentType]
        OTHER_MECHANICAL_LOAD: _ClassVar[Subsystem.ComponentType]
        BATTERY: _ClassVar[Subsystem.ComponentType]
        SUPERCAPACITOR: _ClassVar[Subsystem.ComponentType]
        SUPERCAPACITOR_SYSTEM: _ClassVar[Subsystem.ComponentType]
        SHORE_POWER: _ClassVar[Subsystem.ComponentType]
        COGAS: _ClassVar[Subsystem.ComponentType]
        COGES: _ClassVar[Subsystem.ComponentType]
    NONE: Subsystem.ComponentType
    MAIN_ENGINE: Subsystem.ComponentType
    AUXILIARY_ENGINE: Subsystem.ComponentType
    GENERATOR: Subsystem.ComponentType
    PROPULSION_DRIVE: Subsystem.ComponentType
    OTHER_LOAD: Subsystem.ComponentType
    PTI_PTO_SYSTEM: Subsystem.ComponentType
    BATTERY_SYSTEM: Subsystem.ComponentType
    FUEL_CELL_SYSTEM: Subsystem.ComponentType
    RECTIFIER: Subsystem.ComponentType
    MAIN_ENGINE_WITH_GEARBOX: Subsystem.ComponentType
    ELECTRIC_MOTOR: Subsystem.ComponentType
    GENSET: Subsystem.ComponentType
    TRANSFORMER: Subsystem.ComponentType
    INVERTER: Subsystem.ComponentType
    CIRCUIT_BREAKER: Subsystem.ComponentType
    ACTIVE_FRONT_END: Subsystem.ComponentType
    POWER_CONVERTER: Subsystem.ComponentType
    SYNCHRONOUS_MACHINE: Subsystem.ComponentType
    INDUCTION_MACHINE: Subsystem.ComponentType
    GEARBOX: Subsystem.ComponentType
    FUEL_CELL: Subsystem.ComponentType
    PROPELLER_LOAD: Subsystem.ComponentType
    OTHER_MECHANICAL_LOAD: Subsystem.ComponentType
    BATTERY: Subsystem.ComponentType
    SUPERCAPACITOR: Subsystem.ComponentType
    SUPERCAPACITOR_SYSTEM: Subsystem.ComponentType
    SHORE_POWER: Subsystem.ComponentType
    COGAS: Subsystem.ComponentType
    COGES: Subsystem.ComponentType
    GEAR_FIELD_NUMBER: _ClassVar[int]
    ENGINE_FIELD_NUMBER: _ClassVar[int]
    ELECTRIC_MACHINE_FIELD_NUMBER: _ClassVar[int]
    TRANSFORMER_FIELD_NUMBER: _ClassVar[int]
    CONVERTER1_FIELD_NUMBER: _ClassVar[int]
    CONVERTER2_FIELD_NUMBER: _ClassVar[int]
    BATTERY_FIELD_NUMBER: _ClassVar[int]
    FUEL_CELL_FIELD_NUMBER: _ClassVar[int]
    PROPELLER_FIELD_NUMBER: _ClassVar[int]
    BUS_BREAKER_FIELD_NUMBER: _ClassVar[int]
    SUPERCAPACITOR_FIELD_NUMBER: _ClassVar[int]
    OTHER_LOAD_FIELD_NUMBER: _ClassVar[int]
    COGAS_FIELD_NUMBER: _ClassVar[int]
    POWER_TYPE_FIELD_NUMBER: _ClassVar[int]
    COMPONENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    RATED_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    RATED_SPEED_RPM_FIELD_NUMBER: _ClassVar[int]
    RAMP_UP_RATE_LIMIT_PERCENT_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    RAMP_DOWN_RATE_LIMIT_PERCENT_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    BASE_LOAD_ORDER_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    MULTI_FUEL_ENGINE_FIELD_NUMBER: _ClassVar[int]
    gear: Gear
    engine: Engine
    electric_machine: ElectricMachine
    transformer: ElectricComponent
    converter1: ElectricComponent
    converter2: ElectricComponent
    battery: Battery
    fuel_cell: FuelCell
    propeller: Propeller
    bus_breaker: BusBreaker
    supercapacitor: SuperCapacitor
    other_load: ElectricComponent
    cogas: COGAS
    power_type: Subsystem.PowerType
    component_type: Subsystem.ComponentType
    name: str
    rated_power_kw: float
    rated_speed_rpm: float
    ramp_up_rate_limit_percent_per_second: float
    ramp_down_rate_limit_percent_per_second: float
    base_load_order: int
    uid: str
    multi_fuel_engine: MultiFuelEngine
    def __init__(
        self,
        gear: _Optional[_Union[Gear, _Mapping]] = ...,
        engine: _Optional[_Union[Engine, _Mapping]] = ...,
        electric_machine: _Optional[_Union[ElectricMachine, _Mapping]] = ...,
        transformer: _Optional[_Union[ElectricComponent, _Mapping]] = ...,
        converter1: _Optional[_Union[ElectricComponent, _Mapping]] = ...,
        converter2: _Optional[_Union[ElectricComponent, _Mapping]] = ...,
        battery: _Optional[_Union[Battery, _Mapping]] = ...,
        fuel_cell: _Optional[_Union[FuelCell, _Mapping]] = ...,
        propeller: _Optional[_Union[Propeller, _Mapping]] = ...,
        bus_breaker: _Optional[_Union[BusBreaker, _Mapping]] = ...,
        supercapacitor: _Optional[_Union[SuperCapacitor, _Mapping]] = ...,
        other_load: _Optional[_Union[ElectricComponent, _Mapping]] = ...,
        cogas: _Optional[_Union[COGAS, _Mapping]] = ...,
        power_type: _Optional[_Union[Subsystem.PowerType, str]] = ...,
        component_type: _Optional[_Union[Subsystem.ComponentType, str]] = ...,
        name: _Optional[str] = ...,
        rated_power_kw: _Optional[float] = ...,
        rated_speed_rpm: _Optional[float] = ...,
        ramp_up_rate_limit_percent_per_second: _Optional[float] = ...,
        ramp_down_rate_limit_percent_per_second: _Optional[float] = ...,
        base_load_order: _Optional[int] = ...,
        uid: _Optional[str] = ...,
        multi_fuel_engine: _Optional[_Union[MultiFuelEngine, _Mapping]] = ...,
    ) -> None: ...

class Switchboard(_message.Message):
    __slots__ = ["switchboard_id", "subsystems"]
    SWITCHBOARD_ID_FIELD_NUMBER: _ClassVar[int]
    SUBSYSTEMS_FIELD_NUMBER: _ClassVar[int]
    switchboard_id: int
    subsystems: _containers.RepeatedCompositeFieldContainer[Subsystem]
    def __init__(
        self,
        switchboard_id: _Optional[int] = ...,
        subsystems: _Optional[_Iterable[_Union[Subsystem, _Mapping]]] = ...,
    ) -> None: ...

class ShaftLine(_message.Message):
    __slots__ = ["shaft_line_id", "subsystems"]
    SHAFT_LINE_ID_FIELD_NUMBER: _ClassVar[int]
    SUBSYSTEMS_FIELD_NUMBER: _ClassVar[int]
    shaft_line_id: int
    subsystems: _containers.RepeatedCompositeFieldContainer[Subsystem]
    def __init__(
        self,
        shaft_line_id: _Optional[int] = ...,
        subsystems: _Optional[_Iterable[_Union[Subsystem, _Mapping]]] = ...,
    ) -> None: ...

class MechanicalSystem(_message.Message):
    __slots__ = ["shaft_lines"]
    SHAFT_LINES_FIELD_NUMBER: _ClassVar[int]
    shaft_lines: _containers.RepeatedCompositeFieldContainer[ShaftLine]
    def __init__(
        self, shaft_lines: _Optional[_Iterable[_Union[ShaftLine, _Mapping]]] = ...
    ) -> None: ...

class ElectricSystem(_message.Message):
    __slots__ = ["switchboards"]
    SWITCHBOARDS_FIELD_NUMBER: _ClassVar[int]
    switchboards: _containers.RepeatedCompositeFieldContainer[Switchboard]
    def __init__(
        self, switchboards: _Optional[_Iterable[_Union[Switchboard, _Mapping]]] = ...
    ) -> None: ...

class FuelStorage(_message.Message):
    __slots__ = ["fuel_type", "capacity_kg"]
    FUEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    CAPACITY_KG_FIELD_NUMBER: _ClassVar[int]
    fuel_type: FuelType
    capacity_kg: float
    def __init__(
        self,
        fuel_type: _Optional[_Union[FuelType, str]] = ...,
        capacity_kg: _Optional[float] = ...,
    ) -> None: ...

class MachinerySystem(_message.Message):
    __slots__ = [
        "name",
        "propulsion_type",
        "fuel_storage",
        "maximum_allowed_genset_load_percentage",
        "mechanical_system",
        "electric_system",
        "maximum_allowed_fuel_cell_load_percentage",
        "average_base_load_percentage",
    ]

    class PropulsionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        MECHANICAL: _ClassVar[MachinerySystem.PropulsionType]
        ELECTRIC: _ClassVar[MachinerySystem.PropulsionType]
        HYBRID: _ClassVar[MachinerySystem.PropulsionType]
    MECHANICAL: MachinerySystem.PropulsionType
    ELECTRIC: MachinerySystem.PropulsionType
    HYBRID: MachinerySystem.PropulsionType
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROPULSION_TYPE_FIELD_NUMBER: _ClassVar[int]
    FUEL_STORAGE_FIELD_NUMBER: _ClassVar[int]
    MAXIMUM_ALLOWED_GENSET_LOAD_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    MECHANICAL_SYSTEM_FIELD_NUMBER: _ClassVar[int]
    ELECTRIC_SYSTEM_FIELD_NUMBER: _ClassVar[int]
    MAXIMUM_ALLOWED_FUEL_CELL_LOAD_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    AVERAGE_BASE_LOAD_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    name: str
    propulsion_type: MachinerySystem.PropulsionType
    fuel_storage: _containers.RepeatedCompositeFieldContainer[FuelStorage]
    maximum_allowed_genset_load_percentage: float
    mechanical_system: MechanicalSystem
    electric_system: ElectricSystem
    maximum_allowed_fuel_cell_load_percentage: float
    average_base_load_percentage: float
    def __init__(
        self,
        name: _Optional[str] = ...,
        propulsion_type: _Optional[_Union[MachinerySystem.PropulsionType, str]] = ...,
        fuel_storage: _Optional[_Iterable[_Union[FuelStorage, _Mapping]]] = ...,
        maximum_allowed_genset_load_percentage: _Optional[float] = ...,
        mechanical_system: _Optional[_Union[MechanicalSystem, _Mapping]] = ...,
        electric_system: _Optional[_Union[ElectricSystem, _Mapping]] = ...,
        maximum_allowed_fuel_cell_load_percentage: _Optional[float] = ...,
        average_base_load_percentage: _Optional[float] = ...,
    ) -> None: ...

class MultiFuelEngine(_message.Message):
    __slots__ = [
        "name",
        "rated_power_kw",
        "rated_speed_rpm",
        "fuel_modes",
        "order_from_switchboard_or_shaftline",
        "unit_price_usd",
        "start_delay_s",
        "turn_off_power_kw",
        "uid",
    ]

    class FuelMode(_message.Message):
        __slots__ = [
            "main_fuel",
            "main_bsfc",
            "pilot_fuel",
            "pilot_bsfc",
            "emission_curves",
            "engine_cycle_type",
            "nox_calculation_method",
        ]
        MAIN_FUEL_FIELD_NUMBER: _ClassVar[int]
        MAIN_BSFC_FIELD_NUMBER: _ClassVar[int]
        PILOT_FUEL_FIELD_NUMBER: _ClassVar[int]
        PILOT_BSFC_FIELD_NUMBER: _ClassVar[int]
        EMISSION_CURVES_FIELD_NUMBER: _ClassVar[int]
        ENGINE_CYCLE_TYPE_FIELD_NUMBER: _ClassVar[int]
        NOX_CALCULATION_METHOD_FIELD_NUMBER: _ClassVar[int]
        main_fuel: Fuel
        main_bsfc: BSFC
        pilot_fuel: Fuel
        pilot_bsfc: BSFC
        emission_curves: _containers.RepeatedCompositeFieldContainer[EmissionCurve]
        engine_cycle_type: Engine.EngineCycleType
        nox_calculation_method: Engine.NOxCalculationMethod
        def __init__(
            self,
            main_fuel: _Optional[_Union[Fuel, _Mapping]] = ...,
            main_bsfc: _Optional[_Union[BSFC, _Mapping]] = ...,
            pilot_fuel: _Optional[_Union[Fuel, _Mapping]] = ...,
            pilot_bsfc: _Optional[_Union[BSFC, _Mapping]] = ...,
            emission_curves: _Optional[
                _Iterable[_Union[EmissionCurve, _Mapping]]
            ] = ...,
            engine_cycle_type: _Optional[_Union[Engine.EngineCycleType, str]] = ...,
            nox_calculation_method: _Optional[
                _Union[Engine.NOxCalculationMethod, str]
            ] = ...,
        ) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    RATED_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    RATED_SPEED_RPM_FIELD_NUMBER: _ClassVar[int]
    FUEL_MODES_FIELD_NUMBER: _ClassVar[int]
    ORDER_FROM_SWITCHBOARD_OR_SHAFTLINE_FIELD_NUMBER: _ClassVar[int]
    UNIT_PRICE_USD_FIELD_NUMBER: _ClassVar[int]
    START_DELAY_S_FIELD_NUMBER: _ClassVar[int]
    TURN_OFF_POWER_KW_FIELD_NUMBER: _ClassVar[int]
    UID_FIELD_NUMBER: _ClassVar[int]
    name: str
    rated_power_kw: float
    rated_speed_rpm: float
    fuel_modes: _containers.RepeatedCompositeFieldContainer[MultiFuelEngine.FuelMode]
    order_from_switchboard_or_shaftline: int
    unit_price_usd: float
    start_delay_s: float
    turn_off_power_kw: float
    uid: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        rated_power_kw: _Optional[float] = ...,
        rated_speed_rpm: _Optional[float] = ...,
        fuel_modes: _Optional[
            _Iterable[_Union[MultiFuelEngine.FuelMode, _Mapping]]
        ] = ...,
        order_from_switchboard_or_shaftline: _Optional[int] = ...,
        unit_price_usd: _Optional[float] = ...,
        start_delay_s: _Optional[float] = ...,
        turn_off_power_kw: _Optional[float] = ...,
        uid: _Optional[str] = ...,
    ) -> None: ...
