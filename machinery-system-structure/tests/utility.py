import random
from typing import List, Union, NamedTuple

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator

from feems import get_logger
from feems.components_model.component_base import Component, BasicComponent
from feems.components_model.component_electric import (
    FuelCellSystem,
    FuelCell,
    Genset,
    ElectricMachine,
    ElectricComponent,
    BatterySystem,
    SerialSystemElectric,
    Battery,
    PTIPTO,
)
from feems.components_model.component_mechanical import (
    Engine,
    MainEngineForMechanicalPropulsion,
    MechanicalPropulsionComponent,
)
from feems.components_model.node import Switchboard, ShaftLine
from feems.exceptions import ConfigurationError
from feems.types_for_feems import TypeComponent, TypePower, Power_kW, Speed_rpm
from feems.fuel import TypeFuel

# Create a electric efficiency curve for an electric machine
load = np.array([1.00, 0.75, 0.50, 0.25])
eff = np.array([0.9585018015, 0.9595580564, 0.9533974336, 0.9298900684])
ELECTRIC_MACHINE_EFF_CURVE = np.array([load, eff]).transpose()

# Create an efficiency curve for an electric inverter
CONVERTER_EFF = np.array(
    [[1.00, 0.75, 0.50, 0.25], [0.98, 0.972, 0.97, 0.96]]
).transpose()


logger = get_logger(__name__)


class PowerSummary(NamedTuple):
    load_perc_symmetric_loaded_power_source: np.ndarray
    sum_power_input_power_consumer: np.ndarray
    sum_power_input_pti_pto: np.ndarray
    sum_power_input_energy_storage: np.ndarray


# noinspection PyShadowingNames
def create_random_monotonic_eff_curve(
    min_efficiency_perc=0, max_efficiency_perc=1
) -> np.ndarray:
    assert (
        max_efficiency_perc > min_efficiency_perc
    ), "maximum efficiency should be greater than minimum efficiency"
    monotonic = False
    load = np.array([0.25, 0.50, 0.75, 1.00])
    eff = np.zeros(load.shape)
    load_check = np.arange(0, 1.001, 0.001)
    while not monotonic:
        load = np.array([0.25, 0.50, 0.75, 1.00])
        eff = (
            np.random.rand(4) * (max_efficiency_perc - min_efficiency_perc)
            + min_efficiency_perc
        )
        eff.sort()
        # Check monotonic mapping
        interp_function = PchipInterpolator(load, eff, extrapolate=True)
        input_value = load_check / np.clip(interp_function(load_check), 0.01, 1)
        diff_input = np.diff(input_value)
        monotonic = (diff_input > 0).all() or (diff_input < 0).all()
    # plt.plot(load_check, input_value)
    # plt.show()
    return np.array([load, eff]).transpose()


def create_a_pti_pto(
    name: str = "PTI/PTO",
    rated_power: Power_kW = 3000,
    rated_speed: Speed_rpm = 900,
    switchboard_id: int = 1,
    shaft_line_id: int = 1,
):
    # Create a synchronous_machine instance
    synch_mach = ElectricMachine(
        type_=TypeComponent.SYNCHRONOUS_MACHINE,
        power_type=TypePower.PTI_PTO,
        name="synchronous machine",
        rated_power=rated_power,
        rated_speed=rated_speed,
        eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
    )

    # Create a rectifier instance
    rectifier = ElectricComponent(
        type_=TypeComponent.RECTIFIER,
        power_type=TypePower.POWER_TRANSMISSION,
        name="rectifier",
        rated_power=Power_kW(3000),
        eff_curve=np.array([99.5]),
    )

    # Create a inverter instance
    inverter = ElectricComponent(
        type_=TypeComponent.INVERTER,
        power_type=TypePower.POWER_TRANSMISSION,
        name="inverter",
        rated_power=rated_power,
        eff_curve=CONVERTER_EFF,
    )

    # Create a transformer instance
    transformer = ElectricComponent(
        type_=TypeComponent.TRANSFORMER,
        power_type=TypePower.POWER_TRANSMISSION,
        name="transformer",
        rated_power=rated_power,
        eff_curve=np.array([99]),
    )

    # Create a PTI/PTO instance and return.
    return PTIPTO(
        name=name,
        components=[transformer, inverter, rectifier, synch_mach],
        switchboard_id=switchboard_id,
        rated_power=rated_power,
        rated_speed=rated_speed,
        shaft_line_id=shaft_line_id,
    )


