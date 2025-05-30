# AUTOGENERATED! DO NOT EDIT! File to edit: ../00_ConvertToFeems.ipynb.

# %% auto 0
__all__ = [
    "convert_proto_point_to_list",
    "convert_proto_curve1d_to_np_array",
    "convert_proto_efficiency_bsfc_power_to_np_array",
    "convert_proto_electric_component_to_feems",
    "convert_proto_electric_machine_to_feems",
    "convert_proto_fuel_cell_system_to_feems",
    "convert_emission_curve_to_feems",
    "convert_nox_calculation_method",
    "convert_proto_engine_to_feems",
    "convert_proto_cogas_to_feems",
    "convert_proto_genset_to_feems",
    "convert_proto_coges_to_feems",
    "convert_proto_battery_to_feems",
    "convert_proto_battery_system_to_feems",
    "convert_proto_supercapacitor_to_feems",
    "convert_proto_supercapacitor_system_to_feems",
    "collect_electric_components_from_sub_system",
    "convert_proto_generic_electric_component_to_feems",
    "get_component_type",
    "convert_proto_pti_pto_subsystem_to_feems",
    "convert_proto_serial_subsystem_to_feems",
    "convert_generic_electric_subsystem_to_feems",
    "convert_proto_switchboard_to_feems",
    "convert_proto_shaftline_to_feems",
    "convert_feems_switchboards_to_feems_electric_power_system",
    "convert_feems_shaftlines_to_feems_mechanical_propulsion_system",
    "convert_proto_electric_system_to_feems",
    "convert_proto_mechanical_system_to_feems",
    "convert_proto_propulsion_system_to_feems",
]

# %% ../00_ConvertToFeems.ipynb 3
from functools import reduce
from typing import Union, List, Dict, Any, Optional

import numpy as np
from feems.components_model import (
    Engine,
    Switchboard,
    ShaftLine,
    BasicComponent,
    MechanicalPropulsionComponent,
)
from feems.components_model.component_electric import (
    ElectricComponent,
    FuelCellSystem,
    ElectricMachine,
    BatterySystem,
    Battery,
    SuperCapacitorSystem,
    PTIPTO,
    SuperCapacitor,
    FuelCell,
    COGES,
)
from feems.components_model.component_electric import SerialSystemElectric, Genset
from feems.components_model.component_mechanical import COGAS, EngineDualFuel
from feems.fuel import FuelOrigin, TypeFuel
from feems.system_model import (
    ElectricPowerSystem,
    MechanicalPropulsionSystem,
    HybridPropulsionSystem,
    MechanicalPropulsionSystemWithElectricPowerSystem,
    MainEngineForMechanicalPropulsion,
    MainEngineWithGearBoxForMechanicalPropulsion,
)
from feems.types_for_feems import (
    TypeComponent,
    TypePower,
    EmissionCurve,
    EmissionCurvePoint,
    EmissionType,
    NOxCalculationMethod,
    EngineCycleType,
)

import MachSysS.system_structure_pb2 as proto

_MIN_LENGTH_UID = 5


def convert_proto_point_to_list(point: proto.Point) -> List[float]:
    """Converts protobuf point to a list"""
    return [point.x, point.y]


def convert_proto_curve1d_to_np_array(curve: proto.Curve1D) -> np.ndarray:
    """Converts protobuf curve1d to numpy array"""
    return np.array(list(map(convert_proto_point_to_list, curve.points)))


def convert_proto_efficiency_bsfc_power_to_np_array(
    efficiency_bsfc_power: Union[proto.Efficiency, proto.BSFC, proto.PowerCurve],
) -> np.ndarray:
    """Converts protobuf efficiency or bsfc to numpy array"""
    if isinstance(efficiency_bsfc_power, proto.PowerCurve):
        return convert_proto_curve1d_to_np_array(efficiency_bsfc_power.curve)
    if efficiency_bsfc_power.HasField("value"):
        if efficiency_bsfc_power.value > 0:
            return np.array([efficiency_bsfc_power.value])
    if efficiency_bsfc_power.HasField("curve"):
        return convert_proto_curve1d_to_np_array(efficiency_bsfc_power.curve.curve)
    else:
        raise TypeError("The efficiency value or curve is not properly set.")


