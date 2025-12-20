"""
This module contains utility functions to compare proto objects.

Functions:
    compare_proto_components: compare two proto components and return a dict of differences.
    compare_proto_subsystems: compare two proto subsystems and return a dict of differences.
    convert_camel_case_to_snake_case: convert a camel case string to snake case.
    convert_camel_case_list_to_snake_case_list: convert a list of camel case strings to snake case.

History:
    created: 22/02/2021

Creator: Kevin K. Yum
CopyRight: SINTEF Ocean
"""

import re
from dataclasses import dataclass
from functools import reduce
from typing import List, Union, Dict
import MachSysS.system_structure_pb2 as proto
from deepdiff.diff import DeepDiff
from google.protobuf.json_format import MessageToDict


ProtoComponent = Union[
    proto.MechanicalComponent,
    proto.ElectricComponent,
    proto.FuelCell,
]


def convert_camel_case_to_snake_case(camel_case_string: str) -> str:
    """
    Convert a camel case string to snake case.

    :param camel_case_string: string in camel case
    :return: string in snake case
    """
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel_case_string).lower()


def convert_camel_case_list_to_snake_case_list(camel_case_list: List[str]) -> List[str]:
    """
    Convert a list of camel case strings to snake case.

    :param camel_case_list: list of strings in camel case
    :return: list of strings in snake case
    """
    return [
        convert_camel_case_to_snake_case(camel_case_string)
        for camel_case_string in camel_case_list
    ]


@dataclass
class DiffSubsystems:
    """
    Class to store the differences between two subsystems.
    """

    diff_attributes: DeepDiff
    components_removed: List[str]
    components_added: List[str]
    components_modified: Dict[str, DeepDiff]

    def to_dict(self) -> dict:
        """
        Convert the class to a dict.

        :return: dict representation of the class
        """
        result = self.__dict__
        result["diff_attributes"] = self.diff_attributes.to_dict()
        result["components_modified"] = {
            key: value.to_dict() for key, value in self.components_modified.items()
        }
        return result


@dataclass
class DiffSwitchboardShaftLines:
    """
    Class to store the differences between two switchboards.
    """

    subsystems_removed: List[str]
    subsystems_added: List[str]
    subsystems_modified: Dict[str, DiffSubsystems]

    def to_dict(self) -> dict:
        """
        Convert the class to a dict.

        :return: dict representation of the class
        """
        result = self.__dict__
        result["subsystems_modified"] = {
            name: diff.to_dict() for name, diff in self.subsystems_modified.items()
        }
        return result


@dataclass
class DiffElectricPowerSystem:
    switchboards_removed: List[int]
    switchboards_added: List[int]
    switchboards_modified: Dict[int, DiffSwitchboardShaftLines]


@dataclass
class DiffMechanicalSystem:
    shaft_lines_removed: List[int]
    shaft_lines_added: List[int]
    shaft_lines_modified: Dict[int, DiffSwitchboardShaftLines]


@dataclass
class DiffMachinerySystem:
    diff_attributes: DeepDiff
    diff_electric_system: DiffElectricPowerSystem
    diff_mechanical_system: DiffMechanicalSystem


def compare_proto_components(comp1: ProtoComponent, comp2: ProtoComponent) -> DeepDiff:
    """
    Compare two proto components and return a dict of differences.

    :param comp1: first component to compare. It should be a basic proto component.
    :param comp2: second component to compare. It should be a basic proto component.
    :return: DeepDiff object
    """
    comp1_dict = MessageToDict(comp1)
    comp2_dict = MessageToDict(comp2)
    return DeepDiff(
        t1=comp1_dict,
        t2=comp2_dict,
        ignore_order=True,
        report_repetition=True,
        ignore_string_case=True,
    )


def compare_proto_subsystems(
    subsystem1: proto.Subsystem, subsystem2: proto.Subsystem
) -> DiffSubsystems:
    """
    Compare two proto subsystems and return a dict of differences.

    :param subsystem1: first subsystem to compare. It should be a basic proto subsystem.
    :param subsystem2: second subsystem to compare. It should be a basic proto subsystem.
    :return: dict of differences
    """
    non_component_attribute_keys = [
        "powerType",
        "componentType",
        "name",
        "ratedPowerKw",
        "ratedSpeedRpm",
        "uid",
    ]
    subsystem1_dict = MessageToDict(subsystem1)
    subsystem2_dict = MessageToDict(subsystem2)
    subsystem1_dict_non_components = reduce(
        lambda acc, key: (
            {**acc, **{key: subsystem1_dict.pop(key)}}
            if key in subsystem1_dict
            else acc
        ),
        non_component_attribute_keys,
        {},
    )
    subsystem2_dict_non_components = reduce(
        lambda acc, key: (
            {**acc, **{key: subsystem2_dict.pop(key)}}
            if key in subsystem2_dict
            else acc
        ),
        non_component_attribute_keys,
        {},
    )
    diff_non_components = DeepDiff(
        subsystem1_dict_non_components,
        subsystem2_dict_non_components,
        ignore_order=True,
        report_repetition=True,
    )
    components_list_subsystem1 = convert_camel_case_list_to_snake_case_list(
        list(subsystem1_dict.keys())
    )
    components_list_subsystem2 = convert_camel_case_list_to_snake_case_list(
        list(subsystem2_dict.keys())
    )
    components_removed = list(
        set(components_list_subsystem1) - set(components_list_subsystem2)
    )
    components_added = list(
        set(components_list_subsystem2) - set(components_list_subsystem1)
    )
    components_common = list(
        set(components_list_subsystem1) & set(components_list_subsystem2)
    )
    diff_components = {}
    for component_name in components_common:
        diff_components[component_name] = compare_proto_components(
            getattr(subsystem1, component_name), getattr(subsystem2, component_name)
        )
    return DiffSubsystems(
        diff_attributes=diff_non_components,
        components_removed=components_removed,
        components_added=components_added,
        components_modified=diff_components,
    )


