import logging
from collections import defaultdict
from functools import reduce
from typing import Dict, Tuple, List, Union, cast, Sequence, Optional

import numpy as np
import pandas as pd

from .component_base import Component
from .component_electric import (
    COGES,
    ElectricComponent,
    FuelCellSystem,
    Genset,
    MechanicalComponent,
    SerialSystemElectric,
    FuelCell,
    Battery,
    BatterySystem,
    SuperCapacitor,
    SuperCapacitorSystem,
    PTIPTO,
    ShorePowerConnection,
    ShorePowerConnectionSystem,
    ElectricMachine,
)
from .component_mechanical import (
    MainEngineForMechanicalPropulsion,
    MainEngineWithGearBoxForMechanicalPropulsion,
    EngineRunPoint,
    Engine,
    EngineDualFuel,
    EngineMultiFuel,
)
from .utility import (
    integrate_data,
    IntegrationMethod,
    integrate_multi_fuel_consumption,
    IntegrationError,
)
from .. import get_logger
from ..exceptions import InputError
from ..fuel import (
    FuelConsumption,
    FuelByMassFraction,
    FuelOrigin,
    FuelSpecifiedBy,
    FuelConsumerClassFuelEUMaritime,
    TypeFuel,
)
from ..types_for_feems import (
    FEEMSResult,
    TypeNode,
    TypePower,
    TypeComponent,
    TimeIntervalList,
    SwbId,
    EmissionType,
    Numeric,
)

# Define logger
logger = get_logger(__name__)


PowerSource = Union[
    Engine,
    EngineDualFuel,
    EngineMultiFuel,
    Genset,
    ElectricMachine,
    FuelCellSystem,
    FuelCell,
    Battery,
    BatterySystem,
    PTIPTO,
    MainEngineWithGearBoxForMechanicalPropulsion,
    MainEngineForMechanicalPropulsion,
]

PowerConsumer = Union[
    ElectricMachine,
    MechanicalComponent,
    ElectricComponent,
    SerialSystemElectric,
    ShorePowerConnection,
    ShorePowerConnectionSystem,
]


class Node:
    def __init__(self, name: str, type_: TypeNode, components: Sequence[Component]):
        self.name = name
        self.type = type_
        self.status = np.ones(1).astype(bool)
        self.power_out = np.zeros(1)
        self.no_connection = 0
        self.components: Sequence[Component] = components

    def get_power_out(self) -> np.ndarray:
        len_power_values = [len(component.power_input) for component in self.components]
        if not len_power_values:
            return np.zeros(1)
        if len(set(len_power_values)) != 1:
            err_msg = (
                f"The length of power consumption values for the "
                f"components connected to the %{self.name} are not identical."
            )
            logger.error(err_msg)
            raise InputError(err_msg)
        self.power_out = np.zeros(len_power_values[0])
        for component in self.components:
            self.power_out += component.power_input