def create_components(
    name, number_components, rated_power_max, rated_speed_max
) -> Union[List[Component], Component]:
    components = []
    for i in range(number_components):
        rated_power = np.random.rand() * rated_power_max
        rated_speed = np.random.rand() * rated_speed_max
        type_ = TypeComponent(
            np.ceil(np.random.rand() * (len(TypeComponent.__members__) - 1))
        )
        components.append(
            Component("{0}{1}".format(name, i), type_, rated_power, rated_speed)
        )
    if number_components == 1:
        components[0].name = name
        return components[0]
    else:
        return components


def create_basic_components(
    name, number_components, rated_power_max, rated_speed_max
) -> Union[BasicComponent, List[BasicComponent]]:
    components = create_components(
        name, number_components, rated_power_max, rated_speed_max
    )
    basic_components = []
    if type(components) is list:
        for component in components:
            basic_components.append(
                BasicComponent(
                    type_=component.type,
                    name=component.name,
                    rated_power=component.rated_power,
                    power_type=random.choice([power_type for power_type in TypePower]),
                    rated_speed=component.rated_speed,
                    eff_curve=create_random_monotonic_eff_curve(),
                )
            )
    else:
        basic_components = BasicComponent(
            type_=components.type,
            name=components.name,
            rated_power=components.rated_power,
            power_type=random.choice([power_type for power_type in TypePower]),
            rated_speed=components.rated_speed,
            eff_curve=create_random_monotonic_eff_curve(),
        )
    return basic_components


# noinspection PyTypeChecker
def create_battery_system(
    name: str,
    rated_power: float,
    battery_capacity_kwh: float,
    switchboard_id: int,
    charging_rate_c=1,
    discharging_rate_c=1,
    converter: ElectricComponent = None,
    battery: ElectricComponent = None,
) -> BatterySystem:
    """
    Creat an energy storage system including the converter
    :param name: name
    :param rated_power: rated power at the terminal
    :param battery_capacity_kwh: Energy capacity of battery in kWh
    :param charging_rate_c: Maximum charging rate in C-rated
    :param discharging_rate_c: Maximum discharging rate in C-rated
    :param switchboard_id: switchboard id
    :param converter: (Optional) converter component
    :param battery: (Optional) energy storage component
    :return: BatterySystem component
    """
    # Create a converter with a random monotonic efficiency
    if converter is None:
        converter = ElectricComponent(
            TypeComponent.POWER_CONVERTER,
            "converter",
            rated_power,
            create_random_monotonic_eff_curve(),
            switchboard_id=switchboard_id,
        )

    # Create a fuel cell module with a random monotonic efficiency
    if battery is None:
        battery = Battery(
            "battery",
            battery_capacity_kwh,
            charging_rate_c,
            discharging_rate_c,
            switchboard_id=switchboard_id,
        )

    # Create a fuel cell system and return
    return BatterySystem(name, battery, converter, switchboard_id)


