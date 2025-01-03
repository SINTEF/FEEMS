"""This module provides classes for fuel consumption and emissions."""

from functools import cache
import os
import warnings
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Dict, Union, Optional, List

import pandas as pd
import numpy as np


@unique
class TypeFuel(Enum):
    DIESEL = 0
    HFO = 1
    NATURAL_GAS = 2
    HYDROGEN = 3
    AMMONIA = 4
    LPG_PROPANE = 5
    LPG_BUTANE = 6
    ETHANOL = 7
    METHANOL = 8
    LFO = 9
    LSFO_CRUDE = 10
    LSFO_BLEND = 11
    ULSFO = 12
    VLSFO = 13


@unique
class FuelOrigin(Enum):
    NONE = 0
    FOSSIL = 1
    BIO = 2
    RENEWABLE_NON_BIO = 3


_GWP100_CO2 = 1
_GWP100_CH4 = 25
_GWP100_N2O = 298


_PATH_TO_FUELEU_MARITIME_GHG_FACTORS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "package_data", "fuel_eu_fuel_table.csv"
)
_PATH_TO_IMO_GHG_FACTORS = os.path.join(
    os.path.dirname(_PATH_TO_FUELEU_MARITIME_GHG_FACTORS), "fuel_imo_table.csv"
)
_DF_GHG_FACTORS_DICTIONARY = {}
for path in [_PATH_TO_FUELEU_MARITIME_GHG_FACTORS, _PATH_TO_IMO_GHG_FACTORS]:
    with open(path, "rt") as f:
        lines = f.readlines()
    line_number_table_start = int(lines[0].split(",")[1])
    line_number_table_header = int(lines[1].split(",")[1])
    line_number_unit = int(lines[2].split(",")[1])
    line_number_table_value_start = int(lines[3].split(",")[1])
    header = lines[line_number_table_header - 1].split(",")
    header[-1] = header[-1].replace("\n", "")
    while "" in header:
        header.remove("")
    key_name = "eu" if "fuel_eu" in path else "imo"
    _DF_GHG_FACTORS_DICTIONARY[key_name] = pd.read_csv(
        path, skiprows=line_number_table_value_start - 1, header=None
    )
    _DF_GHG_FACTORS_DICTIONARY[key_name].columns = header


_FUEL_CLASS_FUEL_EU_MARITIME_MAPPING = {
    FuelOrigin.FOSSIL: "Fossil",
    FuelOrigin.BIO: "Bio",
    FuelOrigin.RENEWABLE_NON_BIO: "RFNBO",
}


_FUEL_TYPE_FUEL_EU_MARITIME_MAPPING = {
    TypeFuel.DIESEL: "Diesel",
    TypeFuel.HFO: "HFO",
    TypeFuel.NATURAL_GAS: "LNG",
    TypeFuel.HYDROGEN: "H2",
    TypeFuel.AMMONIA: "NH3",
    TypeFuel.LPG_PROPANE: "LPG (Propane)",
    TypeFuel.LPG_BUTANE: "LPG (Butane)",
    TypeFuel.ETHANOL: "Ethanol",
    TypeFuel.METHANOL: "Methanol",
    TypeFuel.LFO: "LFO",
    TypeFuel.LSFO_CRUDE: "LSFO (Crude)",
    TypeFuel.LSFO_BLEND: "LSFO (Blend)",
    TypeFuel.ULSFO: "ULSFO",
    TypeFuel.VLSFO: "VLSFO",
}


class FuelSpecifiedBy(Enum):
    NONE = 0
    FUEL_EU_MARITIME = 1
    IMO = 2
    USER = 3


class FuelConsumerClassFuelEUMaritime(Enum):
    NONE = 0
    ICE = 1
    LNG_OTTO_MEDIUM_SPEED = 2
    LNG_OTTO_SLOW_SPEED = 3
    LNG_DIESEL = 4
    LNG_LBSI = 5
    FUEL_CELL = 6


_FUEL_CONSUMER_CLASS_FUEL_EU_MARITIME_MAPPING = {
    FuelConsumerClassFuelEUMaritime.ICE: "ALL ICEs",
    FuelConsumerClassFuelEUMaritime.LNG_OTTO_MEDIUM_SPEED: "LNG otto (medium speed)",
    FuelConsumerClassFuelEUMaritime.LNG_OTTO_SLOW_SPEED: "LNG otto (slow speed)",
    FuelConsumerClassFuelEUMaritime.LNG_DIESEL: "LNG diesel (slow speed)",
    FuelConsumerClassFuelEUMaritime.LNG_LBSI: "LBSI",
    FuelConsumerClassFuelEUMaritime.FUEL_CELL: "Fuel Cells",
}


