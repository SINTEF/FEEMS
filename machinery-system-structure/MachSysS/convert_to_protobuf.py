# AUTOGENERATED! DO NOT EDIT! File to edit: ../01_ConvertToProtobuf.ipynb.

# %% auto 0
__all__ = [
    "convert_efficiency_curve_to_protobuf",
    "convert_np_array_to_protobuf_power_curve",
    "convert_bsfc_curve_to_protobuf",
    "convert_electric_machine_to_protobuf",
    "convert_electric_component_to_protobuf",
    "convert_battery_component_to_protobuf",
    "convert_supercapacitor_component_to_protobuf",
    "convert_serial_electric_system_to_protobuf",
    "convert_nox_calculation_method_to_protobuf",
    "convert_emission_curves_to_protobuf",
    "convert_engine_component_to_protobuf",
    "convert_cogas_component_to_protobuf",
    "convert_switchboard_to_protobuf",
    "convert_shaftline_to_protobuf",
    "convert_electric_system_to_protobuf",
    "convert_electric_system_to_protobuf_machinery_system",
    "convert_mechanical_system_to_protobuf",
    "convert_mechanical_propulsion_system_with_electric_system_to_protobuf",
    "convert_hybrid_propulsion_system_to_protobuf",
]

# %% ../01_ConvertToProtobuf.ipynb 3
from feems.components_model import (
    Engine,
    Switchboard,
    ShaftLine,
    MainEngineForMechanicalPropulsion,
    MechanicalPropulsionComponent,
    MainEngineWithGearBoxForMechanicalPropulsion,
)
from typing import cast, Union, List

from feems.components_model.component_base import BasicComponent
from feems.types_for_feems import TypeComponent, NOxCalculationMethod, EmissionCurve
from feems.components_model.component_mechanical import COGAS, EngineDualFuel
from feems.components_model.component_electric import (
    COGES,
    ElectricComponent,
    FuelCellSystem,
    ElectricMachine,
    BatterySystem,
    Battery,
    SuperCapacitorSystem,
    PTIPTO,
    SuperCapacitor,
)
from feems.components_model.component_electric import SerialSystemElectric, Genset
from feems.system_model import (
    ElectricPowerSystem,
    MechanicalPropulsionSystem,
    MechanicalPropulsionSystemWithElectricPowerSystem,
    HybridPropulsionSystem,
)
import numpy as np

import MachSysS.system_structure_pb2 as proto


def convert_efficiency_curve_to_protobuf(
    component: ElectricComponent,
) -> proto.Efficiency:
    """Convert efficiency value or curve in the component to protobuf message"""
    efficiency = proto.Efficiency()
    if len(component._efficiency_points) == 1:
        efficiency.value = component._efficiency_points[0]
    else:
        efficiency.curve.curve.points.extend(
            [
                proto.Point(x=each_point[0], y=each_point[1])
                for each_point in component._efficiency_points
            ]
        )
        efficiency.curve.x_label = "power load"
        efficiency.curve.y_label = "efficiency"
    return efficiency


def convert_np_array_to_protobuf_power_curve(power_curve: np.array) -> proto.PowerCurve:
    """Convert power curve in the component to protobuf message"""
    # Check if the array is in n x 2 dimension or a single value
    if power_curve.shape[1] == 2:
        curve = proto.Curve1D()
        curve.points.extend(
            [
                proto.Point(x=each_point[0], y=each_point[1])
                for each_point in power_curve
            ]
        )
        return proto.PowerCurve(
            x_label="load_ratio",
            y_label="power_kw",
            curve=curve,
        )
    else:
        raise ValueError(
            f"The power curve array should have 2 columns. The array has {power_curve.shape[1]} columns."
        )


def convert_bsfc_curve_to_protobuf(
    component: Union[Engine, EngineDualFuel], for_pilot_fuel: bool = False
) -> proto.BSFC:
    """Convert bsfc value or curve in the component to protobuf message"""
    bsfc = proto.BSFC()
    bsfc_points = (
        component.specific_fuel_consumption_points
        if not for_pilot_fuel
        else component.specific_pilot_fuel_consumption_points
    )
    if len(bsfc_points) == 1:
        bsfc.value = bsfc_points[0]
    else:
        bsfc.curve.curve.points.extend(
            [
                proto.Point(x=each_point[0], y=each_point[1])
                for each_point in bsfc_points
            ]
        )
        bsfc.curve.x_label = "power load"
        bsfc.curve.y_label = "bsfc"
    return bsfc


