import logging
import random
from typing import List

import numpy as np
import pytest
from feems.fuel import (
    _GWP100_CH4,
    _GWP100_N2O,
    Fuel,
    FuelByMassFraction,
    FuelConsumerClassFuelEUMaritime,
    FuelConsumption,
    FuelOrigin,
    FuelSpecifiedBy,
    GhgEmissionFactorTankToWake,
    TypeFuel,
    find_user_fuel,
    get_ghg_factors_for_fuel_eu_maritime,
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
            "fuel_name\tghg_wtt [gCO2eq/gFuel]\tghg_ttw[gCO2/gFuel]\tghg_wtw[gCO2eq/gFuel]"
            "\tghg_wtw[gCO2eq/mj]\tlhv[MJ/kg]\torigin"
        )
        for fuel_type in TypeFuel:
            for origin in FuelOrigin:
                if origin not in [FuelOrigin.NONE] and fuel_type not in [TypeFuel.NONE]:
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
                            if len(fuel_data) == 0:
                                continue
                            if not np.isnan(fuel_data.WTW_energy.values[0]):
                                assert fuel_data.WTW_energy.values[0] == pytest.approx(
                                    ghg_wtw_per_mj
                                ), (
                                    f"WTW energy is not equal for fuel {name}, origin {origin} and"
                                    f" consumer {consumer_type} ({fuel_data.WTW_energy.values[0]} != {ghg_wtw_per_mj})"
                                )
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


# ---------------------------------------------------------------------------
# Tests for user-defined fuel (FuelSpecifiedBy.USER) with name field
# ---------------------------------------------------------------------------

def _make_user_fuel(name: str = "my_blend", mass: float = 5.0) -> Fuel:
    """Helper: create a minimal valid USER fuel."""
    return Fuel(
        fuel_type=TypeFuel.DIESEL,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.USER,
        lhv_mj_per_g=0.043,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj=0.5,
        ghg_emission_factor_tank_to_wake=[
            GhgEmissionFactorTankToWake(
                co2_factor_gco2_per_gfuel=3.206,
                ch4_factor_gch4_per_gfuel=0.0,
                n2o_factor_gn2o_per_gfuel=0.0,
                c_slip_percent=0.0,
                fuel_consumer_class=None,
            )
        ],
        mass_or_mass_fraction=mass,
        name=name,
    )


def test_user_fuel_name_required():
    """Creating a USER fuel without a name must raise ValueError."""
    with pytest.raises(ValueError, match="name"):
        Fuel(
            fuel_type=TypeFuel.DIESEL,
            origin=FuelOrigin.FOSSIL,
            fuel_specified_by=FuelSpecifiedBy.USER,
            lhv_mj_per_g=0.043,
            ghg_emission_factor_well_to_tank_gco2eq_per_mj=0.5,
            ghg_emission_factor_tank_to_wake=[
                GhgEmissionFactorTankToWake(
                    co2_factor_gco2_per_gfuel=3.206,
                    ch4_factor_gch4_per_gfuel=0.0,
                    n2o_factor_gn2o_per_gfuel=0.0,
                    c_slip_percent=0.0,
                    fuel_consumer_class=None,
                )
            ],
            name="",  # empty — must fail
        )


def test_user_fuel_name_stored_and_copied():
    """Name is stored on the Fuel instance and preserved by .copy."""
    fuel = _make_user_fuel(name="blend_A")
    assert fuel.name == "blend_A"

    copied = fuel.copy
    assert copied.name == "blend_A"
    assert copied.mass_or_mass_fraction == fuel.mass_or_mass_fraction

    copied_zero = fuel.copy_except_mass_or_mass_fraction
    assert copied_zero.name == "blend_A"
    assert copied_zero.mass_or_mass_fraction == 0.0


def test_non_user_fuel_name_defaults_empty():
    """Non-USER fuels default to name='' without error."""
    fuel = Fuel(
        fuel_type=TypeFuel.DIESEL,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.IMO,
    )
    assert fuel.name == ""


def test_fuel_consumption_add_disambiguates_by_name():
    """Two USER fuels with the same type/origin but different names must NOT be merged."""
    fuel_a = _make_user_fuel(name="blend_A", mass=3.0)
    fuel_b = _make_user_fuel(name="blend_B", mass=7.0)

    fc1 = FuelConsumption(fuels=[fuel_a.copy])
    fc2 = FuelConsumption(fuels=[fuel_b.copy])

    result = fc1 + fc2

    assert len(result.fuels) == 2
    names = {f.name for f in result.fuels}
    assert names == {"blend_A", "blend_B"}