def get_fuel_emission_energy_balance_for_component(
    component: Union[PowerSource, PowerConsumer],
    time_interval_s: TimeIntervalList,
    integration_method: IntegrationMethod,
    fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
    isSystemMechanical: bool = False,
    fuel_type: Optional[TypeFuel] = None,
    fuel_origin: Optional[FuelOrigin] = None,
) -> FEEMSResult:
    def _resolve_fuel_consumer_class(
        source_component: Union[PowerSource, PowerConsumer],
        fuel_consumption: FuelConsumption,
    ) -> Optional[FuelConsumerClassFuelEUMaritime]:
        engine_candidate: Union[Engine, EngineDualFuel, EngineMultiFuel, None]
        if isinstance(source_component, Genset):
            engine_candidate = source_component.aux_engine
        elif hasattr(source_component, "engine"):
            engine_candidate = cast(
                Union[Engine, EngineDualFuel, EngineMultiFuel], getattr(source_component, "engine")
            )
        else:
            engine_candidate = cast(
                Union[Engine, EngineDualFuel, EngineMultiFuel], source_component
            )

        if isinstance(engine_candidate, EngineMultiFuel):
            if not fuel_consumption.fuels:
                raise ValueError(
                    "Fuel consumption data is required to resolve fuel consumer class for EngineMultiFuel components."
                )
            primary_fuel = fuel_consumption.fuels[0]
            engine_candidate.set_fuel_in_use(
                fuel_type=primary_fuel.fuel_type, fuel_origin=primary_fuel.origin
            )
            return engine_candidate.engine_in_use.fuel_consumer_type_fuel_eu_maritime

        if isinstance(engine_candidate, (Engine, EngineDualFuel)):
            return engine_candidate.fuel_consumer_type_fuel_eu_maritime

        return None

    res = FEEMSResult(
        duration_s=0,
        running_hours_genset_total_hr=0,
        running_hours_fuel_cell_total_hr=0,
        running_hours_pti_pto_total_hr=0,
        energy_consumption_electric_total_mj=0,
        energy_consumption_mechanical_total_mj=0,
        energy_stored_total_mj=0,
    )
    running_hours = (
        (np.atleast_1d(component.power_output)[0] != 0) * np.atleast_1d(time_interval_s)[0] / 3600
    )
    if len(np.atleast_1d(component.power_output)) > 1:
        running_hours = np.dot((component.power_output != 0), time_interval_s).sum() / 3600
    # Calculate fuel consumption for engines
    if component.type in [
        TypeComponent.MAIN_ENGINE,
        TypeComponent.MAIN_ENGINE_WITH_GEARBOX,
    ]:
        engine_run_point = component.get_engine_run_point_from_power_out_kw(
            fuel_specified_by=fuel_specified_by,
            fuel_type=fuel_type,
            fuel_origin=fuel_origin,
        )
        fuel_consumption_kg_per_s = engine_run_point.fuel_flow_rate_kg_per_s
        res.multi_fuel_consumption_total_kg = integrate_multi_fuel_consumption(
            fuel_consumption_kg_per_s=fuel_consumption_kg_per_s,
            time_interval_s=time_interval_s,
            integration_method=integration_method,
        )
        fuel_consumer_class = _resolve_fuel_consumer_class(component, fuel_consumption_kg_per_s)
        if fuel_consumer_class is not None:
            res.co2_emission_total_kg = (
                res.multi_fuel_consumption_total_kg.get_total_co2_emissions(
                    fuel_consumer_class=fuel_consumer_class
                )
            )
        set_emission(
            engine_out=engine_run_point,
            integration_method=integration_method,
            result=res,
            time_interval_s=time_interval_s,
        )
        res.running_hours_main_engines_hr = running_hours
    # Calculate fuel consumption for genset
    elif component.type == TypeComponent.GENSET:
        component = cast(Genset, component)
        genset_run_point = component.get_fuel_cons_load_bsfc_from_power_out_generator_kw(
            power=component.power_output,
            fuel_specified_by=fuel_specified_by,
            fuel_type=fuel_type,
            fuel_origin=fuel_origin,
        )
        res.multi_fuel_consumption_total_kg = integrate_multi_fuel_consumption(
            fuel_consumption_kg_per_s=genset_run_point.engine.fuel_flow_rate_kg_per_s,
            time_interval_s=time_interval_s,
            integration_method=integration_method,
        )
        fuel_consumer_class = _resolve_fuel_consumer_class(
            component, genset_run_point.engine.fuel_flow_rate_kg_per_s
        )
        if fuel_consumer_class is not None:
            res.co2_emission_total_kg = (
                res.multi_fuel_consumption_total_kg.get_total_co2_emissions(
                    fuel_consumer_class=fuel_consumer_class,
                )
            )

        if (
            np.isscalar(genset_run_point.genset_load_ratio)
            or genset_run_point.genset_load_ratio.size == 1
        ):
            res.load_ratio_genset = genset_run_point.genset_load_ratio

        set_emission(genset_run_point.engine, integration_method, res, time_interval_s)

        res.running_hours_genset_total_hr = running_hours

    # Calculate fuel consumption for fuel cell
    elif component.type in [
        TypeComponent.FUEL_CELL_SYSTEM,
        TypeComponent.FUEL_CELL,
    ]:
        component = cast(Union[FuelCellSystem, FuelCell], component)
        fuel_cell_run_point = component.get_fuel_cell_run_point(
            power_out_kw=component.power_output,
            fuel_specified_by=fuel_specified_by,
        )
        fuel_consumption_kg_per_s = fuel_cell_run_point.fuel_flow_rate_kg_per_s
        res.multi_fuel_consumption_total_kg = integrate_multi_fuel_consumption(
            fuel_consumption_kg_per_s=fuel_consumption_kg_per_s,
            time_interval_s=time_interval_s,
            integration_method=integration_method,
        )
        res.co2_emission_total_kg = res.multi_fuel_consumption_total_kg.get_total_co2_emissions(
            fuel_consumer_class=FuelConsumerClassFuelEUMaritime.FUEL_CELL,
        )
        res.running_hours_fuel_cell_total_hr = running_hours

    #: Calculate mechanical energy consumption for generator / PTI/PTO
    elif component.type == TypeComponent.GENERATOR:
        component.set_power_input_from_output(component.power_output)
        res.energy_input_mechanical_total_mj = (
            integrate_data(
                data_to_integrate=component.power_input,
                time_interval_s=time_interval_s,
                integration_method=integration_method,
            )
            / 1000
        )
        res.running_hours_genset_total_hr += running_hours

    # Calculate electric energy input / consumption for PTI/PTO
    elif component.type == TypeComponent.PTI_PTO_SYSTEM:
        power_input = component.power_input.copy()
        power_output = component.power_output.copy()
        index_pti_mode = power_input > 0
        index_pto_mode = power_input < 0
        power_input[index_pto_mode] = 0  # PTI mode
        power_output[index_pto_mode] = 0  # PTI mode
        if isSystemMechanical:
            res.energy_input_mechanical_total_mj = (
                integrate_data(
                    data_to_integrate=power_output,
                    time_interval_s=time_interval_s,
                    integration_method=integration_method,
                )
                / 1000
            )
        else:
            res.energy_consumption_electric_total_mj = (
                integrate_data(
                    data_to_integrate=power_input,
                    time_interval_s=time_interval_s,
                    integration_method=integration_method,
                )
                / 1000
            )
        power_input = component.power_input.copy()
        power_output = component.power_output.copy()
        power_input[index_pti_mode] = 0  # PTO mode
        power_output[index_pti_mode] = 0  # PTO mode
        if isSystemMechanical:
            res.energy_consumption_mechanical_total_mj = (
                integrate_data(
                    data_to_integrate=power_output,
                    time_interval_s=time_interval_s,
                    integration_method=integration_method,
                )
                / 1000
            )
        else:
            res.energy_input_electric_total_mj = (
                integrate_data(
                    data_to_integrate=-power_input,
                    time_interval_s=time_interval_s,
                    integration_method=integration_method,
                )
                / 1000
            )
        res.running_hours_pti_pto_total_hr += running_hours

    #: Calculate electric energy stored for energy storage system
    elif component.power_type == TypePower.ENERGY_STORAGE:
        component = cast(
            Union[Battery, BatterySystem, SuperCapacitor, SuperCapacitorSystem],
            component,
        )
        res.energy_stored_total_mj = (
            component.get_energy_stored_kj(
                time_interval_s=time_interval_s,
                integration_method=integration_method,
            )
            / 1000
        )

    #: Calculate electric energy input for shore power
    elif component.type == TypeComponent.SHORE_POWER:
        component = cast(Union[ShorePowerConnection, ShorePowerConnectionSystem], component)
        res.energy_input_electric_total_mj = (
            integrate_data(
                data_to_integrate=component.power_input,
                time_interval_s=time_interval_s,
                integration_method=integration_method,
            )
            / 1000
        )
    elif component.type in [
        TypeComponent.OTHER_LOAD,
        TypeComponent.OTHER_MECHANICAL_LOAD,
    ]:
        component.set_power_output_from_input(component.power_input)
        try:
            res.energy_consumption_auxiliary_total_mj = (
                integrate_data(
                    data_to_integrate=component.power_output,
                    time_interval_s=time_interval_s,
                    integration_method=integration_method,
                )
                / 1000
            )
        except IntegrationError as e:
            logger.warning("Integration occurred for other load: " + e.__str__())
    elif component.type in [
        TypeComponent.PROPELLER_LOAD,
        TypeComponent.PROPULSION_DRIVE,
    ]:
        res.energy_consumption_propulsion_total_mj = (
            integrate_data(
                data_to_integrate=component.power_output,
                time_interval_s=time_interval_s,
                integration_method=integration_method,
            )
            / 1000
        )
    elif component.type == TypeComponent.COGES:
        component = cast(COGES, component)
        coges_run_point = component.get_system_run_point_from_power_output_kw(
            fuel_specified_by=fuel_specified_by,
        )
        res.multi_fuel_consumption_total_kg = integrate_multi_fuel_consumption(
            fuel_consumption_kg_per_s=coges_run_point.cogas.fuel_flow_rate_kg_per_s,
            time_interval_s=time_interval_s,
            integration_method=integration_method,
        )
        res.co2_emission_total_kg = res.multi_fuel_consumption_total_kg.get_total_co2_emissions(
            component.cogas.fuel_consumer_type_fuel_eu_maritime
        )

        if (
            np.isscalar(coges_run_point.coges_load_ratio)
            or coges_run_point.coges_load_ratio.size == 1
        ):
            res.load_ratio_genset = coges_run_point.coges_load_ratio

        set_emission(
            engine_out=coges_run_point.cogas,
            integration_method=integration_method,
            result=res,
            time_interval_s=time_interval_s,
        )

        res.running_hours_genset_total_hr = running_hours
    else:
        raise TypeError(
            f"Component type {component.type} not supported for energy balance calculation"
        )

    return res