def convert_proto_electric_component_to_feems(
    proto_component: proto.ElectricComponent,
    component_type: TypeComponent,
    power_type: TypePower,
    switchboard_id: int = 0,
) -> ElectricComponent:
    return ElectricComponent(
        type_=component_type,
        name=proto_component.name,
        rated_power=proto_component.rated_power_kw,
        eff_curve=convert_proto_efficiency_bsfc_power_to_np_array(
            proto_component.efficiency
        ),
        power_type=power_type,
        switchboard_id=switchboard_id,
        uid=proto_component.uid if len(proto_component.uid) > _MIN_LENGTH_UID else None,
    )


def convert_proto_electric_machine_to_feems(
    proto_component: proto.ElectricMachine,
    component_type: TypeComponent,
    power_type: TypePower,
    switchboard_id: int = 0,
) -> ElectricMachine:
    return ElectricMachine(
        type_=component_type,
        name=proto_component.name,
        rated_power=proto_component.rated_power_kw,
        rated_speed=proto_component.rated_speed_rpm,
        power_type=power_type,
        eff_curve=convert_proto_efficiency_bsfc_power_to_np_array(
            proto_component.efficiency
        ),
        switchboard_id=switchboard_id,
        uid=proto_component.uid if len(proto_component.uid) > _MIN_LENGTH_UID else None,
    )


def convert_proto_fuel_cell_system_to_feems(
    subsystem: proto.Subsystem, switchboard_id: int
) -> FuelCellSystem:
    """Converts protobuf subsystem message to feems component"""
    number_modules = 1
    if subsystem.fuel_cell.number_modules > 1:
        number_modules = subsystem.fuel_cell.number_modules
    fuel_cell = FuelCell(
        name=subsystem.fuel_cell.name,
        rated_power=subsystem.fuel_cell.rated_power_kw,
        eff_curve=convert_proto_efficiency_bsfc_power_to_np_array(
            subsystem.fuel_cell.efficiency
        ),
        fuel_type=TypeFuel(subsystem.fuel_cell.fuel.fuel_type),
        fuel_origin=FuelOrigin(subsystem.fuel_cell.fuel.fuel_origin),
        uid=(
            subsystem.fuel_cell.uid
            if len(subsystem.fuel_cell.uid) > _MIN_LENGTH_UID
            else None
        ),
    )
    converter = convert_proto_electric_component_to_feems(
        subsystem.converter1,
        component_type=TypeComponent.POWER_CONVERTER,
        power_type=TypePower.POWER_TRANSMISSION,
        switchboard_id=switchboard_id,
    )
    return FuelCellSystem(
        name=subsystem.name,
        fuel_cell_module=fuel_cell,
        converter=converter,
        switchboard_id=switchboard_id,
        number_modules=number_modules,
        uid=subsystem.uid if len(subsystem.uid) > _MIN_LENGTH_UID else None,
    )


def convert_emission_curve_to_feems(
    emission_curve: proto.EmissionCurve,
) -> EmissionCurve:
    """Converts protobuf emission curve to numpy array"""
    points_per_kwh = [
        EmissionCurvePoint(load_ratio=point.x, emission_g_per_kwh=point.y)
        for point in emission_curve.curve.points
    ]
    return EmissionCurve(
        points_per_kwh=points_per_kwh,
        emission=EmissionType(emission_curve.emission_type),
    )


def convert_nox_calculation_method(
    proto_comp: Union[proto.Engine, proto.COGAS],
) -> NOxCalculationMethod:
    """Converts protobuf nox calculation type to feems nox calculation method"""
    if isinstance(proto_comp, proto.Engine):
        nox_calculation_method = NOxCalculationMethod.TIER_2
    elif isinstance(proto_comp, proto.COGAS):
        nox_calculation_method = NOxCalculationMethod.TIER_3
    else:
        raise TypeError("The component should be either an engine or COGAS")
    if proto_comp.nox_calculation_method is not None:
        name = proto.Engine.NOxCalculationMethod.Name(proto_comp.nox_calculation_method)
        nox_calculation_method = NOxCalculationMethod[name]
    return nox_calculation_method


