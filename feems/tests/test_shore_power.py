from feems.components_model.component_electric import (
    ElectricComponent,
    ShorePowerConnection,
    ShorePowerConnectionSystem,
)
from feems.system_model import ElectricPowerSystem
from feems.types_for_feems import Power_kW, SwbId, TypeComponent, TypePower


def test_add_shore_power_to_electric_system():
    shore_power = ShorePowerConnection(
        name="Shore Power", rated_power=Power_kW(1000), switchboard_id=SwbId(1)
    )

    system = ElectricPowerSystem(
        name="Test System", power_plant_components=[shore_power], bus_tie_connections=[]
    )

    assert shore_power in system.power_sources


def test_add_shore_power_system_to_electric_system():
    shore_power_connection = ShorePowerConnection(
        name="Shore Power", rated_power=Power_kW(1000), switchboard_id=SwbId(1)
    )
    converter = ElectricComponent(
        type_=TypeComponent.POWER_CONVERTER,
        name="Converter",
        rated_power=Power_kW(1000),
        power_type=TypePower.POWER_TRANSMISSION,
        switchboard_id=SwbId(1),
    )
    shore_power_connection_system = ShorePowerConnectionSystem(
        name="Shore Power System",
        shore_power_connection=shore_power_connection,
        converter=converter,
        switchboard_id=SwbId(1),
    )

    system = ElectricPowerSystem(
        name="Test System",
        power_plant_components=[shore_power_connection_system],
        bus_tie_connections=[],
    )

    assert shore_power_connection_system in system.power_sources