def convert_electric_machine_to_protobuf(
    component: ElectricMachine, order_from_switchboard: int = 1
) -> proto.ElectricMachine:
    """Convert elecrtic machine component of FEEMS to protobuf message"""
    return proto.ElectricMachine(
        name=component.name,
        rated_power_kw=component.rated_power,
        rated_speed_rpm=component.rated_speed,
        efficiency=convert_efficiency_curve_to_protobuf(component),
        order_from_switchboard_or_shaftline=order_from_switchboard,
        uid=component.uid,
    )


def convert_electric_component_to_protobuf(
    component: ElectricComponent, order_from_switchboard: int = 1
) -> proto.ElectricMachine:
    """Convert converter component of FEEMS to protobuf message"""
    return proto.ElectricComponent(
        name=component.name,
        rated_power_kw=component.rated_power,
        efficiency=convert_efficiency_curve_to_protobuf(component),
        order_from_switchboard_or_shaftline=order_from_switchboard,
        uid=component.uid,
    )


def convert_battery_component_to_protobuf(
    component: Battery, order_from_switchboard: int = 1
) -> proto.ElectricMachine:
    """Convert battery component of FEEMS to protobuf message"""
    return proto.Battery(
        name=component.name,
        energy_capacity_kwh=component.rated_capacity_kWh,
        rated_charging_rate_c=component.charging_rate_C,
        rated_discharging_rate_c=component.discharging_rate_C,
        efficiency_charging=component.eff_charging,
        efficiency_discharging=component.eff_discharging,
        initial_state_of_charge=component.soc0,
        order_from_switchboard_or_shaftline=order_from_switchboard,
        uid=component.uid,
    )


def convert_supercapacitor_component_to_protobuf(
    component: SuperCapacitor, order_from_switchboard: int = 1
) -> proto.ElectricMachine:
    """Convert converter component of FEEMS to protobuf message"""
    return proto.SuperCapacitor(
        name=component.name,
        energy_capacity_wh=component.rated_capacity_Wh,
        rated_power_kw=component.rated_power,
        efficiency_charging=component.eff_charging,
        efficiency_discharging=component.eff_discharging,
        initial_state_of_charge=component.soc0,
        order_from_switchboard_or_shaftline=order_from_switchboard,
        uid=component.uid,
    )


def convert_serial_electric_system_to_protobuf(
    component: Union[SerialSystemElectric, PTIPTO],
    initial_order_from_switchboard: int = 1,
) -> proto.Subsystem:
    """Convert serial electric system or PTI/PTO component to protobuf message"""
    order = initial_order_from_switchboard
    subsystem = proto.Subsystem(
        name=component.name,
        rated_power_kw=component.rated_power,
        rated_speed_rpm=component.rated_speed,
        component_type=component.type.value,
        power_type=component.power_type.value,
        uid=component.uid,
    )
    for subcomponent in component.components:
        if subcomponent.type == TypeComponent.TRANSFORMER:
            subsystem.transformer.CopyFrom(
                convert_electric_component_to_protobuf(
                    component=subcomponent, order_from_switchboard=order
                )
            )
        if subcomponent.type in [
            TypeComponent.POWER_CONVERTER,
            TypeComponent.INVERTER,
            TypeComponent.RECTIFIER,
            TypeComponent.ACTIVE_FRONT_END,
        ]:
            if not subsystem.HasField("converter1"):
                subsystem.converter1.CopyFrom(
                    convert_electric_component_to_protobuf(
                        component=subcomponent, order_from_switchboard=order
                    )
                )
            else:
                subsystem.converter2.CopyFrom(
                    convert_electric_component_to_protobuf(
                        component=subcomponent, order_from_switchboard=order
                    )
                )
        if subcomponent.type in [
            TypeComponent.SYNCHRONOUS_MACHINE,
            TypeComponent.INDUCTION_MACHINE,
            TypeComponent.ELECTRIC_MOTOR,
        ]:
            subsystem.electric_machine.CopyFrom(
                convert_electric_machine_to_protobuf(
                    component=subcomponent, order_from_switchboard=order
                )
            )
        order += 1
    return subsystem


def convert_nox_calculation_method_to_protobuf(
    nox_calculation_method_feems: NOxCalculationMethod,
) -> proto.Engine.NOxCalculationMethod:
    """Convert nox calculation method of FEEMS to protobuf message"""
    index = proto.Engine.NOxCalculationMethod.Value(nox_calculation_method_feems.name)
    return index