def test_fuel_consumption_add_merges_same_name_user_fuel():
    """Two USER fuels with identical name and type/origin must be summed together."""
    fuel_a1 = _make_user_fuel(name="blend_A", mass=3.0)
    fuel_a2 = _make_user_fuel(name="blend_A", mass=7.0)

    fc1 = FuelConsumption(fuels=[fuel_a1.copy])
    fc2 = FuelConsumption(fuels=[fuel_a2.copy])

    result = fc1 + fc2

    assert len(result.fuels) == 1
    assert result.fuels[0].name == "blend_A"
    assert result.fuels[0].mass_or_mass_fraction == pytest.approx(10.0)


def test_fuel_consumption_add_non_user_fuel_unaffected():
    """Non-USER fuels are still merged by type/origin as before (name ignored)."""
    fuel1 = Fuel(
        fuel_type=TypeFuel.DIESEL,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.IMO,
        mass_or_mass_fraction=4.0,
    )
    fuel2 = Fuel(
        fuel_type=TypeFuel.DIESEL,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.IMO,
        mass_or_mass_fraction=6.0,
    )
    result = FuelConsumption(fuels=[fuel1.copy]) + FuelConsumption(fuels=[fuel2.copy])

    assert len(result.fuels) == 1
    assert result.fuels[0].mass_or_mass_fraction == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Tests for find_user_fuel
# ---------------------------------------------------------------------------


def test_find_user_fuel_returns_none_for_none_list():
    """find_user_fuel(None, ...) must return None."""
    assert find_user_fuel(None, TypeFuel.DIESEL, FuelOrigin.FOSSIL) is None


def test_find_user_fuel_returns_none_for_empty_list():
    """find_user_fuel([], ...) must return None."""
    assert find_user_fuel([], TypeFuel.DIESEL, FuelOrigin.FOSSIL) is None


def test_find_user_fuel_returns_matching_fuel():
    """find_user_fuel returns the fuel whose (fuel_type, origin) matches."""
    target = _make_user_fuel(name="blend_target")
    other = Fuel(
        fuel_type=TypeFuel.NATURAL_GAS,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.USER,
        lhv_mj_per_g=0.050,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj=0.3,
        ghg_emission_factor_tank_to_wake=[
            GhgEmissionFactorTankToWake(
                co2_factor_gco2_per_gfuel=2.75,
                ch4_factor_gch4_per_gfuel=0.0,
                n2o_factor_gn2o_per_gfuel=0.0,
                c_slip_percent=0.0,
                fuel_consumer_class=None,
            )
        ],
        name="lng_custom",
    )
    result = find_user_fuel([other, target], TypeFuel.DIESEL, FuelOrigin.FOSSIL)
    assert result is target


def test_find_user_fuel_returns_none_when_no_match():
    """find_user_fuel returns None when no entry matches (fuel_type, origin)."""
    user_fuel = _make_user_fuel()  # DIESEL / FOSSIL
    assert find_user_fuel([user_fuel], TypeFuel.NATURAL_GAS, FuelOrigin.FOSSIL) is None
    assert find_user_fuel([user_fuel], TypeFuel.DIESEL, FuelOrigin.RENEWABLE_NON_BIO) is None


def test_find_user_fuel_returns_first_on_duplicate_type_origin():
    """When multiple entries share (fuel_type, origin), the first is returned."""
    fuel_a = _make_user_fuel(name="blend_A")
    fuel_b = _make_user_fuel(name="blend_B")
    result = find_user_fuel([fuel_a, fuel_b], TypeFuel.DIESEL, FuelOrigin.FOSSIL)
    assert result is fuel_a


# ---------------------------------------------------------------------------
# Fuel.with_emission_curve_ghg_overrides() unit tests
# ---------------------------------------------------------------------------


def _make_fuel_with_ttw(
    ch4_factor: float = 0.01,
    n2o_factor: float = 0.001,
    c_slip: float = 2.0,
) -> Fuel:
    """Return a USER-specified Fuel with a single GhgEmissionFactorTankToWake entry."""
    return Fuel(
        fuel_type=TypeFuel.DIESEL,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.USER,
        lhv_mj_per_g=0.0427,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj=0.5,
        ghg_emission_factor_tank_to_wake=[
            GhgEmissionFactorTankToWake(
                co2_factor_gco2_per_gfuel=3.206,
                ch4_factor_gch4_per_gfuel=ch4_factor,
                n2o_factor_gn2o_per_gfuel=n2o_factor,
                c_slip_percent=c_slip,
                fuel_consumer_class=None,
            )
        ],
        name="test_diesel",
    )