# noinspection PyTypeChecker
def create_a_propulsion_drive(
    name: str,
    rated_power: float,
    rated_speed: float,
    switchboard_id: int,
    transformer: ElectricComponent = None,
    converter: ElectricComponent = None,
    motor: ElectricMachine = None,
    gear_box: BasicComponent = None,
) -> SerialSystemElectric:
    """
    Create a propulsion drive component
    :param name: name
    :param rated_power: Rated power in kW
    :param rated_speed: Rated speed in RPM
    :param switchboard_id: Switchboard ID
    :param transformer: (Optional) transformer component
    :param converter: (Optional) converter component
    :param motor: (Optional) electric motor component
    :param gear_box: (Optional) gear box component
    :return: a propulsion drive component as an instance of SerialSystemElectric
    """
    while True:
        try:
            if transformer is None:
                transformer = ElectricComponent(
                    type_=TypeComponent.TRANSFORMER,
                    name="transformer for %s" % name,
                    power_type=TypePower.POWER_TRANSMISSION,
                    rated_power=rated_power,
                    rated_speed=rated_speed,
                    eff_curve=np.array([98.5]),
                )

            if converter is None:
                converter = ElectricComponent(
                    type_=TypeComponent.POWER_CONVERTER,
                    name="frequency converter for %s" % name,
                    power_type=TypePower.POWER_TRANSMISSION,
                    rated_power=rated_power,
                    rated_speed=rated_speed,
                    eff_curve=CONVERTER_EFF,
                )

            if motor is None:
                motor = ElectricComponent(
                    type_=TypeComponent.ELECTRIC_MOTOR,
                    name="electric motor for %s" % name,
                    power_type=TypePower.POWER_CONSUMER,
                    rated_power=rated_power,
                    rated_speed=rated_speed,
                    eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
                )

            if gear_box is None:
                gear_box = BasicComponent(
                    type_=TypeComponent.GEARBOX,
                    power_type=TypePower.POWER_TRANSMISSION,
                    name="gearbox for %s" % name,
                    rated_power=rated_power,
                    rated_speed=rated_speed,
                    eff_curve=np.array([98.0]),
                )

            propulsion_drive = SerialSystemElectric(
                type_=TypeComponent.PROPULSION_DRIVE,
                name=name,
                power_type=TypePower.POWER_CONSUMER,
                rated_power=rated_power,
                rated_speed=rated_speed,
                components=[transformer, converter, motor, gear_box],
                switchboard_id=switchboard_id,
            )
            return propulsion_drive
        except AssertionError:
            pass


def create_engine_component(
    name, rated_power_max, rated_speed_max, bsfc_curve=None
) -> Engine:
    # Create an engine component with a arbitrary bsfc curve
    rated_power = rated_power_max * np.random.rand()
    rated_speed = rated_speed_max * np.random.rand()
    if bsfc_curve is None:
        bsfc_curve = np.append(
            np.reshape(np.arange(0.1, 1.1, 0.1), (-1, 1)),
            np.random.rand(10, 1) * 200,
            axis=1,
        )
        logger.warning(
            "Efficiency of engine is not supplied, using random monotonic curve"
        )
    return Engine(
        type_=TypeComponent.MAIN_ENGINE,
        name=name,
        rated_power=rated_power,
        rated_speed=rated_speed,
        bsfc_curve=bsfc_curve,
    )


def create_main_engine_component(
    name, rated_power_max, rated_speed_max, shaft_line_id: int, bsfc_curve=None
) -> MainEngineForMechanicalPropulsion:
    engine = create_engine_component(
        name=name,
        rated_power_max=rated_power_max,
        rated_speed_max=rated_speed_max,
        bsfc_curve=bsfc_curve,
    )
    return MainEngineForMechanicalPropulsion(engine=engine, shaft_line_id=shaft_line_id)


# noinspection PyTypeChecker
def create_fuel_cell_system(
    name: str, rated_power: float, switchboard_id: int
) -> FuelCellSystem:
    """
    Create a fuel cell system with random monotonic efficiency
    :param name: name
    :param rated_power: rated power at the terminal
    :param switchboard_id: switchboard id
    :return: FuelCellSystem component instance
    """

    # Create a converter with a random monotonic efficiency
    converter = ElectricComponent(
        TypeComponent.POWER_CONVERTER,
        "converter",
        rated_power,
        create_random_monotonic_eff_curve(),
        switchboard_id=switchboard_id,
    )

    # Get the maximum efficiency at 100%
    max_eff_converter = converter.get_efficiency_from_load_percentage(1)

    # Create a fuel cell module with a random monotonic efficiency
    fuel_cell_module = FuelCell(
        "fuel cell",
        rated_power / max_eff_converter,
        create_random_monotonic_eff_curve(),
    )

    # Create a fuel cell system and return
    return FuelCellSystem(name, fuel_cell_module, converter, switchboard_id)