def convert_emission_curves_to_protobuf(
    emission_curves_feems: List[EmissionCurve],
) -> List[proto.EmissionCurve]:
    """Convert emission curves of FEEMS to protobuf message"""
    if emission_curves_feems is None:
        return []
    return [
        proto.EmissionCurve(
            x_label="load_ratio",
            y_label="emission_g_per_kwh",
            curve=proto.Curve1D(
                points=[
                    proto.Point(
                        x=each_point.load_ratio, y=each_point.emission_g_per_kwh
                    )
                    for each_point in each_curve.points_per_kwh
                ]
            ),
            emission_type=each_curve.emission.value,
        )
        for each_curve in emission_curves_feems
    ]


def convert_engine_component_to_protobuf(
    engine_feems: Union[Engine, EngineDualFuel],
    order_from_shaftline_or_switchboard: int = 1,
) -> proto.Engine:
    """Convert engine component of FEEMS to protobuf message"""
    engine = proto.Engine(
        name=engine_feems.name,
        rated_power_kw=engine_feems.rated_power,
        rated_speed_rpm=engine_feems.rated_speed,
        bsfc=convert_bsfc_curve_to_protobuf(engine_feems),
        main_fuel=proto.Fuel(
            fuel_type=engine_feems.fuel_type.value,
            fuel_origin=engine_feems.fuel_origin.value,
        ),
        nox_calculation_method=convert_nox_calculation_method_to_protobuf(
            engine_feems.nox_calculation_method
        ),
        emission_curves=convert_emission_curves_to_protobuf(
            engine_feems.emission_curves
        ),
        engine_cycle_type=engine_feems.engine_cycle_type.value,
        order_from_switchboard_or_shaftline=order_from_shaftline_or_switchboard,
        uid=engine_feems.uid,
    )
    if isinstance(engine_feems, EngineDualFuel):
        engine.pilot_bsfc.CopyFrom(
            convert_bsfc_curve_to_protobuf(engine_feems, for_pilot_fuel=True)
        )
        engine.pilot_fuel.CopyFrom(
            proto.Fuel(
                fuel_type=engine_feems.pilot_fuel_type.value,
                fuel_origin=engine_feems.pilot_fuel_origin.value,
            )
        )
    return engine


def convert_cogas_component_to_protobuf(
    component: COGAS,
    order_from_shaftline_or_switchboard: int = 1,
) -> proto.Engine:
    """Convert engine component of FEEMS to protobuf message"""
    cogas = proto.COGAS(
        name=component.name,
        rated_power_kw=component.rated_power,
        rated_speed_rpm=component.rated_speed,
        efficiency=convert_efficiency_curve_to_protobuf(component),
        fuel=proto.Fuel(
            fuel_type=component.fuel_type.value,
            fuel_origin=component.fuel_origin.value,
        ),
        nox_calculation_method=convert_nox_calculation_method_to_protobuf(
            component.nox_calculation_method
        ),
        emission_curves=convert_emission_curves_to_protobuf(component.emission_curves),
        order_from_switchboard_or_shaftline=order_from_shaftline_or_switchboard,
        uid=component.uid,
    )
    if component.gas_turbine_power_curve is not None:
        cogas.gas_turbine_power_curve.CopyFrom(
            convert_np_array_to_protobuf_power_curve(component.gas_turbine_power_curve)
        )
        cogas.steam_turbine_power_curve.CopyFrom(
            convert_np_array_to_protobuf_power_curve(
                component.steam_turbine_power_curve
            )
        )
    return cogas