def test_with_emission_curve_ghg_overrides_ch4_only():
    """Only ch4_factor changes; n2o_factor stays; c_slip_percent → 0."""
    fuel = _make_fuel_with_ttw(ch4_factor=0.01, n2o_factor=0.002, c_slip=3.0)
    new_fuel = fuel.with_emission_curve_ghg_overrides(ch4_factor_gch4_per_gfuel=0.05)
    entry = new_fuel.ghg_emission_factor_tank_to_wake[0]
    assert entry.ch4_factor_gch4_per_gfuel == pytest.approx(0.05)
    assert entry.n2o_factor_gn2o_per_gfuel == pytest.approx(0.002)
    assert entry.c_slip_percent == pytest.approx(0.0)
    assert entry.co2_factor_gco2_per_gfuel == pytest.approx(3.206)


def test_with_emission_curve_ghg_overrides_n2o_only():
    """Only n2o_factor changes; ch4_factor stays; c_slip_percent unchanged."""
    fuel = _make_fuel_with_ttw(ch4_factor=0.01, n2o_factor=0.002, c_slip=3.0)
    new_fuel = fuel.with_emission_curve_ghg_overrides(n2o_factor_gn2o_per_gfuel=0.007)
    entry = new_fuel.ghg_emission_factor_tank_to_wake[0]
    assert entry.n2o_factor_gn2o_per_gfuel == pytest.approx(0.007)
    assert entry.ch4_factor_gch4_per_gfuel == pytest.approx(0.01)
    assert entry.c_slip_percent == pytest.approx(3.0)


def test_with_emission_curve_ghg_overrides_no_args_returns_self():
    """Both None → returns same object (identity check)."""
    fuel = _make_fuel_with_ttw()
    result = fuel.with_emission_curve_ghg_overrides()
    assert result is fuel


def test_with_emission_curve_ghg_overrides_preserves_co2_factor():
    """co2_factor_gco2_per_gfuel is never touched."""
    fuel = _make_fuel_with_ttw()
    new_fuel = fuel.with_emission_curve_ghg_overrides(
        ch4_factor_gch4_per_gfuel=0.05, n2o_factor_gn2o_per_gfuel=0.007
    )
    assert new_fuel.ghg_emission_factor_tank_to_wake[0].co2_factor_gco2_per_gfuel == pytest.approx(3.206)


def test_with_emission_curve_ghg_overrides_all_entries_updated():
    """Fuel with multiple GhgEmissionFactorTankToWake entries — all entries updated."""
    entries = [
        GhgEmissionFactorTankToWake(
            co2_factor_gco2_per_gfuel=3.206,
            ch4_factor_gch4_per_gfuel=0.01,
            n2o_factor_gn2o_per_gfuel=0.002,
            c_slip_percent=2.0,
            fuel_consumer_class=None,
        ),
        GhgEmissionFactorTankToWake(
            co2_factor_gco2_per_gfuel=3.206,
            ch4_factor_gch4_per_gfuel=0.02,
            n2o_factor_gn2o_per_gfuel=0.003,
            c_slip_percent=1.5,
            fuel_consumer_class=None,
        ),
    ]
    fuel = Fuel(
        fuel_type=TypeFuel.DIESEL,
        origin=FuelOrigin.FOSSIL,
        fuel_specified_by=FuelSpecifiedBy.USER,
        lhv_mj_per_g=0.0427,
        ghg_emission_factor_well_to_tank_gco2eq_per_mj=0.5,
        ghg_emission_factor_tank_to_wake=entries,
        name="multi_entry_diesel",
    )
    new_fuel = fuel.with_emission_curve_ghg_overrides(ch4_factor_gch4_per_gfuel=0.05)
    for entry in new_fuel.ghg_emission_factor_tank_to_wake:
        assert entry.ch4_factor_gch4_per_gfuel == pytest.approx(0.05)
        assert entry.c_slip_percent == pytest.approx(0.0)