@dataclass
class GhgEmissionFactorTankToWake:
    """Class for GHG emission factor from tank to wake

    Attributes:
        fuel_consumer_class (FuelConsumerClassFuelEUMaritime, str): Fuel consumer class
        co2_factor_gco2_per_gfuel (float): CO2 emission factor from tank to wake in gCO2eq/gfuel
        ch4_factor_gch4_per_gfuel (float): CH4 emission factor from tank to wake in gCH4/gfuel
        n2o_factor_gn2o_per_gfuel (float): N2O emission factor from tank to wake in gN2O/gfuel
        c_slip_percent (float): Methane slip percentage
    """

    co2_factor_gco2_per_gfuel: float
    ch4_factor_gch4_per_gfuel: float
    n2o_factor_gn2o_per_gfuel: float
    c_slip_percent: float
    fuel_consumer_class: Optional[Union[FuelConsumerClassFuelEUMaritime, str]] = None

    def __post_init__(self):
        try:
            if isinstance(self.fuel_consumer_class, str):
                self.fuel_consumer_class = next(
                    filter(
                        lambda x: (
                            self.fuel_consumer_class
                            == _FUEL_CONSUMER_CLASS_FUEL_EU_MARITIME_MAPPING[x]
                        ),
                        _FUEL_CONSUMER_CLASS_FUEL_EU_MARITIME_MAPPING,
                    )
                )
        except StopIteration:
            raise ValueError(
                f"Fuel consumer class {self.fuel_consumer_class} is not of proper string value."
            )

    @property
    def ghg_emission_factor_gco2eq_per_gfuel(self) -> float:
        return (1 - self.c_slip_percent / 100) * (
            self.co2_factor_gco2_per_gfuel
            + self.ch4_factor_gch4_per_gfuel * _GWP100_CH4
            + self.n2o_factor_gn2o_per_gfuel * _GWP100_N2O
        ) + self.c_slip_percent / 100 * _GWP100_CH4


