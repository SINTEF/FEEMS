from dataclasses import dataclass
from functools import reduce
from operator import itemgetter
from typing import Union, List, Tuple, Dict, NewType, NamedTuple, Set, Optional

import numpy as np
import pandas as pd
from feems.fuel import FuelSpecifiedBy, FuelOrigin, TypeFuel

from feems.components_model import (
    MainEngineForMechanicalPropulsion,
    MainEngineWithGearBoxForMechanicalPropulsion,
)
from .components_model.component_mechanical import EngineMultiFuel, Engine

from . import get_logger
from .components_model.component_electric import (
    COGES,
    ElectricComponent,
    ElectricMachine,
    Genset,
    SerialSystemElectric,
    PTIPTO,
    Battery,
    MechanicalComponent,
    BatterySystem,
    SuperCapacitor,
    SuperCapacitorSystem,
    PowerSystemComponent,
    EnergyStorageComponent,
    FuelCellSystem,
)
from .components_model.node import Switchboard, BusBreaker, ShaftLine, SwbId
from .components_model.utility import IntegrationMethod
from .exceptions import ConfigurationError, InputError
from .types_for_feems import (
    FEEMSResult,
    TypePower,
    TypeComponent,
    TypeValueBus,
    TimeIntervalList,
)

BusId = NewType("BusId", int)

logger = get_logger(__name__)


class FEEMSResultForMachinerySystem(NamedTuple):
    electric_system: FEEMSResult
    mechanical_system: FEEMSResult


class FuelOption(NamedTuple):
    """
    Represents a specific configuration for a fuel source used within the system.
    This class defines the characteristics of a fuel option, including its type,
    origin, and usage role (primary vs. secondary, main vs. pilot).
    Attributes:
        fuel_type (TypeFuel): The specific classification of the fuel (e.g., MDO, HFO, LNG).
        fuel_origin (FuelOrigin): The source or region of origin for the fuel, which may
            impact emission factors or specific energy content.
        for_pilot (bool): Indicates if this fuel is used specifically for pilot injection
            (ignition) purposes. Defaults to False.
        primary (bool): Indicates if this is the primary fuel source for the consumer.
            Defaults to True.
    """
    
    fuel_type: TypeFuel
    fuel_origin: FuelOrigin
    for_pilot: bool = False
    primary: bool = True


def _extract_multi_fuel_options(engine: object) -> List[FuelOption]:
    if not isinstance(engine, EngineMultiFuel):
        return []

    options: List[FuelOption] = []
    seen: Set[FuelOption] = set()
    for i, characteristics in enumerate(engine.multi_fuel_characteristics):
        option = FuelOption(
            fuel_type=characteristics.main_fuel_type,
            fuel_origin=characteristics.main_fuel_origin,
            for_pilot=False,
            primary=i == 0,
        )
        if option not in seen:
            options.append(option)
            seen.add(option)
        if characteristics.pilot_fuel_type is not None:
            option = FuelOption(
                fuel_type=characteristics.pilot_fuel_type,
                fuel_origin=characteristics.pilot_fuel_origin,
                for_pilot=True,
                primary=i == 0,
            )
            if option not in seen:
                options.append(option)
                seen.add(option)
    return options


class MachinerySystem:
    time_interval_s: float
    integration_method: IntegrationMethod

    def set_time_interval(
        self, time_interval_s: TimeIntervalList, integration_method: IntegrationMethod
    ) -> None:
        time_interval_s_is_scalar_number = np.isscalar(time_interval_s) and isinstance(
            time_interval_s, (float, int)
        )
        if (
            integration_method == IntegrationMethod.simpson
            or integration_method == IntegrationMethod.trapezoid
        ):
            if not time_interval_s_is_scalar_number:
                msg = (
                    f"The time interval for {integration_method.value} method should be"
                    f"a scalar value."
                )
                logger.error(msg)
                raise InputError(msg)
        self.time_interval_s = time_interval_s
        self.integration_method = integration_method

    @property
    def multi_fuel_engine_inventory(self) -> Dict[str, List[FuelOption]]:
        return {}

    @property
    def has_multi_fuel_engines(self) -> bool:
        return any(self.multi_fuel_engine_inventory.values())

    @property
    def available_fuel_options(self) -> List[FuelOption]:
        return []

    def _validate_selected_fuel_option(
        self, fuel_option: Optional[FuelOption]
    ) -> Optional[FuelOption]:
        if fuel_option is None:
            return None

        inventory = self.multi_fuel_engine_inventory
        if not inventory:
            option_repr = f"{fuel_option.fuel_type.name}/{fuel_option.fuel_origin.name}"
            raise InputError(
                "Fuel option '{option}' cannot be selected because this system has no multi-fuel engines.".format(
                    option=option_repr
                )
            )

        unsupported_components = [
            name for name, options in inventory.items() if fuel_option not in options
        ]
        if unsupported_components:
            option_repr = f"{fuel_option.fuel_type.name}/{fuel_option.fuel_origin.name}"
            raise InputError(
                "Fuel option '{option}' is not supported by: {components}.".format(
                    option=option_repr,
                    components=", ".join(unsupported_components),
                )
            )

        return fuel_option