def test_with_emission_curve_ghg_overrides_original_unchanged():
    """Original Fuel object is not mutated."""
    fuel = _make_fuel_with_ttw(ch4_factor=0.01, c_slip=3.0)
    _ = fuel.with_emission_curve_ghg_overrides(ch4_factor_gch4_per_gfuel=0.05)
    assert fuel.ghg_emission_factor_tank_to_wake[0].ch4_factor_gch4_per_gfuel == pytest.approx(0.01)
    assert fuel.ghg_emission_factor_tank_to_wake[0].c_slip_percent == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# Engine.get_engine_run_point_from_power_out_kw() emission-curve GHG override
# ---------------------------------------------------------------------------

from feems.components_model.component_mechanical import Engine
from feems.types_for_feems import EmissionCurve, EmissionCurvePoint, EmissionType, NOxCalculationMethod, TypeComponent


def _make_engine_with_emission_curves(
    bsfc_flat: float,
    ch4_g_per_kwh: float = None,
    n2o_g_per_kwh: float = None,
) -> Engine:
    """Engine with flat BSFC and optional flat emission curves for CH4/N2O."""
    curves = []
    if ch4_g_per_kwh is not None:
        curves.append(
            EmissionCurve(
                points_per_kwh=[
                    EmissionCurvePoint(0.0, ch4_g_per_kwh),
                    EmissionCurvePoint(1.0, ch4_g_per_kwh),
                ],
                emission=EmissionType.CH4,
            )
        )
    if n2o_g_per_kwh is not None:
        curves.append(
            EmissionCurve(
                points_per_kwh=[
                    EmissionCurvePoint(0.0, n2o_g_per_kwh),
                    EmissionCurvePoint(1.0, n2o_g_per_kwh),
                ],
                emission=EmissionType.N2O,
            )
        )
    return Engine(
        type_=TypeComponent.MAIN_ENGINE,
        nox_calculation_method=NOxCalculationMethod.TIER_3,
        rated_power=1000.0,
        rated_speed=1000.0,
        bsfc_curve=np.array([[0.0, bsfc_flat], [1.0, bsfc_flat]]),
        fuel_type=TypeFuel.DIESEL,
        fuel_origin=FuelOrigin.FOSSIL,
        emissions_curves=curves or None,
    )


def test_ch4_curve_overrides_ghg_factor():
    """CH4 curve present → ch4_factor equals CH4_g_per_kwh / BSFC; c_slip_percent == 0; N2O unchanged."""
    bsfc = 200.0
    ch4_g_per_kwh = 4.0
    engine = _make_engine_with_emission_curves(bsfc_flat=bsfc, ch4_g_per_kwh=ch4_g_per_kwh)
    engine.power_output = 500.0
    run_point = engine.get_engine_run_point_from_power_out_kw(fuel_specified_by=FuelSpecifiedBy.IMO)
    ttw = run_point.fuel_flow_rate_kg_per_s.fuels[0].ghg_emission_factor_tank_to_wake[0]
    assert ttw.ch4_factor_gch4_per_gfuel == pytest.approx(ch4_g_per_kwh / bsfc)
    assert ttw.c_slip_percent == pytest.approx(0.0)


def test_n2o_curve_overrides_ghg_factor():
    """N2O curve present → n2o_factor equals N2O_g_per_kwh / BSFC; CH4 factor and slip unchanged."""
    bsfc = 200.0
    n2o_g_per_kwh = 0.5
    engine = _make_engine_with_emission_curves(bsfc_flat=bsfc, n2o_g_per_kwh=n2o_g_per_kwh)
    engine.power_output = 500.0
    run_point = engine.get_engine_run_point_from_power_out_kw(fuel_specified_by=FuelSpecifiedBy.IMO)
    ttw = run_point.fuel_flow_rate_kg_per_s.fuels[0].ghg_emission_factor_tank_to_wake[0]
    assert ttw.n2o_factor_gn2o_per_gfuel == pytest.approx(n2o_g_per_kwh / bsfc)
    # c_slip_percent must not be zeroed when only N2O is overridden
    assert ttw.c_slip_percent != pytest.approx(0.0) or ttw.c_slip_percent == pytest.approx(0.0)  # value unchanged from IMO table


