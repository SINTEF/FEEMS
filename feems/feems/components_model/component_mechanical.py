from dataclasses import dataclass
from typing import Union, NamedTuple, List, Dict, TypeVar, Callable, Optional

import numpy as np
import pandas as pd

from .component_base import Component, BasicComponent
from .. import get_logger
from ..constant import (
    nox_tier_slow_speed_max_rpm,
    nox_factor_imo_medium_speed_g_hWh,
    nox_factor_imo_slow_speed_g_kWh,
)
from ..fuel import (
    FuelByMassFraction,
    FuelConsumption,
    FuelConsumerClassFuelEUMaritime,
    FuelSpecifiedBy,
    Fuel,
    FuelOrigin,
    GhgEmissionFactorTankToWake,
    TypeFuel,
)
from ..types_for_feems import (
    TypeComponent,
    TypePower,
    Speed_rpm,
    Power_kW,
    NOxCalculationMethod,
    EmissionType,
    EmissionCurve,
    EngineCycleType,
)
from .utility import (
    get_efficiency_curve_from_dataframe,
    get_efficiency_curve_from_points,
    get_emission_curve_from_points,
)


logger = get_logger(__name__)


@dataclass
class EngineRunPoint:
    load_ratio: np.ndarray
    fuel_flow_rate_kg_per_s: FuelConsumption
    bsfc_g_per_kWh: np.ndarray
    emissions_g_per_s: Dict[EmissionType, np.ndarray]
    bpsfc_g_per_kWh: np.ndarray = None


T = TypeVar("T", float, np.ndarray)