def convert_proto_engine_to_feems(
    proto_engine: proto.Engine,
    type_engine: TypeComponent = TypeComponent.AUXILIARY_ENGINE,
) -> Engine:
    """Converts protobuf engine message to feems engine component"""
    nox_calculation_method = convert_nox_calculation_method(proto_engine)
    emission_curves = (
        [
            convert_emission_curve_to_feems(emission_curve)
            for emission_curve in proto_engine.emission_curves
        ]
        if proto_engine.emission_curves
        else None
    )
    if proto_engine.HasField("pilot_bsfc"):
        return EngineDualFuel(
            type_=type_engine,
            name=proto_engine.name,
            rated_power=proto_engine.rated_power_kw,
            rated_speed=proto_engine.rated_speed_rpm,
            bsfc_curve=convert_proto_efficiency_bsfc_power_to_np_array(
                proto_engine.bsfc
            ),
            bspfc_curve=convert_proto_efficiency_bsfc_power_to_np_array(
                proto_engine.pilot_bsfc
            ),
            fuel_type=TypeFuel(proto_engine.main_fuel.fuel_type),
            fuel_origin=FuelOrigin(proto_engine.main_fuel.fuel_origin),
            pilot_fuel_type=TypeFuel(proto_engine.pilot_fuel.fuel_type),
            pilot_fuel_origin=FuelOrigin(proto_engine.pilot_fuel.fuel_origin),
            nox_calculation_method=nox_calculation_method,
            emissions_curves=emission_curves,
            engine_cycle_type=EngineCycleType(proto_engine.engine_cycle_type),
            uid=proto_engine.uid if len(proto_engine.uid) > _MIN_LENGTH_UID else None,
        )
    return Engine(
        type_=type_engine,
        name=proto_engine.name,
        rated_power=proto_engine.rated_power_kw,
        rated_speed=proto_engine.rated_speed_rpm,
        bsfc_curve=convert_proto_efficiency_bsfc_power_to_np_array(proto_engine.bsfc),
        fuel_type=TypeFuel(proto_engine.main_fuel.fuel_type),
        fuel_origin=FuelOrigin(proto_engine.main_fuel.fuel_origin),
        nox_calculation_method=nox_calculation_method,
        emissions_curves=emission_curves,
        uid=proto_engine.uid if len(proto_engine.uid) > _MIN_LENGTH_UID else None,
    )


def convert_proto_cogas_to_feems(
    proto_cogas: proto.COGAS,
) -> Engine:
    """Converts protobuf COGAS message to feems COGAS component"""
    nox_calculation_method = convert_nox_calculation_method(proto_cogas)
    emission_curves = (
        [
            convert_emission_curve_to_feems(emission_curve)
            for emission_curve in proto_cogas.emission_curves
        ]
        if proto_cogas.emission_curves
        else None
    )
    return COGAS(
        name=proto_cogas.name,
        rated_power=proto_cogas.rated_power_kw,
        rated_speed=proto_cogas.rated_speed_rpm,
        eff_curve=convert_proto_efficiency_bsfc_power_to_np_array(
            proto_cogas.efficiency
        ),
        gas_turbine_power_curve=convert_proto_efficiency_bsfc_power_to_np_array(
            proto_cogas.gas_turbine_power_curve
        ),
        steam_turbine_power_curve=convert_proto_efficiency_bsfc_power_to_np_array(
            proto_cogas.steam_turbine_power_curve
        ),
        fuel_type=TypeFuel(proto_cogas.fuel.fuel_type),
        fuel_origin=FuelOrigin(proto_cogas.fuel.fuel_origin),
        nox_calculation_method=nox_calculation_method,
        emissions_curves=emission_curves,
        uid=proto_cogas.uid if len(proto_cogas.uid) > _MIN_LENGTH_UID else None,
    )