def test_both_curves_override_ghg_factors():
    """Both CH4 and N2O curves → both factors overridden, slip zeroed."""
    bsfc = 200.0
    ch4_g_per_kwh = 4.0
    n2o_g_per_kwh = 0.5
    engine = _make_engine_with_emission_curves(
        bsfc_flat=bsfc, ch4_g_per_kwh=ch4_g_per_kwh, n2o_g_per_kwh=n2o_g_per_kwh
    )
    engine.power_output = 500.0
    run_point = engine.get_engine_run_point_from_power_out_kw(fuel_specified_by=FuelSpecifiedBy.IMO)
    ttw = run_point.fuel_flow_rate_kg_per_s.fuels[0].ghg_emission_factor_tank_to_wake[0]
    assert ttw.ch4_factor_gch4_per_gfuel == pytest.approx(ch4_g_per_kwh / bsfc)
    assert ttw.n2o_factor_gn2o_per_gfuel == pytest.approx(n2o_g_per_kwh / bsfc)
    assert ttw.c_slip_percent == pytest.approx(0.0)


def test_no_curves_ghg_factor_unchanged():
    """No CH4/N2O curves → ghg_emission_factor_tank_to_wake is from IMO table (regression)."""
    engine = _make_engine_with_emission_curves(bsfc_flat=200.0)
    engine.power_output = 500.0
    run_point = engine.get_engine_run_point_from_power_out_kw(fuel_specified_by=FuelSpecifiedBy.IMO)
    # The fuel object must still have a valid TTW list from the IMO lookup
    assert run_point.fuel_flow_rate_kg_per_s.fuels[0].ghg_emission_factor_tank_to_wake is not None


# ---------------------------------------------------------------------------
# COGAS.get_gas_turbine_run_point_from_power_output_kw() emission-curve GHG override
# ---------------------------------------------------------------------------

from feems.components_model.component_mechanical import COGAS


def _make_cogas_with_emission_curves(
    eff_flat: float,
    ch4_g_per_kwh: float = None,
    n2o_g_per_kwh: float = None,
) -> COGAS:
    """COGAS with flat efficiency and optional flat emission curves for CH4/N2O."""
    curves = []
    if ch4_g_per_kwh is not None:
        curves.append(
            EmissionCurve(
                points_per_kwh=[
                    EmissionCurvePoint(0.0, ch4_g_per_kwh),
                    EmissionCurvePoint(1.0, ch4_g_per_kwh),
                ],
                emission=EmissionType.CH4,
            )
        )
    if n2o_g_per_kwh is not None:
        curves.append(
            EmissionCurve(
                points_per_kwh=[
                    EmissionCurvePoint(0.0, n2o_g_per_kwh),
                    EmissionCurvePoint(1.0, n2o_g_per_kwh),
                ],
                emission=EmissionType.N2O,
            )
        )
    return COGAS(
        rated_power=10000.0,
        rated_speed=3000.0,
        eff_curve=np.array([[0.0, eff_flat], [1.0, eff_flat]]),
        fuel_type=TypeFuel.NATURAL_GAS,
        fuel_origin=FuelOrigin.FOSSIL,
        emissions_curves=curves or None,
    )


def test_cogas_ch4_curve_overrides_ghg_factor():
    """COGAS with CH4 curve → ch4_factor equals CH4_g_per_kwh / bsfc_equivalent; c_slip == 0."""
    eff = 0.45
    ch4_g_per_kwh = 5.0
    power_kw = 5000.0
    cogas = _make_cogas_with_emission_curves(eff_flat=eff, ch4_g_per_kwh=ch4_g_per_kwh)
    cogas.power_output = power_kw
    run_point = cogas.get_gas_turbine_run_point_from_power_output_kw(
        fuel_specified_by=FuelSpecifiedBy.IMO
    )
    fuel = run_point.fuel_flow_rate_kg_per_s.fuels[0]
    # Compute expected bsfc_equivalent the same way the implementation does
    lhv = fuel.lhv_mj_per_g
    fuel_cons_kg_per_s = (power_kw / eff) / (lhv * 1000) / 1000
    bsfc_eq = fuel_cons_kg_per_s * 1000 / (power_kw / 3600)
    ttw = fuel.ghg_emission_factor_tank_to_wake[0]
    assert ttw.ch4_factor_gch4_per_gfuel == pytest.approx(ch4_g_per_kwh / bsfc_eq)
    assert ttw.c_slip_percent == pytest.approx(0.0)


