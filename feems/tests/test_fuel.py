import random
from typing import List
import logging

import numpy as np
import pytest
from feems.fuel import (
    FuelByMassFraction,
    FuelConsumption,
    Fuel,
    FuelSpecifiedBy,
    TypeFuel,
    FuelOrigin,
    FuelConsumerClassFuelEUMaritime,
    get_ghg_factors_for_fuel_eu_maritime,
    _GWP100_N2O,
    _GWP100_CH4,
)
from pytest_subtests import SubTests


def test_fuel_class():
    fuel_by_imo = Fuel(
        fuel_type=TypeFuel.DIESEL,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.IMO,
    )
    assert fuel_by_imo.ghg_emission_factor_well_to_tank_gco2_per_gfuel == pytest.approx(0)
    assert len(fuel_by_imo.ghg_emission_factor_tank_to_wake) == 1
    assert fuel_by_imo.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel() == 3.206
    assert fuel_by_imo.lhv_mj_per_g == 0.0427

    fuel_by_eu = Fuel(
        fuel_type=TypeFuel.NATURAL_GAS,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.FUEL_EU_MARITIME,
    )
    assert fuel_by_eu.ghg_emission_factor_well_to_tank_gco2eq_per_mj == pytest.approx(18.5)
    assert len(fuel_by_eu.ghg_emission_factor_tank_to_wake) == 5
    assert fuel_by_eu.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel(
        fuel_consumer_class=FuelConsumerClassFuelEUMaritime.LNG_OTTO_MEDIUM_SPEED,
    ) == pytest.approx((1 - 3.1 / 100) * (2.75 + 0.00011 * _GWP100_N2O) + 3.1 / 100 * _GWP100_CH4)

    for specified_by in [FuelSpecifiedBy.FUEL_EU_MARITIME]:
        print(f"Fuel specified by {specified_by.name}")
        print(
            "fuel_name\tghg_wtt [gCO2eq/gFuel]\tghg_ttw[gCO2/gFuel]\tghg_wtw[gCO2eq/gFuel]\tghg_wtw[gCO2eq/mj]\tlhv[MJ/kg]\torigin"
        )
        for fuel_type in TypeFuel:
            for origin in FuelOrigin:
                if origin not in [FuelOrigin.NONE]:
                    try:
                        fuel = Fuel(
                            fuel_type=fuel_type,
                            origin=origin,
                            fuel_specified_by=specified_by,
                        )
                    except ValueError as e:
                        logging.error(e)
                        continue
                    for fuel_kind_by_consumer in fuel.ghg_emission_factor_tank_to_wake:
                        name = fuel.fuel_type.name
                        origin = fuel.origin.name
                        consumer_type = (
                            fuel_kind_by_consumer.fuel_consumer_class.name
                            if isinstance(
                                fuel_kind_by_consumer.fuel_consumer_class,
                                FuelConsumerClassFuelEUMaritime,
                            )
                            else "None"
                        )
                        ghg_wtt = fuel.ghg_emission_factor_well_to_tank_gco2_per_gfuel
                        ghg_ttw = fuel.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel(
                            fuel_consumer_class=fuel_kind_by_consumer.fuel_consumer_class,
                        )
                        ghg_wtw = ghg_ttw + ghg_wtt
                        ghg_wtw_per_mj = ghg_wtw / fuel.lhv_mj_per_g
                        if specified_by == FuelSpecifiedBy.FUEL_EU_MARITIME:
                            fuel_data = get_ghg_factors_for_fuel_eu_maritime(
                                fuel_type=fuel.fuel_type,
                                origin=fuel.origin,
                                fuel_consumer_class=fuel_kind_by_consumer.fuel_consumer_class,
                            )
                            if not np.isnan(fuel_data.WTW_energy.values[0]):
                                assert fuel_data.WTW_energy.values[0] == pytest.approx(
                                    ghg_wtw_per_mj
                                ), f"WTW energy is not equal for fuel {name}, origin {origin} and consumer {consumer_type} ({fuel_data.WTW_energy.values[0]} != {ghg_wtw_per_mj})"
                        lhv_mj_per_kg = fuel.lhv_mj_per_g * 1000
                        print(
                            f"{name}\t{ghg_wtt:.2f}\t{ghg_ttw:.2f}\t{ghg_wtw}\t{ghg_wtw_per_mj}"
                            f"\t{lhv_mj_per_kg:.2f}\t{origin}\t{consumer_type}"
                        )
        print()