def create_genset_component(
    name: str,
    rated_power: Power_kW,
    rated_speed: Speed_rpm,
    switchboard_id: int,
    generator: ElectricMachine = None,
    engine: Engine = None,
    bsfc_curve: np.ndarray = None,
    eff_curve_gen: np.ndarray = None,
) -> Genset:
    """
    Create a genset component and return
    :param name: name
    :param rated_power: rated power at the terminal
    :param rated_speed: rated speed
    :param switchboard_id: switchboard id
    :param (Optional) generator: generator component instance
    :param (Optional) engine: engine component instance
    :param (Optional) bsfc_curve: BSFC curve for the engine with a dim of n x 2.
    A randomly generated curve will be used unless it is given.
    :param (Optional) eff_curve_gen: Efficiency curve for generator with a dimension of n x 2.
    A randomly generated curve will be used unless it is given.
    :return: Genset component instance
    """
    if eff_curve_gen is None:
        eff_curve_gen = create_random_monotonic_eff_curve()
        logger.warning(
            "Efficiency of generator is not supplied, using random monotonic curve"
        )

    # Create a generator component, if not provided or not proper component
    if generator is None or type(generator) is not ElectricMachine:
        generator = ElectricMachine(
            type_=TypeComponent.GENERATOR,
            name="generator for %s" % name,
            rated_power=rated_power,
            rated_speed=rated_speed,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=switchboard_id,
            eff_curve=eff_curve_gen,
        )

    # Get the maximum efficiency
    eff_max_generator = generator.get_efficiency_from_load_percentage(1)

    # Create an engine component with an arbitrary bsfc curve if not provided or
    # not proper component
    if engine is None or type(engine) is not Engine:
        engine = create_engine_component(
            "engine for %s" % name,
            rated_power / eff_max_generator,
            rated_speed,
            bsfc_curve,
        )

    # Create and return a genset component
    return Genset(name, engine, generator)


def create_dataframe_save_and_return(name, filename, columns):
    # Create a DataFrame and save it to csv
    values = np.append(np.zeros([1, 1]), np.random.rand(1, len(columns) - 1), axis=1)
    eff_curve = create_random_monotonic_eff_curve()
    columns_eff = [
        "Efficiency@{}%".format(each_load) for each_load in eff_curve[:, 0].tolist()
    ]
    columns += columns_eff
    values = np.append(values, np.reshape(eff_curve[:, 1], (1, -1)), axis=1)
    df = pd.DataFrame(values, columns=columns, index=[name])
    df.to_csv(filename)
    return df


def create_switchboard_with_components(
    switchboard_id: int,
    rated_power_available_total: float,
    no_power_sources: int,
    no_power_consumer: int,
    no_pti_ptos: int = 1,
    no_energy_storage: int = 1,
) -> Switchboard:
    power_sources = create_electric_components_for_switchboard(
        TypePower.POWER_SOURCE,
        no_power_sources,
        rated_power_available_total,
        switchboard_id=switchboard_id,
    )
    power_consumers = create_electric_components_for_switchboard(
        TypePower.POWER_CONSUMER,
        no_power_consumer,
        int(rated_power_available_total * 0.8),
        switchboard_id=switchboard_id,
    )
    pti_ptos = create_electric_components_for_switchboard(
        TypePower.PTI_PTO,
        no_pti_ptos,
        rated_power_available_total * random.random(),
        switchboard_id=switchboard_id,
    )
    battery_systems = create_electric_components_for_switchboard(
        TypePower.ENERGY_STORAGE,
        no_energy_storage,
        rated_power_available_total * random.random(),
        switchboard_id=switchboard_id,
    )
    electric_components = power_sources + power_consumers + pti_ptos + battery_systems
    return Switchboard(
        name="switchboard", idx=switchboard_id, components=electric_components
    )