def convert_proto_genset_to_feems(
    subsystem: proto.Subsystem, switchboard_id: int
) -> Genset:
    """Converts protobuf subsystem message to feems component"""
    engine = convert_proto_engine_to_feems(proto_engine=subsystem.engine)
    generator = convert_proto_electric_machine_to_feems(
        proto_component=subsystem.electric_machine,
        component_type=TypeComponent.SYNCHRONOUS_MACHINE,
        power_type=TypePower.POWER_SOURCE,
        switchboard_id=switchboard_id,
    )
    rectifier = None
    if subsystem.HasField("converter1"):
        rectifier = convert_proto_electric_component_to_feems(
            proto_component=subsystem.converter1,
            component_type=TypeComponent.RECTIFIER,
            power_type=TypePower.POWER_TRANSMISSION,
            switchboard_id=switchboard_id,
        )
    return Genset(
        name=subsystem.name,
        aux_engine=engine,
        generator=generator,
        rectifier=rectifier,
        uid=subsystem.uid if len(subsystem.uid) > _MIN_LENGTH_UID else None,
    )


def convert_proto_coges_to_feems(
    subsystem: proto.Subsystem, switchboard_id: int
) -> COGES:
    """Converts protobuf subsystem message to feems component"""
    cogas = convert_proto_cogas_to_feems(proto_cogas=subsystem.cogas)
    generator = convert_proto_electric_machine_to_feems(
        proto_component=subsystem.electric_machine,
        component_type=TypeComponent.SYNCHRONOUS_MACHINE,
        power_type=TypePower.POWER_SOURCE,
        switchboard_id=switchboard_id,
    )
    return COGES(
        name=subsystem.name,
        cogas=cogas,
        generator=generator,
        uid=subsystem.uid if len(subsystem.uid) > _MIN_LENGTH_UID else None,
    )


def convert_proto_battery_to_feems(
    proto_component: proto.Battery, switchboard_id: int = 0
) -> Battery:
    return Battery(
        name=proto_component.name,
        rated_capacity_kwh=proto_component.energy_capacity_kwh,
        charging_rate_c=proto_component.rated_charging_rate_c,
        discharge_rate_c=proto_component.rated_discharging_rate_c,
        eff_charging=proto_component.efficiency_charging,
        eff_discharging=proto_component.efficiency_discharging,
        soc0=proto_component.initial_state_of_charge,
        switchboard_id=switchboard_id,
        uid=proto_component.uid if len(proto_component.uid) > _MIN_LENGTH_UID else None,
    )


def convert_proto_battery_system_to_feems(
    subsystem: proto.Subsystem, switchboard_id: int
) -> BatterySystem:
    """Converts protobuf subsystem message to feems component"""
    battery = convert_proto_battery_to_feems(
        proto_component=subsystem.battery,
    )
    converter = convert_proto_electric_component_to_feems(
        proto_component=subsystem.converter1,
        component_type=TypeComponent.POWER_CONVERTER,
        power_type=TypePower.POWER_TRANSMISSION,
    )
    return BatterySystem(
        name=subsystem.name,
        battery=battery,
        converter=converter,
        switchboard_id=switchboard_id,
        uid=subsystem.uid if len(subsystem.uid) > _MIN_LENGTH_UID else None,
    )


def convert_proto_supercapacitor_to_feems(
    proto_component: proto.SuperCapacitor, switchboard_id: int = 0
) -> SuperCapacitor:
    return SuperCapacitor(
        name=proto_component.name,
        rated_capacity_wh=proto_component.energy_capacity_wh,
        rated_power=proto_component.rated_power_kw,
        eff_charging=proto_component.efficiency_charging,
        eff_discharging=proto_component.efficiency_discharging,
        soc0=proto_component.initial_state_of_charge,
        switchboard_id=switchboard_id,
        uid=proto_component.uid if len(proto_component.uid) > _MIN_LENGTH_UID else None,
    )