def compare_proto_switchboards_shaft_lines(
    switchboard1: proto.Switchboard, switchboard2: proto.Switchboard
) -> DiffSwitchboardShaftLines:
    """
    Compare two proto switchboards and return a dict of differences.

    :param switchboard1: first switchboard to compare. It should be a basic proto switchboard.
    :param switchboard2: second switchboard to compare. It should be a basic proto switchboard.
    :return: dict of differences
    """
    diff = DiffSwitchboardShaftLines(
        subsystems_removed=[],
        subsystems_added=[subsystem.name for subsystem in switchboard2.subsystems],
        subsystems_modified={},
    )
    for subsystem_ref in switchboard1.subsystems:
        try:
            subsystem_to_compare = next(
                filter(
                    lambda subsystem: subsystem_ref.name == subsystem.name,
                    switchboard2.subsystems,
                )
            )
        except StopIteration:
            diff.subsystems_removed.append(subsystem_ref.name)
        else:
            diff.subsystems_added.remove(subsystem_ref.name)
            diff_subsystem = compare_proto_subsystems(
                subsystem_ref, subsystem_to_compare
            )
            diff.subsystems_modified[subsystem_ref.name] = diff_subsystem
    return diff


def compare_proto_electric_systems(
    eps1: proto.ElectricSystem, eps2: proto.ElectricSystem
) -> DiffElectricPowerSystem:
    """
    Compare two proto electric power systems and return a dict of differences.

    :param eps1: first electric power system to compare. It should be a basic proto electric power system.
    :param eps2: second electric power system to compare. It should be a basic proto electric power system.
    :return: DiffElectricPowerSystem object
    """
    diff = DiffElectricPowerSystem(
        switchboards_removed=[],
        switchboards_added=[
            switchboard.switchboard_id for switchboard in eps2.switchboards
        ],
        switchboards_modified={},
    )
    for switchboard_ref in eps1.switchboards:
        try:
            switchboard_to_compare = next(
                filter(
                    lambda switchboard: switchboard_ref.switchboard_id
                    == switchboard.switchboard_id,
                    eps2.switchboards,
                )
            )
        except StopIteration:
            diff.switchboards_removed.append(switchboard_ref.switchboard_id)
        else:
            diff.switchboards_added.remove(switchboard_ref.switchboard_id)
            diff_switchboard = compare_proto_switchboards_shaft_lines(
                switchboard_ref, switchboard_to_compare
            )
            diff.switchboards_modified[
                switchboard_ref.switchboard_id
            ] = diff_switchboard
    return diff


def compare_proto_mechanical_system(
    shaft_lines1: proto.ShaftLine, shaft_lines2: proto.ShaftLine
) -> DiffMechanicalSystem:
    """
    Compare two proto shaft lines and return a dict of differences.

    :param shaft_lines1: first shaft lines to compare. It should be a basic proto shaft lines.
    :param shaft_lines2: second shaft lines to compare. It should be a basic proto shaft lines.
    :return: DiffMechanicalSystem object
    """
    diff = DiffMechanicalSystem(
        shaft_lines_removed=[],
        shaft_lines_added=[
            shaft_line.shaft_line_id for shaft_line in shaft_lines2.shaft_lines
        ],
        shaft_lines_modified={},
    )
    for shaft_line_ref in shaft_lines1.shaft_lines:
        try:
            shaft_line_to_compare = next(
                filter(
                    lambda shaft_line: shaft_line_ref.shaft_line_id
                    == shaft_line.shaft_line_id,
                    shaft_lines2.shaft_lines,
                )
            )
        except StopIteration:
            diff.shaft_lines_removed.append(shaft_line_ref.shaft_line_id)
        else:
            diff.shaft_lines_added.remove(shaft_line_ref.shaft_line_id)
            diff_shaft_line = compare_proto_switchboards_shaft_lines(
                shaft_line_ref, shaft_line_to_compare
            )
            diff.shaft_lines_modified[shaft_line_ref.shaft_line_id] = diff_shaft_line
    return diff


def compare_proto_machinery_system(
    machinery1: proto.MachinerySystem, machinery2: proto.MachinerySystem
) -> DiffMachinerySystem:
    """
    Compare two proto machinery systems and return a dict of differences.

    :param machinery1: first machinery system to compare. It should be a basic proto machinery system.
    :param machinery2: second machinery system to compare. It should be a basic proto machinery system.
    :return: DiffMachinerySystem object
    """
    machinery_system1_dict = MessageToDict(machinery1)
    machinery_system2_dict = MessageToDict(machinery2)
    machinery_system1_dict.pop("electricSystem", None)
    machinery_system2_dict.pop("electricSystem", None)
    machinery_system1_dict.pop("mechanicalSystem", None)
    machinery_system2_dict.pop("mechanicalSystem", None)
    return DiffMachinerySystem(
        diff_attributes=DeepDiff(machinery_system1_dict, machinery_system2_dict),
        diff_electric_system=compare_proto_electric_systems(
            machinery1.electric_system, machinery2.electric_system
        ),
        diff_mechanical_system=compare_proto_mechanical_system(
            machinery1.mechanical_system, machinery2.mechanical_system
        ),
    )