def convert_switchboard_to_protobuf(
    switchboard_feems: Switchboard,
) -> proto.Switchboard:
    switchboard_proto = proto.Switchboard()
    switchboard_proto.switchboard_id = switchboard_feems.id

    for component in switchboard_feems.components:
        subsystem = proto.Subsystem(
            power_type=component.power_type.value,
            component_type=component.type.value,
            name=component.name,
            rated_power_kw=component.rated_power,
            rated_speed_rpm=component.rated_speed,
            uid=component.uid,
        )
        if component.type == TypeComponent.GENERATOR:
            subsystem.electric_machine.CopyFrom(
                convert_electric_machine_to_protobuf(
                    component=component,
                )
            )
        elif component.type == TypeComponent.FUEL_CELL_SYSTEM:
            component = cast(FuelCellSystem, component)
            subsystem.converter1.CopyFrom(
                convert_electric_component_to_protobuf(component=component.converter)
            )
            subsystem.fuel_cell.CopyFrom(
                proto.FuelCell(
                    name=component.fuel_cell.name,
                    rated_power_kw=component.fuel_cell.rated_power,
                    efficiency=convert_efficiency_curve_to_protobuf(
                        component.fuel_cell
                    ),
                    fuel=proto.Fuel(
                        fuel_type=component.fuel_cell.fuel_type.value,
                        fuel_origin=component.fuel_cell.fuel_origin.value,
                    ),
                    number_modules=component.number_modules,
                    order_from_switchboard_or_shaftline=2,
                    uid=component.fuel_cell.uid,
                )
            )
        elif component.type == TypeComponent.COGES:
            component = cast(COGES, component)
            subsystem.cogas.CopyFrom(
                convert_cogas_component_to_protobuf(
                    component=component.cogas, order_from_shaftline_or_switchboard=2
                )
            )
            subsystem.electric_machine.CopyFrom(
                convert_electric_machine_to_protobuf(
                    component=component.generator, order_from_switchboard=1
                )
            )
        elif component.type == TypeComponent.GENSET:
            component = cast(Genset, component)
            subsystem.electric_machine.CopyFrom(
                convert_electric_machine_to_protobuf(
                    component=component.generator,
                )
            )
            subsystem.engine.CopyFrom(
                convert_engine_component_to_protobuf(
                    engine_feems=component.aux_engine,
                    order_from_shaftline_or_switchboard=2,
                )
            )
        elif component.type == TypeComponent.OTHER_LOAD:
            subsystem.other_load.CopyFrom(
                convert_electric_component_to_protobuf(component=component)
            )
        elif component.type in [
            TypeComponent.PTI_PTO_SYSTEM,
            TypeComponent.PROPULSION_DRIVE,
        ]:
            subsystem.MergeFrom(
                convert_serial_electric_system_to_protobuf(component=component)
            )
        elif component.type == TypeComponent.BATTERY_SYSTEM:
            component = cast(BatterySystem, component)
            subsystem.converter1.CopyFrom(
                convert_electric_component_to_protobuf(component=component.converter)
            )
            subsystem.battery.CopyFrom(
                convert_battery_component_to_protobuf(
                    component=component.battery, order_from_switchboard=2
                )
            )
        elif component.type == TypeComponent.BATTERY:
            subsystem.battery.CopyFrom(
                convert_battery_component_to_protobuf(component=component)
            )
        elif component.type == TypeComponent.SUPERCAPACITOR_SYSTEM:
            component = cast(SuperCapacitorSystem, component)
            subsystem.converter1.CopyFrom(
                convert_electric_component_to_protobuf(component=component.converter)
            )
            subsystem.battery.CopyFrom(
                convert_supercapacitor_component_to_protobuf(
                    component=component.supercapacitor, order_from_switchboard=2
                )
            )
        elif component.type == TypeComponent.SUPERCAPACITOR:
            subsystem.battery.CopyFrom(
                convert_supercapacitor_component_to_protobuf(component=component)
            )
        else:
            raise TypeError(
                f"The component type ({component.type.name}) is not a proper type for an electric "
                f"system or the conversion for the type is not implemented."
            )
        switchboard_proto.subsystems.append(subsystem)
    return switchboard_proto


