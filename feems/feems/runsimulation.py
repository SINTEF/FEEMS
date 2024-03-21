from dataclasses import dataclass

from itertools import chain
from typing import Dict, List
from enum import Enum, auto

import numpy as np

from . import get_logger
from .components_model import SwbId
from .simulation_interface import (
    SimulationInterface,
    ElectricPowerPlantStatus,
    EnergySource,
    EnergySourceType,
)
from .system_model import ElectricPowerSystem
from .types_for_feems import TypePower, TypeComponent

logger = get_logger(__name__)


def run_simulation(
    electric_power_system: ElectricPowerSystem,
    simulation_interface: SimulationInterface,
    energy_source_to_prioritize: EnergySourceType = None,
) -> None:
    power_kw_per_switchboard = electric_power_system.get_sum_consumption_kw_sources_switchboard()

    simulation_interface.set_status(
        power_kw_per_switchboard=power_kw_per_switchboard,
        electric_power_system=electric_power_system,
        time_interval_s=electric_power_system.time_interval_s,
        power_source_priority=energy_source_to_prioritize,
    )
    electric_power_system.do_power_balance_calculation()


class EqualEngineSizeAllClosedSimulationInterface(SimulationInterface):
    def __init__(
        self,
        *,
        swb2n_gensets: Dict[SwbId, int],
        rated_power_gensets: float,
        n_bus_ties: int,
        maximum_allowable_genset_load_percentage: float,
    ):
        self.swb2n_gensets = swb2n_gensets
        self.n_gensets = sum([x for x in swb2n_gensets.values()])
        self.n_bus_ties = n_bus_ties
        self.rated_power_gensets = rated_power_gensets
        self.maximum_allowable_genset_load_percentage = maximum_allowable_genset_load_percentage

    def set_status(
        self,
        *,
        power_kw_per_switchboard: Dict[SwbId, np.ndarray],
        electric_power_system: ElectricPowerSystem,
        time_interval_s: np.ndarray,
        power_source_priority: EnergySourceType = None,
    ) -> None:
        n_datapoints = len(next(iter(power_kw_per_switchboard.values())))
        genset_on = self._make_genset_on_matrix(power_kw_per_switchboard, n_datapoints)
        status = ElectricPowerPlantStatus(
            bus_tie_breaker_status=np.ones(shape=[self.n_bus_ties, n_datapoints]),
            genset_connection_status=genset_on,
        )
        if self.n_bus_ties > 0:
            electric_power_system.set_bus_tie_status_all(status.bus_tie_breaker_status)
        for swb_id, on_status in status.genset_connection_status.items():
            electric_power_system.set_status_by_switchboard_id_power_type(
                status=on_status,
                switchboard_id=swb_id,
                power_type=TypePower.POWER_SOURCE,
            )
        on_vector = np.ones(n_datapoints)
        equal_load_sharing_vector = np.zeros(n_datapoints)
        for component in chain(electric_power_system.energy_storage):
            component.status = on_vector
            component.load_sharing_mode = equal_load_sharing_vector

    def _make_genset_on_matrix(
        self, power_kw_per_switchboard: Dict[SwbId, np.ndarray], n_datapoints: int
    ) -> Dict[SwbId, np.ndarray]:
        total_power_kw = self._sum_switchboard_power(n_datapoints, power_kw_per_switchboard)
        ideal_number_genset = self._ideal_number_of_gensets_on(n_datapoints, total_power_kw)
        return self._convert_number_of_engines_on_to_status_matrix(
            ideal_number_genset=ideal_number_genset, n_datapoints=n_datapoints
        )

    @staticmethod
    def _sum_switchboard_power(n_datapoints: int, power_kw_per_switchboard: dict) -> np.ndarray:
        #: Calculate the total power load on all switchboards
        total_power_kw = np.zeros(shape=[n_datapoints])
        for power_kw_on_swb in power_kw_per_switchboard.values():
            total_power_kw += power_kw_on_swb
        return total_power_kw

    def _ideal_number_of_gensets_on(
        self, n_datapoints: int, total_power_kw: np.ndarray
    ) -> np.ndarray:
        ideal_number_genset = np.ones(n_datapoints)
        index_genset_on = total_power_kw > 0
        ideal_number_genset[index_genset_on] = np.ceil(
            total_power_kw[index_genset_on]
            / (self.rated_power_gensets * self.maximum_allowable_genset_load_percentage)
        )
        ideal_number_genset = np.minimum(ideal_number_genset, self.n_gensets)
        return ideal_number_genset

    def _convert_number_of_engines_on_to_status_matrix(
        self, ideal_number_genset: np.ndarray, n_datapoints: int
    ) -> Dict[SwbId, np.ndarray]:
        genset_on_matrix = np.zeros(shape=[n_datapoints, self.n_gensets])
        for time_idx in range(n_datapoints):
            for genset_idx in range(int(ideal_number_genset[time_idx])):
                genset_on_matrix[time_idx, genset_idx] = 1
        genset_on_swb = {}
        start_idx = 0
        for swb_id, n_gensets in self.swb2n_gensets.items():
            genset_range = range(start_idx, start_idx + n_gensets)
            genset_on_swb[swb_id] = genset_on_matrix[:, genset_range]
            start_idx += n_gensets
        return genset_on_swb


class BatteryFuelCellDieselHybridSimulationInterface(SimulationInterface):
    def set_status(
        self,
        *,
        power_kw_per_switchboard: Dict[SwbId, np.ndarray],
        electric_power_system: ElectricPowerSystem,
        time_interval_s: np.ndarray,
        power_source_priority: EnergySourceType = EnergySourceType.LNG_DIESEL,
    ) -> None:
        n_datapoints = len(next(iter(power_kw_per_switchboard.values())))
        assert all(
            n_datapoints == len(v) for v in power_kw_per_switchboard.values()
        ), "All load vectors must have equal length"
        off_vector = np.zeros(n_datapoints)
        on_vector = np.ones(n_datapoints)
        equal_load_sharing_vector = np.zeros(n_datapoints)
        if power_source_priority == EnergySourceType.HYDROGEN:
            for source in electric_power_system.power_sources:
                if source.type in [
                    TypeComponent.FUEL_CELL,
                    TypeComponent.FUEL_CELL_SYSTEM,
                ]:
                    source.status = on_vector
                    source.load_sharing_mode = equal_load_sharing_vector
                else:
                    source.status = off_vector
                    source.load_sharing_mode = equal_load_sharing_vector
            for component in chain(electric_power_system.energy_storage):
                component.status = off_vector
                component.load_sharing_mode = equal_load_sharing_vector
        elif power_source_priority == EnergySourceType.BATTERY:
            for component in chain(electric_power_system.energy_storage):
                component.status = on_vector
                component.load_sharing_mode = equal_load_sharing_vector
            for source in electric_power_system.power_sources:
                source.status = off_vector
                source.load_sharing_mode = equal_load_sharing_vector
        else:
            for source in electric_power_system.power_sources:
                if source.type in [TypeComponent.GENSET, TypeComponent.GENERATOR]:
                    source.status = on_vector
                    source.load_sharing_mode = equal_load_sharing_vector
                else:
                    source.status = off_vector
                    source.load_sharing_mode = equal_load_sharing_vector
            for component in chain(electric_power_system.energy_storage):
                component.status = off_vector
                component.load_sharing_mode = equal_load_sharing_vector