def create_shaftline_with_components(
    shaft_line_id: int,
    rated_power_available_total: float,
    no_power_sources: int,
    no_power_consumer: int,
    has_gear: bool = True,
    has_pti_pto: bool = True,
) -> ShaftLine:
    power_sources = create_components_for_shaftline(
        type_power=TypePower.POWER_SOURCE,
        number_components=no_power_sources,
        rated_power_total=rated_power_available_total,
        shaftline_id=shaft_line_id,
    )
    power_consumers = create_components_for_shaftline(
        type_power=TypePower.POWER_CONSUMER,
        number_components=no_power_consumer,
        rated_power_total=int(rated_power_available_total * 0.8),
        shaftline_id=shaft_line_id,
    )
    if has_gear:
        gear = create_components_for_shaftline(
            type_power=TypePower.POWER_TRANSMISSION,
            number_components=1,
            rated_power_total=rated_power_available_total,
            shaftline_id=shaft_line_id,
        )
    else:
        gear = []
    if has_pti_pto:
        pti_pto = create_components_for_shaftline(
            type_power=TypePower.PTI_PTO,
            number_components=1,
            rated_power_total=rated_power_available_total,
            shaftline_id=shaft_line_id,
        )
    else:
        pti_pto = []
    components = power_sources + power_consumers + pti_pto + gear
    return ShaftLine(
        name=f"shaftline {shaft_line_id}",
        shaft_line_id=shaft_line_id,
        component_list=components,
    )