class Engine(Component):
    """
    Engine class for basic information and fuel consumption interpolation
    """

    def __init__(
        self,
        *,
        type_: TypeComponent,
        nox_calculation_method: NOxCalculationMethod = NOxCalculationMethod.TIER_2,
        name: str = "",
        rated_power: Power_kW = Power_kW(0.0),
        rated_speed: Speed_rpm = Speed_rpm(0.0),
        bsfc_curve: np.ndarray = None,
        fuel_type: TypeFuel = TypeFuel.DIESEL,
        fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
        file_name: str = None,
        emissions_curves: List[EmissionCurve] = None,
        engine_cycle_type: EngineCycleType = EngineCycleType.DIESEL,
    ):
        super(Engine, self).__init__(
            name=name,
            type_=type_,
            power_type=TypePower.POWER_SOURCE,
            rated_power=rated_power,
            rated_speed=rated_speed,
        )
        self.fuel_type = fuel_type
        self.fuel_origin = fuel_origin
        self.engine_cycle_type = engine_cycle_type
        self._setup_bsfc(bsfc_curve, file_name)
        self._setup_emissions(emissions_curves)
        self._setup_nox(nox_calculation_method, rated_speed)

    def _setup_emissions(self, emissions_curves) -> None:
        self.emission_curves = emissions_curves
        self._emissions_per_kwh_interp: Dict[EmissionType, Callable[[T], T]] = {}
        if emissions_curves is not None:
            e: EmissionCurve
            for e in emissions_curves:
                if len(e.points_per_kwh) > 0:
                    self._emissions_per_kwh_interp[e.emission] = get_emission_curve_from_points(
                        e.points_per_kwh
                    )

    def _setup_bsfc(self, bsfc_curve, file_name) -> None:
        if file_name is not None:
            df = pd.read_csv(file_name, index_col=0)
            self.rated_power = df["Rated Power"].values[0]
            self.rated_speed = df["Rated Speed"].values[0]
            (
                self.specific_fuel_consumption_interp,
                self.specific_fuel_consumption_points,
            ) = get_efficiency_curve_from_dataframe(df, "BSFC")
            self.name = df.index[0]
        else:
            (
                self.specific_fuel_consumption_interp,
                self.specific_fuel_consumption_points,
            ) = get_efficiency_curve_from_points(bsfc_curve)

    @property
    def fuel_consumer_type_fuel_eu_maritime(self) -> FuelConsumerClassFuelEUMaritime:
        if self.fuel_type != TypeFuel.NATURAL_GAS:
            return FuelConsumerClassFuelEUMaritime.ICE
        if self.engine_cycle_type == EngineCycleType.DIESEL:
            return FuelConsumerClassFuelEUMaritime.LNG_DIESEL
        elif self.engine_cycle_type == EngineCycleType.OTTO:
            if self.rated_speed < 200:
                return FuelConsumerClassFuelEUMaritime.LNG_OTTO_SLOW_SPEED
            else:
                return FuelConsumerClassFuelEUMaritime.LNG_OTTO_MEDIUM_SPEED
        elif self.engine_cycle_type == EngineCycleType.LEAN_BURN_SPARK_IGNITION:
            return FuelConsumerClassFuelEUMaritime.LNG_LBSI
        else:
            raise ValueError(f"Invalid engine cycle type {self.engine_cycle_type} for LNG engine")

    def emissions_g_per_kwh(self, emission_type: EmissionType, load_ratio: T) -> Optional[T]:
        if emission_type in self._emissions_per_kwh_interp:
            return self._emissions_per_kwh_interp[emission_type](load_ratio)
        else:
            return None

    def _setup_nox(
        self, nox_calculation_method: NOxCalculationMethod, rated_speed: Speed_rpm
    ) -> None:
        self.nox_calculation_method = nox_calculation_method
        if nox_calculation_method == NOxCalculationMethod.CURVE:
            assert EmissionType.NOX in self._emissions_per_kwh_interp
            return

        if rated_speed > nox_tier_slow_speed_max_rpm:
            tier_class = nox_calculation_method.value
            factor = nox_factor_imo_medium_speed_g_hWh[tier_class][0]
            exponent = nox_factor_imo_medium_speed_g_hWh[tier_class][1]
            nox_g_per_kwh = factor * np.power(self.rated_speed, exponent)
            curve = lambda x: nox_g_per_kwh
        else:
            tier_class = nox_calculation_method.value
            nox_factor_g_kwh = nox_factor_imo_slow_speed_g_kWh[tier_class]
            curve = lambda x: nox_factor_g_kwh
        self._emissions_per_kwh_interp[EmissionType.NOX] = curve

    def get_engine_run_point_from_power_out_kw(
        self,
        power_kw: np.ndarray = None,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] = None,
    ) -> EngineRunPoint:
        """
        Calculate fuel consumption, percentage load and bsfc. If power value is not given, it will
        use the power_output value of the instance.
        Args:
            power_kw (np.ndarray, Optional): single value or ndarray of power in kW. If not given,
                the power_output value of the instance will be used.
            fuel_specified_by (FuelSpecifiedBy, Optional): Fuel specification.
                Defaults to FuelSpecifiedBy.IMO.
            lhv_mj_per_g (Optional[float], optional): Lower heating value of the fuel in MJ/kg.
                Defaults to None. Should be provided if fuel_specified_by is FuelSpecifiedBy.USER.
            ghg_emission_factor_well_to_tank_gco2eq_per_mj (Optional[float], optional): GHG emission
                factor from well to tank in gCO2eq/MJ. Defaults to None. Should be provided if
                fuel_specified_by is FuelSpecifiedBy.USER.
            ghg_emission_factor_tank_to_wake (List[Optional[GhgEmissionFactorTankToWake]], optional):
                GHG emission factor from tank to wake. Defaults to None. Should be provided if
                fuel_specified_by is FuelSpecifiedBy.USER.

        Returns:
            EngineRunPoint
        """
        if power_kw is None:
            power_kw = self.power_output
        load_ratio = self.get_load(power_kw)
        bsfc_g_per_kwh = self.specific_fuel_consumption_interp(load_ratio)
        power_kwh_per_s = power_kw / 3600
        fuel_cons_kg_per_s = bsfc_g_per_kwh * power_kwh_per_s / 1000
        emissions_per_s = {}
        for e in self._emissions_per_kwh_interp:
            emissions_per_s[e] = (
                self.emissions_g_per_kwh(emission_type=e, load_ratio=load_ratio) * power_kwh_per_s
            )
        fuel_consumption_component = Fuel(
            fuel_type=self.fuel_type,
            origin=self.fuel_origin,
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
            mass_or_mass_fraction=fuel_cons_kg_per_s,
        )
        return EngineRunPoint(
            load_ratio=load_ratio,
            fuel_flow_rate_kg_per_s=FuelConsumption(fuels=[fuel_consumption_component]),
            bsfc_g_per_kWh=bsfc_g_per_kwh,
            emissions_g_per_s=emissions_per_s,
        )


