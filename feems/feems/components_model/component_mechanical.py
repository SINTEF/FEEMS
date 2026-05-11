from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, TypeVar, Union

import numpy as np
import pandas as pd

from .. import get_logger
from ..constant import (
    get_saturated_steam_h_g_kj_per_kg,
    nox_factor_imo_medium_speed_g_hWh,
    nox_factor_imo_slow_speed_g_kWh,
    nox_tier_slow_speed_max_rpm,
)
from ..fuel import (
    Fuel,
    FuelConsumerClassFuelEUMaritime,
    FuelConsumption,
    FuelOrigin,
    FuelSpecifiedBy,
    GhgEmissionFactorTankToWake,
    TypeFuel,
    find_user_fuel,
)
from ..types_for_feems import (
    EmissionCurve,
    EmissionType,
    EngineCycleType,
    NOxCalculationMethod,
    Power_kW,
    Speed_rpm,
    TypeComponent,
    TypePower,
)
from .component_base import BasicComponent, Component, ComponentRunPoint
from .utility import (
    get_efficiency_curve_from_dataframe,
    get_efficiency_curve_from_points,
    get_emission_curve_from_points,
)

logger = get_logger(__name__)

# IPCC 2006 Vol.2 Ch.2 Table 2.6 defaults for gas turbines (Brayton cycle).
# Source: 4th IMO GHG Study / MEPC.391(81); no FuelEU Maritime Annex II entry exists.
_DEFAULT_BRAYTON_C_SLIP_PERCENT: float = 0.01
_DEFAULT_BRAYTON_CH4_GFUEL: float = 0.000192  # 4 kg/TJ at LNG LCV 48 MJ/kg
_DEFAULT_BRAYTON_N2O_GFUEL: float = 0.000048  # 1 kg/TJ at LNG LCV 48 MJ/kg