def set_emission(
    engine_out: EngineRunPoint,
    integration_method: IntegrationMethod,
    result: FEEMSResult,
    time_interval_s: TimeIntervalList,
) -> FEEMSResult:
    if result.total_emission_kg is None:
        result.total_emission_kg = defaultdict(float)

    for emission_type, rate_g_per_S in engine_out.emissions_g_per_s.items():
        total_kg_s = (
            integrate_data(
                data_to_integrate=rate_g_per_S,
                time_interval_s=time_interval_s,
                integration_method=integration_method,
            )
            / 1_000
        )
        result.total_emission_kg[emission_type] += total_kg_s

    return result


class Switchboard(Node):
    def __init__(self, name: str, idx: SwbId, components: Sequence[ElectricComponent]):
        super(Switchboard, self).__init__(
            name=name, type_=TypeNode.SWITCHBOARD, components=components
        )
        self.id: SwbId = idx
        self.component_by_power_type: List[
            List[Union[ElectricComponent, Genset, FuelCellSystem]]
        ] = [[] for _ in TypePower]
        self.name_component_by_power_type: List[List[str]] = [[] for _ in TypePower]
        #: Categorize the components by its power type
        for component in components:
            self.component_by_power_type[component.power_type.value].append(component)
            self.name_component_by_power_type[component.power_type.value].append(component.name)
        #: Check if the names are duplicates in each category
        for i, name_list in enumerate(self.name_component_by_power_type):
            name_list_unique = list(set(name_list))
            if len(name_list) != len(name_list_unique):
                raise NameError(
                    "There are duplicates in the component name for {0} "
                    "category for the switchboard no. {1}".format(TypePower(i).name, self.id)
                )
        #: Rated power for the bus (summing all the rated power of the power sources)
        self.rated_power = sum(
            [
                component.rated_power
                for component in self.component_by_power_type[TypePower.POWER_SOURCE.value]
            ]
        )
        self.no_power_sources = len(self.component_by_power_type[TypePower.POWER_SOURCE.value])
        self.no_consumers = len(self.component_by_power_type[TypePower.POWER_CONSUMER.value])
        self.no_pti_pto = len(self.component_by_power_type[TypePower.PTI_PTO.value])
        self.no_energy_storage = len(self.component_by_power_type[TypePower.ENERGY_STORAGE.value])

    def get_status_component_by_power_type(self, type_: TypePower) -> List[np.ndarray]:
        #: Check if the length of the values for different components are the same
        len_status = [
            len(component.status) for component in self.component_by_power_type[type_.value]
        ]
        if not len_status:
            return [False]
        if len(set(len_status)) != 1:
            err_msg = (
                f"The length of status values for the power source "
                f"connected to the %{self.name} are not identical."
            )
            logger.error(err_msg)
            raise InputError(err_msg)
        return [component.status for component in self.component_by_power_type[type_.value]]

    def get_load_sharing_mode_components_by_power_type(self, type_: TypePower) -> List[np.ndarray]:
        #: Check if the length of the values for different components are the same
        len_load_sharing = [
            len(component.load_sharing_mode)
            for component in self.component_by_power_type[type_.value]
        ]
        if not len_load_sharing:
            return []
        if len(set(len_load_sharing)) != 1:
            err_msg = (
                f"The length of load sharing values for the power source "
                f"connected to the %{self.name} are not identical."
            )
            logger.error(err_msg)
            raise InputError(err_msg)
        return [
            component.load_sharing_mode for component in self.component_by_power_type[type_.value]
        ]

    def get_power_rated_component_by_power_type(self, type_: TypePower) -> List[float]:
        return [
            power_source.rated_power for power_source in self.component_by_power_type[type_.value]
        ]

    def get_power_avail_component_by_power_type(self, type_: TypePower) -> List[np.ndarray]:
        #: Check if the length of the values for different components are the same
        len_status = [
            len(component.status) for component in self.component_by_power_type[type_.value]
        ]
        if not len_status:
            return []
        if len(set(len_status)) != 1:
            err_msg = (
                f"The length of load sharing values for the power source "
                f"connected to the %{self.name} are not identical."
            )
            logger.error(err_msg)
            raise InputError(err_msg)
        return [
            component.rated_power * component.status
            for component in self.component_by_power_type[type_.value]
        ]

    def _get_sum_power(self, power: np.ndarray) -> np.ndarray:
        """
        Return the sum of power value or vectors.
        Note that the power input values of the components that have 0 values for the
        corresponding load sharing mode (Equally load sharing mode) will be excluded from the sum
        """

    # noinspection DuplicatedCode
    def get_sum_power_input_by_power_type(self, type_: TypePower) -> np.ndarray:
        """
        Return the sum of power input value or vectors of the components specified by the power
        type. Note that the power input values of the components that have 0 values for the
        corresponding load sharing mode (Equally load sharing mode) will be excluded from the sum
        """
        #: Check if the length of the values for different components are the same
        len_power_values = []
        for component in self.component_by_power_type[type_.value]:
            try:
                len_power_values.append(len(component.power_input))
            except TypeError:
                len_power_values.append(1)

        if len(len_power_values) == 0:
            return np.zeros(1)

        if len(set(len_power_values)) != 1:
            err_msg = (
                f"The length of power input values for the components of {type_.value}"
                f"connected to the %{self.name} are not identical."
            )
            logger.error(err_msg)
            raise InputError(err_msg)

        power_input_sum = np.zeros(len_power_values[0])
        for component in self.component_by_power_type[type_.value]:
            if (
                component.power_type == TypePower.PTI_PTO
                or component.power_type == TypePower.ENERGY_STORAGE
            ):
                power_input_sum += component.power_input * component.load_sharing_mode
            else:
                power_input_sum += component.power_input
        return power_input_sum

    def _get_component_by_type_and_name(
        self,
        name: str,
        power_type: TypePower,
    ) -> Union[ElectricComponent, Genset, FuelCellSystem, BatterySystem]:
        try:
            idx = self.name_component_by_power_type[power_type.value].index(name)
            return self.component_by_power_type[power_type.value][idx]
        except ValueError:
            raise ValueError("The name does not match the components for the given type")

    def set_power_load_component_from_power_input_by_type_and_name(
        self, name: str, power_type: TypePower, power_input: np.ndarray
    ) -> int:
        """
        Set the power input and output from the given value of power input
        for a component specified by the type and the name.
        :param name: name of the component
        :param power_type: type defined by TypePower Class
        :param power_input: power output of the component
        :return: 1 for success and 0 for error
        """
        component = self._get_component_by_type_and_name(name, power_type)
        if component is not None and not isinstance(component, Genset):
            component.set_power_output_from_input(power_input)
            return 1
        else:
            return 0

    def set_power_load_component_from_power_output_by_type_and_name(
        self, name: str, power_type: TypePower, power_output: np.ndarray
    ) -> int:
        """
        Set the power input and output from the given value of power output
        for a component specified by the type and the name
        :param name: name of the component
        :param power_type: type defined by TypePower Class
        :param power_output: power output of the component
        :return: 1 for success and 0 for error
        """
        component = self._get_component_by_type_and_name(name, power_type)
        if component is not None and not isinstance(component, Genset):
            component.set_power_input_from_output(power_output)
            return 1
        else:
            return 0

    def set_status_components_by_power_type(self, type_: TypePower, status: np.ndarray) -> None:
        """
        Set the status of all the power sources

        :param type_: power type as listed in TypePower class
        :param status: 2d array of bool with dimension [N x n] where n is the number of
            power sources
        """
        no_components = len(self.component_by_power_type[type_.value])
        if len(status.shape) != 2:
            raise ValueError("The status input should be a 2D matrix")
        elif status.shape[1] != no_components:
            if status.shape[0] == no_components:
                raise ValueError("The dimension of the status input should be transposed")
            else:
                raise ValueError(
                    "The dimension of the status input does not match the number of power sources"
                )
        for i, component in enumerate(self.component_by_power_type[type_.value]):
            component.status = status[:, i]

    def set_status_component_by_power_type_name(self, status: np.ndarray, name: str) -> int:
        """
        Sets the status of the power source specified by the name
        :param status: 1d array of bool
        :param name: The name of the power source
        :return: 1 for success, 0 for error
        """
        try:
            index = self.name_component_by_power_type[TypePower.POWER_SOURCE.value].index(name)
        except ValueError:
            raise ValueError("The name given for the power source is not found in the switchboard")
        self.component_by_power_type[TypePower.POWER_SOURCE.value][index].status = status
        return 1

    def set_status_components_by_power_type_and_index(
        self, type_: TypePower, status: np.ndarray, index: int
    ) -> int:
        """
        Sets the status of the power source specified by the index
        :param type_: power type as listed in TypePower
        :param status: 1d array of bool
        :param index: The index of the components in the list
        :return: 1 for success, 0 for error
        """
        if index >= len(self.component_by_power_type[type_.value]) or index < 0:
            raise ValueError(
                "The index exceeds the length of the list of power sources or negative"
            )
        self.component_by_power_type[type_.value][index].status = status
        return 1

    def set_load_sharing_mode_components_by_power_type(
        self, type_: TypePower, load_sharing_mode: np.ndarray
    ) -> None:
        for i, component in enumerate(self.component_by_power_type[type_.value]):
            component.load_sharing_mode = load_sharing_mode[:, i]

    def get_sum_power_out_power_sources_asymmetric(self) -> np.ndarray:
        return (
            np.array(self.get_load_sharing_mode_components_by_power_type(TypePower.POWER_SOURCE))
            * np.array(self.get_power_avail_component_by_power_type(TypePower.POWER_SOURCE))
        ).sum(axis=0)

    def get_sum_power_avail_for_power_sources_asymmetric_by_type(
        self, type_: TypePower = TypePower.POWER_SOURCE
    ) -> np.ndarray:
        return (
            np.ceil(
                np.absolute(np.array(self.get_load_sharing_mode_components_by_power_type(type_)))
            )
            * np.array(self.get_power_avail_component_by_power_type(type_))
        ).sum(axis=0)

    def get_sum_power_avail_for_power_sources_symmetric(self) -> np.ndarray:
        sum_power_avail_power_sources = (
            np.array(self.get_power_avail_component_by_power_type(TypePower.POWER_SOURCE))
            .sum(axis=0)
            .astype(float)
        )
        sum_power_avail_pti_pto = (
            np.array(self.get_power_avail_component_by_power_type(TypePower.PTI_PTO))
            .sum(axis=0)
            .astype(float)
        )
        sum_power_avail_energy_storage = (
            np.array(self.get_power_avail_component_by_power_type(TypePower.ENERGY_STORAGE))
            .sum(axis=0)
            .astype(float)
        )
        sum_power_avail_power_source_asymm = (
            self.get_sum_power_avail_for_power_sources_asymmetric_by_type(TypePower.POWER_SOURCE)
        )
        sum_power_avail_pti_pto_asymm = (
            self.get_sum_power_avail_for_power_sources_asymmetric_by_type(TypePower.PTI_PTO)
        )
        sum_power_avail_energy_storage_asymm = (
            self.get_sum_power_avail_for_power_sources_asymmetric_by_type(TypePower.ENERGY_STORAGE)
        )
        return np.round(
            sum_power_avail_power_sources
            + sum_power_avail_pti_pto
            + sum_power_avail_energy_storage
            - sum_power_avail_power_source_asymm
            - sum_power_avail_pti_pto_asymm
            - sum_power_avail_energy_storage_asymm,
            10,
        )

    def get_sum_load_kw_sources_symmetric(self) -> Numeric:
        """
        Calculate the sum of power loads on the power sources in a symmetric load sharing mode
        :return: sum of the power loads
        """
        sum_power_consumption = self.get_sum_power_input_by_power_type(TypePower.POWER_CONSUMER)
        sum_power_pti_pto = self.get_sum_power_input_by_power_type(TypePower.PTI_PTO)
        if sum_power_pti_pto.size == 0:
            sum_power_pti_pto = 0
        sum_power_energy_storage = self.get_sum_power_input_by_power_type(TypePower.ENERGY_STORAGE)
        if sum_power_energy_storage.size == 0:
            sum_power_energy_storage = 0
        sum_power_power_source_asymm = self.get_sum_power_out_power_sources_asymmetric()
        if sum_power_power_source_asymm.size == 0:
            sum_power_power_source_asymm = 0
        return (
            sum_power_consumption
            + sum_power_pti_pto
            + sum_power_energy_storage
            - sum_power_power_source_asymm
        )

    # noinspection DuplicatedCode
    def get_sum_power_output_by_power_type(self, type_: TypePower) -> np.ndarray:
        """
        Return the sum of power output value or vectors of the components specified by the power
        type. Note that the power input values of the components that have 0 values for the
        corresponding load sharing mode (Equally load sharing mode) will be excluded from the sum
        """
        #: Check if the length of the values for different components are the same
        len_power_values = [
            len(component.power_output) for component in self.component_by_power_type[type_.value]
        ]
        if not len_power_values:
            return np.zeros(1)
        if len(set(len_power_values)) > 1:
            err_msg = (
                f"The length of power output values for the "
                f"components connected to the %{self.name} are not identical."
            )
            logger.error(err_msg)
            raise InputError(err_msg)

        power_output_sum = np.zeros(len_power_values[0])
        for component in self.component_by_power_type[type_.value]:
            if (
                component.power_type == TypePower.PTI_PTO
                or component.power_type == TypePower.ENERGY_STORAGE
            ):
                power_output_sum += component.power_output * component.load_sharing_mode
            else:
                power_output_sum += component.power_output
        return power_output_sum

    def set_power_out_power_sources(
        self, load_switchboard_symmetric_power_source: np.ndarray
    ) -> None:
        """
        Set the power out for the power sources in symmetric and asymmetric load sharing mode.
        The power sources have the power type of TypePower.POWER_SOURCE, TypePower.PTI_PTO and
        TypePower.ENERGY_STORAGE. For PTI/PTO and energy storage, power input should be set
        manually when the load sharing mode is not symmetric.
        :param load_switchboard_symmetric_power_source: the load (0~1) on the switchboard for
        the power sources that share the power load symmetrically. 1d array
        :return: 1 for success, 0 for error
        """
        no_points = len(load_switchboard_symmetric_power_source)
        for component in self.component_by_power_type[TypePower.POWER_SOURCE.value]:
            power_out = np.zeros(no_points)
            index_symmetric_load = np.bitwise_and(
                component.load_sharing_mode == 0, component.status == 1
            )
            try:
                power_out[index_symmetric_load] = (
                    component.rated_power
                    * load_switchboard_symmetric_power_source[index_symmetric_load]
                    * component.status[index_symmetric_load]
                )
            except IndexError:
                raise ValueError(
                    f"The length of the input (load_switchboard) does not match the length of "
                    f"load sharing mode of the component, {component.name}."
                )
            index_asymmetric_load = np.bitwise_not(index_symmetric_load)
            power_out[index_asymmetric_load] = (
                component.rated_power
                * component.load_sharing_mode[index_asymmetric_load]
                * component.status[index_asymmetric_load]
            )
            component.power_output = power_out
        for component in (
            self.component_by_power_type[TypePower.PTI_PTO.value]
            + self.component_by_power_type[TypePower.ENERGY_STORAGE.value]
        ):
            index_symmetric_load = component.load_sharing_mode == 0
            try:
                component.power_input[index_symmetric_load] = (
                    -component.rated_power
                    * load_switchboard_symmetric_power_source[index_symmetric_load]
                    * component.status[index_symmetric_load]
                )
            except IndexError:
                raise ValueError(
                    f"The length of the input (load_switchboard) does not match the length of "
                    f"the power input / output values for the component, {component.name}"
                )
            if not isinstance(component, Genset):
                (
                    component.power_output,
                    load_perc,
                ) = component.get_power_output_from_bidirectional_input(component.power_input)

    def get_fuel_energy_consumption_running_time(
        self,
        time_interval_s: TimeIntervalList,
        integration_method: IntegrationMethod = IntegrationMethod.simpson,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        fuel_type: Optional[TypeFuel] = None,
        fuel_origin: Optional[FuelOrigin] = None,
    ) -> FEEMSResult:
        """
        Calculates fuel/energy consumption at the shaftline. Power output of the main engines
        and PTI/PTO should have set manually or by power balance calculation.

        Args:
            time_interval_s: time interval for power output data
            integration_method: 'simpson' or 'trapezoid'. 'simpson' is default value
            fuel_specified_by: FuelSpecifiedBy.IMO/EU. Default is IMO

        Returns:
            FEEMSResult
        """
        if fuel_specified_by not in [
            FuelSpecifiedBy.IMO,
            FuelSpecifiedBy.FUEL_EU_MARITIME,
        ]:
            raise NotImplementedError(
                f"Fuel specified by {fuel_specified_by.name} is not implemented"
            )
        #: Create a empty data frame for the result_dataframe
        column_names = [
            "multi fuel consumption [kg]",
            "electric energy consumption [MJ]",
            "mechanical energy consumption [MJ]",
            "energy_stored [MJ]",
            "running hours [h]",
            "CO2 emission [kg]",
            "NOx emission [kg]",
            "component type",
            "rated capacity",
            "rated capacity unit",
            "fuel consumer type",
        ]
        res = FEEMSResult(
            detail_result=pd.DataFrame(columns=column_names),
        )

        # Get the fuel consumption / running hours for each power source, pti/pto, energy_
        # storage component
        for component in self.components:
            res_comp = get_fuel_emission_energy_balance_for_component(
                component=component,
                time_interval_s=time_interval_s,
                integration_method=integration_method,
                fuel_specified_by=fuel_specified_by,
                fuel_type=fuel_type,
                fuel_origin=fuel_origin,
            )

            res = res.sum_with_freeze_duration(res_comp)

            if (
                component
                not in self.component_by_power_type[TypePower.POWER_SOURCE.value]
                + self.component_by_power_type[TypePower.PTI_PTO.value]
                + self.component_by_power_type[TypePower.ENERGY_STORAGE.value]
            ):
                continue

            if component.type == TypeComponent.GENSET:
                res_comp.energy_consumption_mechanical_total_mj = (
                    integrate_data(
                        data_to_integrate=component.aux_engine.power_output,
                        time_interval_s=time_interval_s,
                        integration_method=integration_method,
                    )
                    / 1000
                )

            #: Add the calculation to the result_dataframe
            data_to_add = [
                *res_comp.to_list_for_electric_component(),
                component.type.name,
                component.rated_capacity,
                component.rated_capacity_unit,
                (
                    component.fuel_consumer_type_fuel_eu_maritime.name
                    if component.fuel_consumer_type_fuel_eu_maritime
                    else "None"
                ),
            ]

            res.detail_result = pd.concat(
                [
                    res.detail_result,
                    pd.Series(data_to_add, index=column_names, name=component.name).to_frame().T,
                ]
            )

        if len(self.components) == 0:
            logger.warning(
                f"There is no component connected to the switchboard "
                f"'{self.name}' for fuel calculation"
            )

        if isinstance(component.power_input, float) and isinstance(component.power_output, float):
            n_steps = 1
        else:
            n_steps = max(len(component.power_input), len(component.power_output))

        res.duration_s = get_duration_s(integration_method, n_steps, time_interval_s)

        return res

    def get_fuel_energy_consumption_running_time_without_details(
        self,
        time_interval_s: TimeIntervalList,
        integration_method: IntegrationMethod = IntegrationMethod.simpson,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        fuel_type: Optional[TypeFuel] = None,
        fuel_origin: Optional[FuelOrigin] = None,
    ) -> FEEMSResult:
        """Similar function as `get_fuel_energy_consumption_running_time` but this version does not
        supply details.

        Args:
            time_interval_s: time interval for power output data
            integration_method: 'simpson' or 'trapezoid'. 'simpson' is default value
            fuel_specified_by: FuelSpecifiedBy.IMO/EU. Default is IMO
            fuel_type: Optional[TypeFuel] = None
            fuel_origin: Optional[FuelOrigin] = None

        Returns:
            FEEMSResult
        """
        if fuel_specified_by not in [
            FuelSpecifiedBy.IMO,
            FuelSpecifiedBy.FUEL_EU_MARITIME,
        ]:
            raise NotImplementedError(
                f"Fuel specified by {fuel_specified_by.name} is not implemented"
            )
        res = FEEMSResult(
            duration_s=0,
            energy_consumption_electric_total_mj=0.0,
            energy_consumption_mechanical_total_mj=0.0,
            energy_stored_total_mj=0.0,
            running_hours_genset_total_hr=0.0,
            running_hours_fuel_cell_total_hr=0.0,
            running_hours_pti_pto_total_hr=0.0,
            multi_fuel_consumption_total_kg=FuelConsumption(),
        )

        # Get the fuel consumption / running hours for each power source, pti/pto,
        # energy_storage component
        for component in self.components:
            #: Calculate running hours
            res_component = get_fuel_emission_energy_balance_for_component(
                component=component,
                time_interval_s=time_interval_s,
                integration_method=integration_method,
                fuel_specified_by=fuel_specified_by,
                fuel_type=fuel_type,
                fuel_origin=fuel_origin,
            )
            res = res.sum_with_freeze_duration(res_component)

        def get_length(
            v: Union[float, int, List[float], np.ndarray, np.float64],
        ) -> int:
            if isinstance(v, float) or isinstance(v, int) or np.isscalar(v):
                return 1
            elif isinstance(v, np.ndarray):
                return v.size
            else:
                return len(v)

        n_steps = max(get_length(component.power_input), get_length(component.power_output))
        res.duration_s = get_duration_s(integration_method, n_steps, time_interval_s)

        return res


