from dataclasses import dataclass, field
from enum import Enum, unique, auto
from functools import reduce
from typing import NewType, NamedTuple, Union, List, Optional, TypeVar, DefaultDict

import numpy as np
import pandas as pd

Power_kW = NewType("Power_kW", float)
Speed_rpm = NewType("Speed_rpm", float)
SwbId = NewType("SwbId", int)


class EngineCycleType(Enum):
    NONE = 0
    DIESEL = auto()
    OTTO = auto()
    LEAN_BURN_SPARK_IGNITION = auto()


class EmissionType(Enum):
    SOX = auto()
    NOX = auto()
    CO = auto()
    PM = auto()
    HC = auto()
    CH4 = auto()
    N2O = auto()


@dataclass
class FEEMSResult:
    from feems.fuel import FuelConsumption, FuelByMassFraction, GHGEmissions

    duration_s: Optional[float] = None
    energy_consumption_electric_total_mj: float = 0.0
    energy_consumption_mechanical_total_mj: float = (
        0.0  # energy consumption of PTI (electric side) or PTO (mechanical side)
    )
    energy_stored_total_mj: float = 0.0
    load_ratio_genset: Optional[float] = None
    running_hours_main_engines_hr: float = 0.0
    running_hours_genset_total_hr: float = 0.0
    running_hours_fuel_cell_total_hr: float = 0.0
    running_hours_pti_pto_total_hr: float = 0.0
    total_emission_kg: Optional[DefaultDict[EmissionType, float]] = None
    detail_result: Optional[pd.DataFrame] = None
    multi_fuel_consumption_total_kg: FuelConsumption = field(default_factory=FuelConsumption)
    co2_emission_total_kg: GHGEmissions = field(default_factory=GHGEmissions)
    energy_input_mechanical_total_mj: float = (
        0.0  # Energy input for generator / PTO (electric side) or PTI (mechanical side)
    )
    energy_input_electric_total_mj: float = 0.0  # Energy input for shore power
    energy_consumption_propulsion_total_mj: float = 0.0  # Energy consumption of propulsion shaft
    energy_consumption_auxiliary_total_mj: float = (
        0.0  # Energy consumption of auxiliary (electric) or mechanical load (mechanical)
    )

    @property
    def fuel_consumption_total_kg(self):
        return self.multi_fuel_consumption_total_kg.total_fuel_consumption

    @property
    def fuel_energy_total_mj(self):
        return reduce(
            lambda acc, fuel: acc + fuel.lhv_mj_per_g * fuel.mass_or_mass_fraction * 1e3,
            self.multi_fuel_consumption_total_kg.fuels,
            0.0,
        )

    def sum_with_freeze_duration(self, other: "FEEMSResult") -> "FEEMSResult":
        """Sum two results and freeze the duration of the first result"""
        return self.__merge(other, freeze_duration=True)

    def sum_and_extend_duration(self, other: "FEEMSResult") -> "FEEMSResult":
        """Sum two results and extend the duration of the first result"""
        return self.__merge(other, freeze_duration=False)

    def __merge(self, other: "FEEMSResult", *, freeze_duration: bool) -> "FEEMSResult":
        res = {}
        for field_name in self.__dict__:
            self_value = getattr(self, field_name)
            other_value = getattr(other, field_name)
            if self_value is None:
                value = other_value
            elif other_value is None:
                value = self_value
            else:
                if field_name == "detail_result":
                    value = pd.concat([self_value, other_value])
                elif field_name == "load_ratio_genset" and freeze_duration:
                    value = max(self_value, other_value)
                elif field_name == "load_ratio_genset" and not freeze_duration:
                    # Average load ratio
                    if self.duration_s is None:
                        value = other_value
                    elif other.duration_s is None:
                        value = self_value
                    else:
                        value = (self_value * self.duration_s + other_value * other.duration_s) / (
                            self.duration_s + other.duration_s
                        )
                elif field_name == "total_emission_kg":
                    value = {k: self_value[k] + other_value[k] for k in self_value}
                elif field_name == "duration_s" and freeze_duration:
                    assert self_value == other_value, (
                        f"The duration of the two results are not "
                        f"equal. {self_value} != {other_value}"
                    )
                    value = self_value
                else:
                    value = self_value + other_value
            res[field_name] = value
        return FEEMSResult(**res)

    def to_list_for_electric_component(self) -> List[Optional[float]]:
        return [
            self.multi_fuel_consumption_total_kg,
            self.energy_consumption_electric_total_mj,
            self.energy_consumption_mechanical_total_mj,
            self.energy_stored_total_mj,
            (self.running_hours_genset_total_hr or 0.0)
            + (self.running_hours_pti_pto_total_hr or 0.0)
            + (self.running_hours_fuel_cell_total_hr or 0.0),
            self.co2_emission_total_kg,
            (self.total_emission_kg[EmissionType.NOX] if self.total_emission_kg else None),
        ]

    def to_list_for_mechanical_component(self) -> List[Optional[float]]:
        return [
            self.multi_fuel_consumption_total_kg,
            self.energy_consumption_electric_total_mj,
            self.energy_consumption_mechanical_total_mj,
            (self.running_hours_main_engines_hr or 0.0)
            + (self.running_hours_pti_pto_total_hr or 0.0),
            self.co2_emission_total_kg,
            (self.total_emission_kg[EmissionType.NOX] if self.total_emission_kg else None),
        ]


