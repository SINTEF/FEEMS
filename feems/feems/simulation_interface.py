from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Dict, Tuple

import numpy as np
from feems.fuel import TypeFuel

from feems.types_for_feems import FEEMSResult, Numeric

from . import get_logger
from .components_model import SwbId
from .system_model import ElectricPowerSystem


logger = get_logger(__name__)


class EnergySourceType(Enum):
    BATTERY = "Battery"
    HYDROGEN = "Hydrogen"
    LNG_DIESEL = "LNG Diesel"
    AMMONIA = "Ammonia"


@dataclass
class EnergySource:
    source_type: EnergySourceType
    rated_capacity: float
    unit: str
    remaining_capacity: float

    def set_remaining_capacity_from_feems_result(
        self,
        feems_result: FEEMSResult,
        ratio_energy_used_in_previous_source: float = 0,
        is_last_energy_source: bool = False,
    ) -> Tuple[float, FEEMSResult]:
        """
        Set the remaining capacity from FEEMS result. If the result exceeds the
        remaining capacity, returns the ratio of energy exceeding capacity to energy required and
        updated feems result.
        """
        co2_factor = feems_result.co2_emission_total_kg / feems_result.fuel_consumption_total_kg
        energy_exceeding_capacity = 0
        if self.source_type == EnergySourceType.BATTERY:
            energy_consumption = -feems_result.energy_stored_total_mj / 3.6
        elif self.source_type == EnergySourceType.HYDROGEN:
            energy_consumption = feems_result.multi_fuel_consumption_total_kg.hydrogen
        elif self.source_type == EnergySourceType.LNG_DIESEL:
            energy_consumption = feems_result.fuel_consumption_total_kg
        else:
            raise TypeError(
                "The energy source type is not valid. It should be " "EnergySourceType enum type."
            )
        energy_consumption_actual = (1 - ratio_energy_used_in_previous_source) * energy_consumption
        self.remaining_capacity -= energy_consumption_actual
        if self.remaining_capacity <= 0 and not is_last_energy_source:
            energy_exceeding_capacity = -self.remaining_capacity  # type: ignore[assignment]
            self.remaining_capacity = 0

        if self.source_type == EnergySourceType.BATTERY:
            actual_energy_stored = -energy_consumption_actual + energy_exceeding_capacity
            feems_result.energy_stored_total_mj = actual_energy_stored * 3.6
            feems_result.energy_consumption_electric_total_mj *= (
                (actual_energy_stored / energy_consumption) if energy_consumption != 0 else 0
            )
        elif self.source_type == EnergySourceType.HYDROGEN:
            fuel = next(
                filter(
                    lambda fuel: fuel.fuel_type == TypeFuel.HYDROGEN,
                    feems_result.multi_fuel_consumption_total_kg.fuels,
                )
            )
            fuel.mass_or_mass_fraction = energy_consumption_actual - energy_exceeding_capacity
        elif self.source_type == EnergySourceType.LNG_DIESEL:
            if feems_result.multi_fuel_consumption_total_kg.diesel > 0:
                fuel = next(
                    filter(
                        lambda fuel: fuel.fuel_type == TypeFuel.DIESEL,
                        feems_result.multi_fuel_consumption_total_kg.fuels,
                    )
                )
                fuel.mass_or_mass_fraction = energy_consumption_actual - energy_exceeding_capacity
                feems_result.co2_emission_total_kg = (
                    energy_consumption_actual - energy_exceeding_capacity
                ) * co2_factor
            elif feems_result.multi_fuel_consumption_total_kg.natural_gas > 0:
                fuel = next(
                    filter(
                        lambda fuel: fuel.fuel_type == TypeFuel.NATURAL_GAS,
                        feems_result.multi_fuel_consumption_total_kg.fuels,
                    )
                )
                fuel.mass_or_mass_fraction = energy_consumption_actual - energy_exceeding_capacity
                feems_result.co2_emission_total_kg = (
                    energy_consumption_actual - energy_exceeding_capacity
                ) * co2_factor
            elif energy_consumption_actual - energy_exceeding_capacity > 0:
                logger.warning(
                    "The energy consumption is positive, but there is no "
                    "fuel consumption in the result."
                )
            else:
                pass

        ratio_energy_used_in_this_energy_source = (
            (energy_consumption_actual - energy_exceeding_capacity) / energy_consumption
            if energy_consumption != 0
            else 0
        )
        ratio_energy_used_in_previous_source += ratio_energy_used_in_this_energy_source
        return ratio_energy_used_in_previous_source, feems_result

    @property
    def consumption(self) -> float:
        return self.rated_capacity - self.remaining_capacity

    def reset_capacity(self) -> float:
        self.remaining_capacity = self.rated_capacity
        return self.remaining_capacity

    def refill_capacity(self, refill: float) -> float:
        self.remaining_capacity += refill
        return self.remaining_capacity

    @property
    def filling_ratio_or_state_of_charge(self) -> float:
        return self.remaining_capacity / self.rated_capacity


class ElectricPowerPlantStatus(NamedTuple):
    bus_tie_breaker_status: (
        np.ndarray
    )  # First index is time index, second is bus_tie_breaker_index
    genset_connection_status: Dict[SwbId, np.ndarray]
    # Dictionary where key is teh swbid, the value is a matrix where the first index is time,
    # and second is genset_index


class SimulationInterface:
    @abstractmethod
    def set_status(
        self,
        *,
        power_kw_per_switchboard: Dict[SwbId, np.ndarray],
        electric_power_system: ElectricPowerSystem,
        time_interval_s: Numeric,
        power_source_priority: EnergySourceType = None,
    ) -> None:
        """Calculate the status of the power plant

        :param power_kw_per_switchboard: A dictionary with power consumption for each switchboard.
        :param electric_power_system: an electric power system instance
        :param time_interval_s: time interval for data
        :param power_source_priority: list of power source that has to be used in order
        """
        pass