def get_duration_s(
    integration_method: IntegrationMethod,
    n_steps: int,
    time_interval_s: TimeIntervalList,
) -> float:
    if integration_method == IntegrationMethod.sum_with_time:
        if isinstance(time_interval_s, np.ndarray):
            return time_interval_s.sum()
        elif isinstance(time_interval_s, float) or isinstance(time_interval_s, int):
            return time_interval_s
        elif isinstance(time_interval_s, list):
            return sum(time_interval_s)
    elif (
        integration_method == IntegrationMethod.simpson
        or integration_method == IntegrationMethod.trapezoid
    ):
        if isinstance(time_interval_s, (float, int)):
            return n_steps * time_interval_s
        else:
            raise TypeError(
                "time_interval_s should be float or integer"
                f"type for simpson and trapezoid method. The current type is {type(time_interval_s)}"
            )
    raise NotImplementedError()


class BusBreaker:
    """
    class for circuit breaker
    """

    def __init__(
        self,
        name: str,
        switchboard_ids: Tuple[SwbId, SwbId],
        switchboards: List[Switchboard],
    ):
        self.name = name
        self.no_connection = 2
        self.switchboard_ids = switchboard_ids
        self.switchboards = switchboards
        self.status = np.ones(1).astype(bool)


class ShaftLine(Node):
    """
    class for main interface for the mechanical propulsion system.
    """

    def __init__(self, name: str, shaft_line_id: int, component_list: List[MechanicalComponent]):
        super(ShaftLine, self).__init__(name, TypeNode.SHAFTLINE, component_list)
        self.id = shaft_line_id
        self.component_by_power_type: Dict[TypePower, List[MechanicalComponent]] = {
            each_type: [] for each_type in TypePower
        }
        self.name_component_by_power_type: Dict[TypePower, List[str]] = {
            each_type: [] for each_type in TypePower
        }

        #: Categorize the components by its power type
        for component in component_list:
            self.component_by_power_type[component.power_type].append(component)
            self.name_component_by_power_type[component.power_type].append(component.name)

        #: Check if the names are duplicates in each category
        for power_type, name_list in self.name_component_by_power_type.items():
            name_list_unique = list(set(name_list))
            if len(name_list) != len(name_list_unique):
                msg = "There are duplicates in the component name for %s" "category for the %s" % (
                    power_type,
                    self.name,
                )
                raise NameError(msg)

        #: Get the summary of the system
        self.no_power_sources = len(self.component_by_power_type[TypePower.POWER_SOURCE])
        self.no_consumers = len(self.component_by_power_type[TypePower.POWER_CONSUMER])
        self.no_pti_pto = len(self.component_by_power_type[TypePower.PTI_PTO])

    def get_component_by_name_power_type(
        self, name: str, power_type: TypePower
    ) -> MechanicalComponent:
        #: Find the component by the given name. If not found, log it as error and return 0
        name_component_list = self.name_component_by_power_type[power_type]
        try:
            return self.component_by_power_type[power_type][name_component_list.index(name)]
        except ValueError:
            raise ValueError(
                "The given name is not found among the power consumer components in the %s."
                % self.name
            )

    def set_power_input_load_by_name(
        self, name: str, power_input: Union[float, np.ndarray]
    ) -> int:
        """
        Sets power input value for the load on the component specified by the name
        :param name: name of the component
        :param power_input: power input to the load in kW. Scalar or 1D ndarray
        :return: 1 for success 0 for error
        """
        #: Get the load component from the name
        component = self.get_component_by_name_power_type(name, TypePower.POWER_CONSUMER)

        #: Set the power_input
        if component is not None:
            component.power_input = (
                np.array([power_input]) if type(component.power_input) is float else power_input
            )
            return 1
        else:
            return 0

    def set_status_main_engine_by_name(self, name: str, status: Union[bool, np.ndarray]) -> int:
        """
        Sets the status of main engine (0: off, 1: on) of the given name
        :param name: name of the main engine as in the component instance
        :param status: True or False for on or off respectively. Scalar or 1d ndarray of boolean
        :return: 1 for success, 0 for error
        """
        #: Get the main engine component from the name
        component = self.get_component_by_name_power_type(name, TypePower.POWER_SOURCE)

        #: Set the status of the main engine
        if component is not None:
            component.status = np.array([status]) if type(component.status) is bool else status
            return 1
        else:
            return 0

    def set_power_output_pti_pto(
        self, power_output: Union[float, np.ndarray]
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """
        Sets the power output (Shaft power) for PTI/PTO. Positive power output means that the
        power is supplied from the electric power grid to the shaft (PTI mode). Negative means
        that the power is supplied from the shaft to the electrical power grid. (PTO mode).
        Setting power output will also set the electric power input by calculating the system
        efficiency

        :param power_output: Shaft power of PTI/PTO
        :return: power_input and load %
        """
        #: Get the component instance
        try:
            pti_pto = self.component_by_power_type[TypePower.PTI_PTO][0]
        except (IndexError, KeyError):
            raise ValueError("PTI/PTO doesn't exist in the %s" % self.name)

        #: Set the power output
        if isinstance(pti_pto, PTIPTO):
            pti_pto.power_output = (
                np.array([power_output]) if type(power_output) is float else power_output
            )
            (
                pti_pto.power_input,
                load,
            ) = pti_pto.get_power_input_from_bidirectional_output(pti_pto.power_output)

            return pti_pto.power_input, load
        raise TypeError("The component should be of PTIPTO")

    def set_power_input_pti_pto(
        self, power_input: Union[float, np.ndarray]
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """
        Sets the power input (electric power) for PTI/PTO. Positive power output means that the
        power is supplied from the electric power grid to the shaft (PTI mode). Negative means
        that the power is supplied from the shaft to the electrical power grid. (PTO mode).
        Setting power input will also set the shaft power output by calculating the system
        efficiency.

        :param power_input: Electric power of PTI/PTO
        :return: power_output (Shaft power) and load %
        """
        #: Get the component instance
        try:
            pti_pto = self.component_by_power_type[TypePower.PTI_PTO][0]
        except (IndexError, KeyError) as e:
            msg = "PTI/PTO doesn't exist in the %s" % self.name
            logging.error(msg)
            raise e

        #: Set the power output
        if isinstance(pti_pto, PTIPTO):
            pti_pto.power_input = (
                np.array([power_input]) if type(power_input) is float else power_input
            )
            (
                pti_pto.power_output,
                load,
            ) = pti_pto.get_power_output_from_bidirectional_input(pti_pto.power_input)

            return pti_pto.power_output, load
        else:
            raise TypeError("The component should be of PTIPTO.")

    def do_power_balance(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate the main engine power / PTT and set their as power output.
        Following has be to be done before calling this function.
        - Power input of all the load components set
        - Power input or output of PTI/PTO set except full PTI mode
        - Status of main engines set
        """

        #: Calculate the total power load
        total_power_load = np.array([0.0])
        for component in self.component_by_power_type[TypePower.POWER_CONSUMER]:
            try:
                total_power_load = total_power_load + component.power_input
            except ValueError:
                msg = (
                    "The dimension of the power input of the component (%s) "
                    "is not the same as other components" % component.name
                )
                raise ValueError(msg)

        #: Get the PTI/PTO power output
        #: In case of full PTI mode, the PTI should cover all the load alone
        try:
            pti_pto = self.component_by_power_type[TypePower.PTI_PTO][0]
            pti_pto = cast(PTIPTO, pti_pto)
        except (IndexError, KeyError):
            pti_pto = None
            power_output_pti_pto = np.zeros_like(total_power_load)
        else:
            #: For full PTI mode, PTI covers all the load. Set the power input accordingly
            power_output_pti_pto = pti_pto.power_output
            power_output_pti_pto[pti_pto.full_pti_mode] = total_power_load[pti_pto.full_pti_mode]
            pti_pto.set_power_input_from_output(power_output_pti_pto)

        #: Calculate the main engine power output
        try:
            power_output_main_engine = total_power_load - power_output_pti_pto
        except ValueError:
            msg = (
                "The dimension of the power output of the PTI/PTO (%s) "
                "is not the same as other components" % pti_pto.name
            )
            logging.error(msg)
            raise ValueError(msg)

        #: calculate the total power available from the main engines
        total_power_avail = reduce(
            lambda acc, main_engine: acc
            + main_engine.rated_power * main_engine.status.astype(float),
            self.component_by_power_type[TypePower.POWER_SOURCE],
            0,
        )

        #: Calculate the load percentage
        if isinstance(total_power_load, np.ndarray):
            # noinspection PyUnresolvedReferences
            load_perc = np.zeros(total_power_load.shape)
            is_power_available = total_power_avail > 0
            if np.bitwise_and(power_output_main_engine > 0, total_power_avail == 0).any():
                logger.warning(
                    "There are cases where the sum of power output of the main "
                    "engines are greater than 0 when there is no available power."
                    "The load will be set 0 for these cases if it is not in PTI mode."
                )
            # noinspection PyUnresolvedReferences
            load_perc[is_power_available] = (
                power_output_main_engine[is_power_available]
                / total_power_avail[is_power_available]
            )
        else:
            load_perc = np.array([0.0])
            if total_power_avail > 0:
                load_perc = power_output_main_engine / total_power_avail
            else:
                if power_output_main_engine > 0:
                    logger.warning(
                        "The sum of power output of the main engines is greater than 0 "
                        "when there is no available power. The load will be set 0"
                    )

        if self.no_pti_pto > 0:
            load_perc[pti_pto.full_pti_mode] = 0

        #: Set all the power output of the main engine
        for main_engine in self.component_by_power_type[TypePower.POWER_SOURCE]:
            main_engine.power_output = main_engine.rated_power * load_perc * main_engine.status

            #: Set the status false(off) if the power output is 0
            main_engine.status[main_engine.power_output == 0] = False

            #: Check the power balance (negative power for :
            if len(main_engine.power_output[main_engine.power_output < 0]) > 0:
                msg = "There are cases with negative power outputs for the main engine"
                logging.warning(msg)

        return load_perc, total_power_avail

    def get_fuel_calculation_running_hours(
        self,
        time_step: float,
        integration_method: IntegrationMethod = IntegrationMethod.simpson,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        fuel_type: Optional[TypeFuel] = None,
        fuel_origin: Optional[FuelOrigin] = None,
    ) -> FEEMSResult:
        """
        Calculate fuel consumption and running hours.
        Power balance calculation has to be done in advance.

        Args:
            time_step: time step for the time series in seconds
            integration_method: 'simpson' or 'trapezoid'. 'simpson' is the default method.
            fuel_specified_by: 'IMO' or 'EU'. 'IMO' is the default method.
            fuel_type: Optional[TypeFuel] = None
            fuel_origin: Optional[FuelOrigin] = None

        Returns: FEEMResult with total fuel consumption [kg], total_mechanical_energy_input [MJ],
            total running hours for engines[hours], CO2 emissions [kg], NOx emissions [kg] and
            the detail numbers for each engine and PTI/PTO
        """
        if fuel_specified_by not in [
            FuelSpecifiedBy.IMO,
            FuelSpecifiedBy.FUEL_EU_MARITIME,
        ]:
            raise NotImplementedError(
                f"Fuel specified by {fuel_specified_by.name} is not implemented"
            )
        #: Get the main engine instances and collect the names
        main_engines = self.component_by_power_type[TypePower.POWER_SOURCE]
        pti_ptos = self.component_by_power_type[TypePower.PTI_PTO]
        loads = self.component_by_power_type[TypePower.POWER_CONSUMER]

        #: Create a dataframe template for the result
        column_names = [
            "multi fuel consumption [kg]",
            "electric energy consumption [MJ]",
            "mechanical energy consumption [MJ]",
            "running hours [h]",
            "CO2 emission [kg]",
            "NOx emission [kg]",
            "component type",
            "rated capacity",
            "rated capacity unit",
            "fuel consumer type",
        ]
        res = FEEMSResult(detail_result=pd.DataFrame(columns=column_names))

        #: Get the fuel consumption rate and on time for each engine / integrate them
        for component in [*main_engines, *pti_ptos, *loads]:
            # Calculate fuel consumption
            res_comp = get_fuel_emission_energy_balance_for_component(
                component=component,
                time_interval_s=time_step,
                integration_method=integration_method,
                fuel_specified_by=fuel_specified_by,
                isSystemMechanical=True,
                fuel_type=fuel_type,
                fuel_origin=fuel_origin,
            )
            res = res.sum_with_freeze_duration(res_comp)
            if not (
                isinstance(component, MainEngineForMechanicalPropulsion)
                or isinstance(component, PTIPTO)
            ):
                continue

            # Calculate shaft energy output for main engine, genset
            if component.type in [
                TypeComponent.MAIN_ENGINE,
                TypeComponent.MAIN_ENGINE_WITH_GEARBOX,
            ]:
                res_comp.energy_consumption_mechanical_total_mj = (
                    integrate_data(
                        data_to_integrate=component.engine.power_output,
                        time_interval_s=time_step,
                        integration_method=integration_method,
                    )
                    / 1000
                )
            # Add the calculation to the result_dataframe
            data_to_add = [
                *res_comp.to_list_for_mechanical_component(),
                component.type.name,
                component.rated_capacity,
                component.rated_capacity_unit,
                (
                    component.fuel_consumer_type_fuel_eu_maritime.name
                    if component.fuel_consumer_type_fuel_eu_maritime
                    else "None"
                ),
            ]
            res.detail_result = pd.concat(
                [
                    res.detail_result,
                    pd.Series(data_to_add, index=column_names, name=component.name).to_frame().T,
                ]
            )

        if len(self.components) == 0:
            logger.warning(
                f"There is no component connected to the shaftline "
                f"'{self.name}' for fuel calculation"
            )

        if isinstance(component.power_input, float) and isinstance(component.power_output, float):
            n_steps = 1
        else:
            n_steps = max(len(component.power_input), len(component.power_output))

        res.duration_s = get_duration_s(integration_method, n_steps, time_step)

        return res