class ElectricPowerSystem(MachinerySystem):
    def __init__(
        self,
        name: str,
        power_plant_components: List[PowerSystemComponent],
        bus_tie_connections: List[Tuple[SwbId, SwbId]],
    ):
        component2switchboard: List[SwbId] = []
        power_source2switchboard: List[SwbId] = []
        energy_storage2switchboard: List[SwbId] = []
        self.name = name
        self.power_sources: List[
            Union[ElectricComponent, Genset, SerialSystemElectric, ElectricMachine]
        ] = []
        self.propulsion_drives: List[Union[ElectricComponent, SerialSystemElectric]] = []
        self.pti_pto: List[PTIPTO] = []
        self.energy_storage: List[EnergyStorageComponent] = []
        self.other_load: List[Union[ElectricComponent, SerialSystemElectric]] = []
        self.switchboards: Dict[SwbId, Switchboard] = {}
        self.bus_tie_breakers: List[BusBreaker] = []
        self.no_bus: List[int] = []
        self.switchboard2bus: List[Dict[SwbId, BusId]] = []
        self.bus_tie_status_system: List[np.ndarray] = []
        self.bus_configuration_change_index: List = [0]
        #: Categorize the components
        for component in power_plant_components:
            if component.power_type == TypePower.POWER_SOURCE:
                if isinstance(component, (ElectricMachine, Genset, FuelCellSystem, COGES)):
                    self.power_sources.append(component)
                    power_source2switchboard.append(component.switchboard_id)
                    component2switchboard.append(component.switchboard_id)
                else:
                    raise TypeError(
                        "The component was specified to be power source but is not an instance of ElectricMachine, Genset, FuelCellSystem"
                    )
            elif component.type == TypeComponent.PROPULSION_DRIVE:
                if isinstance(component, (ElectricComponent, SerialSystemElectric)):
                    self.propulsion_drives.append(component)
                else:
                    raise TypeError(
                        "The component was specified to be propulsion drive but is not a ElectricComponent or SerialSystemElectric insetance"
                    )
                component2switchboard.append(component.switchboard_id)
            elif component.type == TypeComponent.PTI_PTO_SYSTEM:
                if isinstance(component, PTIPTO):
                    self.pti_pto.append(component)
                else:
                    raise TypeError(
                        "The component was specified to be PTI/PTO but is not a PTIPTO instance"
                    )
                component2switchboard.append(component.switchboard_id)
            elif component.power_type == TypePower.ENERGY_STORAGE:
                if isinstance(
                    component,
                    (Battery, BatterySystem, SuperCapacitor, SuperCapacitorSystem),
                ):
                    self.energy_storage.append(component)
                else:
                    raise TypeError(
                        "The component was specified to be energy storage but is not an instance of Battery, BatterySystem, SuperCapacitor, SuperCapacitorSystem"
                    )
                component2switchboard.append(component.switchboard_id)
                energy_storage2switchboard.append(component.switchboard_id)
            elif component.power_type == TypePower.POWER_CONSUMER:
                if isinstance(component, (ElectricComponent, SerialSystemElectric)):
                    self.other_load.append(component)
                else:
                    raise TypeError(
                        "The component was specified to be energy storage but is not an instance of ElectricComponent or SerialSystemElectric"
                    )
                component2switchboard.append(component.switchboard_id)
            else:
                raise TypeError(f"Component - {component.name} - does have a proper type.")

        #: Create a list of Switchboard objects based on the switchboard information given
        switchboard_id_from_power_sources = list(dict.fromkeys(power_source2switchboard).keys())
        switchboard_id_from_energy_storage = list(dict.fromkeys(energy_storage2switchboard).keys())
        switchboard_id_from_power_sources.sort()
        switchboard_id_from_energy_storage.sort()
        self.switchboard_id: List[SwbId] = list(dict.fromkeys(component2switchboard).keys())
        self.switchboard_id.sort()
        for swb_id in self.switchboard_id:
            if (
                swb_id not in switchboard_id_from_energy_storage
                and swb_id not in switchboard_id_from_power_sources
            ):
                raise ConfigurationError(
                    "Swb id=%d has no power source or energy storage" % swb_id
                )
        for s in self.switchboard_id:
            if isinstance(s, int) and s <= 0:
                raise ConfigurationError(
                    "The switchboard id should be a positive integer, " "it is: %s" % s
                )
        self.switchboard_id.sort()
        for swb_id in self.switchboard_id:
            comp_idx = np.arange(0, len(power_plant_components))[
                np.array(component2switchboard) == swb_id
            ].tolist()
            comp_by_swb_id = itemgetter(*comp_idx)(power_plant_components)
            if type(comp_by_swb_id) is tuple:
                comp_by_swb_id_list = list(comp_by_swb_id)
            else:
                comp_by_swb_id_list = [comp_by_swb_id]
            self.switchboards[swb_id] = Switchboard(
                "switchboard{:d}".format(swb_id), swb_id, comp_by_swb_id_list
            )

        #: Assign the switchboards to the breaker
        self.no_bus_tie_breakers = len(bus_tie_connections)
        for i, connection in enumerate(bus_tie_connections):
            self.bus_tie_breakers.append(
                BusBreaker(
                    name="bus breaker {}".format(i + 1),
                    switchboard_ids=connection,
                    switchboards=[
                        self.switchboards[connection[0]],
                        self.switchboards[connection[1]],
                    ],
                )
            )

        # Close all bus tie breakers by default
        for each_breaker in self.bus_tie_breakers:
            each_breaker.status = np.ones(1).astype(bool)
        self.switchboard2bus_configuration()
        self.no_power_sources = len(self.power_sources)
        self.no_propulsion_units = len(self.propulsion_drives)
        self.no_energy_storage = len(self.energy_storage)
        self.no_pti_pto = len(self.pti_pto)
        self.no_other_load = len(self.other_load)
        self.no_switchboard = len(self.switchboards)
        self.time_interval_s: TimeIntervalList = []
        self.integration_method: IntegrationMethod = IntegrationMethod.simpson

    @property
    def multi_fuel_engine_inventory(self) -> Dict[str, List[FuelOption]]:
        inventory: Dict[str, List[FuelOption]] = {}
        for component in self.power_sources:
            if isinstance(component, Genset):
                options = _extract_multi_fuel_options(component.aux_engine)
                if options:
                    inventory[component.name] = list(options)
        return inventory

    @property
    def available_fuel_options(self) -> List[FuelOption]:
        options: List[FuelOption] = []
        seen: Set[FuelOption] = set()
        for engine_options in self.multi_fuel_engine_inventory.values():
            for option in engine_options:
                if option not in seen:
                    options.append(option)
                    seen.add(option)
        # Check all the power sources that use fuel but are not multi-fuel engines
        for component in self.power_sources:
            if isinstance(component, Genset):
                if isinstance(component.aux_engine, EngineMultiFuel):
                    continue
                fuel_option = FuelOption(
                    fuel_type=component.aux_engine.fuel_type,
                    fuel_origin=component.aux_engine.fuel_origin,
                    primary=True,
                    for_pilot=False,
                )
                if fuel_option not in seen:
                    options.append(fuel_option)
                    seen.add(fuel_option)
                if hasattr(component.aux_engine, "pilot_fuel_type"):
                    fuel_option = FuelOption(
                        fuel_type=component.aux_engine.pilot_fuel_type,
                        fuel_origin=component.aux_engine.pilot_fuel_origin,
                        primary=True,
                        for_pilot=True,
                    )
                    if fuel_option not in seen:
                        options.append(fuel_option)
                        seen.add(fuel_option)
            elif isinstance(component, FuelCellSystem):
                fuel_option = FuelOption(
                    fuel_type=component.fuel_cell.fuel_type,
                    fuel_origin=component.fuel_cell.fuel_origin,
                    primary=True,
                    for_pilot=False,
                )
            elif isinstance(component, COGES):
                fuel_option = FuelOption(
                    fuel_type=component.cogas.fuel_type,
                    fuel_origin=component.cogas.fuel_origin,
                    primary=True,
                    for_pilot=False,
                )
            else:
                continue
            if fuel_option not in seen:
                options.append(fuel_option)
                seen.add(fuel_option)
        return options

    def set_status_by_switchboard_id_power_type(
        self, switchboard_id: SwbId, power_type: TypePower, status: np.ndarray
    ) -> None:
        self.switchboards[switchboard_id].set_status_components_by_power_type(
            type_=power_type, status=status
        )

    def set_load_sharing_mode_power_sources_by_switchboard_id_power_type(
        self,
        switchboard_id: SwbId,
        power_type: TypePower,
        load_sharing_mode: np.ndarray,
    ) -> None:
        self.switchboards[switchboard_id].set_load_sharing_mode_components_by_power_type(
            type_=power_type, load_sharing_mode=load_sharing_mode
        )

    def set_power_input_from_power_output_by_switchboard_id_type_name(
        self,
        power_output: np.ndarray,
        switchboard_id: SwbId,
        type_: TypePower,
        name: str,
    ) -> int:
        """Set power input from power output for the component specified by its switchboard id,
        type and name

        :param power_output: Power output of the component, 1d array of float
        :param switchboard_id: Switchboard number that the component is connected to
        :param type_: Type of the component as specified by TypePower class
        :param name: Name of the component
        :return: 1 for success, 0 for error
        """
        return self.switchboards[
            switchboard_id
        ].set_power_load_component_from_power_output_by_type_and_name(
            name=name, power_type=type_, power_output=power_output
        )

    def set_bus_tie_status_all(self, bus_tie_status: np.ndarray) -> None:
        if self.no_bus_tie_breakers > 0:
            for i, bus_tie_breaker in enumerate(self.bus_tie_breakers):
                bus_tie_breaker.status = bus_tie_status[:, i]
            self.switchboard2bus_configuration()
        else:
            logger.warning("There is no bus tie breaker to set the status for.")

    def set_bus_tie_status(self, bus_ties_status: List[Tuple[int, np.ndarray]]) -> None:
        length_status = len(bus_ties_status[0][1])
        for bus_tie_status in bus_ties_status:
            if length_status != len(bus_tie_status[1]):
                raise IndexError(
                    "The length of the status values for bus tie breakers is not "
                    "identical for no. {} breaker".format(bus_tie_status[0]),
                )
            self.bus_tie_breakers[bus_tie_status[0] - 1].status = bus_tie_status[1]
        self.switchboard2bus_configuration()

    def get_bus_tie_status(self) -> List[np.ndarray]:
        if len(self.bus_tie_breakers) == 0:
            return []

        length_status = len(self.bus_tie_breakers[0].status)
        bus_tie_status = []
        for i, bus_tie_breaker in enumerate(self.bus_tie_breakers):
            if len(bus_tie_breaker.status) != length_status:
                raise IndexError(
                    "The length of the status values for bus tie breakers is not "
                    "identical for no. {} breaker".format(i + 1)
                )
            bus_tie_status.append(bus_tie_breaker.status)
        return bus_tie_status

    def switchboard2bus_configuration(self) -> None:
        bus_tie_status_list = self.get_bus_tie_status()
        bus_tie_status_array = np.array(bus_tie_status_list)
        self.no_bus = []
        self.switchboard2bus = []
        self.bus_tie_status_system = []
        self.bus_configuration_change_index = [0]

        if len(self.bus_tie_breakers) == 0:
            self.no_bus.append(1)
            if len(self.switchboards) > 1:
                msg = "There should be only one switchboard when there is no bus tie breaker."
                logger.error(msg)
                raise ConfigurationError(msg)
            swb_id = None
            for _, swb in self.switchboards.items():
                swb_id = swb.id
                break
            if swb_id is None:
                msg = "There should be at least one switchboards for bus tie configuration."
                logger.error(msg)
                raise ConfigurationError(msg)
            bus_id = BusId(swb_id)
            self.switchboard2bus.append({swb_id: bus_id})
            return

        #: Find the index when the bus configuration changes
        bus_tie_diff = np.any(np.diff(bus_tie_status_array, axis=1), axis=0)
        index = np.concatenate((np.array([True]), bus_tie_diff))
        self.bus_tie_status_system = [
            bus_tie_status[index] for bus_tie_status in bus_tie_status_list
        ]
        self.bus_configuration_change_index = np.arange(0, len(index))[index].tolist()

        #: Find the number of logical buses and mapping for switchboard to bus
        for i in range(len(self.bus_tie_status_system[0])):
            bus_config_status = [
                self.bus_tie_status_system[j][i]
                for j, bus_tie_breaker in enumerate(self.bus_tie_breakers)
            ]
            switchboard2bus: Dict[SwbId, BusId] = {}
            for busId, swbId in enumerate(self.switchboard_id):
                switchboard2bus[swbId] = BusId(busId)
            merge_buses: Dict[BusId, BusId] = {}
            for j, closed in enumerate(bus_config_status):
                if closed:
                    bus1 = switchboard2bus[self.bus_tie_breakers[j].switchboard_ids[0]]
                    bus2 = switchboard2bus[self.bus_tie_breakers[j].switchboard_ids[1]]
                    if bus1 in merge_buses and bus2 in merge_buses:
                        raise NotImplementedError("this case is not implemented")
                    elif bus1 in merge_buses:
                        new_bus_id = merge_buses[bus1]
                        merge_buses[bus2] = new_bus_id
                    elif bus2 in merge_buses:
                        new_bus_id = merge_buses[bus2]
                        merge_buses[bus1] = new_bus_id
                    else:
                        new_bus_id = bus1
                        merge_buses[bus2] = new_bus_id

            no_bus = 0
            for idx, old_bus_id in switchboard2bus.items():
                if old_bus_id in merge_buses:
                    new_bus_id = merge_buses[old_bus_id]
                    switchboard2bus[idx] = new_bus_id
                else:
                    no_bus += 1

            # Rename so that the numbers are consecutive:
            bus_ids = []
            for _, bus in switchboard2bus.items():
                if bus not in bus_ids:
                    bus_ids.append(bus)
            new_bus_ids = {}
            for new, old in enumerate(bus_ids):
                new_bus_ids[old] = BusId(new + 1)

            for swb_id, bus_id in switchboard2bus.items():
                switchboard2bus[swb_id] = new_bus_ids[bus_id]

            self.no_bus.append(no_bus)
            self.switchboard2bus.append(switchboard2bus)

    @property
    def no_bus_configuration_change(self) -> int:
        return len(self.no_bus)

    def get_sum_power_out_rated_buses_by_power_type(
        self, type_: TypePower
    ) -> Dict[BusId, np.ndarray]:
        sum_power_out_rated_switchboards = {}
        for swb_id, switchboard in self.switchboards.items():
            sum_power_out_rated_switchboards[swb_id] = np.array(
                switchboard.get_power_rated_component_by_power_type(type_)
            ).sum()
        sum_power_out_rated_bus = {}
        for index, _ in enumerate(self.switchboards):
            sum_power_out_rated_bus[BusId(index + 1)] = np.zeros(self.no_bus_configuration_change)
        for i, switchboard2bus in enumerate(self.switchboard2bus):
            for swb_id, bus_id in switchboard2bus.items():
                sum_power_out_rated_bus[bus_id][i] += sum_power_out_rated_switchboards[swb_id]
        return sum_power_out_rated_bus

    def _get_sum_buses(
        self,
        which_value: TypeValueBus,
        power_type: TypePower = TypePower.POWER_CONSUMER,
    ) -> Dict[BusId, np.ndarray]:
        sum_switchboards = self._get_sum_switchboard(
            power_type=power_type, which_value=which_value
        )
        sum_buses: Dict[BusId, np.ndarray] = {}
        if len(sum_switchboards) == 0:
            for i in range(self.no_switchboard):
                sum_buses[BusId(i + 1)] = np.zeros(1)
            return sum_buses

        no_points = None
        for _, data in sum_switchboards.items():
            no_points = len(data)
            break
        if no_points is None:
            msg = "There is no data in sum_switchboards."
            logger.error(msg)
            raise ConfigurationError(msg)
        for i in range(self.no_switchboard):
            sum_buses[BusId(i + 1)] = np.zeros(no_points)
        for i in range(self.no_bus_configuration_change):
            index_start = self.bus_configuration_change_index[i]

            if i + 1 == self.no_bus_configuration_change:
                index_end = no_points
            else:
                index_end = self.bus_configuration_change_index[i + 1]

            for swb_id, bus_id in self.switchboard2bus[i].items():
                is_which_value_load_or_power_avail = which_value in [
                    TypeValueBus.LOAD_KW_SOURCES,
                    TypeValueBus.POWER_AVAIL_POWER_SOURCES_SYMMETRIC,
                ]
                is_component_of_power_type = self.switchboards[swb_id].component_by_power_type[
                    power_type.value
                ]
                if is_which_value_load_or_power_avail or is_component_of_power_type:
                    sum_buses[bus_id][index_start:index_end] += sum_switchboards[swb_id][
                        index_start:index_end
                    ]

        return sum_buses

    def _get_sum_switchboard(
        self, *, power_type: TypePower, which_value: TypeValueBus
    ) -> Dict[SwbId, np.ndarray]:
        """
        Calculates following sum for each switchboard: power input for components,
        power output for components, power load in kW for symmetrically loaded
        power sources, available power for symmetrically loaded power sources
        :param power_type:
        :param which_value:
        :return:
        """
        sum_switchboards: Dict[SwbId, np.ndarray] = {}
        len_sum = []
        sum_temp = None
        for _, switchboard in self.switchboards.items():
            if which_value == TypeValueBus.LOAD_KW_SOURCES:
                sum_temp = switchboard.get_sum_load_kw_sources_symmetric()
            elif which_value == TypeValueBus.POWER_AVAIL_POWER_SOURCES_SYMMETRIC:
                sum_temp = switchboard.get_sum_power_avail_for_power_sources_symmetric()
            else:
                if switchboard.component_by_power_type[power_type.value]:
                    if which_value == TypeValueBus.POWER_IN_BY_POWER_TYPE:
                        sum_temp = switchboard.get_sum_power_input_by_power_type(power_type)
                    elif which_value == TypeValueBus.POWER_OUT_BY_POWER_TYPE:
                        sum_temp = switchboard.get_sum_power_output_by_power_type(power_type)
                    else:
                        raise TypeError("The value name specified is not valid")
            if sum_temp is not None:
                sum_switchboards[switchboard.id] = sum_temp
                len_sum.append(sum_temp.size)
        number_diff_length = len(set(len_sum))
        if number_diff_length == 1:
            number_points = len_sum[0]
        elif number_diff_length == 2 and min(len_sum) == 1:
            number_points = max(len_sum)
        elif number_diff_length == 0:
            number_points = 0
        else:
            err_msg = (
                "The length of the sum of values ({}) of the switchboards is "
                "are not identical to each other.".format(which_value.name)
            )
            raise ConfigurationError(err_msg)

        # If any sum has a single value (size == 1) and others are array,
        # then make it a 1d array of zeros
        for swb_id, sum_power in sum_switchboards.items():
            if sum_power.size == 1 and number_points > 1:
                sum_switchboards[swb_id] = np.ones(number_points) * sum_power[0]

        return sum_switchboards

    def get_sum_power_in_buses_by_power_type(self, type_: TypePower) -> Dict[BusId, np.ndarray]:
        return self._get_sum_buses(TypeValueBus.POWER_IN_BY_POWER_TYPE, power_type=type_)

    def get_sum_power_output_buses_by_power_type(
        self, type_: TypePower
    ) -> Dict[BusId, np.ndarray]:
        return self._get_sum_buses(TypeValueBus.POWER_OUT_BY_POWER_TYPE, power_type=type_)

    def get_sum_load_kw_sources_symmetric_buses(self) -> Dict[BusId, np.ndarray]:
        return self._get_sum_buses(TypeValueBus.LOAD_KW_SOURCES, power_type=TypePower.POWER_SOURCE)

    def get_sum_consumption_kw_sources_switchboard(self) -> Dict[SwbId, np.ndarray]:
        sum_switchboards: Dict[SwbId, np.ndarray] = {}
        len_sum = set()
        for swb_id, switchboard in self.switchboards.items():
            sum_temp = switchboard.get_sum_power_input_by_power_type(TypePower.POWER_CONSUMER)
            sum_switchboards[swb_id] = sum_temp
            len_sum.add(len(sum_temp))

        # Allow scalars
        if 1 in len_sum and len(len_sum) > 1:
            len_sum.remove(1)

        if len(len_sum) > 1:
            msg = (
                "The length of the sum of power consumptions of the switchboards "
                "are not identical to each other."
            )
            logger.error(msg)
            raise ConfigurationError(msg)
        return sum_switchboards

    def get_sum_power_avail_power_sources_symmetric_buses(
        self,
    ) -> Dict[BusId, np.ndarray]:
        return self._get_sum_buses(TypeValueBus.POWER_AVAIL_POWER_SOURCES_SYMMETRIC)

    def validate_inputs_before_power_balance_calculation(self) -> None:
        """
        Make sure that the number of points are the same for all components.
        Need to set the power input of PTI/PTO and energy storage system
        to zeros  when they are used as a symmetric load sharing device for
        the whole period and no power input has been defined
        """
        power_input_sum_consumers = self.get_sum_power_in_buses_by_power_type(
            TypePower.POWER_CONSUMER
        )
        number_points = power_input_sum_consumers[BusId(1)].size

        if not isinstance(self.time_interval_s, (float, int)):
            if len(self.time_interval_s) == 0:
                msg = f"Time interval should be set. It is {self.time_interval_s}."
                logger.error(msg)
                raise InputError(msg)

        for swb_id, swb in self.switchboards.items():
            load_sharing_mode_energy_storage = swb.get_load_sharing_mode_components_by_power_type(
                TypePower.ENERGY_STORAGE
            )
            if load_sharing_mode_energy_storage:
                if number_points != load_sharing_mode_energy_storage[0].size:
                    msg = (
                        f"The dimension of thw load sharing mode "
                        f"{load_sharing_mode_energy_storage[0].size} is not the same as "
                        f"that of consumers {number_points}"
                    )
                    logger.error(msg)
                    raise InputError(msg)

            for i, load_sharing_mode_each in enumerate(load_sharing_mode_energy_storage):
                if load_sharing_mode_each.sum() == 0:
                    swb.set_power_load_component_from_power_input_by_type_and_name(
                        name=swb.name_component_by_power_type[TypePower.ENERGY_STORAGE.value][i],
                        power_type=TypePower.ENERGY_STORAGE,
                        power_input=np.zeros(number_points),
                    )
                else:
                    component = swb.component_by_power_type[TypePower.ENERGY_STORAGE.value][i]
                    if component.power_input.size != number_points:
                        msg = (
                            f"The dimension of the power input of the energy storage "
                            f"({component.power_input.size}) is not the same as that of of "
                            f"consumer ({number_points})"
                        )
                        logger.error(msg)
                        raise InputError(msg)

            load_sharing_mode_pti_pto = swb.get_load_sharing_mode_components_by_power_type(
                TypePower.PTI_PTO
            )
            if load_sharing_mode_pti_pto:
                if number_points != load_sharing_mode_pti_pto[0].size:
                    msg = (
                        "The dimension of thw load sharing mode for PTI/PTO component "
                        f"({load_sharing_mode_pti_pto[0].size}) is "
                        f"not the same as that of of consumer ({number_points})"
                    )
                    logger.error(msg)
                    raise InputError(msg)
            for i, load_sharing_mode_each in enumerate(load_sharing_mode_pti_pto):
                if load_sharing_mode_each.sum() == 0:
                    swb.set_power_load_component_from_power_input_by_type_and_name(
                        name=swb.name_component_by_power_type[TypePower.PTI_PTO.value][i],
                        power_type=TypePower.PTI_PTO,
                        power_input=np.zeros(number_points),
                    )
                else:
                    component = swb.component_by_power_type[TypePower.PTI_PTO.value][i]
                    if component.power_input.size != number_points:
                        msg = (
                            "The dimension of the power input of the PTI/PTO component "
                            f"({component.power_input.size})is "
                            f"not the same as that of of consumer ({number_points})"
                        )
                        logger.error(msg)
                        raise InputError(msg)

    def do_power_balance_calculation(self) -> None:
        """
        Calculate the power output of the gensets and power sources (PTI/PTO or energy
        storage device at symmetric load sharing mode) based on the power balance.
        """
        self.validate_inputs_before_power_balance_calculation()

        sum_load_kw_sources_symmetric_buses = self.get_sum_load_kw_sources_symmetric_buses()
        sum_power_avail_power_sources_symmetric_buses = (
            self.get_sum_power_avail_power_sources_symmetric_buses()
        )

        no_points = 0

        # Calculate the bus load (0-1)
        load_buses: Dict[BusId, np.ndarray] = {}
        for bus_id, sum_load in sum_load_kw_sources_symmetric_buses.items():
            sum_power_avail = sum_power_avail_power_sources_symmetric_buses[bus_id]
            no_points = sum_load.size
            index_non_zero: np.ndarray = sum_load != 0
            load_buses[bus_id] = np.zeros(shape=sum_load.shape)
            if index_non_zero.any():
                load_buses[bus_id][index_non_zero] = (
                    sum_load[index_non_zero] / sum_power_avail[index_non_zero]
                )

        # Set the power output for the power sources for each switchboard
        for _, switchboard in self.switchboards.items():
            load_switchboard_symmetric_power_source = np.zeros(no_points)
            for i, switchboard2bus in enumerate(self.switchboard2bus):
                index_start = self.bus_configuration_change_index[i]
                index_end = (
                    self.bus_configuration_change_index[i + 1]
                    if i + 1 < self.no_bus_configuration_change
                    else no_points
                )
                bus_id = switchboard2bus[switchboard.id]
                load_switchboard_symmetric_power_source[index_start:index_end] = load_buses[
                    bus_id
                ][index_start:index_end]
            switchboard.set_power_out_power_sources(load_switchboard_symmetric_power_source)

    # noinspection DuplicatedCode
    def get_fuel_energy_consumption_running_time(
        self,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        fuel_option: Optional[FuelOption] = None,
    ) -> FEEMSResult:
        """
        Get the performance result of the power calculation. Prerequisite:
          - setting load on the power consumers,
          - setting status (on/off) of the power consumers, pti_pto, energy storage devices,
          - setting the load sharing status (0 for symmetric load sharing, 0~1 for specific power)
            of the power consumers, pti_pto, energy storage devices
          - setting power input to the power sources with asymmetric load sharing
          - doing power balance calculation

        Args:
            fuel_specified_by: FuelSpecifiedBy.IMO/EU. Default is IMO
            fuel_option: Optional fuel selection to apply to all multi-fuel engines.

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
        selected_option = self._validate_selected_fuel_option(fuel_option)
        fuel_type = selected_option.fuel_type if selected_option else None
        fuel_origin = selected_option.fuel_origin if selected_option else None
        res = FEEMSResult(detail_result=pd.DataFrame())
        if len(self.switchboards) == 0:
            logger.warning("There is no switchboard in the system")
            return FEEMSResult(duration_s=0)
        for _, switchboard in self.switchboards.items():
            result_swb: FEEMSResult = switchboard.get_fuel_energy_consumption_running_time(
                time_interval_s=self.time_interval_s,
                integration_method=self.integration_method,
                fuel_specified_by=fuel_specified_by,
                fuel_type=fuel_type,
                fuel_origin=fuel_origin,
            )
            result_swb.detail_result["switchboard id"] = switchboard.id
            res = res.sum_with_freeze_duration(result_swb)

        return res

    def get_fuel_energy_consumption_running_time_scalar(
        self,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        fuel_option: Optional[FuelOption] = None,
    ) -> FEEMSResult:
        """
        Get the performance result of the power calculation. Prerequisite:
          - setting load on the power consumers,
          - setting status (on/off) of the power consumers, pti_pto, energy storage devices,
          - setting the load sharing status (0 for symmetric load sharing, 0~1 for specific power) of the power
            consumers, pti_pto, energy storage devices
          - setting power input to the power sources with asymmetric load sharing
          - doing power balance calculation

        Args:
            fuel_specified_by: FuelSpecifiedBy.IMO/EU. Default is IMO
            fuel_option: Optional fuel selection to apply to all multi-fuel engines.

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
        selected_option = self._validate_selected_fuel_option(fuel_option)
        fuel_type = selected_option.fuel_type if selected_option else None
        fuel_origin = selected_option.fuel_origin if selected_option else None
        res = FEEMSResult()
        for _, switchboard in self.switchboards.items():
            result_swb: FEEMSResult = (
                switchboard.get_fuel_energy_consumption_running_time_without_details(
                    time_interval_s=self.time_interval_s,
                    integration_method=self.integration_method,
                    fuel_specified_by=fuel_specified_by,
                    fuel_type=fuel_type,
                    fuel_origin=fuel_origin,
                )
            )
            res = res.sum_with_freeze_duration(result_swb)
        return res