def convert_proto_supercapacitor_system_to_feems(
    subsystem: proto.Subsystem, switchboard_id: int
) -> SuperCapacitorSystem:
    """Converts protobuf subsystem message to feems component"""
    supercapacitor = convert_proto_supercapacitor_to_feems(
        proto_component=subsystem.battery,
    )
    converter = convert_proto_electric_component_to_feems(
        proto_component=subsystem.converter1,
        component_type=TypeComponent.POWER_CONVERTER,
        power_type=TypePower.POWER_TRANSMISSION,
    )
    return SuperCapacitorSystem(
        name=subsystem.name,
        supercapacitor=supercapacitor,
        converter=converter,
        switchboard_id=switchboard_id,
        uid=subsystem.uid if len(subsystem.uid) > _MIN_LENGTH_UID else None,
    )


def collect_electric_components_from_sub_system(
    subsystem: proto.Subsystem,
) -> List[Dict[str, Union[str, Union[proto.ElectricMachine, proto.ElectricComponent]]]]:
    field_names = [
        "electric_machine",
        "transformer",
        "converter1",
        "converter2",
        "propeller",
        "other_load",
    ]
    components = [
        {"name": field_name, "proto_component": getattr(subsystem, field_name)}
        for field_name in field_names
        if subsystem.HasField(field_name)
    ]
    return sorted(
        components,
        key=lambda component: component.get(
            "proto_component"
        ).order_from_switchboard_or_shaftline,
    )


def convert_proto_generic_electric_component_to_feems(
    proto_component: Union[proto.ElectricComponent, proto.ElectricMachine],
    component_type: TypeComponent,
    power_type: TypePower,
    switchboard_id: int = 0,
) -> Union[ElectricComponent, ElectricMachine]:
    if proto_component.DESCRIPTOR.name == "ElectricComponent":
        return convert_proto_electric_component_to_feems(
            proto_component=proto_component,
            component_type=component_type,
            power_type=power_type,
            switchboard_id=switchboard_id,
        )
    else:
        return convert_proto_electric_machine_to_feems(
            proto_component=proto_component,
            component_type=component_type,
            power_type=power_type,
            switchboard_id=switchboard_id,
        )


def get_component_type(component_category: str) -> TypeComponent:
    if component_category == "transformer":
        return TypeComponent.TRANSFORMER
    if component_category in ["converter1", "converter2"]:
        return TypeComponent.POWER_CONVERTER
    if component_category == "electric_machine":
        return TypeComponent.SYNCHRONOUS_MACHINE
    if component_category == "other_load":
        return TypeComponent.OTHER_LOAD
    else:
        raise TypeError("The component category cannot be determined.")


def convert_proto_pti_pto_subsystem_to_feems(
    subsystem: proto.Subsystem,
    switchboard_id: int,
    shaft_line_id: int = 1,
) -> PTIPTO:
    proto_components = collect_electric_components_from_sub_system(subsystem)
    components_feems = [
        convert_proto_generic_electric_component_to_feems(
            proto_component=each_proto_component.get("proto_component"),
            component_type=get_component_type(each_proto_component.get("name")),
            power_type=TypePower.PTI_PTO,
        )
        for each_proto_component in proto_components
    ]
    return PTIPTO(
        name=subsystem.name,
        components=components_feems,
        rated_power=None if subsystem.rated_power_kw == 0 else subsystem.rated_power_kw,
        rated_speed=subsystem.rated_speed_rpm,
        switchboard_id=switchboard_id,
        shaft_line_id=shaft_line_id,
        uid=subsystem.uid if len(subsystem.uid) > _MIN_LENGTH_UID else None,
    )


def convert_proto_serial_subsystem_to_feems(
    subsystem: proto.Subsystem, switchboard_id: int
) -> SerialSystemElectric:
    proto_components = collect_electric_components_from_sub_system(subsystem)
    components_feems = [
        convert_proto_generic_electric_component_to_feems(
            proto_component=each_proto_component.get("proto_component"),
            component_type=get_component_type(each_proto_component.get("name")),
            power_type=TypePower(subsystem.power_type),
        )
        for each_proto_component in proto_components
    ]
    return SerialSystemElectric(
        type_=TypeComponent(subsystem.component_type),
        name=subsystem.name,
        power_type=TypePower(subsystem.power_type),
        components=components_feems,
        switchboard_id=switchboard_id,
        rated_power=None if subsystem.rated_power_kw == 0 else subsystem.rated_power_kw,
        rated_speed=(
            None if subsystem.rated_speed_rpm == 0 else subsystem.rated_speed_rpm
        ),
        uid=subsystem.uid if len(subsystem.uid) > _MIN_LENGTH_UID else None,
    )