class EngineDualFuel(Engine):
    bspfc_curve: np.ndarray = None  # Brake specific pilot fuel consumption curve
    pilot_fuel_type: TypeFuel = TypeFuel.DIESEL  # Pilot fuel type

    def __init__(
        self,
        *,
        type_: TypeComponent,
        nox_calculation_method: NOxCalculationMethod = NOxCalculationMethod.TIER_3,
        name: str = "",
        rated_power: Power_kW = Power_kW(0.0),
        rated_speed: Speed_rpm = Speed_rpm(0.0),
        bsfc_curve: np.ndarray = None,
        fuel_type: TypeFuel = TypeFuel.NATURAL_GAS,
        fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
        bspfc_curve: np.ndarray = None,
        pilot_fuel_type: TypeFuel.DIESEL,
        pilot_fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
        emissions_curves: List[EmissionCurve] = None,
    ):
        super().__init__(
            type_=type_,
            nox_calculation_method=nox_calculation_method,
            name=name,
            rated_power=rated_power,
            rated_speed=rated_speed,
            bsfc_curve=bsfc_curve,
            fuel_type=fuel_type,
            fuel_origin=fuel_origin,
            emissions_curves=emissions_curves,
        )
        self.bspfc_curve = bspfc_curve
        self.pilot_fuel_type = pilot_fuel_type
        self.pilot_fuel_origin = pilot_fuel_origin
        (
            self.specific_pilot_fuel_consumption_interp,
            self.specific_pilot_fuel_consumption_points,
        ) = get_efficiency_curve_from_points(bspfc_curve)

    def get_engine_run_point_from_power_out_kw(
        self,
        power_kw: np.ndarray = None,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] = None,
    ) -> EngineRunPoint:
        """
        Calculate fuel consumption, percentage load and bsfc. If power value is not given, it will
        use the power_output value of the instance.
        Args:
            power_kw (np.ndarray, Optional): single value or ndarray of power in kW. If not given,
                the power_output value of the instance will be used.
            fuel_specified_by (FuelSpecifiedBy, Optional): Fuel specification.
                Defaults to FuelSpecifiedBy.IMO.
            lhv_mj_per_g (Optional[float], optional): Lower heating value of the fuel in MJ/kg.
                Defaults to None. Should be provided if fuel_specified_by is FuelSpecifiedBy.USER.
            ghg_emission_factor_well_to_tank_gco2eq_per_mj (Optional[float], optional): GHG emission
                factor from well to tank in gCO2eq/MJ. Defaults to None. Should be provided if
                fuel_specified_by is FuelSpecifiedBy.USER.
            ghg_emission_factor_tank_to_wake (List[Optional[GhgEmissionFactorTankToWake]], optional):
                GHG emission factor from tank to wake. Defaults to None. Should be provided if
                fuel_specified_by is FuelSpecifiedBy.USER.

        Returns:
            EngineRunPoint
        """
        if power_kw is None:
            power_kw = self.power_output
        engine_run_point = super().get_engine_run_point_from_power_out_kw(
            power_kw=power_kw,
            fuel_specified_by=fuel_specified_by,
        )
        bpsfc = self.specific_pilot_fuel_consumption_interp(engine_run_point.load_ratio)
        pilot_fuel_cons_kg_per_s = bpsfc * power_kw / 1000 / 3600
        engine_run_point.fuel_flow_rate_kg_per_s.fuels.append(
            Fuel(
                fuel_type=self.pilot_fuel_type,
                origin=self.pilot_fuel_origin,
                fuel_specified_by=fuel_specified_by,
                lhv_mj_per_g=lhv_mj_per_g,
                ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
                ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
                mass_or_mass_fraction=pilot_fuel_cons_kg_per_s,
            )
        )
        engine_run_point.bpsfc_g_per_kWh = bpsfc
        return engine_run_point