class MechanicalPropulsionSystem(MachinerySystem):
    """
    System configuration for mechanical / hybrid propulsion. One should provide its name,
    and components for initialization to create an instance. The components should include
    at least one of each following category.
    - Main engine: Required. At least one per shaftline. Power source of the mechanical
    propulsion. Use MainEngineForMechanicalPropulsion instance. If it is connected to gearbox,
    it is recommended to set the gearbox together as a serial system component.
    Use MainEngineWithGearBoxForMechanicalPropulsion in that case.
    - PTI_PTO: Optional. Only one per shaftline allowed. Use PTIPTO class to create an instance.
    - Mechanical loads: Required. At least one per shaftline. Use MechanicalPropulsionComponent.
    """

    name: str
    main_engines: List[
        Union[
            MainEngineForMechanicalPropulsion,
            MainEngineWithGearBoxForMechanicalPropulsion,
        ]
    ]
    pti_ptos: List[PTIPTO]
    mechanical_loads: List[MechanicalComponent]
    shaft_line: List[ShaftLine]
    component_by_shaft_line_id: Dict[int, List[MechanicalComponent]]
    shaft_line_id: List[int]
    errors_simulation_inputs: List[str]

    def __init__(self, name: str, components_list: List[MechanicalComponent]):
        self.name = name
        self.main_engines = []
        self.pti_ptos = []
        self.mechanical_loads = []
        self.shaft_line: List[ShaftLine] = []
        self.component_by_shaft_line_id: Dict[int, List[MechanicalComponent]] = {}
        self.errors_simulation_inputs = []
        #: Collect the components in the category and collect shaft line ids.
        for component in components_list:
            if component.shaft_line_id not in self.component_by_shaft_line_id.keys():
                self.component_by_shaft_line_id[component.shaft_line_id] = [component]
            else:
                self.component_by_shaft_line_id[component.shaft_line_id].append(component)
            if component.type in [
                TypeComponent.MAIN_ENGINE,
                TypeComponent.MAIN_ENGINE_WITH_GEARBOX,
            ]:
                self.main_engines.append(component)
            elif component.type == TypeComponent.PTI_PTO_SYSTEM:
                self.pti_ptos.append(component)
            else:
                self.mechanical_loads.append(component)

        #: make a sorted, unique list of shaft line id.
        self.shaft_line_id = list(self.component_by_shaft_line_id.keys())
        self.shaft_line_id.sort()

        #: Create a shaft line instances
        for id_num in self.shaft_line_id:
            self.shaft_line.append(
                ShaftLine(
                    "shaft line %i" % id_num,
                    id_num,
                    self.component_by_shaft_line_id[id_num],
                )
            )

    @property
    def multi_fuel_engine_inventory(self) -> Dict[str, List[FuelOption]]:
        inventory: Dict[str, List[FuelOption]] = {}
        for main_engine in self.main_engines:
            engine_obj = getattr(main_engine, "engine", None)
            options = _extract_multi_fuel_options(engine_obj)
            if options:
                inventory[main_engine.name] = list(options)
        return inventory

    @property
    def available_fuel_options(self) -> List[FuelOption]:
        options: List[FuelOption] = []
        seen: Set[FuelOption] = set()
        for engine_options in self.multi_fuel_engine_inventory.values():
            for option in engine_options:
                if option not in seen:
                    options.append(option)
                    seen.add(option)
        for main_engine in self.main_engines:
            engine_obj: Optional[Union[Engine, EngineMultiFuel]] = getattr(
                main_engine, "engine", None
            )
            if engine_obj is None or isinstance(engine_obj, EngineMultiFuel):
                continue
            fuel_option = FuelOption(
                fuel_type=engine_obj.fuel_type,
                fuel_origin=engine_obj.fuel_origin,
                for_pilot=False,
                primary=True,
            )
            if fuel_option not in seen:
                options.append(fuel_option)
                seen.add(fuel_option)
            if hasattr(engine_obj, "pilot_fuel_type"):
                fuel_option = FuelOption(
                    fuel_type=engine_obj.pilot_fuel_type,
                    fuel_origin=engine_obj.pilot_fuel_origin,
                    for_pilot=True,
                    primary=True,
                )
                if fuel_option not in seen:
                    options.append(fuel_option)
                    seen.add(fuel_option)
        return options

    @property
    def no_shaft_lines(self) -> int:
        return len(self.shaft_line_id)

    @property
    def no_main_engines(self) -> int:
        return len(self.main_engines)

    @property
    def no_pti_ptos(self) -> int:
        return len(self.pti_ptos)

    @property
    def no_mechanical_loads(self) -> int:
        return len(self.mechanical_loads)

    def get_component_by_name_shaft_line_id_power_type(
        self, name: str, shaft_line_id: int, power_type: TypePower
    ) -> MechanicalComponent:
        index_shaft_line = self.shaft_line_id.index(shaft_line_id)
        return self.shaft_line[index_shaft_line].get_component_by_name_power_type(name, power_type)

    def set_power_consumer_load_by_value_for_given_name_shaft_line_id(
        self, name: str, shaft_line_id: int, power_input: np.ndarray
    ) -> Union[int, None]:
        """
        Set power load (power input) of the power consumer directly by values
        for the given name and the shaft line id.
        :param name: The name of the component
        :param shaft_line_id: The id of the shaft line
        :param power_input: ndarray of power input value in kW
        :return: 1 for success, None for error
        """
        component = self.get_component_by_name_shaft_line_id_power_type(
            name, shaft_line_id, TypePower.POWER_CONSUMER
        )
        if component is not None:
            if not isinstance(
                component,
                (
                    MainEngineForMechanicalPropulsion,
                    MainEngineWithGearBoxForMechanicalPropulsion,
                ),
            ):
                component.set_power_output_from_input(power_input)
                return 1
        return None

    def set_power_consumer_load_by_power_output_for_given_name_shaft_line_id(
        self, name: str, shaft_line_id: int, power_output: np.ndarray
    ) -> Union[int, None]:
        """
        Set power load (power input) of the power consumer by giving the power output
        for the given name and the shaft line id.
        :param name: The name of the component
        :param shaft_line_id: The id of the shaft line
        :param power_output: ndarray of power output value in kW
        :return: 1 for success, None for error
        """
        component = self.get_component_by_name_shaft_line_id_power_type(
            name, shaft_line_id, TypePower.POWER_CONSUMER
        )
        if component is not None:
            if not isinstance(
                component,
                (
                    MainEngineForMechanicalPropulsion,
                    MainEngineWithGearBoxForMechanicalPropulsion,
                ),
            ):
                component.set_power_input_from_output(power_output)
                return 1
        return None

    def set_full_pti_mode_for_name_shaft_line_id(
        self, name: str, shaft_line_id: int, full_pti_pto_mode: np.ndarray
    ) -> Union[int, None]:
        """
        Set full PTI mode for the PTI/PTO (True: full PTI mode, False: otherwise)
        :param name: name of the PTI/PTO
        :param shaft_line_id: shaft line id for the PTI/PTO
        :param full_pti_pto_mode: ndarray of boolean
        :return: 1 for success, None for error
        """
        pti_pto = self.get_component_by_name_shaft_line_id_power_type(
            name, shaft_line_id, TypePower.PTI_PTO
        )
        if isinstance(pti_pto, PTIPTO):
            pti_pto.full_pti_mode = full_pti_pto_mode
            return 1
        raise TypeError(
            "The component for PTIPTO is not found or specified as PTIPTO but not a correct instance"
        )

    def set_power_input_pti_pto_by_value_for_name_shaft_line_id(
        self, name: str, shaft_line_id: int, power_input: np.ndarray
    ) -> Union[int, None]:
        """
        Set power input / output for the PTI/PTO by the given power input
        :param name: name of the PTI/PTO
        :param shaft_line_id: shaft line id for the PTI/PTO
        :param power_input: ndarray of power output value in kW
        :return: 1 for success, None for error
        """
        pti_pto = self.get_component_by_name_shaft_line_id_power_type(
            name, shaft_line_id, TypePower.PTI_PTO
        )
        if isinstance(pti_pto, PTIPTO):
            pti_pto.set_power_output_from_input(power_input)
            return 1
        raise TypeError(
            "The component for PTIPTO is not found or specified as PTIPTO but not a correct instance"
        )

    def set_power_input_pti_pto_by_power_output_value_for_name_shaft_line_id(
        self, name: str, shaft_line_id: int, power_output: np.ndarray
    ) -> Union[int, None]:
        """
        Set power input / output for the PTI/PTO by the given power output
        :param name: name of the PTI/PTO
        :param shaft_line_id: shaft line id for the PTI/PTO
        :param power_output: ndarray of power output value in kW
        :return: 1 for success, None for error
        """
        pti_pto = self.get_component_by_name_shaft_line_id_power_type(
            name, shaft_line_id, TypePower.PTI_PTO
        )
        if isinstance(pti_pto, PTIPTO):
            pti_pto.set_power_input_from_output(power_output)
            return 1
        raise TypeError(
            "The component for PTIPTO is not found or specified as PTIPTO but not a correct instance"
        )

    def set_status_main_engine_for_name_shaft_line_id(
        self, name: str, shaft_line_id: int, status: np.ndarray
    ) -> Union[int, None]:
        """
        Set status for the main engine (True: on, False: off)
        :param name: name of the main engine
        :param shaft_line_id: shaft line id for the main engine
        :param status: array of status of the engine status (boolean)
        :return: 1 for success, None for error
        """
        engine = self.get_component_by_name_shaft_line_id_power_type(
            name, shaft_line_id, TypePower.POWER_SOURCE
        )
        if engine:
            engine.status = status
            return 1
        return None

    def do_power_balance(self) -> None:
        """
        Perform power balance calculation, determining the main engine outputs.
        Pre-requisite:
          - All the loads on the power consumers have been set
          - PTI/PTO power input/output has been set from the electrical power balance, if relevant
          - Set Full PTI mode if applicable
        In some cases, the power balance calculation has to be done at least two times if there is
        any case of full PTI mode. In the full PTI mode, it is the PTI that balances the mechanical
        loads on the shaft lines. Therefore, the PTI power input is the output of this mechanical
        power balance calculation which is input to the power balance calculation of the electric
        system. The recommendation is
          - to perform electric power balance to get the power output of the pto.
          - then to perform mechanical power balance calculation which will change the
            power input/output in case of full PTI mode
          - finally to perform electric power balance again with the updated power input
            of the PTI/PTO
        """
        if self.validate_inputs_before_power_balance_calculation():
            for shaft_line in self.shaft_line:
                shaft_line.do_power_balance()
        else:
            err_msg = "There are errors in the input for the simulation."
            err_msg += "\n".join(self.errors_simulation_inputs)
            raise ConfigurationError(err_msg)

    def validate_inputs_before_power_balance_calculation(self) -> bool:
        """
        Make sure that the number of points are the same for all components.
        Need to set the power input of PTI/PTO and energy storage system
        to zeros  when they are used as a symmetric load sharing device for
        the whole period and no power input has been defined
        """
        self.errors_simulation_inputs = []
        # collect all the input values and check if the number of points are the same
        components = self.mechanical_loads + self.pti_ptos
        number_point_power_inputs = [
            power_consumer.power_input.size for power_consumer in components
        ]
        if len(set(number_point_power_inputs)) > 1:
            err_msg = (
                "There are mismatches in the length of the power inputs "
                "for the mechanical loads or PTI/PTOs."
            )
            err_msg = reduce(
                lambda acc, component: acc + f"\n\t{component.name}: {component.power_input.size}",
                components,
                err_msg,
            )
            self.errors_simulation_inputs.append(err_msg)
            return False
        number_points = set(number_point_power_inputs).pop()

        # Check the size of the status of the main engines and pti_ptos
        number_points_me_pti = {
            "main engines": [me.status.size for me in self.main_engines],
            "PTI/PTO": [pti_pto.status.size for pti_pto in self.pti_ptos],
        }
        if len(number_points_me_pti["PTI/PTO"]) == 0:
            number_points_me_pti.pop("PTI/PTO")
        for key, number_points_comp in number_points_me_pti.items():
            components = self.main_engines if key == "main engines" else self.pti_ptos
            if len(set(number_points_comp)) > 1:
                err_msg = (
                    f"There are mismatches in the number of points of the status "
                    f"for the {key}."
                    f"The size should be the same as power inputs of consumers: "
                    f"({number_point_power_inputs})"
                )
                err_msg = reduce(
                    lambda acc, comp: acc + f"\n\t{comp.name}: {comp.status.size}",
                    components,
                    err_msg,
                )
                self.errors_simulation_inputs.append(err_msg)
                return False
            if len(set(number_points_comp)) > 0:
                number_points_status = set(number_points_comp).pop()
                if number_points != number_points_status:
                    err_msg = (
                        f"The number of points of the status ({number_points_status}) of the "
                        f"{key} should be the same as that of power "
                        f"inputs of consumers ({number_points})."
                    )
                    err_msg = reduce(
                        lambda acc, comp: acc + f"\n\t{comp.name}: {comp.status.size}",
                        components,
                        err_msg,
                    )
                    self.errors_simulation_inputs.append(err_msg)
                    return False

        # Check the size of the full pti mode of the pti_ptos
        number_points_full_pti = [pti_pto.full_pti_mode.size for pti_pto in self.pti_ptos]
        if len(set(number_points_full_pti)) > 1:
            err_msg = (
                f"There are mismatches in the number of points of the full pti mode "
                f"for the PTI/PTO."
                f"The size should be the same as power inputs of consumers: "
                f"({number_point_power_inputs})"
            )
            err_msg = reduce(
                lambda acc, comp: acc + f"\n\t{comp.name}: {comp.full_pti_mode.size}",
                self.pti_ptos,
                err_msg,
            )
            self.errors_simulation_inputs.append(err_msg)
            return False
        if len(set(number_points_full_pti)) > 0:
            number_points_full_pti = set(number_points_full_pti).pop()
            if number_points != number_points_full_pti:
                err_msg = (
                    f"The number of points of the full pti mode ({number_points_full_pti}) of the "
                    f"PTI/PTO should be the same as that of power "
                    f"inputs of consumers ({number_points})."
                )
                err_msg = reduce(
                    lambda acc, comp: acc + f"\n\t{comp.name}: {comp.full_pti_mode.size}",
                    self.pti_ptos,
                    err_msg,
                )
                self.errors_simulation_inputs.append(err_msg)
                return False
        return True

    def get_fuel_energy_consumption_running_time(
        self,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        fuel_option: Optional[FuelOption] = None,
    ) -> FEEMSResult:
        """
        Get the performance result of the power calculation. Prerequisite:
          - setting load on the power consumers,
          - setting status (on/off) of the main engines and PTI/PTOs
          - doing power balance calculation

        Args:
            fuel_specified_by: FuelSpecifiedBy.IMO/EU. Default is IMO
            fuel_option: Optional fuel selection to apply to all multi-fuel engines.

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
        selected_option = self._validate_selected_fuel_option(fuel_option)
        fuel_type = selected_option.fuel_type if selected_option else None
        fuel_origin = selected_option.fuel_origin if selected_option else None
        res = FEEMSResult(
            energy_consumption_electric_total_mj=0,
            energy_consumption_mechanical_total_mj=0,
            energy_stored_total_mj=0,
            running_hours_genset_total_hr=0,
            running_hours_fuel_cell_total_hr=0,
            running_hours_pti_pto_total_hr=0,
            detail_result=pd.DataFrame(),
        )
        if len(self.shaft_line) == 0:
            logger.warning("There is no shaftline in the system")
            return FEEMSResult(duration_s=0)
        for shaft_line in self.shaft_line:
            result_shaft_line: FEEMSResult = shaft_line.get_fuel_calculation_running_hours(
                time_step=self.time_interval_s,
                integration_method=self.integration_method,
                fuel_specified_by=fuel_specified_by,
                fuel_type=fuel_type,
                fuel_origin=fuel_origin,
            )
            result_shaft_line.detail_result["shaftline id"] = shaft_line.id
            res = res.sum_with_freeze_duration(result_shaft_line)
        return res


class HybridPropulsionSystem(MachinerySystem):
    def __init__(
        self,
        name: str,
        electric_system: ElectricPowerSystem,
        mechanical_system: MechanicalPropulsionSystem,
    ):
        self.name = name
        self.electric_system = electric_system
        self.mechanical_system = mechanical_system

        #: Check if PTI/PTO machine exists and if it is the same component instance for both
        #: electric and mechanical system
        self._check_configuration()

    def _check_configuration(self) -> None:
        if self.electric_system.no_pti_pto == 0:
            msg = "PTI/PTO is not configured for the electric system."
            logger.error(msg)
            raise ConfigurationError(msg)
        if self.mechanical_system.no_pti_ptos == 0:
            msg = "PTI/PTO is not configured for the mechanical system."
            logger.error(msg)
            raise ConfigurationError(msg)
        if self.electric_system.no_pti_pto != self.mechanical_system.no_pti_ptos:
            msg = "Number of PTI/PTO for electric system does not match the mechanical."
            logger.error(msg)
            raise ConfigurationError(msg)
        for pti_pto in self.electric_system.pti_pto:
            if pti_pto not in self.mechanical_system.pti_ptos:
                msg = (
                    "One of the PTI/PTOs configured for electric system "
                    "does not match the ones in the mechanical system"
                )
                logger.error(msg)
                raise ConfigurationError(msg)

    def do_power_balance_calculation(self) -> None:
        """
        Perform power balance calculation, determining the power output of all the power sources
        Pre-requisite:
          - All the loads on the power consumers have been set (Mechanical / Electrical)
          - PTI/PTO power input/output has been set from the electrical power balance, if applicable
          - Set Full PTI mode if applicable
        The power balance calculation has to be done two times if there is
        any case of full PTI mode. In the full PTI mode, it is the PTI that balances the mechanical
        loads on the shaft lines. Therefore, the PTI power input is the output of this mechanical
        power balance calculation which becomes input to the power balance calculation of the
        electric system. The recommendation is
          - to perform electric power balance to get the power output of the pto.
          - then to perform mechanical power balance calculation which will change
            the power input/output in case of full PTI mode
          - finally to perform electric power balance again with the updated power
            input of the PTI/PTO
        """
        self.electric_system.do_power_balance_calculation()
        self.mechanical_system.do_power_balance()
        # Check for full PTI mode and repeat power balance calculation for electric system if
        # full PTI mode is found
        full_pti_pto_mode_exists = False
        for pti_pto in self.electric_system.pti_pto:
            full_pti_pto_mode_exists |= any(pti_pto.full_pti_mode)
        if full_pti_pto_mode_exists:
            self.electric_system.do_power_balance_calculation()

    @property
    def multi_fuel_engine_inventory(self) -> Dict[str, List[FuelOption]]:
        inventory: Dict[str, List[FuelOption]] = {}
        for name, options in self.mechanical_system.multi_fuel_engine_inventory.items():
            inventory[f"mechanical::{name}"] = list(options)
        for name, options in self.electric_system.multi_fuel_engine_inventory.items():
            inventory[f"electric::{name}"] = list(options)
        return inventory

    @property
    def available_fuel_options(self) -> List[FuelOption]:
        # Combine available fuel options from both systems
        options: List[FuelOption] = self.mechanical_system.available_fuel_options.copy()
        seen: Set[FuelOption] = set(options)
        for option in self.electric_system.available_fuel_options:
            if option not in seen:
                options.append(option)
                seen.add(option)
        return options

    def get_fuel_energy_consumption_running_time(
        self,
        time_interval_s: float,
        integration_method: IntegrationMethod = IntegrationMethod.simpson,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        fuel_option: Optional[FuelOption] = None,
    ) -> FEEMSResultForMachinerySystem:
        """Calculates fuel consumption, emissions, energy consumption and running hours and
        returns the result.

        Args:
            time_interval_s: the time interval for input load series in seconds
            integration_method: Integration method, "simpson" or "trapezoid"
            fuel_specified_by: FuelSpecifiedBy.IMO/EU. Default is IMO
            fuel_option: Optional fuel selection to apply across both subsystems.
        Returns:
            FEEMSResultForMachinerySystem
        """
        if fuel_specified_by not in [
            FuelSpecifiedBy.IMO,
            FuelSpecifiedBy.FUEL_EU_MARITIME,
        ]:
            raise NotImplementedError(
                f"Fuel specified by {fuel_specified_by.name} is not implemented"
            )
        selected_option = self._validate_selected_fuel_option(fuel_option)
        mechanical_option = (
            selected_option
            if selected_option and selected_option in self.mechanical_system.available_fuel_options
            else None
        )
        electric_option = (
            selected_option
            if selected_option and selected_option in self.electric_system.available_fuel_options
            else None
        )
        self.mechanical_system.set_time_interval(
            time_interval_s=time_interval_s,
            integration_method=integration_method,
        )
        result_mech = self.mechanical_system.get_fuel_energy_consumption_running_time(
            fuel_specified_by=fuel_specified_by,
            fuel_option=mechanical_option,
        )
        self.electric_system.set_time_interval(
            time_interval_s=time_interval_s, integration_method=integration_method
        )
        result_elec = self.electric_system.get_fuel_energy_consumption_running_time(
            fuel_specified_by=fuel_specified_by,
            fuel_option=electric_option,
        )
        return FEEMSResultForMachinerySystem(
            electric_system=result_elec,
            mechanical_system=result_mech,
        )


class MechanicalPropulsionSystemWithElectricPowerSystem(MachinerySystem):
    """Class for conventional mechanical system with independent power system"""

    def __init__(
        self,
        name: str,
        electric_system: ElectricPowerSystem,
        mechanical_system: MechanicalPropulsionSystem,
    ):
        """Constructor for the class"""
        self.name = name
        self.electric_system = electric_system
        self.mechanical_system = mechanical_system

    def do_power_balance_calculation(self) -> None:
        """Perform power balance calculation, determining the power output of all the power sources
        Pre-requisite:
          - Refer to do_power_balance_calculation for ElectricPowerSystem
          - Refer to do_power_balance for MechanicalPropulsionSystem
        """
        self.electric_system.do_power_balance_calculation()
        self.mechanical_system.do_power_balance()

    def get_fuel_energy_consumption_running_time(
        self,
        time_interval_s: float,
        nox_emission_criteria: int = 2,
        integration_method: IntegrationMethod = IntegrationMethod.simpson,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        fuel_option: Optional[FuelOption] = None,
    ) -> FEEMSResultForMachinerySystem:
        """Calculates fuel consumption, emissions, energy consumption and running hours and
        returns the result.

        Args:
            time_interval_s: the time interval for input load series in seconds
            nox_emission_criteria: IMO NOx emission tier 1, 2, 3
            integration_method: Integration method, "simpson" or "trapezoid"
            fuel_specified_by: FuelSpecifiedBy.IMO/EU. Default is IMO
            fuel_option: Optional fuel selection to apply across both subsystems.
        Returns:
            Tuple of FEEMSResult for mechanical system and electric system, respectively
        """
        if fuel_specified_by not in [
            FuelSpecifiedBy.IMO,
            FuelSpecifiedBy.FUEL_EU_MARITIME,
        ]:
            raise NotImplementedError(
                f"Fuel specified by {fuel_specified_by.name} is not implemented"
            )
        selected_option = self._validate_selected_fuel_option(fuel_option)
        mechanical_option = (
            selected_option
            if selected_option and selected_option in self.mechanical_system.available_fuel_options
            else None
        )
        electric_option = (
            selected_option
            if selected_option and selected_option in self.electric_system.available_fuel_options
            else None
        )
        self.mechanical_system.set_time_interval(
            time_interval_s=time_interval_s,
            integration_method=integration_method,
        )
        result_mech = self.mechanical_system.get_fuel_energy_consumption_running_time(
            fuel_specified_by=fuel_specified_by,
            fuel_option=mechanical_option,
        )
        self.electric_system.set_time_interval(
            time_interval_s=time_interval_s, integration_method=integration_method
        )
        result_elec = self.electric_system.get_fuel_energy_consumption_running_time(
            fuel_specified_by=fuel_specified_by,
            fuel_option=electric_option,
        )
        return FEEMSResultForMachinerySystem(
            electric_system=result_elec,
            mechanical_system=result_mech,
        )

    @property
    def multi_fuel_engine_inventory(self) -> Dict[str, List[FuelOption]]:
        inventory: Dict[str, List[FuelOption]] = {}
        for name, options in self.mechanical_system.multi_fuel_engine_inventory.items():
            inventory[f"mechanical::{name}"] = list(options)
        for name, options in self.electric_system.multi_fuel_engine_inventory.items():
            inventory[f"electric::{name}"] = list(options)
        return inventory

    @property
    def available_fuel_options(self) -> List[FuelOption]:
        # Combine available fuel options from both systems
        options: List[FuelOption] = self.mechanical_system.available_fuel_options.copy()
        seen: Set[FuelOption] = set(options)
        for option in self.electric_system.available_fuel_options:
            if option not in seen:
                options.append(option)
                seen.add(option)
        return options