def create_random_fuel_by_mass_fraction(
    number_fuel_type: int = 2,
    fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
    for_fuel_cell: bool = False,
) -> FuelByMassFraction:
    assert number_fuel_type > 0, "Number of fuel types must be greater than 1"
    fuel_types_available_for_test = [
        TypeFuel.DIESEL,
        TypeFuel.NATURAL_GAS,
        TypeFuel.HYDROGEN,
    ]
    if fuel_specified_by == FuelSpecifiedBy.FUEL_EU_MARITIME:
        fuel_types_available_for_test.remove(TypeFuel.HYDROGEN)
    if for_fuel_cell:
        fuel_types_available_for_test = [TypeFuel.HYDROGEN]
    number_fuel_type = min(number_fuel_type, len(fuel_types_available_for_test))
    while True:
        fuel_types = np.random.choice(
            fuel_types_available_for_test, size=number_fuel_type, replace=False
        )
        fuel_list: List[Fuel] = []
        fuel_origins = np.random.choice(
            [FuelOrigin.FOSSIL, FuelOrigin.RENEWABLE_NON_BIO],
            size=number_fuel_type,
            replace=True,
        )
        try:
            for fuel_type, fuel_origin in zip(fuel_types, fuel_origins):
                fuel_list.append(
                    Fuel(
                        fuel_type=fuel_type,
                        origin=fuel_origin,
                        fuel_specified_by=fuel_specified_by,
                    )
                )
        except ValueError:
            continue
        else:
            break
    mass_fraction_left = 1.0
    for index, fuel in enumerate(fuel_list):
        if index == number_fuel_type - 1:
            fuel.mass_or_mass_fraction = mass_fraction_left
        else:
            fuel.mass_or_mass_fraction = mass_fraction_left * random.random()
            mass_fraction_left -= fuel.mass_or_mass_fraction
    return FuelByMassFraction(fuels=fuel_list)


def test_fuel_by_mass_fraction_class(subtests: SubTests):
    with subtests.test(msg="Test fuel with no component"):
        assert (
            FuelByMassFraction(fuels=[])
            .get_kg_co2_per_kg_fuel()
            .well_to_wake_kg_or_gco2eq_per_gfuel
            == 0
        )

    with subtests.test(msg="Test fuel with random components for IMO specified fuels"):
        fuel_by_mass_fraction = create_random_fuel_by_mass_fraction(4)
        ghg_factor_ttw = 0
        ghg_factor_wtt = 0
        lhv = 0
        for fuel in fuel_by_mass_fraction.fuels:
            lhv += fuel.mass_or_mass_fraction * fuel.lhv_mj_per_g * 1000
            ghg_factor_wtt += (
                fuel.mass_or_mass_fraction * fuel.ghg_emission_factor_well_to_tank_gco2_per_gfuel
            )
            ghg_factor_ttw += (
                fuel.mass_or_mass_fraction
                * fuel.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel()
            )
        ghg_factors = fuel_by_mass_fraction.get_kg_co2_per_kg_fuel()
        assert ghg_factors.well_to_tank_kg_or_gco2eq_per_gfuel == pytest.approx(ghg_factor_wtt)
        assert ghg_factors.tank_to_wake_kg_or_gco2eq_per_gfuel == pytest.approx(ghg_factor_ttw)
        assert ghg_factors.well_to_wake_kg_or_gco2eq_per_gfuel == pytest.approx(
            ghg_factor_wtt + ghg_factor_ttw
        )
        assert fuel_by_mass_fraction.lhv_mj_per_kg == pytest.approx(lhv)

    with subtests.test(msg="Test fuel with random components for FuelEU specified fuels"):
        fuel_by_mass_fraction = create_random_fuel_by_mass_fraction(
            number_fuel_type=3, fuel_specified_by=FuelSpecifiedBy.FUEL_EU_MARITIME
        )
        ghg_factor_wtt = 0
        ghg_factor_ttw = 0
        lhv = 0
        fuel_types = [fuel.fuel_type for fuel in fuel_by_mass_fraction.fuels]
        if TypeFuel.NATURAL_GAS in fuel_types:
            fuel_consumer_class = FuelConsumerClassFuelEUMaritime.LNG_OTTO_MEDIUM_SPEED
        elif TypeFuel.HYDROGEN in fuel_types:
            fuel_consumer_class = FuelConsumerClassFuelEUMaritime.FUEL_CELL
        else:
            fuel_consumer_class = FuelConsumerClassFuelEUMaritime.ICE
        for fuel in fuel_by_mass_fraction.fuels:
            lhv += fuel.mass_or_mass_fraction * fuel.lhv_mj_per_g * 1000
            if fuel.fuel_type == TypeFuel.NATURAL_GAS:
                fuel_consumption_class_each = FuelConsumerClassFuelEUMaritime.LNG_OTTO_MEDIUM_SPEED
            elif fuel.fuel_type == TypeFuel.HYDROGEN:
                fuel_consumption_class_each = FuelConsumerClassFuelEUMaritime.FUEL_CELL
            else:
                fuel_consumption_class_each = FuelConsumerClassFuelEUMaritime.ICE
            ghg_factor_wtt += (
                fuel.mass_or_mass_fraction * fuel.ghg_emission_factor_well_to_tank_gco2_per_gfuel
            )
            ghg_factor_ttw += (
                fuel.mass_or_mass_fraction
                * fuel.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel(
                    fuel_consumer_class=fuel_consumption_class_each,
                )
            )
            if np.isnan(ghg_factor_wtt) or np.isnan(ghg_factor_ttw):
                pass
        ghg_factors = fuel_by_mass_fraction.get_kg_co2_per_kg_fuel(
            fuel_consumer_class=fuel_consumer_class
        )
        assert ghg_factors.tank_to_wake_kg_or_gco2eq_per_gfuel == pytest.approx(ghg_factor_ttw)
        assert ghg_factors.well_to_tank_kg_or_gco2eq_per_gfuel == pytest.approx(ghg_factor_wtt)
        assert ghg_factors.well_to_wake_kg_or_gco2eq_per_gfuel == pytest.approx(
            ghg_factor_wtt + ghg_factor_ttw
        )
        assert fuel_by_mass_fraction.lhv_mj_per_kg == pytest.approx(lhv)