def set_random_power_input_consumer_pti_pto_energy_storage(
    no_points_to_test, switchboard
) -> PowerSummary:
    """
    Sets random power input values for the consumers, PTI/PTO (as motor) and energy storage
    (charging)

    :param no_points_to_test: number of points in the vector of time(data) series
    :param switchboard: switchboard object
    :return: time(data) series of load percentage of the symmetrically loaded power sources,
        sum of the power input of the power consumers, sum of the power input of the PTI/PTOs as
        motors and sum of the power input of the energy storage devices at charging mode
    """
    sum_power_by_asymmetric_loaded_power_source = (
        switchboard.get_sum_power_out_power_sources_asymmetric()
    )
    # Set arbitrary load percentage for symmetric loaded power sources
    load_perc_symmetric_loaded_power_source = np.random.rand(no_points_to_test)
    sum_power_available_by_symmetric_loaded_power_source = (
        switchboard.get_sum_power_avail_for_power_sources_symmetric()
    )
    load_perc_symmetric_loaded_power_source[
        sum_power_available_by_symmetric_loaded_power_source == 0
    ] = 0
    # Calculate the total power produced
    total_power_produced = (
        sum_power_available_by_symmetric_loaded_power_source
        * load_perc_symmetric_loaded_power_source
        + sum_power_by_asymmetric_loaded_power_source
    )
    # Assign the power input for the consumers, pti/pto, energy storage devices
    # randomly within the total power produced
    no_electric_load_switchboard = (
        switchboard.no_consumers
        + switchboard.no_pti_pto
        + switchboard.no_energy_storage
    )
    count_electric_load = 0
    remaining_power = total_power_produced.copy()
    sum_power_input_power_consumer = np.zeros(total_power_produced.shape)
    sum_power_input_pti_pto = np.zeros(total_power_produced.shape)
    sum_power_input_energy_storage = np.zeros(total_power_produced.shape)
    for i, components_by_power_type in enumerate(switchboard.component_by_power_type):
        if i in [
            TypePower.POWER_CONSUMER.value,
            TypePower.PTI_PTO.value,
            TypePower.ENERGY_STORAGE.value,
        ]:
            for component in components_by_power_type:
                count_electric_load += 1
                if count_electric_load == no_electric_load_switchboard:
                    component.power_input = remaining_power.copy()
                    if i in [TypePower.PTI_PTO.value, TypePower.ENERGY_STORAGE.value]:
                        component.status = np.ones(no_points_to_test)
                        component.load_sharing_mode = np.ones(no_points_to_test)
                else:
                    component.power_input = (
                        np.random.rand(no_points_to_test)
                        * component.rated_power
                        * load_perc_symmetric_loaded_power_source
                        / 100
                    )
                    if i in [TypePower.PTI_PTO.value, TypePower.ENERGY_STORAGE.value]:
                        component.power_input *= (
                            component.load_sharing_mode * component.status
                        )
                    remaining_power -= component.power_input
                index_overload = remaining_power < 0
                component.power_input[index_overload] += remaining_power[index_overload]
                remaining_power[index_overload] = 0
                sum_power_input_power_consumer += component.power_input * (
                    i == TypePower.POWER_CONSUMER.value
                )
                sum_power_input_pti_pto += component.power_input * (
                    i == TypePower.PTI_PTO.value
                )
                sum_power_input_energy_storage += component.power_input * (
                    i == TypePower.ENERGY_STORAGE.value
                )
    # noinspection PyUnresolvedReferences
    if not np.isclose(
        total_power_produced,
        sum_power_input_power_consumer
        + sum_power_input_pti_pto
        + sum_power_input_energy_storage,
    ).all():
        msg = "Power balance is not met between the produced power and consumed power"
        logger.error(msg)
        raise AssertionError(msg)
    # Update the load percentage of symmetric loaded power sources for the changes
    # made during random load assignment

    sum_power_avail_from_equally_load_sharing_sources = (
        switchboard.get_sum_power_avail_for_power_sources_symmetric()
    )
    sum_power_output_from_equally_load_sharing_sources = (
        sum_power_input_power_consumer
        + sum_power_input_pti_pto
        + sum_power_input_energy_storage
        - sum_power_by_asymmetric_loaded_power_source
    )

    if isinstance(sum_power_avail_from_equally_load_sharing_sources, np.ndarray):
        load_perc_symmetric_loaded_power_source = np.zeros(
            sum_power_avail_from_equally_load_sharing_sources.shape
        )
        index_no_power_available = (
            sum_power_avail_from_equally_load_sharing_sources == 0
        )
        if np.bitwise_and(
            sum_power_output_from_equally_load_sharing_sources > 0,
            index_no_power_available,
        ).any():
            msg = (
                "There are cases where the power output is required when there is no "
                "available power from equally load sharing sources. The load will be set 0 "
                "for these cases."
            )
            logger.warning(msg)
        index_power_available = np.bitwise_not(index_no_power_available)
        load_perc_symmetric_loaded_power_source[index_power_available] = (
            sum_power_output_from_equally_load_sharing_sources[index_power_available]
            / sum_power_avail_from_equally_load_sharing_sources[index_power_available]
        )
    else:
        load_perc_symmetric_loaded_power_source = 0
        if (
            sum_power_avail_from_equally_load_sharing_sources == 0
            and sum_power_output_from_equally_load_sharing_sources > 0
        ):
            msg = "The power output is required with no power available. The load will be set 0."
            logger.warning(msg)
        else:
            load_perc_symmetric_loaded_power_source = (
                sum_power_output_from_equally_load_sharing_sources
                / sum_power_avail_from_equally_load_sharing_sources
            )

    result = PowerSummary(
        load_perc_symmetric_loaded_power_source=load_perc_symmetric_loaded_power_source,
        sum_power_input_power_consumer=sum_power_input_power_consumer,
        sum_power_input_pti_pto=sum_power_input_pti_pto,
        sum_power_input_energy_storage=sum_power_input_energy_storage,
    )
    return result


