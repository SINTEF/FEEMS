from dataclasses import dataclass
from typing import Union, NamedTuple, List, Dict, TypeVar, Callable, Optional

import numpy as np
import pandas as pd

from .component_base import Component, BasicComponent, ComponentRunPoint
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
    bspfc_g_per_kWh: np.ndarray = None


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
        uid: Optional[str] = None,
    ):
        super(Engine, self).__init__(
            name=name,
            type_=type_,
            power_type=TypePower.POWER_SOURCE,
            rated_power=rated_power,
            rated_speed=rated_speed,
            uid=uid,
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
        uid: Optional[str] = None,
        engine_cycle_type: EngineCycleType = EngineCycleType.DIESEL,
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
            uid=uid,
            engine_cycle_type=engine_cycle_type,
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
        bspfc = self.specific_pilot_fuel_consumption_interp(engine_run_point.load_ratio)
        pilot_fuel_cons_kg_per_s = bspfc * power_kw / 1000 / 3600
        engine_run_point.fuel_flow_rate_kg_per_s += FuelConsumption(
            fuels=[
                Fuel(
                    fuel_type=self.pilot_fuel_type,
                    origin=self.pilot_fuel_origin,
                    fuel_specified_by=fuel_specified_by,
                    lhv_mj_per_g=lhv_mj_per_g,
                    ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
                    ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
                    mass_or_mass_fraction=pilot_fuel_cons_kg_per_s,
                )
            ]
        )
        engine_run_point.bspfc_g_per_kWh = bspfc
        return engine_run_point


@dataclass
class FuelCharacteristics:
    """
    Class for specific fuel consumption
    """

    nox_calculation_method: NOxCalculationMethod = NOxCalculationMethod.TIER_2
    main_fuel_type: TypeFuel = TypeFuel.DIESEL
    main_fuel_origin: FuelOrigin = FuelOrigin.FOSSIL
    pilot_fuel_type: TypeFuel = None
    pilot_fuel_origin: FuelOrigin = None
    bsfc_curve: np.ndarray = None
    bspfc_curve: np.ndarray = None
    emission_curves: List[EmissionCurve] = None
    engine_cycle_type: EngineCycleType = EngineCycleType.DIESEL


class EngineMultiFuel(Engine):
    """
    Engine class for multi-fuel engines
    """

    def __init__(
        self,
        *,
        type_: TypeComponent,
        name: str = "",
        rated_power: Power_kW = Power_kW(0.0),
        rated_speed: Speed_rpm = Speed_rpm(0.0),
        multi_fuel_characteristics: List[FuelCharacteristics] = None,
        uid: Optional[str] = None,
    ):
        self.type = type_
        self.name = name
        self.rated_power = rated_power
        self.rated_speed = rated_speed
        self.multi_fuel_characteristics = multi_fuel_characteristics
        if self.multi_fuel_characteristics is None:
            raise ValueError("Multi-fuel characteristics must be provided for EngineMultiFuel.")
        if len(self.multi_fuel_characteristics) == 0:
            raise ValueError("Multi-fuel characteristics must not be empty for EngineMultiFuel.")
        self.set_fuel_in_use()
        self.uid = uid

    def set_fuel_in_use(self, fuel_type: TypeFuel = None, fuel_origin: FuelOrigin = None) -> None:
        """
        Set the fuel characteristics in use based on the fuel type and origin. If not provided,
        it will use the first fuel characteristics in the list.
        Args:
            fuel_type (TypeFuel): Fuel type. Optional. Defaults to None, which means the first fuel type in the list.
            fuel_origin (FuelOrigin): Fuel origin. Optional. Defaults to None, which means the first fuel origin in the list.
        """
        if fuel_type is None or fuel_origin is None:
            self.fuel_in_use = self.multi_fuel_characteristics[0]
            return
        fuel_characteristics = next(
            (
                fc
                for fc in self.multi_fuel_characteristics
                if fc.main_fuel_type == fuel_type and fc.main_fuel_origin == fuel_origin
            ),
            None,
        )
        if fuel_characteristics is None:
            raise ValueError(
                f"Fuel characteristics for fuel type {fuel_type} and origin {fuel_origin} not found."
            )
        self.fuel_in_use = fuel_characteristics

    @property
    def engine_in_use(self) -> Engine:
        """
        Get the engine object based on the fuel characteristics in use.
        """
        if self.fuel_in_use.pilot_fuel_type is not None:
            return EngineDualFuel(
                type_=self.type,
                name=self.name,
                rated_power=self.rated_power,
                rated_speed=self.rated_speed,
                bsfc_curve=self.fuel_in_use.bsfc_curve,
                fuel_type=self.fuel_in_use.main_fuel_type,
                fuel_origin=self.fuel_in_use.main_fuel_origin,
                bspfc_curve=self.fuel_in_use.bspfc_curve,
                pilot_fuel_type=self.fuel_in_use.pilot_fuel_type,
                pilot_fuel_origin=self.fuel_in_use.pilot_fuel_origin,
                emissions_curves=self.fuel_in_use.emission_curves,
                engine_cycle_type=self.fuel_in_use.engine_cycle_type,
            )
        return Engine(
            type_=self.type,
            name=self.name,
            rated_power=self.rated_power,
            rated_speed=self.rated_speed,
            bsfc_curve=self.fuel_in_use.bsfc_curve,
            fuel_type=self.fuel_in_use.main_fuel_type,
            fuel_origin=self.fuel_in_use.main_fuel_origin,
            emissions_curves=self.fuel_in_use.emission_curves,
            engine_cycle_type=self.fuel_in_use.engine_cycle_type,
        )

    @property
    def fuel_consumer_type_fuel_eu_maritime(self) -> FuelConsumerClassFuelEUMaritime:
        return self.engine_in_use.fuel_consumer_type_fuel_eu_maritime

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
            fuel_type (TypeFuel, Optional): Fuel type. Defaults to TypeFuel.DIESEL.
            fuel_origin (FuelOrigin, Optional): Fuel origin. Defaults to FuelOrigin.FOSSIL.
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
        return self.engine_in_use.get_engine_run_point_from_power_out_kw(
            power_kw=power_kw,
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
        )

    def get_engine_object(
        self,
        fuel_type: TypeFuel,
        fuel_origin: FuelOrigin,
    ) -> Union[Engine, EngineDualFuel]:
        """
        Get the engine object based on the fuel type and origin.
        Args:
            fuel_type (TypeFuel): Fuel type.
            fuel_origin (FuelOrigin): Fuel origin.

        Returns:
            Union[Engine, EngineDualFuel]: Engine object.
        """
        fuel_characteristics = next(
            (
                fc
                for fc in self.multi_fuel_characteristics
                if fc.main_fuel_type == fuel_type and fc.main_fuel_origin == fuel_origin
            ),
            None,
        )
        if fuel_characteristics is None:
            raise ValueError(
                f"Fuel characteristics for fuel type {fuel_type} and origin {fuel_origin} not found."
            )


class MainEngineForMechanicalPropulsion(Component):
    """
    Main engine component class used for mechanical/hybrid propulsion
    """

    def __init__(
        self,
        name,
        engine: Union[Engine, EngineDualFuel, EngineMultiFuel],
        shaft_line_id: int = 1,
        uid: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            power_type=TypePower.POWER_SOURCE,
            type_=TypeComponent.MAIN_ENGINE,
            rated_power=engine.rated_power,
            rated_speed=engine.rated_speed,
            uid=uid,
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
        fuel_type: Optional[TypeFuel] = None,
        fuel_origin: Optional[FuelOrigin] = None,
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
            fuel_type (Optional[TypeFuel], optional): Desired main fuel type when the engine is a
                multi-fuel engine. Defaults to the first entry in multi-fuel characteristics.
            fuel_origin (Optional[FuelOrigin], optional): Desired main fuel origin when the engine
                is a multi-fuel engine. Defaults to the first entry in multi-fuel characteristics.

        Returns:
            EngineRunPoint
        """
        if power is None:
            power = self.power_output
        self.engine.power_output = power
        if type(self.engine) is EngineMultiFuel:
            self.engine.set_fuel_in_use(fuel_type=fuel_type, fuel_origin=fuel_origin)
        else:
            if fuel_type is not None and fuel_type != self.engine.fuel_type:
                raise ValueError(
                    "fuel_type argument does not match the configured engine fuel type"
                )
            if fuel_origin is not None and fuel_origin != self.engine.fuel_origin:
                raise ValueError(
                    "fuel_origin argument does not match the configured engine fuel origin"
                )
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
        uid: Optional[str] = None,
    ):
        super(MechanicalPropulsionComponent, self).__init__(
            type_=type_,
            power_type=power_type,
            name=name,
            rated_power=rated_power,
            eff_curve=eff_curve,
            rated_speed=rated_speed,
            file_name=file_name,
            uid=uid,
        )
        self.shaft_line_id = shaft_line_id


class MainEngineWithGearBoxForMechanicalPropulsion(MainEngineForMechanicalPropulsion):
    def __init__(
        self,
        name: str,
        engine: Union[Engine, EngineDualFuel, EngineMultiFuel],
        gearbox: BasicComponent,
        shaft_line_id: int = 1,
        uid: Optional[str] = None,
    ):
        super(MainEngineWithGearBoxForMechanicalPropulsion, self).__init__(
            name=name,
            engine=engine,
            shaft_line_id=shaft_line_id,
            uid=uid,
        )
        self.gearbox = gearbox

    def get_engine_run_point_from_power_out_kw(
        self,
        power: np.ndarray = None,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] = None,
        fuel_type: Optional[TypeFuel] = None,
        fuel_origin: Optional[FuelOrigin] = None,
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
            fuel_type (Optional[TypeFuel], optional): Desired main fuel type when the engine is a
                multi-fuel engine. Defaults to the first entry in multi-fuel characteristics.
            fuel_origin (Optional[FuelOrigin], optional): Desired main fuel origin when the engine
                is a multi-fuel engine. Defaults to the first entry in multi-fuel characteristics.

        Returns:
            EngineRunPoint
        """
        if power is None:
            power = self.power_output
        load_ratio = self.get_load(power)
        eff_gearbox = self.gearbox.get_efficiency_from_load_percentage(load_ratio)
        self.engine.power_output = power / eff_gearbox
        if type(self.engine) is EngineMultiFuel:
            self.engine.set_fuel_in_use(fuel_type=fuel_type, fuel_origin=fuel_origin)
        else:
            if fuel_type is not None and fuel_type != self.engine.fuel_type:
                raise ValueError(
                    "fuel_type argument does not match the configured engine fuel type"
                )
            if fuel_origin is not None and fuel_origin != self.engine.fuel_origin:
                raise ValueError(
                    "fuel_origin argument does not match the configured engine fuel origin"
                )
        return self.engine.get_engine_run_point_from_power_out_kw(
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
        )


@dataclass(kw_only=True)
class COGASRunPoint(ComponentRunPoint):
    gas_turbine_power_kw: np.ndarray = None
    steam_turbine_power_kw: np.ndarray = None


class COGAS(BasicComponent):
    """Combined gas and steam component class for basic information and efficiency interpolation"""

    def __init__(
        self,
        name: str = "",
        rated_power: Power_kW = Power_kW(0),
        eff_curve: np.ndarray = np.array([1]),
        rated_speed: Speed_rpm = Speed_rpm(0),
        gas_turbine_power_curve: np.ndarray = None,
        steam_turbine_power_curve: np.ndarray = None,
        fuel_type: TypeFuel = TypeFuel.DIESEL,
        fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
        emissions_curves: List[EmissionCurve] = None,
        nox_calculation_method: NOxCalculationMethod = NOxCalculationMethod.TIER_3,
        uid: Optional[str] = None,
    ):
        """Constructor for COGES component"""
        # Validate the inputs for curves. The length of the curves should be the same and the x values should be the same.
        if gas_turbine_power_curve is not None and steam_turbine_power_curve is not None:
            if gas_turbine_power_curve.shape != steam_turbine_power_curve.shape:
                raise ValueError(
                    "The length of the gas turbine power curve and steam turbine power curve should be the same."
                )
            if np.all(gas_turbine_power_curve[:, 0] != steam_turbine_power_curve[:, 0]):
                raise ValueError(
                    "The x values of the gas turbine power curve and steam turbine power curve should be the same."
                )
            if gas_turbine_power_curve.shape[1] != 2:
                raise ValueError(
                    "The gas turbine power curve and steam turbine power curve should have two columns."
                )

        super().__init__(
            type_=TypeComponent.COGAS,
            power_type=TypePower.POWER_SOURCE,
            name=name,
            rated_power=rated_power,
            eff_curve=eff_curve,
            rated_speed=rated_speed,
            uid=uid,
        )
        self.gas_turbine_power_curve = gas_turbine_power_curve
        self.steam_turbine_power_curve = steam_turbine_power_curve
        if self.gas_turbine_power_curve is not None and self.steam_turbine_power_curve is not None:
            self.total_power_curve = self.gas_turbine_power_curve.copy()
            self.total_power_curve[:, 1] += self.steam_turbine_power_curve[:, 1]
            self.power_ratio_gas_turbine_points = gas_turbine_power_curve.copy()
            self.power_ratio_gas_turbine_points[:, 1] /= self.total_power_curve[:, 1]
            self.power_ratio_gas_turbine_interpolator, _ = get_efficiency_curve_from_points(
                self.power_ratio_gas_turbine_points
            )
        else:
            self.total_power_curve = None
            self.power_ratio_gas_turbine_points = None
            self.power_ratio_gas_turbine_interpolator = None
        self.fuel_type = fuel_type
        self.fuel_origin = fuel_origin
        self._setup_emissions(emissions_curves)
        self._setup_nox(nox_calculation_method, rated_speed)

    def _setup_emissions(self, emissions_curves: List[EmissionCurve] = None) -> None:
        self.emission_curves = emissions_curves
        self._emissions_per_kwh_interp: Dict[EmissionType, Callable[[T], T]] = {}
        if emissions_curves is not None:
            e: EmissionCurve
            for e in emissions_curves:
                if len(e.points_per_kwh) > 0:
                    self._emissions_per_kwh_interp[e.emission] = get_emission_curve_from_points(
                        e.points_per_kwh
                    )

    @property
    def fuel_consumer_type_fuel_eu_maritime(self) -> FuelConsumerClassFuelEUMaritime:
        Warning("Fuel consumer type for COGAS is not defined in FuelEU Maritime regulation yet.")
        return None

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

    @property
    def power_output_gas_turbine(self):
        """Power output of the gas turbine in kW"""
        if self.power_ratio_gas_turbine_interpolator is None:
            raise ValueError(
                "The power ratio gas turbine interpolator is not defined. Please provide the power curves for the gas and steam turbines."
            )
        return self.power_ratio_gas_turbine_interpolator(self.power_output / self.rated_power)

    @property
    def power_output_steam_turbine(self):
        """Power output of the steam turbine in kW"""
        return self.power_output - self.power_output_gas_turbine

    def get_gas_turbine_run_point_from_power_output_kw(
        self,
        power_kw: np.ndarray = None,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] = None,
    ) -> COGASRunPoint:
        # GHG factors for FuelEU Maritime is not available for COGAS yet. It should raise an error if the user tries to use it.
        if fuel_specified_by == FuelSpecifiedBy.FUEL_EU_MARITIME:
            raise ValueError("GHG factors for FuelEU Maritime is not available for COGAS yet.")
        if power_kw is None:
            power_kw = self.power_output
        load_ratio = self.get_load(power_kw)
        eff = self.get_efficiency_from_load_percentage(load_ratio)
        fuel = Fuel(
            origin=self.fuel_origin,
            fuel_type=self.fuel_type,
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
        )
        fuel_power_kw = power_kw / eff
        fuel_consumption_kg_per_s = fuel_power_kw / (fuel.lhv_mj_per_g * 1000) / 1000
        fuel.mass_or_mass_fraction = fuel_consumption_kg_per_s
        emissionn_per_s = {}
        power_kwh_per_s = power_kw / 3600
        for e in self._emissions_per_kwh_interp:
            emissionn_per_s[e] = (
                self.emissions_g_per_kwh(emission_type=e, load_ratio=load_ratio) * power_kwh_per_s
            )
        result = COGASRunPoint(
            load_ratio=load_ratio,
            fuel_flow_rate_kg_per_s=FuelConsumption(fuels=[fuel]),
            efficiency=eff,
            emissions_g_per_s=emissionn_per_s,
        )
        if self.gas_turbine_power_curve is not None:
            result.gas_turbine_power_kw = self.power_output_gas_turbine
            result.steam_turbine_power_kw = self.power_output_steam_turbine
        return result


MechanicalComponent = Union[
    MainEngineForMechanicalPropulsion,
    MainEngineWithGearBoxForMechanicalPropulsion,
    MechanicalPropulsionComponent,
]