class Fuel:
    fuel_type: TypeFuel
    origin: FuelOrigin
    fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO
    lhv_mj_per_g: Optional[float] = None
    ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None
    ghg_emission_factor_tank_to_wake: Optional[List[GhgEmissionFactorTankToWake]] = None
    mass_or_mass_fraction: Union[np.array, float] = 0.0

    def __init__(
        self,
        fuel_type: TypeFuel,
        origin: FuelOrigin,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        lhv_mj_per_g: Optional[float] = None,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj: Optional[float] = None,
        ghg_emission_factor_tank_to_wake: Optional[
            List[GhgEmissionFactorTankToWake]
        ] = None,
        mass_or_mass_fraction: Union[np.array, float] = 0.0,
    ):
        """Constructor for FuelSpecifications class

        Args:
            fuel_type (TypeFuel): Type of fuel
            origin (FuelOrigin): Origin of fuel
            fuel_specified_by (FuelSpecifiedBy): How the fuel is specified
            lhv_mj_per_g (float, optional): Low heat value of fuel. The value should be provided
                if 'fuel_specified_by' is 'USER'.
            ghg_emission_factor_well_to_tank_gco2eq_per_mj (float, optional): GHG emission factor from well
                to tank. The value should be provided if 'fuel_specified_by' is 'USER'.
            ghg_emission_factor_tank_to_wake (list, optional): List of GHG emission factors from tank
                to wake. The value should be provided if 'fuel_specified_by' is 'USER'.
            mass_or_mass_fraction (float, optional): Fuel mass or mass fraction. Defaults to 0.0.

        Raises:
            AssertionError: If the GHG emission factor and low heat value of fuel are not
                provided when 'fuel_specified_by' is 'USER'.
            NotImplementedError: If the fuel is specified by other than 'USER', "FUEL_EU_MARITIME",
                or "IMO".
        """
        if fuel_specified_by in [FuelSpecifiedBy.USER, FuelSpecifiedBy.NONE]:
            assert (
                ghg_emission_factor_well_to_tank_gco2eq_per_mj is not None
                and ghg_emission_factor_tank_to_wake is not None
                and lhv_mj_per_g is not None
            ), "Please specify the GHG emission factor for the fuel."
            self.ghg_emission_factor_well_to_tank_gco2eq_per_mj = (
                ghg_emission_factor_well_to_tank_gco2eq_per_mj
            )
            self.ghg_emission_factor_tank_to_wake = ghg_emission_factor_tank_to_wake
            self.lhv_mj_per_g = lhv_mj_per_g
        else:
            assert (
                ghg_emission_factor_well_to_tank_gco2eq_per_mj is None
                and ghg_emission_factor_tank_to_wake is None
                and lhv_mj_per_g is None
            ), "Please do not specify the GHG emission factor for the fuel."
        self.fuel_type = fuel_type
        self.origin = origin
        self.fuel_specified_by = fuel_specified_by
        self.mass_or_mass_fraction = mass_or_mass_fraction
        self.fuel_specified_by = fuel_specified_by
        if fuel_specified_by == FuelSpecifiedBy.FUEL_EU_MARITIME:
            self._get_factors_for_fuel_eu_maritime()
        elif fuel_specified_by == FuelSpecifiedBy.IMO:
            self._get_factors_for_imo()
        elif fuel_specified_by == FuelSpecifiedBy.USER:
            self.ghg_emission_factor_well_to_tank = (
                ghg_emission_factor_well_to_tank_gco2eq_per_mj
            )
            self.ghg_emission_factor_tank_to_wake = ghg_emission_factor_tank_to_wake
        else:
            raise NotImplementedError(
                f"Fuel specified by {fuel_specified_by} is not implemented."
            )

    def __str__(self):
        return f"{self.fuel_type.name.lower()}_{self.origin.name.lower()}"

    @property
    def copy(self) -> "Fuel":
        """Returns a copy of this object"""
        fuel_specified_by_user = self.fuel_specified_by in [
            FuelSpecifiedBy.USER,
            FuelSpecifiedBy.NONE,
        ]
        return Fuel(
            fuel_type=self.fuel_type,
            origin=self.origin,
            fuel_specified_by=self.fuel_specified_by,
            lhv_mj_per_g=self.lhv_mj_per_g if fuel_specified_by_user else None,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=(
                self.ghg_emission_factor_well_to_tank_gco2eq_per_mj
                if fuel_specified_by_user
                else None
            ),
            ghg_emission_factor_tank_to_wake=(
                self.ghg_emission_factor_tank_to_wake
                if fuel_specified_by_user
                else None
            ),
            mass_or_mass_fraction=self.mass_or_mass_fraction,
        )

    @property
    def copy_except_mass_or_mass_fraction(self) -> "Fuel":
        """Returns a copy of this object"""
        fuel = self.copy
        fuel.mass_or_mass_fraction = 0.0
        return fuel

    @property
    def ghg_emission_factor_well_to_tank_gco2_per_gfuel(self) -> float:
        """Returns the GHG emission factor from well to tank in gCO2eq/gfuel"""
        return self.ghg_emission_factor_well_to_tank_gco2eq_per_mj * self.lhv_mj_per_g

    def get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel(
        self, fuel_consumer_class: FuelConsumerClassFuelEUMaritime = None
    ) -> float:
        """Returns the GHG emission factor from tank to wake in gCO2eq/gfuel

        Args:
            fuel_consumer_class (FuelConsumerClassFuelEUMaritime, optional): Fuel consumer class.
                Defaults to None. For IMO defined fuel, this argument is ignored.

        Returns:
            float: GHG emission factor from tank to wake in gCO2eq/gfuel
        """
        if self.fuel_specified_by == FuelSpecifiedBy.IMO:
            return self.ghg_emission_factor_tank_to_wake[
                0
            ].ghg_emission_factor_gco2eq_per_gfuel
        return next(
            filter(
                lambda x: x.fuel_consumer_class == fuel_consumer_class,
                self.ghg_emission_factor_tank_to_wake,
            )
        ).ghg_emission_factor_gco2eq_per_gfuel

    def _get_prescribed_factors(self, organization: str = "eu") -> None:
        res = get_prescribed_factors(
            organization=organization, origin=self.origin, fuel_type=self.fuel_type
        )
        self.lhv_mj_per_g = res.lhv_mj_per_g
        self.ghg_emission_factor_well_to_tank_gco2eq_per_mj = (
            res.ghg_emission_factor_well_to_tank_gco2eq_per_mj
        )
        self.ghg_emission_factor_tank_to_wake = res.ghg_emission_factor_tank_to_wake

    def _get_factors_for_fuel_eu_maritime(self) -> None:
        """Get the GHG emission factors for fuel specified by EU Maritime Fuel"""
        self._get_prescribed_factors("eu")

    def _get_factors_for_imo(self) -> None:
        """Get the GHG emission factors for fuel specified by IMO"""
        self._get_prescribed_factors("imo")


