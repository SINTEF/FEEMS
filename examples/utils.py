import json
import os
from typing import List, Dict, Union
import numpy as np

from feems.components_model import ElectricComponent, Genset, Engine
from feems.components_model.component_electric import SerialSystemElectric, ElectricMachine
from feems.types_for_feems import TypeComponent, TypePower

JSON_DATA = ['equipment_data.json', 'configuration.json']


def get_component_configuration_data() -> (List[Dict], List[Dict]):
    current_path = os.path.dirname(os.path.abspath(__file__))
    path_to_equipment_data = os.path.join(current_path, JSON_DATA[0])
    path_to_configuration_data = os.path.join(current_path, JSON_DATA[1])
    return get_data_from_json(path_to_equipment_data), \
        get_data_from_json(path_to_configuration_data)


def get_data_from_json(path_to_json: str) -> List[Dict]:
    """
    Returns the list of data in dictionary from the json file
    """
    with open(path_to_json, 'rt') as file:
        return json.JSONDecoder().decode(file.read())


def get_type_component(type_name: str) -> Union[TypeComponent, None]:
    """
    Returns the TypeComponent selection from the type_name given
    """
    for _type in TypeComponent:
        if _type.name == type_name:
            return _type
    return None


def get_component_data_from_name(name: str, component_data: List[Dict]) \
        -> Union[Dict[str, Union[str, float, List]], None]:
    list_name_component = [component['name'] for component in component_data]
    try:
        idx = list_name_component.index(name)
    except ValueError:
        return None
    else:
        return component_data[idx]


def get_configured_component_from_name(
        name: str, configuration_data: List[Dict]
) -> Union[Dict[str, Union[str, float, List]], None]:
    list_name_component = [component['name'] for component in configuration_data]
    try:
        idx = list_name_component.index(name)
    except ValueError:
        return None
    else:
        return configuration_data[idx]


def create_a_component(component, component_data) -> \
        Union[Engine, ElectricMachine, ElectricComponent]:
    if component_data is None:
        return ElectricComponent(
            type_=TypeComponent.OTHER_LOAD,
            name=component['name'],
            power_type=TypePower.POWER_CONSUMER,
            switchboard_id=component['switchboard_id']
        )
    if component_data['type'] == TypeComponent.AUXILIARY_ENGINE.name:
        return Engine(
            type_=get_type_component(component_data['type']),
            name=component['name'],
            rated_power=component_data['rated_power'],
            rated_speed=component_data['rated_speed'],
            bsfc_curve=np.asarray(component_data['bsfc_curve']).transpose()
        )
    elif component_data['type'] == TypeComponent.GENERATOR.name:
        return ElectricMachine(
            type_=component_data['type'],
            name=component['name'],
            rated_power=component_data['rated_power'],
            rated_speed=component_data['rated_speed'],
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=component['switchboard_id'],
            eff_curve=np.asarray(component_data['eff_curve']).transpose()
        )
    elif component_data['type'] in \
        [TypeComponent.TRANSFORMER.name, TypeComponent.RECTIFIER.name, TypeComponent.INVERTER.name]:
        return ElectricComponent(
            type_=get_type_component(component_data['type']),
            name=component['name'],
            rated_power=component_data['rated_power'],
            eff_curve=np.asarray(component_data['eff_curve']).transpose(),
            power_type=TypePower.POWER_TRANSMISSION,
            switchboard_id=component['switchboard_id'],
        )
    elif component_data['type'] == TypeComponent.ELECTRIC_MOTOR.name:
        return ElectricMachine(
            type_=get_type_component(component_data['type']),
            name=component['name'],
            rated_power=component_data['rated_power'],
            rated_speed=component_data['rated_speed'],
            eff_curve=np.asarray(component_data['eff_curve']).transpose(),
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=component['switchboard_id'],
        )
    else:
        raise Exception('No method is available for the component type.')


def create_components_for_an_electric_system() -> \
        List[Union[ElectricComponent, SerialSystemElectric, Genset]]:
    component_data_all, configuration_data = get_component_configuration_data()
    components_to_switchboards = get_component_to_switchboards(configuration_data)
    created_components_to_switchboard = []
    for components_in_series in components_to_switchboards:
        created_components_in_series = []
        for component in components_in_series:
            component = get_configured_component_from_name(component, configuration_data)
            component_data = get_component_data_from_name(component['component'], component_data_all)
            created_components_in_series.append(
                create_a_component(component, component_data)
            )
        if len(created_components_in_series) > 1:
            if created_components_in_series[0].type != TypeComponent.GENERATOR.name:
                name = 'Propulsion drive %s' % created_components_in_series[0].name[-1]
                created_components_to_switchboard.append(
                    SerialSystemElectric(
                        type_=TypeComponent.PROPULSION_DRIVE,
                        name=name,
                        power_type=TypePower.POWER_CONSUMER,
                        components=created_components_in_series,
                        rated_power=created_components_in_series[-1].rated_power,
                        rated_speed=created_components_in_series[-1].rated_speed,
                        switchboard_id=created_components_in_series[0].switchboard_id
                    )
                )
            elif created_components_in_series[0].type == TypeComponent.GENERATOR.name:
                name = 'Genset %s' % created_components_in_series[0].name[-1]
                created_components_to_switchboard.append(
                    Genset(
                        name=name,
                        aux_engine=created_components_in_series[-1],
                        generator=created_components_in_series[0],
                    )
                )
            else:
                raise Exception('No method available for these components in series')
        else:
            created_components_to_switchboard.append(created_components_in_series[0])
    return created_components_to_switchboard


def get_component_to_switchboards(configuration_data):
    component_to_switchboard = []
    first_component_to_switchboard = []
    for component in configuration_data:
        component_to_connect = find_component_to_connect(component, configuration_data)
        component_to_be_connected = find_component_to_be_connected(component, configuration_data)
        component_to_switchboard_to_add = \
            component_to_connect + [component['name']] + component_to_be_connected
        if component_to_switchboard_to_add[0] not in first_component_to_switchboard:
            component_to_switchboard.append(component_to_switchboard_to_add)
            first_component_to_switchboard.append(component_to_switchboard_to_add[0])
    return component_to_switchboard


def find_component_to_connect(component, configuration_data):
    components_to_connect = []
    list_name_component = [component['name'] for component in configuration_data]
    component_to_connect = component['connected_to']
    while component_to_connect != "switchboard":
        idx = list_name_component.index(component_to_connect)
        components_to_connect.insert(0, list_name_component[idx])
        component_to_connect = configuration_data[idx]['connected_to']
    return components_to_connect


def find_component_to_be_connected(component, configuration_data):
    components_to_be_connected = []
    list_name_connected_to = [component['connected_to'] for component in configuration_data]
    component_to_connect = component['name']
    while True:
        try:
            idx = list_name_connected_to.index(component_to_connect)
        except ValueError:
            break
        else:
            components_to_be_connected.append(configuration_data[idx]['name'])
            component_to_connect = configuration_data[idx]['name']
    return components_to_be_connected


if __name__ == "__main__":
    components = create_components_for_an_electric_system()
    for component in components:
        print(component)