def test_fuel_consumption_class():
    # Test FuelConsumption class
    fuel_by_mass_fraction = FuelByMassFraction(
        fuels=[
            Fuel(
                fuel_type=TypeFuel.NATURAL_GAS,
                origin=FuelOrigin.FOSSIL,
                fuel_specified_by=FuelSpecifiedBy.FUEL_EU_MARITIME,
                mass_or_mass_fraction=0.9,
            ),
            Fuel(
                fuel_type=TypeFuel.DIESEL,
                origin=FuelOrigin.FOSSIL,
                fuel_specified_by=FuelSpecifiedBy.FUEL_EU_MARITIME,
                mass_or_mass_fraction=0.1,
            ),
        ]
    )

    total_fuel_consumption_kg = 10
    fuels = [
        Fuel(
            fuel_type=each_fuel_by_mass_fraction.fuel_type,
            origin=each_fuel_by_mass_fraction.origin,
            fuel_specified_by=FuelSpecifiedBy.FUEL_EU_MARITIME,
            mass_or_mass_fraction=each_fuel_by_mass_fraction.mass_or_mass_fraction
            * total_fuel_consumption_kg,
        )
        for each_fuel_by_mass_fraction in fuel_by_mass_fraction.fuels
    ]

    multi_fuel_consumption = FuelConsumption(
        fuels=fuels,
    )

    # Verify the total ghg factor
    total_co2_kg = multi_fuel_consumption.get_total_co2_emissions(
        fuel_consumer_class=FuelConsumerClassFuelEUMaritime.LNG_OTTO_MEDIUM_SPEED
    ).well_to_wake_kg_or_gco2eq_per_gfuel
    total_fuel_energy_mj = sum(
        [fuel.lhv_mj_per_g * fuel.mass_or_mass_fraction * 1e3 for fuel in fuels]
    )
    total_ghg_intensity_gco2_per_mj = total_co2_kg * 1000 / total_fuel_energy_mj
    total_ghg_intensity_gco2_per_gfuel_list = [
        (
            fuel.ghg_emission_factor_well_to_tank_gco2_per_gfuel
            + fuel.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel(
                fuel_consumer_class=(
                    FuelConsumerClassFuelEUMaritime.LNG_OTTO_MEDIUM_SPEED
                    if fuel.fuel_type == TypeFuel.NATURAL_GAS
                    else FuelConsumerClassFuelEUMaritime.ICE
                )
            )
        )
        * fuel_fraction.mass_or_mass_fraction
        for fuel, fuel_fraction in zip(fuels, fuel_by_mass_fraction.fuels)
    ]
    average_lhv_mj_per_g = sum(
        [
            fuel.lhv_mj_per_g * fuel_fraction.mass_or_mass_fraction
            for fuel, fuel_fraction in zip(fuels, fuel_by_mass_fraction.fuels)
        ]
    )
    total_ghg_intensity_gco2_per_mj_expected = (
        sum(total_ghg_intensity_gco2_per_gfuel_list) / average_lhv_mj_per_g
    )
    print(total_ghg_intensity_gco2_per_gfuel_list)
    print(total_ghg_intensity_gco2_per_mj_expected)
    print(total_ghg_intensity_gco2_per_mj)
    assert total_ghg_intensity_gco2_per_mj == pytest.approx(
        total_ghg_intensity_gco2_per_mj_expected
    )
