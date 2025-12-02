from dataclasses import dataclass
from typing import Union, Tuple, NamedTuple, Optional, List

import numpy as np
import pandas as pd

from .. import get_logger

from .component_base import SerialSystem, Component, BasicComponent, ComponentRunPoint
from .component_mechanical import (
    COGAS,
    COGASRunPoint,
    Engine,
    EngineDualFuel,
    EngineMultiFuel,
    EngineRunPoint,
    FuelCharacteristics,
    MainEngineForMechanicalPropulsion,
    MechanicalPropulsionComponent,
    MainEngineWithGearBoxForMechanicalPropulsion,
)
from .utility import integrate_data, IntegrationMethod, integrate_data_accumulative
from ..constant import hhv_hydrogen_mj_per_kg, lhv_hydrogen_mj_per_kg
from ..fuel import (
    FuelConsumption,
    TypeFuel,
    FuelSpecifiedBy,
    Fuel,
    FuelOrigin,
    GhgEmissionFactorTankToWake,
    FuelConsumerClassFuelEUMaritime,
)
from ..types_for_feems import (
    TypeComponent,
    TypePower,
    Power_kW,
    Speed_rpm,
    TimeIntervalList,
    SwbId,
)


logger = get_logger(__name__)


class ElectricComponent(BasicComponent):
    """Electric component class for basic information and efficiency interpolation."""

    def __init__(
        self,
        type_: TypeComponent,
        name: str = "",
        rated_power: Power_kW = Power_kW(1),
        eff_curve: np.ndarray = np.array([1]),
        power_type: TypePower = TypePower.NONE,
        rated_speed: Speed_rpm = Speed_rpm(0),
        switchboard_id: SwbId = SwbId(0),
        file_name: str = None,
        uid: Optional[str] = None,
    ):
        super().__init__(
            type_=type_,
            power_type=power_type,
            name=name,
            rated_power=rated_power,
            rated_speed=rated_speed,
            eff_curve=eff_curve,
            file_name=file_name,
            uid=uid,
        )
        self.power_type = power_type
        if power_type in [
            TypePower.POWER_SOURCE,
            TypePower.PTI_PTO,
            TypePower.ENERGY_STORAGE,
        ]:
            self.load_sharing_mode = np.zeros(1)
            self.status = np.zeros(0).astype(bool)
        if file_name is not None:
            df = pd.read_csv(file_name, index_col=0)
            self.switchboard_id = df["Switchboard No"].values[0]
        else:
            self.switchboard_id = switchboard_id