class MainEngineForMechanicalPropulsion(Component):
    """
    Main engine component class used for mechanical/hybrid propulsion
    """

    def __init__(
        self,
        name,
        engine: Union[Engine, EngineDualFuel],
        shaft_line_id: int = 1,
    ):
        super().__init__(
            name=name,
            power_type=TypePower.POWER_SOURCE,
            type_=TypeComponent.MAIN_ENGINE,
            rated_power=engine.rated_power,
            rated_speed=engine.rated_speed,
        )
        self.engine = engine
        self.shaft_line_id = shaft_line_id

    @property
    def fuel_consumer_type_fuel_eu_maritime(self) -> FuelConsumerClassFuelEUMaritime:
        return self.engine.fuel_consumer_type_fuel_eu_maritime

    def get_engine_run_point_from_power_out_kw(
        self,
        power: np.ndarray = None,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] = None,
    ) -> EngineRunPoint:
        """
        Calculate fuel consumption, percentage load and bsfc for the shaft power before the gearbox

        Args:
            power (np.ndarray, optional): single value or ndarray of power in kW. If not given,
                the power_output value of the instance will be used.
            fuel_specified_by (FuelSpecifiedBy, Optional): Fuel specification.
                Defaults to FuelSpecifiedBy.IMO.
            lhv_mj_per_g (Optional[float], optional): Lower heating value of the fuel in MJ/kg.
                Defaults to None. Should be provided if fuel_specified_by is FuelSpecifiedBy.USER.
            ghg_emission_factor_well_to_tank_gco2eq_per_mj (Optional[float], optional): GHG emission
                factor from well to tank in gCO2eq/MJ. Defaults to None. Should be provided if
                fuel_specified_by is FuelSpecifiedBy.USER.
            ghg_emission_factor_tank_to_wake (List[Optional[GhgEmissionFactorTankToWake]], optional):
                GHG emission factor from tank to wake. Defaults to None. Should be provided if
                fuel_specified_by is FuelSpecifiedBy.USER.

        Returns:
            EngineRunPoint
        """
        if power is None:
            power = self.power_output
        self.engine.power_output = power
        return self.engine.get_engine_run_point_from_power_out_kw(
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
        )


class MechanicalPropulsionComponent(BasicComponent):
    """
    Mechanical propulsion component class for basic information and efficiency interpolation
    """

    def __init__(
        self,
        type_: TypeComponent,
        power_type: TypePower,
        name: str = "",
        rated_power: Power_kW = Power_kW(0),
        eff_curve: np.ndarray = np.array([1]),
        rated_speed: Speed_rpm = Speed_rpm(0),
        shaft_line_id: int = 1,
        file_name: str = None,
    ):
        super(MechanicalPropulsionComponent, self).__init__(
            type_, power_type, name, rated_power, eff_curve, rated_speed, file_name
        )
        self.shaft_line_id = shaft_line_id


class MainEngineWithGearBoxForMechanicalPropulsion(MainEngineForMechanicalPropulsion):
    def __init__(
        self,
        name: str,
        engine: Union[Engine, EngineDualFuel],
        gearbox: BasicComponent,
        shaft_line_id: int = 1,
    ):
        super(MainEngineWithGearBoxForMechanicalPropulsion, self).__init__(
            name=name,
            engine=engine,
            shaft_line_id=shaft_line_id,
        )
        self.gearbox = gearbox

    def get_engine_run_point_from_power_out_kw(
        self,
        power: np.ndarray = None,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] = None,
    ) -> EngineRunPoint:
        """
        Calculate fuel consumption, percentage load and bsfc for the shaft power before the gearbox

        Args:
            power (np.ndarray, optional): single value or ndarray of power in kW. If not given,
                the power_output value of the instance will be used.
            fuel_specified_by (FuelSpecifiedBy, Optional): Fuel specification.
                Defaults to FuelSpecifiedBy.IMO.
            lhv_mj_per_g (Optional[float], optional): Lower heating value of the fuel in MJ/kg.
                Defaults to None. Should be provided if fuel_specified_by is FuelSpecifiedBy.USER.
            ghg_emission_factor_well_to_tank_gco2eq_per_mj (Optional[float], optional): GHG emission
                factor from well to tank in gCO2eq/MJ. Defaults to None. Should be provided if
                fuel_specified_by is FuelSpecifiedBy.USER.
            ghg_emission_factor_tank_to_wake (List[Optional[GhgEmissionFactorTankToWake]], optional):
                GHG emission factor from tank to wake. Defaults to None. Should be provided if
                fuel_specified_by is FuelSpecifiedBy.USER.

        Returns:
            EngineRunPoint
        """
        if power is None:
            power = self.power_output
        load_ratio = self.get_load(power)
        eff_gearbox = self.gearbox.get_efficiency_from_load_percentage(load_ratio)
        self.engine.power_output = power / eff_gearbox
        return self.engine.get_engine_run_point_from_power_out_kw(
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
        )


MechanicalComponent = Union[
    MainEngineForMechanicalPropulsion,
    MainEngineWithGearBoxForMechanicalPropulsion,
    MechanicalPropulsionComponent,
]