def convert_generic_electric_subsystem_to_feems(
    subsystem: proto.Subsystem, switchboard_id: int
) -> Union[ElectricComponent, SerialSystemElectric, PTIPTO]:
    proto_components = collect_electric_components_from_sub_system(subsystem)
    if len(proto_components) == 1:
        component = proto_components[0].get("proto_component")
        if component.name == "":
            component.name = subsystem.name
        return convert_proto_generic_electric_component_to_feems(
            proto_component=component,
            component_type=TypeComponent(subsystem.component_type),
            power_type=TypePower(subsystem.power_type),
            switchboard_id=switchboard_id,
        )
    else:
        if subsystem.component_type == proto.Subsystem.ComponentType.PTI_PTO_SYSTEM:
            return convert_proto_pti_pto_subsystem_to_feems(
                subsystem=subsystem,
                switchboard_id=switchboard_id,
            )
        else:
            return convert_proto_serial_subsystem_to_feems(
                subsystem=subsystem, switchboard_id=switchboard_id
            )


def convert_proto_switchboard_to_feems(switchboard: proto.Switchboard) -> Switchboard:
    components = []
    switchboard_id = switchboard.switchboard_id
    for subsystem in switchboard.subsystems:
        if subsystem.component_type == proto.Subsystem.ComponentType.FUEL_CELL_SYSTEM:
            components.append(
                convert_proto_fuel_cell_system_to_feems(
                    subsystem=subsystem, switchboard_id=switchboard_id
                )
            )
        elif subsystem.component_type == proto.Subsystem.ComponentType.GENSET:
            components.append(
                convert_proto_genset_to_feems(
                    subsystem=subsystem, switchboard_id=switchboard_id
                )
            )
        elif subsystem.component_type == proto.Subsystem.ComponentType.COGES:
            components.append(
                convert_proto_coges_to_feems(
                    subsystem=subsystem, switchboard_id=switchboard_id
                )
            )
        elif subsystem.component_type == proto.Subsystem.ComponentType.BATTERY_SYSTEM:
            components.append(
                convert_proto_battery_system_to_feems(
                    subsystem=subsystem, switchboard_id=switchboard_id
                )
            )
        elif subsystem.component_type == proto.Subsystem.ComponentType.BATTERY:
            components.append(
                convert_proto_battery_to_feems(
                    proto_component=subsystem.battery, switchboard_id=switchboard_id
                )
            )
        elif (
            subsystem.component_type
            == proto.Subsystem.ComponentType.SUPERCAPACITOR_SYSTEM
        ):
            components.append(
                convert_proto_supercapacitor_system_to_feems(
                    subsystem=subsystem, switchboard_id=switchboard_id
                )
            )
        elif subsystem.component_type == proto.Subsystem.ComponentType.SUPERCAPACITOR:
            components.append(
                convert_proto_supercapacitor_to_feems(
                    proto_component=subsystem.supercapacitor,
                    switchboard_id=switchboard_id,
                )
            )
        else:
            components.append(
                convert_generic_electric_subsystem_to_feems(
                    subsystem=subsystem, switchboard_id=switchboard_id
                )
            )

    return Switchboard(
        name=f"SWBD {switchboard.switchboard_id}",
        idx=switchboard.switchboard_id,
        components=components,
    )