@dataclass
class PrescribedFactors:
    lhv_mj_per_g: float
    ghg_emission_factor_well_to_tank_gco2eq_per_mj: float
    ghg_emission_factor_tank_to_wake: List[GhgEmissionFactorTankToWake]


@cache
def get_prescribed_factors(
    *, organization: str = "eu", origin: FuelOrigin, fuel_type: TypeFuel
) -> PrescribedFactors:
    """Get the GHG emission factors for fuel specified by EU Maritime Fuel"""
    fuel_class = _FUEL_CLASS_FUEL_EU_MARITIME_MAPPING[origin]
    fuel_type_eu = _FUEL_TYPE_FUEL_EU_MARITIME_MAPPING[fuel_type]
    fuel_data = _DF_GHG_FACTORS_DICTIONARY[organization].query(
        f"pathway_name == '{fuel_type_eu}' and fuel_class == '{fuel_class}'"
    )
    if len(fuel_data) == 0:
        raise ValueError(
            f"The fuel type {fuel_type} and origin {origin} is not available."
        )
    lhv_mj_per_g = fuel_data["LCV"].values[0]

    ghg_emission_factor_well_to_tank_gco2eq_per_mj = fuel_data["CO2_WtT"].values[0]
    ghg_emission_factor_tank_to_wake = [
        GhgEmissionFactorTankToWake(
            fuel_consumer_class=(
                each_data["fuel_consumer_unit_class"] if organization == "eu" else None
            ),
            co2_factor_gco2_per_gfuel=each_data["Cf_CO2"],
            ch4_factor_gch4_per_gfuel=each_data["Cf_CH4"],
            n2o_factor_gn2o_per_gfuel=each_data["Cf_N2O"],
            c_slip_percent=each_data["C_slip"],
        )
        for _, each_data in fuel_data.iterrows()
    ]
    return PrescribedFactors(
        lhv_mj_per_g,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj,
        ghg_emission_factor_tank_to_wake,
    )


def get_ghg_factors_for_fuel_eu_maritime(
    fuel_type: TypeFuel,
    origin: FuelOrigin,
    fuel_consumer_class: FuelConsumerClassFuelEUMaritime,
) -> PrescribedFactors:
    """Get the GHG emission factors for fuel specified by EU Maritime Fuel"""
    fuel_class = _FUEL_CLASS_FUEL_EU_MARITIME_MAPPING[origin]
    fuel_type_eu = _FUEL_TYPE_FUEL_EU_MARITIME_MAPPING[fuel_type]
    fuel_consumer_class_str = _FUEL_CONSUMER_CLASS_FUEL_EU_MARITIME_MAPPING[
        fuel_consumer_class
    ]
    return _DF_GHG_FACTORS_DICTIONARY["eu"].query(
        f"pathway_name == '{fuel_type_eu}' and fuel_class == '{fuel_class}' and fuel_consumer_unit_class == '{fuel_consumer_class_str}'"
    )