@unique
class TypeComponent(Enum):
    NONE = 0
    MAIN_ENGINE = 1
    AUXILIARY_ENGINE = 2
    GENERATOR = 3
    PROPULSION_DRIVE = 4
    OTHER_LOAD = 5
    PTI_PTO_SYSTEM = 6
    BATTERY_SYSTEM = 7
    FUEL_CELL_SYSTEM = 8
    RECTIFIER = 9
    MAIN_ENGINE_WITH_GEARBOX = 10
    ELECTRIC_MOTOR = 11
    GENSET = 12
    TRANSFORMER = 13
    INVERTER = 14
    CIRCUIT_BREAKER = 15
    ACTIVE_FRONT_END = 16
    POWER_CONVERTER = 17
    SYNCHRONOUS_MACHINE = 18
    INDUCTION_MACHINE = 19
    GEARBOX = 20
    FUEL_CELL = 21
    PROPELLER_LOAD = 22
    OTHER_MECHANICAL_LOAD = 23
    BATTERY = 24
    SUPERCAPACITOR = 25
    SUPERCAPACITOR_SYSTEM = 26
    SHORE_POWER = 27
    COGAS = 28
    COGES = 29


@unique
class TypeNode(Enum):
    NONE = 0
    BUS_TIE_BREAKER = 1
    SWITCHBOARD = 2
    BUS = 3
    SHAFTLINE = 4


@unique
class TypePower(Enum):
    NONE = 0
    POWER_SOURCE = 1
    POWER_CONSUMER = 2
    PTI_PTO = 3
    ENERGY_STORAGE = 4
    POWER_TRANSMISSION = 5


@unique
class TypeValueBus(Enum):
    POWER_IN_BY_POWER_TYPE = 0
    POWER_OUT_BY_POWER_TYPE = 1
    LOAD_KW_SOURCES = 2
    POWER_AVAIL_POWER_SOURCES_SYMMETRIC = 3


@unique
class OperationModeForPTIPTO(Enum):
    FULL_PTO = 0
    PARTIAL_PTO = 1
    PARTIAL_PTI = 2
    FULL_PTI = 3
    INDEPENDENT = 4


TimeIntervalList = Union[np.ndarray, List[float], float, int]


class NOxCalculationMethod(Enum):
    CURVE = "Curve"
    TIER_1 = "Tier 1"
    TIER_2 = "Tier 2"
    TIER_3 = "Tier 3"


Numeric = Union[float, int, np.ndarray, List[float], List[int]]
NumericT = TypeVar("NumericT", float, int, np.ndarray, List[float], List[int])


class EmissionCurvePoint(NamedTuple):
    load_ratio: float
    emission_g_per_kwh: float


class EmissionCurve(NamedTuple):
    points_per_kwh: List[EmissionCurvePoint]
    emission: EmissionType