def convert_proto_shaftline_to_feems(
    shaftline: proto.ShaftLine,
    pti_ptos: Optional[List[PTIPTO]] = None,
) -> ShaftLine:
    shaft_line_id = shaftline.shaft_line_id
    components = []
    for sub_system in shaftline.subsystems:
        if sub_system.component_type == proto.Subsystem.ComponentType.MAIN_ENGINE:
            if sub_system.engine.name == "":
                sub_system.engine.name = sub_system.name
            components.append(
                MainEngineForMechanicalPropulsion(
                    name=sub_system.name,
                    engine=convert_proto_engine_to_feems(
                        proto_engine=sub_system.engine,
                        type_engine=TypeComponent.MAIN_ENGINE,
                    ),
                    shaft_line_id=shaft_line_id,
                    uid=(
                        sub_system.uid
                        if len(sub_system.uid) > _MIN_LENGTH_UID
                        else None
                    ),
                )
            )
        elif (
            sub_system.component_type
            == proto.Subsystem.ComponentType.MAIN_ENGINE_WITH_GEARBOX
        ):
            components.append(
                MainEngineWithGearBoxForMechanicalPropulsion(
                    name=sub_system.name,
                    engine=convert_proto_engine_to_feems(
                        proto_engine=sub_system.engine,
                        type_engine=TypeComponent.MAIN_ENGINE_WITH_GEARBOX,
                    ),
                    gearbox=BasicComponent(
                        type_=TypeComponent.GEARBOX,
                        name=sub_system.gear.name,
                        power_type=TypePower.POWER_TRANSMISSION,
                        rated_power=sub_system.gear.rated_power_kw,
                        rated_speed=sub_system.gear.rated_speed_rpm,
                        eff_curve=convert_proto_efficiency_bsfc_power_to_np_array(
                            efficiency_bsfc_power=sub_system.gear.efficiency
                        ),
                        uid=(
                            sub_system.gear.uid
                            if len(sub_system.gear.uid) > _MIN_LENGTH_UID
                            else None
                        ),
                    ),
                    shaft_line_id=shaft_line_id,
                    uid=(
                        sub_system.uid
                        if len(sub_system.uid) > _MIN_LENGTH_UID
                        else None
                    ),
                )
            )
        elif sub_system.component_type == proto.Subsystem.ComponentType.PTI_PTO_SYSTEM:
            if pti_ptos is None:
                components.append(
                    convert_proto_pti_pto_subsystem_to_feems(
                        subsystem=sub_system,
                        switchboard_id=1,
                        shaft_line_id=shaft_line_id,
                    )
                )
            else:
                try:
                    pti_pto = next(
                        filter(
                            lambda pti_pto: pti_pto.name == sub_system.name, pti_ptos
                        )
                    )
                except StopIteration as e:
                    print(
                        f"PTI/PTO {sub_system.name} not found in pti_ptos given as argument."
                    )
                    print("Creating a new PTI/PTO from the proto definition.")
                    components.append(
                        convert_proto_pti_pto_subsystem_to_feems(
                            subsystem=sub_system,
                            switchboard_id=1,
                            shaft_line_id=shaft_line_id,
                        )
                    )
                else:
                    components.append(pti_pto)
        elif sub_system.component_type == proto.Subsystem.ComponentType.PROPELLER_LOAD:
            components.append(
                MechanicalPropulsionComponent(
                    type_=TypeComponent.PROPELLER_LOAD,
                    power_type=TypePower.POWER_CONSUMER,
                    name=sub_system.name,
                    shaft_line_id=shaft_line_id,
                    rated_power=sub_system.rated_power_kw,
                    rated_speed=sub_system.rated_speed_rpm,
                    eff_curve=convert_proto_efficiency_bsfc_power_to_np_array(
                        efficiency_bsfc_power=sub_system.propeller.efficiency
                    ),
                    uid=(
                        sub_system.uid
                        if len(sub_system.uid) > _MIN_LENGTH_UID
                        else None
                    ),
                )
            )
        else:
            raise ValueError(
                f"The component type {TypeComponent(sub_system.component_type)} "
                f"is not supported."
            )
    return ShaftLine(
        name=f"Shaftline {shaftline.shaft_line_id}",
        shaft_line_id=shaftline.shaft_line_id,
        component_list=components,
    )