# noinspection PyTypeChecker
def create_electric_components_for_switchboard(
    type_power: TypePower,
    number_components: int,
    rated_power_total: float = 1000,
    rated_speed_max: float = 1000,
    switchboard_id=1,
    name_base=None,
) -> List[ElectricComponent]:
    """
    Create a list of electric components
    :param type_power: Enumerator item defined in TypePower
    (POWER_SOURCE, PTI_PTO, ENERGY_STORAGE, POWER_CONSUMER)
    :param number_components: default is 1
    :param rated_power_total: Total rated power of the created components, default is 1000kW
    :param rated_speed_max: Max rated speed for components where applicable
    :param switchboard_id:
    :param name_base: base name of the component
    :return: List of electric components created
    """
    electric_components = []
    type_electric_power_sources = [
        TypeComponent.GENERATOR,
        TypeComponent.FUEL_CELL_SYSTEM,
        TypeComponent.GENSET,
    ]
    type_electric_power_consumer = [
        TypeComponent.PROPULSION_DRIVE,
        TypeComponent.OTHER_LOAD,
    ]

    # Randomly generate the rated power for the components while meeting the
    # constraint of total power
    rated_power = np.clip(np.random.randn(number_components), -2, 2) + 2.25
    rated_power /= rated_power.sum() / rated_power_total

    # Create components for power sources
    if type_power == TypePower.POWER_SOURCE:
        for i in range(number_components):
            # Randomly choose the component type
            type_component = random.choice(type_electric_power_sources)

            # Name the component
            component_id = i + 1
            if name_base is None:
                name_base = type_component.name
            name_component = "%s %s" % (name_base, component_id)

            # Create a power source component
            if type_component == TypeComponent.FUEL_CELL_SYSTEM:
                # Create a fuel cell system
                component = create_fuel_cell_system(
                    name_component, rated_power[i], switchboard_id
                )
            else:
                # Create a generator component
                component = ElectricMachine(
                    type_=TypeComponent.GENERATOR,
                    name=name_component,
                    rated_power=rated_power[i],
                    rated_speed=rated_speed_max * random.random(),
                    power_type=type_power,
                    switchboard_id=switchboard_id,
                    eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
                )
                # Create a genset component
                if type_component == TypeComponent.GENSET:
                    component = create_genset_component(
                        name_component,
                        rated_power[i],
                        rated_speed_max * random.random(),
                        switchboard_id,
                        generator=component,
                    )

            # Add the component to the list
            electric_components.append(component)

    # Create components for PTI_PTO
    elif type_power == TypePower.PTI_PTO:
        for i in range(number_components):
            # Name the component
            component_id = i + 1
            if name_base is None:
                name_base = "PTI/PTO"
            name_component = "%s %s" % (name_base, component_id)

            # Create and add component to the list
            electric_components.append(
                create_a_pti_pto(
                    name_component,
                    rated_power[i],
                    rated_speed_max * random.random(),
                    switchboard_id,
                )
            )

    # Create components for Energy Storage System
    elif type_power == TypePower.ENERGY_STORAGE:
        for i in range(number_components):
            # Name the component
            component_id = i + 1
            if name_base is None:
                name_base = "ENERGY_STORAGE_SYSTEM"
            name_component = "%s %s" % (name_base, component_id)

            # Create and add component to the list
            electric_components.append(
                create_battery_system(
                    name_component,
                    rated_power[i],
                    rated_power[i] / 3,
                    switchboard_id,
                    3,
                    3,
                )
            )

    # Create components for power consumers
    else:
        for i in range(number_components):
            # Select the component type randomly among power consumers
            type_component = random.choice(type_electric_power_consumer)

            # Name the component
            component_id = i + 1
            if name_base is None:
                name_base = type_component.name
            name_component = "%s %s" % (name_base, component_id)

            # Create a propulsion drive
            if type_component == TypeComponent.PROPULSION_DRIVE:
                component = create_a_propulsion_drive(
                    name_component,
                    rated_power[i],
                    rated_speed_max * random.random(),
                    switchboard_id,
                )
            # Create other load
            elif type_component == TypeComponent.OTHER_LOAD:
                component = ElectricComponent(
                    type_component,
                    name_component,
                    rated_power[i],
                    power_type=TypePower.POWER_CONSUMER,
                    switchboard_id=switchboard_id,
                )
            else:
                raise ConfigurationError(
                    f"Component type should be either {TypeComponent.PROPULSION_DRIVE} or "
                    f"{TypeComponent.OTHER_LOAD}, but it is {type_component}."
                )

            # Add the component to the list
            electric_components.append(component)

    return electric_components