def convert_shaftline_to_protobuf(shaftline_feems: ShaftLine) -> proto.ShaftLine:
    """Convert shaft line to protobuf message"""
    shaftline_proto = proto.ShaftLine()
    shaftline_proto.shaft_line_id = shaftline_feems.id
    gear_proto = None
    propeller_id = 1
    # If there is a gear box component on the shaft line, it is recognized as a gear box connecting
    # the main engine to the propeller and pti/pto.
    # The gear box is added to the protobuf message first.
    for gear in filter(
        lambda component: component.type == TypeComponent.GEARBOX,
        shaftline_feems.components,
    ):
        gear = cast(MechanicalPropulsionComponent, gear)
        gear_proto = proto.Gear(
            name=gear.name,
            rated_power_kw=gear.rated_power,
            rated_speed_rpm=gear.rated_speed,
            efficiency=convert_efficiency_curve_to_protobuf(gear),
            order_from_switchboard_or_shaftline=1,
            uid=gear.uid,
        )

    for component in shaftline_feems.components:
        subsystem = proto.Subsystem(
            power_type=component.power_type.value,
            component_type=component.type.value,
            name=component.name,
            rated_power_kw=component.rated_power,
            rated_speed_rpm=component.rated_speed,
            uid=component.uid,
        )
        if component.type == TypeComponent.MAIN_ENGINE:
            component = cast(MainEngineForMechanicalPropulsion, component)
            subsystem.engine.CopyFrom(
                convert_engine_component_to_protobuf(
                    engine_feems=component.engine, order_from_shaftline_or_switchboard=1
                )
            )
        elif component.type == TypeComponent.MAIN_ENGINE_WITH_GEARBOX:
            if gear_proto is not None:
                raise ValueError(
                    f"The shaft line {shaftline_feems.id} already has a gear box. "
                    f"Please use a main-engine component rather than a main-engine-with-a-gear-box"
                    f"component."
                )
            component = cast(MainEngineWithGearBoxForMechanicalPropulsion, component)
            subsystem.engine.CopyFrom(
                convert_engine_component_to_protobuf(
                    engine_feems=component.main_engine,
                    order_from_shaftline_or_switchboard=2,
                )
            )
            subsystem.gear.CopyFrom(
                proto.Gear(
                    name=component.gearbox.name,
                    rated_power_kw=component.gearbox.rated_power,
                    rated_speed_rpm=component.gearbox.rated_speed,
                    efficiency=convert_efficiency_curve_to_protobuf(component.gearbox),
                    order_from_switchboard_or_shaftline=1,
                    uid=component.gearbox.uid,
                )
            )
        elif component.type == TypeComponent.PROPELLER_LOAD:
            if gear_proto is not None:
                subsystem.gear.CopyFrom(gear_proto)
            subsystem.propeller.CopyFrom(
                proto.Propeller(
                    efficiency=convert_efficiency_curve_to_protobuf(component),
                    propulsor_id=propeller_id,
                    order_from_switchboard_or_shaftline=2,
                    uid=component.uid,
                )
            )
            propeller_id += 1
        elif component.type == TypeComponent.PTI_PTO_SYSTEM:
            subsystem.MergeFrom(
                convert_serial_electric_system_to_protobuf(component=component)
            )
        elif component.type == TypeComponent.GEARBOX:
            continue
        else:
            raise ValueError(
                f"The shaftline contains a component ({component.name}) that has an "
                f"imcompatible type ({component.type}) for conversion."
            )
        shaftline_proto.subsystems.append(subsystem)
    return shaftline_proto


# %% ../01_ConvertToProtobuf.ipynb 6
def convert_electric_system_to_protobuf(
    electric_system: ElectricPowerSystem,
) -> proto.ElectricSystem:
    """Convert electric system to protobuf message"""
    return proto.ElectricSystem(
        switchboards=[
            convert_switchboard_to_protobuf(switchboard)
            for _, switchboard in electric_system.switchboards.items()
        ]
    )


def convert_electric_system_to_protobuf_machinery_system(
    electric_system: ElectricPowerSystem,
    maximum_allowed_genset_load_percentage: float = 80.0,
) -> proto.MachinerySystem:
    """Convert electric system to protobuf message as a machinery system"""
    return proto.MachinerySystem(
        name=electric_system.name,
        propulsion_type=proto.MachinerySystem.PropulsionType.ELECTRIC,
        fuel_storage=[],
        maximum_allowed_genset_load_percentage=maximum_allowed_genset_load_percentage,
        electric_system=convert_electric_system_to_protobuf(electric_system),
    )


def convert_mechanical_system_to_protobuf(
    mechanical_propulsion_system: MechanicalPropulsionSystem,
) -> proto.MechanicalSystem:
    return proto.MechanicalSystem(
        shaft_lines=[
            convert_shaftline_to_protobuf(shaftline)
            for shaftline in mechanical_propulsion_system.shaft_line
        ]
    )


def convert_mechanical_propulsion_system_with_electric_system_to_protobuf(
    system_feems: MechanicalPropulsionSystemWithElectricPowerSystem,
    maximum_allowed_genset_load_percentage: float = 80.0,
) -> proto.MachinerySystem:
    return proto.MachinerySystem(
        name=system_feems.name,
        propulsion_type=proto.MachinerySystem.PropulsionType.MECHANICAL,
        fuel_storage=[],
        maximum_allowed_genset_load_percentage=maximum_allowed_genset_load_percentage,
        mechanical_system=convert_mechanical_system_to_protobuf(
            system_feems.mechanical_system
        ),
        electric_system=convert_electric_system_to_protobuf(
            system_feems.electric_system
        ),
    )


def convert_hybrid_propulsion_system_to_protobuf(
    system_feems: HybridPropulsionSystem,
    maximum_allowed_genset_load_percentage: float = 80.0,
) -> proto.MachinerySystem:
    return proto.MachinerySystem(
        name=system_feems.name,
        propulsion_type=proto.MachinerySystem.HYBRID,
        fuel_storage=[],
        maximum_allowed_genset_load_percentage=maximum_allowed_genset_load_percentage,
        mechanical_system=convert_mechanical_system_to_protobuf(
            system_feems.mechanical_system
        ),
        electric_system=convert_electric_system_to_protobuf(
            system_feems.electric_system
        ),
    )