@dataclass
class FuelByMassFraction:
    fuels: List[Fuel] = field(default_factory=list)

    def __post_init__(self):
        if len(self.fuels) > 0:
            total_fraction = sum([fuel.mass_or_mass_fraction for fuel in self.fuels])
            total_fraction = np.atleast_1d(total_fraction)
            assert np.allclose(
                total_fraction, 1.0, atol=1e-3
            ), "The mass fraction must sum to 1."
            assert self.fuel_specified_by is not None

    @property
    def fuel_specified_by(self) -> FuelSpecifiedBy:
        if len(self.fuels) > 0:
            fuel_specified_by_list = [fuel.fuel_specified_by for fuel in self.fuels]
            if len(set(fuel_specified_by_list)) > 1:
                if (
                    FuelSpecifiedBy.IMO in fuel_specified_by_list
                    and FuelSpecifiedBy.FUEL_EU_MARITIME in fuel_specified_by_list
                ):
                    raise ValueError("The fuels are specified by both IMO and EU.")
                elif FuelSpecifiedBy.IMO in fuel_specified_by_list:
                    return FuelSpecifiedBy.IMO
                elif FuelSpecifiedBy.FUEL_EU_MARITIME in fuel_specified_by_list:
                    return FuelSpecifiedBy.FUEL_EU_MARITIME
                elif FuelSpecifiedBy.USER in fuel_specified_by_list:
                    return FuelSpecifiedBy.USER
                else:
                    raise ValueError(
                        "The fuel is not specified by any of the available options."
                    )
            else:
                return self.fuels[0].fuel_specified_by
        else:
            return FuelSpecifiedBy.NONE

    @property
    def lhv_mj_per_kg(self):
        """
        Returns the low heat value of fuel based on fuel mass fraction
        """
        return (
            sum([fuel.lhv_mj_per_g * fuel.mass_or_mass_fraction for fuel in self.fuels])
            * 1000
        )

    def get_kg_co2_per_kg_fuel(
        self, fuel_consumer_class: Optional[FuelConsumerClassFuelEUMaritime] = None
    ) -> float:
        """Returns the GHG emission factor from tank to wake in gCO2eq/gfuel as defined by IMO or EU

        Args:
            fuel_consumer_class (FuelConsumerClassFuelEUMaritime, optional): Fuel consumer class.
                It should be provided if the organization is "eu". Defaults to None.

        Returns:
            float: GHG emission factor from tank to wake in gCO2eq/gfuel
        """

        if self.fuel_specified_by == FuelSpecifiedBy.IMO:
            fuel_consumer_class = None
        elif self.fuel_specified_by == FuelSpecifiedBy.FUEL_EU_MARITIME:
            assert (
                fuel_consumer_class is not None
            ), "Please provide the fuel consumer class for EU defined fuel."
        elif self.fuel_specified_by == FuelSpecifiedBy.USER or (
            self.fuel_specified_by == FuelSpecifiedBy.NONE and len(self.fuels) == 0
        ):
            pass
        else:
            raise ValueError(
                "The fuel is not specified by properly for this calculation."
            )
        res = 0
        for fuel in self.fuels:
            # If the fuel contains other fuel than LNG and the consumer is a gas engine,
            # the GHG factor for those fuel should be calculated as generic internal combustion
            # engine (ICE)
            if fuel_consumer_class is not None and "LNG" in fuel_consumer_class.name:
                if fuel.fuel_type != TypeFuel.NATURAL_GAS:
                    res += (
                        fuel.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel(
                            fuel_consumer_class=FuelConsumerClassFuelEUMaritime.ICE
                        )
                        + fuel.ghg_emission_factor_well_to_tank_gco2_per_gfuel
                    ) * fuel.mass_or_mass_fraction
                else:
                    res += (
                        fuel.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel(
                            fuel_consumer_class=fuel_consumer_class
                        )
                        + fuel.ghg_emission_factor_well_to_tank_gco2_per_gfuel
                    ) * fuel.mass_or_mass_fraction
            else:
                res += (
                    fuel.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel(
                        fuel_consumer_class=fuel_consumer_class
                    )
                    + fuel.ghg_emission_factor_well_to_tank_gco2_per_gfuel
                ) * fuel.mass_or_mass_fraction

        return res

    def get_kg_co2_per_kwh_fuel(
        self, fuel_consumer_class: FuelConsumerClassFuelEUMaritime = None
    ) -> float:
        """Returns the GHG emission factor from tank to wake in gCO2eq/gfuel
        as defined by IMO or EU"""
        return (
            1
            / (self.lhv_mj_per_kg / 3.6)
            * self.get_kg_co2_per_kg_fuel(fuel_consumer_class=fuel_consumer_class)
        )

    def get_kg_co2_per_mj_fuel(
        self, fuel_consumer_class: FuelConsumerClassFuelEUMaritime = None
    ) -> float:
        return (
            self.get_kg_co2_per_kwh_fuel(fuel_consumer_class=fuel_consumer_class) / 3.6
        )