class ElectricMachine(ElectricComponent):
    """Electric Machine as a subclass of ElectricComponent"""

    def __init__(
        self,
        *,
        type_: TypeComponent,
        name: str,
        rated_power: Power_kW,
        rated_speed: Speed_rpm,
        power_type: TypePower = TypePower.NONE,
        switchboard_id: SwbId = SwbId(0),
        number_poles: int = 1,
        eff_curve: np.ndarray = np.ones(1),
        uid: Optional[str] = None,
    ):
        super(ElectricMachine, self).__init__(
            type_=type_,
            name=name,
            power_type=power_type,
            rated_power=rated_power,
            rated_speed=rated_speed,
            eff_curve=eff_curve,
            switchboard_id=switchboard_id,
            uid=uid,
        )
        self.number_of_poles = number_poles

    def get_shaft_power_load_from_electric_power(
        self,
        power_electric: Union[float, np.ndarray],
        strict_power_balance: bool = False,
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """
        Calculate the shaft power and load percentage from electric power

        :param power_electric: in kW, for power source component, positive value means the machine
            is providing powered by the shaft side. For power consumer component, positive value
            means the machine is powered by the electric side. For PTI_PTO, positive value means
            the machine is powered from the electric side (motor) and negative value means the
            machine is powered from the shaft side (generator), ndarray
        :param strict_power_balance: (Optional) If true, it will run iterative method to find
            the exact solution for getting the shaft power. Otherwise, it will use an interpolation
            function. Default is False.
        :return: power: in kW, positive is the power driving the shaft from the electric machine,
            negative is the power driven from the other end. ndarray, load: load percentage, ndarray
        """
        if self.power_type == TypePower.POWER_SOURCE:
            power_shaft, load = self.get_power_input_from_bidirectional_output(
                power_electric, strict_power_balance
            )
        elif (
            self.power_type == TypePower.POWER_CONSUMER or self.power_type == TypePower.PTI_PTO_SYS
        ):
            power_shaft, load = self.get_power_output_from_bidirectional_input(
                power_electric, strict_power_balance
            )
        else:
            raise TypeError(
                "The type of the component for {} is not properly assigned. "
                "It should be either power source, power consumer or PTI/PTO.".format(self.name)
            )
        return power_shaft, load

    def get_electric_power_load_from_shaft_power(
        self, power_shaft: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """
        Calculate the electric power and load percentage from shaft power

        :param power_shaft: in kW, for power source component, positive value means the machine is
            providing powered by the shaft side. For power consumer component, positive value means
            the machine is powered by the electric side. For PTI_PTO, positive value means the
            machine is powered from the electric side (motor) and negative value means the machine
            is powered from the shaft side (generator), ndarray
        :param strict_power_balance: requires to achieve power balance by using Newton's method.
            Default value is False.

        :return: power
        """
        if self.power_type == TypePower.POWER_SOURCE:
            power_electric, load = self.get_power_output_from_bidirectional_input(
                power_shaft, strict_power_balance
            )
        elif self.power_type == TypePower.POWER_CONSUMER or self.power_type == TypePower.PTI_PTO:
            power_electric, load = self.get_power_input_from_bidirectional_output(
                power_shaft, strict_power_balance
            )
        else:
            raise TypeError(
                "The type of the component for {} is not properly assigned. "
                "It should be either power source, power consumer or PTI/PTO.".format(self.name),
            )
        return power_electric, load


class Battery(ElectricComponent):
    """
    Battery class

    :param name: name
    :param rated_capacity_kwh: Energy capacity in kWh
    :param charging_rate_c: Charging rate in C-rate
    :param discharge_rate_c: Discharging rate in C-rate
    :param soc0: Initial SoC in percentage
    :param eff_charging: Charging efficiency in percentage
    :param eff_discharging: Discharging efficiency in percentage
    :param switchboard_id: switchboard ID, if applicable
    """

    def __init__(
        self,
        name: str,
        rated_capacity_kwh: float,
        charging_rate_c: float,
        discharge_rate_c: float,
        soc0: float = 0.80,
        eff_charging: float = 0.975,
        eff_discharging: float = 0.975,
        switchboard_id: SwbId = SwbId(0),
        uid: Optional[str] = None,
    ):
        rated_power = Power_kW(rated_capacity_kwh * discharge_rate_c)
        super().__init__(
            TypeComponent.BATTERY,
            name,
            rated_power,
            power_type=TypePower.ENERGY_STORAGE,
            switchboard_id=switchboard_id,
            uid=uid,
        )
        self.rated_capacity_kWh = rated_capacity_kwh
        self.charging_rate_C = charging_rate_c
        self.discharging_rate_C = discharge_rate_c
        self.soc0 = soc0
        self.eff_charging = eff_charging
        self.eff_discharging = eff_discharging

    def get_energy_stored_kj(
        self,
        time_interval_s: TimeIntervalList,
        integration_method: IntegrationMethod,
        accumulated_time_series: bool = False,
    ) -> Union[float, np.ndarray]:
        """Calculate energy stored based on the power input at the terminal"""
        power_stored_in_battery, _ = self.get_power_output_from_bidirectional_input(
            power_input=self.power_input
        )
        if accumulated_time_series:
            return integrate_data_accumulative(
                data_to_integrate=power_stored_in_battery,
                time_interval_s=time_interval_s,
                integration_method=integration_method,
            )
        else:
            return integrate_data(
                data_to_integrate=power_stored_in_battery,
                time_interval_s=time_interval_s,
                integration_method=integration_method,
            )

    def get_soc(
        self,
        time_interval_s: TimeIntervalList,
        integration_method: IntegrationMethod,
        accumulated_time_series: bool = False,
    ) -> Union[float, np.ndarray]:
        """
        Calculates the SoC based on the power input at the terminal. The power input of the
        battery should have been set.

        :param time_interval_s: time interval for the power_input series
        :param integration_method: 'simpson' or 'trapezoid'. 'simpson' is default value.
        :param accumulated_time_series: function returns accumulated time-series if the
            value is true
        :return: SoC as series
        """
        energy_stored_kj = self.get_energy_stored_kj(
            time_interval_s=time_interval_s,
            integration_method=integration_method,
            accumulated_time_series=accumulated_time_series,
        )

        #: Calculate soc
        return energy_stored_kj / 3600 / self.rated_capacity_kWh + self.soc0

    @property
    def max_charging_power_kw(self) -> Power_kW:
        return Power_kW(self.charging_rate_C * self.rated_capacity_kWh)

    @property
    def max_discharging_power_kw(self) -> float:
        return Power_kW(self.discharging_rate_C * self.rated_capacity_kWh)

    def get_power_input_from_bidirectional_output(
        self, power_output: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        load = self.get_load(power_output)
        if type(power_output) is not np.ndarray:
            if power_output >= 0:
                return power_output / self.eff_charging, load
            else:
                return power_output * self.eff_discharging, load
        else:
            idx_charging = power_output > 0
            idx_discharging = power_output < 0
            power_input = power_output.copy()
            power_input[idx_charging] = power_output[idx_charging] / self.eff_charging
            power_input[idx_discharging] = power_output[idx_discharging] * self.eff_discharging
            return power_input, load

    def get_power_output_from_bidirectional_input(
        self, power_input: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        if type(power_input) is not np.ndarray:
            if power_input > 0:
                power_output = power_input * self.eff_charging
            else:
                power_output = power_input / self.eff_discharging
        else:
            idx_charging = power_input > 0
            idx_discharging = power_input < 0
            power_output = power_input.copy()
            power_output[idx_charging] = power_output[idx_charging] * self.eff_charging
            power_output[idx_discharging] = power_output[idx_discharging] / self.eff_discharging
        load = self.get_load(power_output)
        return power_output, load

    @property
    def rated_capacity(self) -> float:
        return self.rated_capacity_kWh

    @property
    def rated_capacity_unit(self) -> str:
        return "kWh"


class SerialSystemElectric(SerialSystem):
    """
    class for serial system (drive line, DC genset with rectifier) with basic information and
    efficiency interpolation
    """

    def __init__(
        self,
        type_: TypeComponent,
        name: str,
        power_type: TypePower,
        components: list,
        switchboard_id: SwbId,
        rated_power: Power_kW,
        rated_speed: Speed_rpm = Speed_rpm(0),
        uid: Optional[str] = None,
    ):
        super(SerialSystemElectric, self).__init__(
            type_=type_,
            power_type=power_type,
            name=name,
            components=components,
            rated_power=rated_power,
            rated_speed=rated_speed,
            uid=uid,
        )

        #: Set the load sharing mode 0 as default value if the component is either a power source,
        #: PTI/PTO or ESS
        if self.power_type in [
            TypePower.POWER_SOURCE,
            TypePower.PTI_PTO,
            TypePower.ENERGY_STORAGE,
        ]:
            self.load_sharing_mode = np.zeros(1)
        self.switchboard_id = switchboard_id


class FuelCell(BasicComponent):
    def __init__(
        self,
        name: str,
        rated_power: Power_kW,
        eff_curve: np.ndarray,
        fuel_type: TypeFuel = TypeFuel.HYDROGEN,
        fuel_origin: FuelOrigin = FuelOrigin.RENEWABLE_NON_BIO,
        uid: Optional[str] = None,
    ):
        super(FuelCell, self).__init__(
            type_=TypeComponent.FUEL_CELL,
            power_type=TypePower.POWER_SOURCE,
            name=name,
            rated_power=rated_power,
            eff_curve=eff_curve,
            uid=uid,
        )
        self.fuel_type = fuel_type
        self.fuel_origin = fuel_origin

    @property
    def fuel_consumer_type_fuel_eu_maritime(self) -> FuelConsumerClassFuelEUMaritime:
        return FuelConsumerClassFuelEUMaritime.FUEL_CELL

    def get_fuel_cell_run_point(
        self,
        power_out_kw: np.ndarray = None,
        fuel_specified_by=FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] = None,
    ) -> ComponentRunPoint:
        """
        Get the fuel cell run point

        Args:
            power_out_kw (np.ndarray, Optional): power output in kW. If not given, it will take the
                value of power output of the fuel cell.
            fuel_specified_by (FuelSpecifiedBy, Optional): CO2 calculation is calculated based on
                either IMO or FuelEU Maritime. Default is IMO.
            lhv_mj_per_g (float, Optional): lower heating value of the fuel in MJ/kg. It should be
                provided if fuel_specified_by is FuelSpecifiedBy.USER.
            ghg_emission_factor_well_to_tank_gco2eq_per_mj (float, Optional): GHG emission factor
                from well to tank in gCO2eq/MJ. It should be provided if fuel_specified_by is
                FuelSpecifiedBy.USER.
            ghg_emission_factor_tank_to_wake (List[Optional[GhgEmissionFactorTankToWake]], Optional):
                GHG emission factor from tank to wake in gCO2eq/MJ. It should be provided if
                fuel_specified_by is FuelSpecifiedBy.USER.

        Returns:
            ComponentRunPoint: fuel cell run point
        """
        if power_out_kw is None:
            power_out_kw = self.power_output
        power_in_kw, load_ratio = self.get_power_input_from_bidirectional_output(power_out_kw)
        fuel = Fuel(
            fuel_type=self.fuel_type,
            origin=self.fuel_origin,
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
        )
        fuel.mass_or_mass_fraction = power_in_kw / fuel.lhv_mj_per_g / 1e6
        efficiency = self.get_efficiency_from_load_percentage(load_ratio)
        return ComponentRunPoint(
            load_ratio=load_ratio,
            fuel_flow_rate_kg_per_s=FuelConsumption(
                fuels=[
                    fuel,
                ]
            ),
            efficiency=efficiency,
        )


class FuelCellSystem(ElectricComponent):
    """
    Class for serial config for a fuel cell system. It is composed of a fuel cell module
    and a converter
    """

    def __init__(
        self,
        name: str,
        fuel_cell_module: FuelCell,
        converter: ElectricComponent,
        switchboard_id: SwbId,
        number_modules: int = 1,
        uid: Optional[str] = None,
    ):
        super(FuelCellSystem, self).__init__(
            name=name,
            type_=TypeComponent.FUEL_CELL_SYSTEM,
            rated_power=converter.rated_power,
            eff_curve=converter._efficiency_points,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=switchboard_id,
            uid=uid,
        )
        self.converter = converter
        self.fuel_cell = fuel_cell_module
        self.number_modules = number_modules

    @property
    def fuel_consumer_type_fuel_eu_maritime(self) -> FuelConsumerClassFuelEUMaritime:
        return FuelConsumerClassFuelEUMaritime.FUEL_CELL

    def get_fuel_cell_run_point(
        self,
        power_out_kw: np.ndarray = None,
        fuel_specified_by=FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] = None,
    ) -> ComponentRunPoint:
        """
        Get the fuel cell run point

        Args:
            power_out_kw (np.ndarray, Optional): power output in kW. If not given, it will take the
                value of power output of the fuel cell.
            fuel_specified_by (FuelSpecifiedBy, Optional): CO2 calculation is calculated based on
                either IMO or FuelEU Maritime. Default is IMO.
            lhv_mj_per_g (float, Optional): lower heating value of the fuel in MJ/kg. It should be
                provided if fuel_specified_by is FuelSpecifiedBy.USER.
            ghg_emission_factor_well_to_tank_gco2eq_per_mj (float, Optional): GHG emission factor
                from well to tank in gCO2eq/MJ. It should be provided if fuel_specified_by is
                FuelSpecifiedBy.USER.
            ghg_emission_factor_tank_to_wake (List[Optional[GhgEmissionFactorTankToWake]], Optional):
                GHG emission factor from tank to wake in gCO2eq/MJ. It should be provided if
                fuel_specified_by is FuelSpecifiedBy.USER.

        Returns:
            ComponentRunPoint: fuel cell run point
        """
        if power_out_kw is None:
            power_out_kw = self.power_output
        power_out_fuel_cell_kw, load_ratio = self.set_power_input_from_output(power_out_kw)
        result_per_module = self.fuel_cell.get_fuel_cell_run_point(
            power_out_kw=power_out_fuel_cell_kw / self.number_modules,
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
        )
        return ComponentRunPoint(
            load_ratio=result_per_module.load_ratio,
            fuel_flow_rate_kg_per_s=result_per_module.fuel_flow_rate_kg_per_s
            * self.number_modules,
            efficiency=result_per_module.efficiency,
        )


class BatterySystem(Battery):
    """
    Class for serial configuration for a battery system.
    """

    def __init__(
        self,
        name: str,
        battery: Battery,
        converter: ElectricComponent,
        switchboard_id: SwbId,
        uid: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            rated_capacity_kwh=battery.rated_capacity_kWh,
            charging_rate_c=battery.charging_rate_C,
            discharge_rate_c=battery.discharging_rate_C,
            soc0=battery.soc0,
            eff_charging=battery.eff_charging,
            eff_discharging=battery.eff_discharging,
            switchboard_id=switchboard_id,
            uid=uid,
        )
        self.type = TypeComponent.BATTERY_SYSTEM
        self.rated_power = converter.rated_power
        self.converter = converter
        self.battery = battery

    def get_power_input_from_bidirectional_output(
        self, power_output: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        load = self.get_load(power_output)
        battery_power_input, _ = self.battery.get_power_input_from_bidirectional_output(
            power_output=power_output, strict_power_balance=strict_power_balance
        )
        if self.converter is None:
            power_input = battery_power_input
        else:
            power_input, _ = self.converter.get_power_input_from_bidirectional_output(
                battery_power_input, strict_power_balance=strict_power_balance
            )
        return power_input, load

    def get_power_output_from_bidirectional_input(
        self, power_input: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        if self.converter is not None:
            (
                battery_power_input,
                _,
            ) = self.converter.get_power_output_from_bidirectional_input(
                power_input=power_input, strict_power_balance=strict_power_balance
            )
        else:
            battery_power_input = power_input
        power_output, _ = self.battery.get_power_output_from_bidirectional_input(
            power_input=battery_power_input, strict_power_balance=strict_power_balance
        )

        load = self.get_load(power_output)
        return power_output, load


class GensetRunPoint(NamedTuple):
    genset_load_ratio: np.ndarray
    engine: EngineRunPoint


class COGESRunPoint(NamedTuple):
    coges_load_ratio: np.ndarray
    cogas: COGASRunPoint


class Genset(Component):
    """
    Class for serial config for genset. It is composed of an engine, a generator and optionally
    a rectifier in case of DC genset.
    """

    def __init__(
        self,
        name: str,
        aux_engine: Union[Engine, EngineDualFuel, EngineMultiFuel],
        generator: ElectricMachine,
        rectifier: ElectricComponent = None,
        uid: Optional[str] = None,
    ):
        super(Genset, self).__init__(
            name=name,
            type_=TypeComponent.GENSET,
            power_type=TypePower.POWER_SOURCE,
            rated_power=generator.rated_power,
            rated_speed=generator.rated_speed,
            uid=uid,
        )
        self.aux_engine = aux_engine
        self._default_multi_fuel_characteristic: Optional[FuelCharacteristics] = None
        if type(aux_engine) is EngineMultiFuel:
            if len(aux_engine.multi_fuel_characteristics) == 0:
                raise ValueError(
                    "Multi-fuel characteristics must not be empty for EngineMultiFuel genset engine."
                )
            self.fuel_type = aux_engine.fuel_in_use.main_fuel_type
            self.fuel_origin = aux_engine.fuel_in_use.main_fuel_origin
        else:
            self.fuel_type = aux_engine.fuel_type
            self.fuel_origin = aux_engine.fuel_origin
        #: For DC genset, rectifier is included
        if type(rectifier) is ElectricComponent:
            generator_rectifier = SerialSystemElectric(
                name="{:s} with rectifier".format(generator.name),
                type_=TypeComponent.GENERATOR,
                components=[generator, rectifier],
                switchboard_id=generator.switchboard_id,
                power_type=TypePower.POWER_SOURCE,
                rated_power=rectifier.rated_power,
                rated_speed=generator.rated_speed,
            )
            self.generator = ElectricMachine(
                type_=TypeComponent.GENERATOR,
                name=generator_rectifier.name,
                rated_power=generator.rated_power,
                rated_speed=generator.rated_speed,
                power_type=TypePower.POWER_SOURCE,
                switchboard_id=generator.switchboard_id,
                number_poles=generator.number_of_poles,
                eff_curve=generator_rectifier._efficiency_points,
            )
        else:
            self.generator = generator
        self.switchboard_id = generator.switchboard_id
        self.status = np.ones(0).astype(bool)
        self.load_sharing_mode = np.zeros(1)

    @property
    def fuel_consumer_type_fuel_eu_maritime(self) -> FuelConsumerClassFuelEUMaritime:
        return self.aux_engine.fuel_consumer_type_fuel_eu_maritime

    def get_fuel_cons_load_bsfc_from_power_out_generator_kw(
        self,
        power: np.ndarray = None,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] = None,
        fuel_type: Optional[TypeFuel] = None,
        fuel_origin: Optional[FuelOrigin] = None,
    ) -> GensetRunPoint:
        """Calculate fuel consumption, percentage load and bsfc for the shaft power
        before the gearbox. If the power is not given, it will take the value of power output
        of the genset.

        Args:
            power(np.ndarray, Optional): single value or ndarray of power in kW.
                If not given, it will take the value of power output of the genset.
            fuel_specified_by(FuelSpecifiedBy, Optional): CO2 calculation is calculated based on
                either IMO or FuelEU Maritime. Default is IMO.

        Returns:
            Fuel consumption (kg/s), load (%), bsfc (g/kWh), generator load
        """
        if power is not None:
            self.power_output = power
        (
            self.aux_engine.power_output,
            load_ratio_generator,
        ) = self.generator.get_shaft_power_load_from_electric_power(self.power_output)
        if type(self.aux_engine) is EngineMultiFuel:
            self.aux_engine.set_fuel_in_use(fuel_type=fuel_type, fuel_origin=fuel_origin)
            self.fuel_type = self.aux_engine.fuel_in_use.main_fuel_type
            self.fuel_origin = self.aux_engine.fuel_in_use.main_fuel_origin
        else:
            if fuel_type is not None and fuel_type != self.aux_engine.fuel_type:
                raise ValueError(
                    "fuel_type argument does not match the configured genset engine fuel type"
                )
            if fuel_origin is not None and fuel_origin != self.aux_engine.fuel_origin:
                raise ValueError(
                    "fuel_origin argument does not match the configured genset engine fuel origin"
                )
        engine_run_point = self.aux_engine.get_engine_run_point_from_power_out_kw(
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
        )
        return GensetRunPoint(genset_load_ratio=load_ratio_generator, engine=engine_run_point)


class PTIPTO(SerialSystemElectric):
    def __init__(
        self,
        name: str,
        components: list,
        switchboard_id: SwbId,
        rated_power: Power_kW,
        rated_speed: Speed_rpm = Speed_rpm(0),
        shaft_line_id: int = 1,
        uid: Optional[str] = None,
    ):
        super(PTIPTO, self).__init__(
            TypeComponent.PTI_PTO_SYSTEM,
            name,
            TypePower.PTI_PTO,
            components,
            switchboard_id,
            rated_power,
            rated_speed,
            uid=uid,
        )
        self.shaft_line_id = shaft_line_id
        self.full_pti_mode = np.zeros(1).astype(bool)


class SuperCapacitor(ElectricComponent):
    """
    Supercapacitor class

    :param name: Component name
    :param rated_capacity_wh: Rated capacity in Wh
    :param rated_power: Rated power in kW
    :param soc0: State of charge in percentage
    :param eff_charging: Efficiency for charging in percentage
    :param eff_discharging: Efficiency for discharging in percentage
    :param switchboard_id: Switchboard ID
    :param uid: Unique ID
    """

    def __init__(
        self,
        name: str,
        rated_capacity_wh: float,
        rated_power: Power_kW,
        soc0: float = 0.8,
        eff_charging: float = 0.995,
        eff_discharging: float = 0.995,
        switchboard_id: SwbId = SwbId(0),
        uid: Optional[str] = None,
    ):
        super().__init__(
            TypeComponent.SUPERCAPACITOR,
            name,
            rated_power,
            power_type=TypePower.ENERGY_STORAGE,
            switchboard_id=switchboard_id,
            uid=uid,
        )
        self.rated_capacity_Wh = rated_capacity_wh
        self.soc0 = soc0
        self.eff_charging = eff_charging
        self.eff_discharging = eff_discharging

    def get_energy_stored_kj(
        self,
        time_interval_s: TimeIntervalList,
        integration_method: IntegrationMethod,
        accumulated_time_series: bool = False,
    ) -> Union[float, np.ndarray]:
        """Calculate energy stored based on the power input at the terminal"""
        power_stored_in_battery, _ = self.get_power_output_from_bidirectional_input(
            power_input=self.power_input
        )
        if accumulated_time_series:
            return integrate_data_accumulative(
                data_to_integrate=power_stored_in_battery,
                time_interval_s=time_interval_s,
                integration_method=integration_method,
            )
        else:
            return integrate_data(
                data_to_integrate=power_stored_in_battery,
                time_interval_s=time_interval_s,
                integration_method=integration_method,
            )

    def get_soc(
        self,
        time_interval_s: TimeIntervalList,
        integration_method: IntegrationMethod,
        accumulated_time_series: bool = False,
    ) -> Union[float, np.ndarray]:
        """
        Calculates the SoC based on the power input at the terminal. The power input of the
        battery should have been set.

        :param time_interval_s: time interval for the power_input series
        :param integration_method: 'simpson' or 'trapezoid'. 'simpson' is default value.
        :param accumulated_time_series: function returns accumulated time-series if the
            value is true
        :return: SoC as series
        """
        energy_stored_kj = self.get_energy_stored_kj(
            time_interval_s=time_interval_s,
            integration_method=integration_method,
            accumulated_time_series=accumulated_time_series,
        )

        #: Calculate soc
        return energy_stored_kj / 3.6 / self.rated_capacity_Wh + self.soc0

    def get_power_input_from_bidirectional_output(
        self, power_output: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        load = self.get_load(power_output)
        if type(power_output) is not np.ndarray:
            if power_output >= 0:
                return power_output / self.eff_charging, load
            else:
                return power_output * self.eff_discharging, load
        else:
            idx_charging = power_output > 0
            idx_discharging = power_output < 0
            power_input = power_output.copy()
            power_input[idx_charging] = power_output[idx_charging] / self.eff_charging
            power_input[idx_discharging] = power_output[idx_discharging] * self.eff_discharging
            return power_input, load

    def get_power_output_from_bidirectional_input(
        self, power_input: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        if type(power_input) is not np.ndarray:
            if power_input > 0:
                power_output = power_input * self.eff_charging
            else:
                power_output = power_input / self.eff_discharging
        else:
            idx_charging = power_input > 0
            idx_discharging = power_input < 0
            power_output = power_input.copy()
            power_output[idx_charging] = power_output[idx_charging] * self.eff_charging
            power_output[idx_discharging] = power_output[idx_discharging] / self.eff_discharging
        load = self.get_load(power_output)
        return power_output, load

    @property
    def rated_capacity(self) -> float:
        return self.rated_capacity_Wh

    @property
    def rated_capacity_unit(self) -> str:
        return "Wh"


class SuperCapacitorSystem(SuperCapacitor):
    """
    Class for serial configuration for a SuperCapacitor system.
    """

    def __init__(
        self,
        name: str,
        supercapacitor: SuperCapacitor,
        converter: ElectricComponent,
        switchboard_id: SwbId,
        uid: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            rated_capacity_wh=supercapacitor.rated_capacity_Wh,
            rated_power=supercapacitor.rated_power,
            soc0=supercapacitor.soc0,
            eff_charging=supercapacitor.eff_charging,
            eff_discharging=supercapacitor.eff_discharging,
            switchboard_id=switchboard_id,
            uid=uid,
        )
        self.converter = converter
        self.supercapacitor = supercapacitor

    def get_power_input_from_bidirectional_output(
        self, power_output: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        load = self.get_load(power_output)
        (
            supercap_power_input,
            _,
        ) = self.supercapacitor.get_power_input_from_bidirectional_output(
            power_output=power_output, strict_power_balance=strict_power_balance
        )
        if self.converter is None:
            power_input = supercap_power_input
        else:
            power_input, _ = self.converter.get_power_input_from_bidirectional_output(
                supercap_power_input, strict_power_balance=strict_power_balance
            )
        return power_input, load

    def get_power_output_from_bidirectional_input(
        self, power_input: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        if self.converter is not None:
            (
                supercap_power_input,
                _,
            ) = self.converter.get_power_output_from_bidirectional_input(
                power_input=power_input, strict_power_balance=strict_power_balance
            )
        else:
            supercap_power_input = power_input
        power_output, _ = self.supercapacitor.get_power_output_from_bidirectional_input(
            power_input=supercap_power_input, strict_power_balance=strict_power_balance
        )

        load = self.get_load(power_output)
        return power_output, load


class ShorePowerConnection(ElectricComponent):
    """
    Shore power connection class

    :param name: Component name
    :param rated_power: Rated power in kW
    :param switchboard_id: Switchboard ID
    """

    def __init__(
        self,
        name: str,
        rated_power: Power_kW,
        switchboard_id: SwbId = SwbId(0),
        uid: Optional[str] = None,
    ):
        super().__init__(
            TypeComponent.SHORE_POWER,
            name,
            rated_power,
            power_type=TypePower.POWER_SOURCE,
            switchboard_id=switchboard_id,
            uid=uid,
        )


class ShorePowerConnectionSystem(ShorePowerConnection):
    """
    Shore power connection class

    :param name: Component name
    :param shore_power_connection: shore power connection instance (ShorePowerConnection)
    :param converter: converter instance (ElectricComponent)
    :param switchboard_id: Switchboard ID
    """

    def __init__(
        self,
        name: str,
        shore_power_connection: ShorePowerConnection,
        converter: ElectricComponent,
        switchboard_id: SwbId = SwbId(0),
    ):
        super().__init__(
            name=name,
            rated_power=shore_power_connection.rated_power,
            switchboard_id=switchboard_id,
        )
        self.shore_power_connection = shore_power_connection
        self.converter = converter


class COGES(Component):
    """
    Class for serial configuration for a COGES system.
    """

    def __init__(
        self,
        name: str,
        cogas: COGAS,
        generator: ElectricMachine,
        uid: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            type_=TypeComponent.COGES,
            power_type=TypePower.POWER_SOURCE,
            rated_power=generator.rated_power,
            rated_speed=generator.rated_speed,
            uid=uid,
        )
        self.fuel_type = cogas.fuel_type
        self.cogas = cogas
        self.generator = generator
        self.switchboard_id = generator.switchboard_id
        self.status = np.ones(0).astype(bool)
        self.load_sharing_mode = np.zeros(1)

    def get_system_run_point_from_power_output_kw(
        self,
        power_output_kw: np.ndarray = None,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] = None,
    ) -> COGESRunPoint:
        """
        Get the run point of the COGES system based on the power output of the system

        Args:
            power_output_kw (np.ndarray): power output of the COGES system in kW or None. If None,
                it will take the value of power output of the COGES system.

        Returns:
            ComponentRunPoint: run point of the COGES system
        """
        if power_output_kw is None:
            power_output_kw = self.power_output

        self.cogas.power_output, load_generator = self.generator.set_power_input_from_output(
            power_output_kw
        )
        cogas_run_point = self.cogas.get_gas_turbine_run_point_from_power_output_kw(
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
        )
        return COGESRunPoint(
            coges_load_ratio=load_generator,
            cogas=cogas_run_point,
        )


MechanicalComponent = Union[
    MainEngineForMechanicalPropulsion,
    MainEngineWithGearBoxForMechanicalPropulsion,
    PTIPTO,
    MechanicalPropulsionComponent,
    COGAS,
]

PowerSystemComponent = Union[
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
    FuelCellSystem,
    ShorePowerConnection,
    ShorePowerConnectionSystem,
]

EnergyStorageComponent = Union[Battery, BatterySystem, SuperCapacitor, SuperCapacitorSystem]