# %% ../00_ConvertToFeems.ipynb 8
def convert_feems_switchboards_to_feems_electric_power_system(
    switchboards: List[Switchboard],
) -> ElectricPowerSystem:
    def get_all_components(switchboard: Switchboard) -> List[Any]:
        return reduce(
            lambda components1, components2: [*components1, *components2],
            switchboard.component_by_power_type,
            [],
        )

    components = reduce(
        lambda acc, switchboard: [
            *acc,
            *get_all_components(switchboard),
        ],
        switchboards,
        [],
    )
    bus_tie_connection = [
        (index + 1, index + 2) for index in range(len(switchboards) - 1)
    ]
    return ElectricPowerSystem(
        name="electric power system",
        power_plant_components=components,
        bus_tie_connections=bus_tie_connection,
    )


def convert_feems_shaftlines_to_feems_mechanical_propulsion_system(
    shaftlines: List[ShaftLine],
) -> MechanicalPropulsionSystem:

    components = reduce(
        lambda acc, shaftline: [*acc, *shaftline.components], shaftlines, []
    )
    return MechanicalPropulsionSystem(
        name="mechanical propulsion system",
        components_list=components,
    )


def convert_proto_electric_system_to_feems(
    system: proto.ElectricSystem,
) -> ElectricPowerSystem:
    switchboards = [
        convert_proto_switchboard_to_feems(proto_switchboard)
        for proto_switchboard in system.switchboards
    ]
    return convert_feems_switchboards_to_feems_electric_power_system(switchboards)


def convert_proto_mechanical_system_to_feems(
    system: proto.MechanicalSystem, pti_ptos: List[PTIPTO] = None
) -> MechanicalPropulsionSystem:
    shaft_lines = []
    for proto_shaftline in system.shaft_lines:
        if pti_ptos is not None:
            pti_ptos_shaft_line_proto = list(
                filter(
                    lambda subsystem: subsystem.component_type
                    == proto.Subsystem.ComponentType.PTI_PTO_SYSTEM,
                    proto_shaftline.subsystems,
                )
            )
            uid_list = list(map(lambda x: x.uid, pti_ptos_shaft_line_proto))
            pti_ptos_for_shaft_lines = list(
                filter(
                    lambda pti_pto: pti_pto.uid in uid_list,
                    pti_ptos,
                )
            )
            for each in pti_ptos_for_shaft_lines:
                each.shaft_line_id = proto_shaftline.shaft_line_id
        else:
            pti_ptos_for_shaft_lines = None
        shaft_lines.append(
            convert_proto_shaftline_to_feems(
                shaftline=proto_shaftline, pti_ptos=pti_ptos_for_shaft_lines
            )
        )
    return convert_feems_shaftlines_to_feems_mechanical_propulsion_system(
        shaftlines=shaft_lines
    )


def convert_proto_propulsion_system_to_feems(
    system: proto.MachinerySystem,
) -> Union[
    MechanicalPropulsionSystemWithElectricPowerSystem,
    ElectricPowerSystem,
    HybridPropulsionSystem,
    None,
]:
    if system.propulsion_type == proto.MachinerySystem.PropulsionType.MECHANICAL:
        return MechanicalPropulsionSystemWithElectricPowerSystem(
            name=system.name,
            electric_system=convert_proto_electric_system_to_feems(
                system.electric_system
            ),
            mechanical_system=convert_proto_mechanical_system_to_feems(
                system.mechanical_system
            ),
        )
    if system.propulsion_type == proto.MachinerySystem.PropulsionType.ELECTRIC:
        return convert_proto_electric_system_to_feems(system.electric_system)
    if system.propulsion_type == proto.MachinerySystem.PropulsionType.HYBRID:
        electric_system = convert_proto_electric_system_to_feems(system.electric_system)
        pti_ptos = electric_system.pti_pto if len(electric_system.pti_pto) > 0 else None
        return HybridPropulsionSystem(
            name=system.name,
            electric_system=electric_system,
            mechanical_system=convert_proto_mechanical_system_to_feems(
                system=system.mechanical_system, pti_ptos=pti_ptos
            ),
        )
    return None