# noinspection PyTypeChecker
def create_components_for_shaftline(
    type_power: TypePower,
    number_components: int,
    rated_power_total: float = 1000,
    rated_speed_max: float = 1000,
    shaftline_id=1,
    name_base=None,
) -> List[ElectricComponent]:
    """
    Create a list of components for a shaft line
    :param type_power: Enumerator item defined in TypePower
    (POWER_SOURCE, PTI_PTO, ENERGY_STORAGE, POWER_CONSUMER)
    :param number_components: default is 1
    :param rated_power_total: Total rated power of the created components, default is 1000kW
    :param rated_speed_max: Max rated speed for components where applicable
    :param shaftline_id:
    :param name_base: base name of the component
    :return: List of electric components created
    """
    components = []

    # Randomly generate the rated power for the components while meeting the
    # constraint of total power
    rated_power = np.clip(np.random.randn(number_components), -2, 2) + 2.25
    rated_power /= rated_power.sum() / rated_power_total

    # Create components for power sources
    if type_power == TypePower.POWER_SOURCE:
        for i in range(number_components):
            # Name the component
            component_id = i + 1
            if name_base is None:
                name_base = "Main engine"
            name_component = "%s %s" % (name_base, component_id)
            component = MainEngineForMechanicalPropulsion(
                name=name_component,
                engine=Engine(
                    name=name_component,
                    type_=TypeComponent.MAIN_ENGINE,
                    rated_power=rated_power[i],
                    rated_speed=rated_speed_max * random.random(),
                    bsfc_curve=np.append(
                        np.reshape(np.arange(0.1, 1.1, 0.1), (-1, 1)),
                        np.random.rand(10, 1) * 200,
                        axis=1,
                    ),
                    fuel_type=TypeFuel.HFO,
                ),
                shaft_line_id=shaftline_id,
            )
            # Add the component to the list
            components.append(component)

    # Create components for PTI_PTO
    elif type_power == TypePower.PTI_PTO:
        for i in range(number_components):
            # Name the component
            component_id = i + 1
            if name_base is None:
                name_base = "PTI/PTO"
            name_component = "%s %s" % (name_base, component_id)

            # Create and add component to the list
            components.append(
                create_a_pti_pto(
                    name_component,
                    rated_power[i],
                    rated_speed_max * random.random(),
                    switchboard_id=1,
                    shaft_line_id=shaftline_id,
                )
            )

    elif type_power == TypePower.POWER_TRANSMISSION:
        for i in range(number_components):
            component_id = i + 1
            if name_base is None:
                name_base = "Gear"
            name_component = f"{name_base} {component_id}"
            components.append(
                MechanicalPropulsionComponent(
                    name=name_component,
                    type_=TypeComponent.GEARBOX,
                    power_type=TypePower.POWER_TRANSMISSION,
                    eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
                    rated_power=rated_power[i],
                    rated_speed=rated_speed_max,
                    shaft_line_id=shaftline_id,
                )
            )

    # Create components for power consumers
    else:
        for i in range(number_components):
            # Name the component
            component_id = i + 1
            if name_base is None:
                name_base = "Propeller"
            name_component = "%s %s" % (name_base, component_id)

            # Add the component to the list
            components.append(
                MechanicalPropulsionComponent(
                    name=name_component,
                    type_=TypeComponent.PROPELLER_LOAD,
                    power_type=TypePower.POWER_CONSUMER,
                    eff_curve=ELECTRIC_MACHINE_EFF_CURVE,
                    rated_power=rated_power[i],
                    rated_speed=rated_speed_max,
                    shaft_line_id=shaftline_id,
                )
            )

    return components