@dataclass
class FuelConsumption:
    """
    The FuelConsumption class represents the fuel consumption of a ship.
    The unit of fuel consumption is kg or kg/s depending on the context.
    Please use the unit for the name of the variable.
    """

    fuels: List[Fuel] = field(default_factory=list)

    def __add__(self, other: "FuelConsumption"):
        # Create a new FuelConsumption object with zero fuel consumption
        if len(self.fuels) == 0:
            return FuelConsumption(fuels=[fuel.copy for fuel in other.fuels])
        sum_fuel = FuelConsumption()
        index_fuel_added = []
        for each_fuel in self.fuels:
            try:
                other_fuel = next(
                    filter(
                        lambda x: x.fuel_type == each_fuel.fuel_type
                        and x.origin == each_fuel.origin
                        and x.fuel_specified_by == each_fuel.fuel_specified_by,
                        other.fuels,
                    )
                )
            except StopIteration:
                sum_fuel.fuels.append(each_fuel.copy)
                continue
            index_fuel_added.append(other.fuels.index(other_fuel))
            fuel_to_add = each_fuel.copy
            fuel_to_add.mass_or_mass_fraction += other_fuel.mass_or_mass_fraction
            sum_fuel.fuels.append(fuel_to_add)
        for index, each_fuel in enumerate(other.fuels):
            if index not in index_fuel_added:
                sum_fuel.fuels.append(each_fuel.copy)
        return sum_fuel

    def __mul__(self, other: Union[float, np.ndarray]):
        res = FuelConsumption()
        for fuel in self.fuels:
            fuel_to_add = fuel.copy
            fuel_to_add.mass_or_mass_fraction *= other
            res.fuels.append(fuel_to_add)
        return res

    @property
    def total_fuel_consumption(self) -> Union[float, np.ndarray]:
        """Returns the total fuel consumption in kg or kg/s depending on the context."""
        return np.sum([fuel.mass_or_mass_fraction for fuel in self.fuels], axis=0)

    @property
    def hydrogen(self) -> Union[float, np.ndarray]:
        """Return the hydrogen fuel consumption in kg or kg/s depending on the context."""
        return np.sum(
            [
                fuel.mass_or_mass_fraction
                for fuel in self.fuels
                if fuel.fuel_type == TypeFuel.HYDROGEN
            ],
            axis=0,
        )

    @property
    def diesel(self) -> Union[float, np.ndarray]:
        """Return the diesel fuel consumption in kg or kg/s depending on the context."""
        return np.sum(
            [
                fuel.mass_or_mass_fraction
                for fuel in self.fuels
                if fuel.fuel_type == TypeFuel.DIESEL
            ],
            axis=0,
        )

    @property
    def natural_gas(self) -> Union[float, np.ndarray]:
        """Return the natural gas fuel consumption in kg or kg/s depending on the context."""
        return np.sum(
            [
                fuel.mass_or_mass_fraction
                for fuel in self.fuels
                if fuel.fuel_type == TypeFuel.NATURAL_GAS
            ],
            axis=0,
        )

    @property
    def fuel_by_mass_fraction(self) -> FuelByMassFraction:
        index_fuel_consumption_zero = self.total_fuel_consumption == 0
        fuel_by_mass_fraction = FuelByMassFraction()
        if np.isscalar(index_fuel_consumption_zero):
            if index_fuel_consumption_zero:
                return fuel_by_mass_fraction
            else:
                for fuel in self.fuels:
                    fuel_fraction_to_add = fuel.copy
                    fuel_fraction_to_add.mass_or_mass_fraction /= (
                        self.total_fuel_consumption
                    )
                    fuel_by_mass_fraction.fuels.append(fuel_fraction_to_add)
        else:
            for fuel in self.fuels:
                fuel_fraction_new = fuel.copy
                fuel_fraction_new.mass_or_mass_fraction[
                    ~index_fuel_consumption_zero
                ] = (
                    fuel.mass_or_mass_fraction[~index_fuel_consumption_zero]
                    / self.total_fuel_consumption[~index_fuel_consumption_zero]
                )
                fuel_fraction_new.mass_or_mass_fraction[index_fuel_consumption_zero] = 0
                fuel_by_mass_fraction.fuels.append(fuel_fraction_new)
        return fuel_by_mass_fraction

    @property
    def asdict(self) -> Dict[str, np.ndarray]:
        return {str(fuel): fuel.mass_or_mass_fraction for fuel in self.fuels}

    def get_total_co2_emissions(
        self, fuel_consumer_class: FuelConsumerClassFuelEUMaritime = None
    ) -> Union[float, np.ndarray]:
        """Returns the total CO2 emissions in kg or kg/s depending on the context.

        Args:
            fuel_consumer_class (FuelConsumerClassFuelEUMaritime, optional): Fuel consumer class.
                It should be provided if the organization is "eu". Defaults to None.

        Returns:
            total co2 emission: Total CO2 emissions in kg or kg/s depending on the context.
        """
        return (
            self.total_fuel_consumption
            * self.fuel_by_mass_fraction.get_kg_co2_per_kg_fuel(
                fuel_consumer_class=fuel_consumer_class
            )
        )