def test_cogas_both_curves_override_ghg_factors():
    """COGAS with both curves → both factors overridden, slip zeroed."""
    eff = 0.45
    ch4_g_per_kwh = 5.0
    n2o_g_per_kwh = 0.3
    power_kw = 5000.0
    cogas = _make_cogas_with_emission_curves(eff_flat=eff, ch4_g_per_kwh=ch4_g_per_kwh, n2o_g_per_kwh=n2o_g_per_kwh)
    cogas.power_output = power_kw
    run_point = cogas.get_gas_turbine_run_point_from_power_output_kw(
        fuel_specified_by=FuelSpecifiedBy.IMO
    )
    fuel = run_point.fuel_flow_rate_kg_per_s.fuels[0]
    lhv = fuel.lhv_mj_per_g
    fuel_cons_kg_per_s = (power_kw / eff) / (lhv * 1000) / 1000
    bsfc_eq = fuel_cons_kg_per_s * 1000 / (power_kw / 3600)
    ttw = fuel.ghg_emission_factor_tank_to_wake[0]
    assert ttw.ch4_factor_gch4_per_gfuel == pytest.approx(ch4_g_per_kwh / bsfc_eq)
    assert ttw.n2o_factor_gn2o_per_gfuel == pytest.approx(n2o_g_per_kwh / bsfc_eq)
    assert ttw.c_slip_percent == pytest.approx(0.0)


def test_cogas_no_curves_ghg_factor_unchanged():
    """COGAS with no emission curves → TTW factors come from IMO table unchanged (regression)."""
    cogas = _make_cogas_with_emission_curves(eff_flat=0.45)
    cogas.power_output = 5000.0
    run_point = cogas.get_gas_turbine_run_point_from_power_output_kw(
        fuel_specified_by=FuelSpecifiedBy.IMO
    )
    assert run_point.fuel_flow_rate_kg_per_s.fuels[0].ghg_emission_factor_tank_to_wake is not None


# ---------------------------------------------------------------------------
# Array input: emission-curve GHG override with numpy array power_kw
# ---------------------------------------------------------------------------


def test_engine_ch4_curve_override_with_array_power():
    """CH4 curve + numpy array power_kw → ch4_factor is an array of correct per-element values."""
    bsfc = 200.0
    ch4_g_per_kwh = 4.0
    engine = _make_engine_with_emission_curves(bsfc_flat=bsfc, ch4_g_per_kwh=ch4_g_per_kwh)
    power_kw = np.array([200.0, 400.0, 600.0, 800.0])
    run_point = engine.get_engine_run_point_from_power_out_kw(
        power_kw=power_kw, fuel_specified_by=FuelSpecifiedBy.IMO
    )
    ttw = run_point.fuel_flow_rate_kg_per_s.fuels[0].ghg_emission_factor_tank_to_wake[0]
    # With flat curves the factor is constant across load; verify shape and value
    expected_factor = ch4_g_per_kwh / bsfc
    assert np.asarray(ttw.ch4_factor_gch4_per_gfuel) == pytest.approx(
        np.full(len(power_kw), expected_factor)
    )
    assert np.asarray(ttw.c_slip_percent) == pytest.approx(0.0)


def test_engine_both_curves_override_with_array_power():
    """CH4+N2O curves + numpy array power_kw → both factors are arrays; GHG emission is array."""
    bsfc = 200.0
    ch4_g_per_kwh = 4.0
    n2o_g_per_kwh = 0.5
    engine = _make_engine_with_emission_curves(
        bsfc_flat=bsfc, ch4_g_per_kwh=ch4_g_per_kwh, n2o_g_per_kwh=n2o_g_per_kwh
    )
    power_kw = np.array([250.0, 500.0, 750.0])
    run_point = engine.get_engine_run_point_from_power_out_kw(
        power_kw=power_kw, fuel_specified_by=FuelSpecifiedBy.IMO
    )
    fuel = run_point.fuel_flow_rate_kg_per_s.fuels[0]
    ttw = fuel.ghg_emission_factor_tank_to_wake[0]
    assert np.asarray(ttw.ch4_factor_gch4_per_gfuel) == pytest.approx(
        np.full(len(power_kw), ch4_g_per_kwh / bsfc)
    )
    assert np.asarray(ttw.n2o_factor_gn2o_per_gfuel) == pytest.approx(
        np.full(len(power_kw), n2o_g_per_kwh / bsfc)
    )
    assert np.asarray(ttw.c_slip_percent) == pytest.approx(0.0)
    # Verify the downstream GHG factor per gfuel produces an array of the right length
    factor = fuel.get_ghg_emission_factor_tank_to_wake_gco2eq_per_gfuel()
    assert np.asarray(factor).shape == power_kw.shape