@dataclass
class EngineRunPoint:
    load_ratio: np.ndarray
    fuel_flow_rate_kg_per_s: FuelConsumption
    bsfc_g_per_kWh: np.ndarray
    emissions_g_per_s: Dict[EmissionType, np.ndarray]
    bspfc_g_per_kWh: np.ndarray | None = None


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
        bsfc_curve: np.ndarray | None = None,
        fuel_type: TypeFuel = TypeFuel.DIESEL,
        fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
        file_name: str | None = None,
        emissions_curves: List[EmissionCurve] | None = None,
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

    def _setup_emissions(self, emissions_curves: List[EmissionCurve] | None) -> None:
        self.emission_curves = emissions_curves
        self._emissions_per_kwh_interp: Dict[EmissionType, Callable[[float], float]] = {}
        if emissions_curves is not None:
            e: EmissionCurve
            for e in emissions_curves:
                if len(e.points_per_kwh) > 0:
                    self._emissions_per_kwh_interp[e.emission] = get_emission_curve_from_points(
                        e.points_per_kwh
                    )

    def _setup_bsfc(self, bsfc_curve: np.ndarray | None, file_name: str | None) -> None:
        self.specific_fuel_consumption_interp: Callable[[float], float] = lambda x: 0.0
        self.specific_fuel_consumption_points: np.ndarray | None = None
        if file_name is not None:
            df = pd.read_csv(file_name, index_col=0)
            self.rated_power = df["Rated Power"].values[0]
            self.rated_speed = df["Rated Speed"].values[0]
            (
                self.specific_fuel_consumption_interp,
                self.specific_fuel_consumption_points,            ) = get_efficiency_curve_from_dataframe(df, "BSFC")
            self.name = df.index[0]
        elif bsfc_curve is not None:
            (
                self.specific_fuel_consumption_interp,
                self.specific_fuel_consumption_points,
            ) = get_efficiency_curve_from_points(bsfc_curve)
        else:
            raise ValueError("Either bsfc_curve or file_name must be provided for Engine.")

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

            def curve(x):
                return nox_g_per_kwh

        else:
            tier_class = nox_calculation_method.value
            nox_factor_g_kwh = nox_factor_imo_slow_speed_g_kWh[tier_class]

            def curve(x):
                return nox_factor_g_kwh

        self._emissions_per_kwh_interp[EmissionType.NOX] = curve

    def get_engine_run_point_from_power_out_kw(
        self,
        power_kw: np.ndarray | None= None,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: List[Optional[GhgEmissionFactorTankToWake]] | None = None,
        user_defined_fuels: Optional[List[Fuel]] = None,
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
            user_defined_fuels (Optional[List[Fuel]], optional): List of user-defined fuels. When
                provided, the fuel matching this engine's (fuel_type, fuel_origin) is used for the
                emission factors, overriding the regulation-table lookup.

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
        matched = find_user_fuel(user_defined_fuels, self.fuel_type, self.fuel_origin)
        if matched is not None:
            fuel_consumption_component = Fuel(
                fuel_type=matched.fuel_type,
                origin=matched.origin,
                fuel_specified_by=FuelSpecifiedBy.USER,
                lhv_mj_per_g=matched.lhv_mj_per_g,
                ghg_emission_factor_well_to_tank_gco2eq_per_mj=matched.ghg_emission_factor_well_to_tank_gco2eq_per_mj,
                ghg_emission_factor_tank_to_wake=matched.ghg_emission_factor_tank_to_wake,
                mass_or_mass_fraction=fuel_cons_kg_per_s,
                name=matched.name,
            )
        else:
            fuel_consumption_component = Fuel(
                fuel_type=self.fuel_type,
                origin=self.fuel_origin,
                fuel_specified_by=fuel_specified_by,
                lhv_mj_per_g=lhv_mj_per_g,
                ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
                ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
                mass_or_mass_fraction=fuel_cons_kg_per_s,
            )
        # --- emission-curve GHG override -------------------------------------------
        _ch4_g_per_kwh = (
            self.emissions_g_per_kwh(EmissionType.CH4, load_ratio)
            if EmissionType.CH4 in self._emissions_per_kwh_interp
            else None
        )
        _n2o_g_per_kwh = (
            self.emissions_g_per_kwh(EmissionType.N2O, load_ratio)
            if EmissionType.N2O in self._emissions_per_kwh_interp
            else None
        )
        if _ch4_g_per_kwh is not None or _n2o_g_per_kwh is not None:
            fuel_consumption_component = fuel_consumption_component.with_emission_curve_ghg_overrides(
                ch4_factor_gch4_per_gfuel=(
                    _ch4_g_per_kwh / bsfc_g_per_kwh if _ch4_g_per_kwh is not None else None
                ),
                n2o_factor_gn2o_per_gfuel=(
                    _n2o_g_per_kwh / bsfc_g_per_kwh if _n2o_g_per_kwh is not None else None
                ),
            )
        # ---------------------------------------------------------------------------
        return EngineRunPoint(
            load_ratio=load_ratio,
            fuel_flow_rate_kg_per_s=FuelConsumption(fuels=[fuel_consumption_component]),
            bsfc_g_per_kWh=bsfc_g_per_kwh,
            emissions_g_per_s=emissions_per_s,
        )


class EngineDualFuel(Engine):
    bspfc_curve: np.ndarray | None = None  # Brake specific pilot fuel consumption curve
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
        user_defined_fuels: Optional[List[Fuel]] = None,
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
            user_defined_fuels (Optional[List[Fuel]], optional): List of user-defined fuels. When
                provided, fuels matching (fuel_type, origin) are used for emission factors for both
                main and pilot fuel.

        Returns:
            EngineRunPoint
        """
        if power_kw is None:
            power_kw = self.power_output
        engine_run_point = super().get_engine_run_point_from_power_out_kw(
            power_kw=power_kw,
            fuel_specified_by=fuel_specified_by,
            user_defined_fuels=user_defined_fuels,
        )
        bspfc = self.specific_pilot_fuel_consumption_interp(engine_run_point.load_ratio)
        pilot_fuel_cons_kg_per_s = bspfc * power_kw / 1000 / 3600
        pilot_matched = find_user_fuel(user_defined_fuels, self.pilot_fuel_type, self.pilot_fuel_origin)
        if pilot_matched is not None:
            pilot_fuel = Fuel(
                fuel_type=pilot_matched.fuel_type,
                origin=pilot_matched.origin,
                fuel_specified_by=FuelSpecifiedBy.USER,
                lhv_mj_per_g=pilot_matched.lhv_mj_per_g,
                ghg_emission_factor_well_to_tank_gco2eq_per_mj=pilot_matched.ghg_emission_factor_well_to_tank_gco2eq_per_mj,
                ghg_emission_factor_tank_to_wake=pilot_matched.ghg_emission_factor_tank_to_wake,
                mass_or_mass_fraction=pilot_fuel_cons_kg_per_s,
                name=pilot_matched.name,
            )
        else:
            pilot_fuel = Fuel(
                fuel_type=self.pilot_fuel_type,
                origin=self.pilot_fuel_origin,
                fuel_specified_by=fuel_specified_by,
                lhv_mj_per_g=lhv_mj_per_g,
                ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
                ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
                mass_or_mass_fraction=pilot_fuel_cons_kg_per_s,
            )
        engine_run_point.fuel_flow_rate_kg_per_s += FuelConsumption(fuels=[pilot_fuel])
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
    eff_curve: np.ndarray = None  # per-mode efficiency curve for COGAS fuel modes
    emission_curves: List[EmissionCurve] = None
    engine_cycle_type: EngineCycleType = EngineCycleType.DIESEL

    @property
    def secondary_fuel_type(self) -> Optional[TypeFuel]:
        """Alias for pilot_fuel_type; use this name for Brayton (gas turbine) fuel-mode switching."""
        return self.pilot_fuel_type

    @secondary_fuel_type.setter
    def secondary_fuel_type(self, value: Optional[TypeFuel]) -> None:
        self.pilot_fuel_type = value

    @property
    def secondary_fuel_origin(self) -> Optional[FuelOrigin]:
        """Alias for pilot_fuel_origin; use this name for Brayton fuel-mode switching."""
        return self.pilot_fuel_origin

    @secondary_fuel_origin.setter
    def secondary_fuel_origin(self, value: Optional[FuelOrigin]) -> None:
        self.pilot_fuel_origin = value


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
            fuel_type (TypeFuel): Fuel type. Optional. Defaults to None,
                which means the first fuel type in the list.
            fuel_origin (FuelOrigin): Fuel origin. Optional. Defaults to None,
                which means the first fuel origin in the list.
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
        user_defined_fuels: Optional[List[Fuel]] = None,
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
            user_defined_fuels (Optional[List[Fuel]], optional): List of user-defined fuels. Passed
                through to the active engine in use.

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
            user_defined_fuels=user_defined_fuels,
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
        user_defined_fuels: Optional[List[Fuel]] = None,
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
            user_defined_fuels (Optional[List[Fuel]], optional): List of user-defined fuels. Passed
                through to the underlying engine.

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
            user_defined_fuels=user_defined_fuels,
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
        user_defined_fuels: Optional[List[Fuel]] = None,
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
            user_defined_fuels (Optional[List[Fuel]], optional): List of user-defined fuels. Passed
                through to the underlying engine.

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
            user_defined_fuels=user_defined_fuels,
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
        multi_fuel_characteristics: Optional[List["FuelCharacteristics"]] = None,
        ch4_factor_gch4_per_gfuel: float = _DEFAULT_BRAYTON_CH4_GFUEL,
        n2o_factor_gn2o_per_gfuel: float = _DEFAULT_BRAYTON_N2O_GFUEL,
        c_slip_percent: float = _DEFAULT_BRAYTON_C_SLIP_PERCENT,
    ):
        """Constructor for COGES component"""
        # Validate the inputs for curves. The length of the curves should be the same
        # and the x values should be the same.
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
        self.multi_fuel_characteristics = multi_fuel_characteristics
        self.ch4_factor_gch4_per_gfuel = ch4_factor_gch4_per_gfuel
        self.n2o_factor_gn2o_per_gfuel = n2o_factor_gn2o_per_gfuel
        self.c_slip_percent = c_slip_percent
        if multi_fuel_characteristics:
            self.fuel_type = multi_fuel_characteristics[0].main_fuel_type
            self.fuel_origin = multi_fuel_characteristics[0].main_fuel_origin
            self._fuel_in_use: Optional[FuelCharacteristics] = multi_fuel_characteristics[0]
        else:
            self._fuel_in_use = None

    def set_fuel_in_use(
        self, fuel_type: Optional[TypeFuel] = None, fuel_origin: Optional[FuelOrigin] = None
    ) -> None:
        """Select the active fuel mode from multi_fuel_characteristics.

        If multi_fuel_characteristics is None (single-fuel COGAS), this is a no-op.
        If fuel_type/fuel_origin are None, resets to the first mode in the list.
        """
        if not self.multi_fuel_characteristics:
            return
        if fuel_type is None or fuel_origin is None:
            self._fuel_in_use = self.multi_fuel_characteristics[0]
            self.fuel_type = self._fuel_in_use.main_fuel_type
            self.fuel_origin = self._fuel_in_use.main_fuel_origin
            return
        fc = next(
            (
                fc
                for fc in self.multi_fuel_characteristics
                if fc.main_fuel_type == fuel_type and fc.main_fuel_origin == fuel_origin
            ),
            None,
        )
        if fc is None:
            raise ValueError(
                f"No FuelCharacteristics for fuel_type={fuel_type}, fuel_origin={fuel_origin}."
            )
        self._fuel_in_use = fc
        self.fuel_type = fc.main_fuel_type
        self.fuel_origin = fc.main_fuel_origin

    def _build_emission_interp(
        self, curves: Optional[List[EmissionCurve]]
    ) -> Dict[EmissionType, Callable[[T], T]]:
        result: Dict[EmissionType, Callable[[T], T]] = {}
        if curves:
            for e in curves:
                if len(e.points_per_kwh) > 0:
                    result[e.emission] = get_emission_curve_from_points(e.points_per_kwh)
        return result

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
        return FuelConsumerClassFuelEUMaritime.GAS_TURBINE

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

            def curve(x):
                return nox_g_per_kwh

        else:
            tier_class = nox_calculation_method.value
            nox_factor_g_kwh = nox_factor_imo_slow_speed_g_kWh[tier_class]

            def curve(x):
                return nox_factor_g_kwh

        self._emissions_per_kwh_interp[EmissionType.NOX] = curve

    @property
    def power_output_gas_turbine(self):
        """Power output of the gas turbine in kW"""
        if self.power_ratio_gas_turbine_interpolator is None:
            raise ValueError(
                "The power ratio gas turbine interpolator is not defined."
                " Please provide the power curves for the gas and steam turbines."
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
        if power_kw is None:
            power_kw = self.power_output
        load_ratio = self.get_load(power_kw)
        fuel = Fuel(
            origin=self.fuel_origin,
            fuel_type=self.fuel_type,
            fuel_specified_by=fuel_specified_by,
            lhv_mj_per_g=lhv_mj_per_g,
            ghg_emission_factor_tank_to_wake=ghg_emission_factor_tank_to_wake,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=ghg_emission_factor_well_to_tank_gco2eq_per_mj,
        )
        # Active fuel mode provides its own efficiency curve; else fall back to self.eff_curve.
        if self._fuel_in_use is not None and self._fuel_in_use.eff_curve is not None:
            eff_interp, _ = get_efficiency_curve_from_points(self._fuel_in_use.eff_curve)
            eff = eff_interp(load_ratio)
        else:
            eff = self.get_efficiency_from_load_percentage(load_ratio)
        fuel_power_kw = power_kw / eff
        fuel_consumption_kg_per_s = fuel_power_kw / (fuel.lhv_mj_per_g * 1000) / 1000
        fuel.mass_or_mass_fraction = fuel_consumption_kg_per_s
        # Use emission curves from active fuel mode if available, else top-level curves.
        active_emission_curves_interp = (
            self._build_emission_interp(self._fuel_in_use.emission_curves)
            if self._fuel_in_use is not None and self._fuel_in_use.emission_curves
            else self._emissions_per_kwh_interp
        )
        # --- GHG override: emission curves (issue #85) take priority over scalar fields ----------
        _ch4_g_per_kwh = (
            active_emission_curves_interp[EmissionType.CH4](load_ratio)
            if EmissionType.CH4 in active_emission_curves_interp
            else None
        )
        _n2o_g_per_kwh = (
            active_emission_curves_interp[EmissionType.N2O](load_ratio)
            if EmissionType.N2O in active_emission_curves_interp
            else None
        )
        if _ch4_g_per_kwh is not None or _n2o_g_per_kwh is not None:
            _power_kwh_per_s = power_kw / 3600
            _bsfc_eq_g_per_kwh = fuel_consumption_kg_per_s * 1000 / _power_kwh_per_s
            fuel = fuel.with_emission_curve_ghg_overrides(
                ch4_factor_gch4_per_gfuel=(
                    _ch4_g_per_kwh / _bsfc_eq_g_per_kwh if _ch4_g_per_kwh is not None else None
                ),
                n2o_factor_gn2o_per_gfuel=(
                    _n2o_g_per_kwh / _bsfc_eq_g_per_kwh if _n2o_g_per_kwh is not None else None
                ),
                # c_slip_percent=None → legacy zero-out behaviour (curve captures all CH4)
            )
        else:
            # --- scalar-field override (BRAYTON IPCC defaults or user-supplied values) -----------
            fuel = fuel.with_emission_curve_ghg_overrides(
                ch4_factor_gch4_per_gfuel=self.ch4_factor_gch4_per_gfuel,
                n2o_factor_gn2o_per_gfuel=self.n2o_factor_gn2o_per_gfuel,
                c_slip_percent=self.c_slip_percent,  # explicit: not zeroed out
            )
        # -----------------------------------------------------------------------------------------
        emissionn_per_s = {}
        power_kwh_per_s = power_kw / 3600
        for e, interp_fn in active_emission_curves_interp.items():
            emissionn_per_s[e] = interp_fn(load_ratio) * power_kwh_per_s
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

#: Specific heat capacity of liquid water (kJ/kg·K) used for feed water enthalpy
_CP_WATER_KJ_PER_KG_K: float = 4.18


@dataclass(kw_only=True)
class BoilerRunPoint:
    load_ratio: np.ndarray
    fuel_flow_rate_kg_per_s: FuelConsumption
    steam_production_kg_per_s: np.ndarray
    thermal_efficiency: np.ndarray
    emissions_g_per_s: Dict[EmissionType, np.ndarray]


class SteamBoiler:
    """Fuel-fired auxiliary boiler producing saturated steam for non-power thermal loads.

    Rated capacity is in kg/h steam production. Thermal efficiency is the single source
    of truth for fuel consumption; the two alternative curve input types are normalised
    to thermal efficiency at construction time using the saturated steam lookup table and
    the fuel LHV.
    
    Arguments:
        name: Name of the boiler.
        rated_steam_production_kg_per_h: Rated steam production in kg/h.
        working_pressure_barg: Working (gauge) pressure of the saturated steam in bar gauge (barg).
            Atmospheric pressure (1 bar) is added internally before the IAPWS-IF97 lookup.
            A boiler operating at 6 barg produces steam at 7 bara.
        thermal_efficiency_curve: 2D array (N x 2) of (load_ratio, thermal_efficiency)
        kg_fuel_per_h_curve: 2D array (N x 2) of (load_ratio, kg_fuel_per_h)
        kg_fuel_per_kg_steam_curve: 2D array (N x 2) of (load_ratio, kg_fuel_per_kg_steam)
        fuel_type: TypeFuel of the fuel used by the boiler.
        fuel_origin: FuelOrigin of the fuel used by the boiler.
        feed_water_temperature_c: Temperature of the feed water in °C, used for calculating
            the enthalpy difference dh of the steam produced by the boiler.
        emissions_curves: List of EmissionCurve, optional.
        multi_fuel_characteristics: List of FuelCharacteristics for multi-fuel boilers,
            optional. If provided, fuel_type and fuel_origin are taken from the first entry
            in the list, and the active fuel mode can be switched using set_fuel_in_use.
        uid: Optional unique identifier for the component instance.

    The boiler is standalone — not connected to any switchboard or shaft line.
    """

    def __init__(
        self,
        *,
        name: str = "",
        rated_steam_production_kg_per_h: float,
        working_pressure_barg: float,
        thermal_efficiency_curve: Optional[np.ndarray] = None,
        kg_fuel_per_h_curve: Optional[np.ndarray] = None,
        kg_fuel_per_kg_steam_curve: Optional[np.ndarray] = None,
        fuel_type: TypeFuel = TypeFuel.HFO,
        fuel_origin: FuelOrigin = FuelOrigin.FOSSIL,
        feed_water_temperature_c: float = 80.0,
        emissions_curves: Optional[List[EmissionCurve]] = None,
        multi_fuel_characteristics: Optional[List["FuelCharacteristics"]] = None,
        uid: Optional[str] = None,
    ):
        from ..exceptions import InputError

        self.name = name
        self.type = TypeComponent.STEAM_BOILER
        self.steam_out_kg_per_h: Optional[np.ndarray] = None
        if rated_steam_production_kg_per_h <= 0:
            raise InputError(
                f"SteamBoiler '{name}': rated_steam_production_kg_per_h must be > 0, "
                f"got {rated_steam_production_kg_per_h}."
            )
        self.rated_steam_production_kg_per_h = rated_steam_production_kg_per_h
        self.working_pressure_barg = working_pressure_barg
        self.feed_water_temperature_c = feed_water_temperature_c
        self.fuel_type = fuel_type
        self.fuel_origin = fuel_origin
        self.uid = uid
        self.multi_fuel_characteristics = multi_fuel_characteristics
        self._fuel_in_use: Optional["FuelCharacteristics"] = None

        #: Δh = h_g(P_abs) − cp_water * T_fw  (kJ/kg); P_abs = working_pressure_barg + 1 bara
        h_g = get_saturated_steam_h_g_kj_per_kg(working_pressure_barg + 1.0)  # raises InputError if OOB
        self.delta_h_kj_per_kg: float = h_g - _CP_WATER_KJ_PER_KG_K * feed_water_temperature_c
        if self.delta_h_kj_per_kg <= 0:
            raise InputError(
                f"SteamBoiler '{name}': computed enthalpy rise delta_h={self.delta_h_kj_per_kg:.1f} kJ/kg "
                f"is not positive — feed_water_temperature_c={feed_water_temperature_c} °C is too high "
                f"for working_pressure_barg={working_pressure_barg} barg."
            )

        self._eta_curve: Optional[np.ndarray] = None
        if multi_fuel_characteristics is not None:
            if len(multi_fuel_characteristics) == 0:
                raise ValueError(f"SteamBoiler '{name}': multi_fuel_characteristics must not be empty.")
            self.fuel_type = multi_fuel_characteristics[0].main_fuel_type
            self.fuel_origin = multi_fuel_characteristics[0].main_fuel_origin
            self._fuel_in_use = multi_fuel_characteristics[0]
            first_eff = multi_fuel_characteristics[0].eff_curve
            if first_eff is None:
                raise ValueError(
                    f"SteamBoiler '{name}': each FuelCharacteristics entry must have eff_curve set."
                )
            self._thermal_efficiency_interp, _ = get_efficiency_curve_from_points(first_eff)
            self._eta_curve = None  # eff_curve lives in each FuelCharacteristics
        else:
            #: Resolve which curve was supplied and normalise to thermal efficiency
            n_curves = sum(c is not None for c in [
                thermal_efficiency_curve, kg_fuel_per_h_curve, kg_fuel_per_kg_steam_curve
            ])
            if n_curves == 0:
                raise InputError(
                    f"SteamBoiler '{name}': one of thermal_efficiency_curve, "
                    "kg_fuel_per_h_curve, or kg_fuel_per_kg_steam_curve must be provided."
                )
            if n_curves > 1:
                raise InputError(
                    f"SteamBoiler '{name}': only one curve input type may be provided."
                )

            if thermal_efficiency_curve is not None:
                eta_curve = thermal_efficiency_curve
            else:
                #: Obtain LHV from a zero-mass Fuel object so we can normalise the curve
                lhv_kj_per_kg = self._get_lhv_kj_per_kg()
                if kg_fuel_per_kg_steam_curve is not None:
                    eta_curve = self._normalise_sfc_curve(kg_fuel_per_kg_steam_curve, lhv_kj_per_kg)
                else:
                    eta_curve = self._normalise_kg_fuel_per_h_curve(kg_fuel_per_h_curve, lhv_kj_per_kg)

            self._thermal_efficiency_interp, _ = get_efficiency_curve_from_points(eta_curve)
            #: Store the normalised curve for serialisation (e.g. proto converters)
            self._eta_curve = eta_curve

        #: Emission curves — store originals for serialisation, build interpolators for computation
        self.emissions_curves: Optional[List[EmissionCurve]] = emissions_curves
        self._emissions_per_kwh_interp: Dict[EmissionType, Callable[[np.ndarray], np.ndarray]] = {}
        if emissions_curves:
            for ec in emissions_curves:
                if len(ec.points_per_kwh) > 0:
                    self._emissions_per_kwh_interp[ec.emission] = get_emission_curve_from_points(
                        ec.points_per_kwh
                    )

        # Cache active-fuel hot-path values; rebuilt by set_fuel_in_use on fuel switch
        self._lhv_kj_per_kg: float = self._get_lhv_kj_per_kg()
        self._active_eff_interp = self._thermal_efficiency_interp
        self._active_emission_interp: Dict[EmissionType, Callable[[np.ndarray], np.ndarray]] = (
            self._build_mode_emission_interp(self._fuel_in_use)
            if self._fuel_in_use is not None
            else self._emissions_per_kwh_interp
        )

    # ------------------------------------------------------------------
    # Curve normalisation helpers
    # ------------------------------------------------------------------

    def _build_mode_emission_interp(
        self, fc: "FuelCharacteristics"
    ) -> Dict[EmissionType, Callable[[np.ndarray], np.ndarray]]:
        """Return emission interpolators for a fuel mode, falling back to top-level curves."""
        if not fc or not fc.emission_curves:
            return self._emissions_per_kwh_interp
        result = {
            ec.emission: get_emission_curve_from_points(ec.points_per_kwh)
            for ec in fc.emission_curves
            if len(ec.points_per_kwh) > 0
        }
        return result or self._emissions_per_kwh_interp

    def _get_lhv_kj_per_kg(self) -> float:
        ref_fuel = Fuel(
            fuel_type=self.fuel_type,
            origin=self.fuel_origin,
            fuel_specified_by=FuelSpecifiedBy.IMO,
            mass_or_mass_fraction=0.0,
        )
        # lhv_mj_per_g × 1000 (kJ/MJ) × 1000 (g/kg) = kJ/kg
        return ref_fuel.lhv_mj_per_g * 1e6

    def _normalise_sfc_curve(
        self, sfc_curve: np.ndarray, lhv_kj_per_kg: float
    ) -> np.ndarray:
        """Convert kg_fuel/kg_steam vs. load_ratio to thermal efficiency vs. load_ratio."""
        result = sfc_curve.copy()
        result[:, 1] = self.delta_h_kj_per_kg / (sfc_curve[:, 1] * lhv_kj_per_kg)
        return result

    def _normalise_kg_fuel_per_h_curve(
        self, kg_fuel_per_h_curve: np.ndarray, lhv_kj_per_kg: float
    ) -> np.ndarray:
        """Convert kg_fuel/h vs. load_ratio to thermal efficiency vs. load_ratio."""
        from ..exceptions import InputError

        load_ratios = kg_fuel_per_h_curve[:, 0]
        if np.any(load_ratios == 0):
            raise InputError(
                f"SteamBoiler '{self.name}': kg_fuel_per_h_curve must not contain "
                "load_ratio=0 — steam production is zero at that point."
            )
        result = kg_fuel_per_h_curve.copy()
        steam_kg_per_h_at_load = load_ratios * self.rated_steam_production_kg_per_h
        sfc = kg_fuel_per_h_curve[:, 1] / steam_kg_per_h_at_load  # kg_fuel/kg_steam
        result[:, 1] = self.delta_h_kj_per_kg / (sfc * lhv_kj_per_kg)
        return result

    # ------------------------------------------------------------------
    # Multi-fuel support
    # ------------------------------------------------------------------

    def set_fuel_in_use(
        self, fuel_type: Optional[TypeFuel] = None, fuel_origin: Optional[FuelOrigin] = None
    ) -> None:
        """Select the active fuel mode from multi_fuel_characteristics.

        No-op for single-fuel boilers. If fuel_type/fuel_origin are None, resets to the first mode.
        Raises ValueError if the combination is not in the list.
        """
        if not self.multi_fuel_characteristics:
            return
        if fuel_type is None or fuel_origin is None:
            fc = self.multi_fuel_characteristics[0]
        else:
            fc = next(
                (
                    f
                    for f in self.multi_fuel_characteristics
                    if f.main_fuel_type == fuel_type and f.main_fuel_origin == fuel_origin
                ),
                None,
            )
            if fc is None:
                raise ValueError(
                    f"No FuelCharacteristics for fuel_type={fuel_type}, fuel_origin={fuel_origin}."
                )
        self._fuel_in_use = fc
        self.fuel_type = fc.main_fuel_type
        self.fuel_origin = fc.main_fuel_origin
        if fc.eff_curve is not None:
            self._active_eff_interp, _ = get_efficiency_curve_from_points(fc.eff_curve)
        self._lhv_kj_per_kg = self._get_lhv_kj_per_kg()
        self._active_emission_interp = self._build_mode_emission_interp(fc)

    # ------------------------------------------------------------------
    # Run point
    # ------------------------------------------------------------------

    def get_boiler_run_point(
        self,
        steam_demand_kg_per_h: np.ndarray,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
    ) -> BoilerRunPoint:
        """Calculate boiler operating state for the given steam demand.

        Args:
            steam_demand_kg_per_h: Instantaneous steam demand in kg/h.
            fuel_specified_by: Fuel specification method (IMO or FUEL_EU_MARITIME).

        Returns:
            BoilerRunPoint with load ratio, fuel flow, steam production, efficiency, emissions.
        """
        steam_demand_kg_per_h = np.asarray(steam_demand_kg_per_h, dtype=float)
        if not np.all(np.isfinite(steam_demand_kg_per_h)) or np.any(steam_demand_kg_per_h < 0):
            raise ValueError(
                f"SteamBoiler '{self.name}': steam_demand_kg_per_h must be finite and >= 0."
            )

        load_ratio = steam_demand_kg_per_h / self.rated_steam_production_kg_per_h

        efficiency_steam_boiler = np.clip(self._active_eff_interp(load_ratio), 1e-6, 1.0)

        steam_kg_per_s = steam_demand_kg_per_h / 3600.0
        heat_flow_steam_kw = steam_kg_per_s * self.delta_h_kj_per_kg
        heat_flow_fuel_kw = np.where(steam_kg_per_s > 0, heat_flow_steam_kw / efficiency_steam_boiler, 0.0)

        fuel_kg_per_s = heat_flow_fuel_kw / self._lhv_kj_per_kg

        fuel_obj = Fuel(
            fuel_type=self.fuel_type,
            origin=self.fuel_origin,
            fuel_specified_by=fuel_specified_by,
            mass_or_mass_fraction=fuel_kg_per_s,
        )

        # Emission curves are in g/kWh of fuel energy input
        fuel_energy_kwh_per_s = heat_flow_fuel_kw / 3600.0
        emissions_g_per_s: Dict[EmissionType, np.ndarray] = {
            et: interp(load_ratio) * fuel_energy_kwh_per_s
            for et, interp in self._active_emission_interp.items()
        }

        return BoilerRunPoint(
            load_ratio=load_ratio,
            fuel_flow_rate_kg_per_s=FuelConsumption(fuels=[fuel_obj]),
            steam_production_kg_per_s=steam_kg_per_s,
            thermal_efficiency=efficiency_steam_boiler,
            emissions_g_per_s=emissions_g_per_s,
        )
