import os
import random

import numpy as np
import pandas as pd
from feems.components_model.component_electric import (
    COGES,
    ElectricComponent,
    ElectricMachine,
    Genset,
)
from feems.components_model.component_mechanical import (
    COGAS,
    EngineMultiFuel,
    FuelCharacteristics,
    SteamBoiler,
)
from feems.fuel import FuelOrigin, FuelSpecifiedBy, TypeFuel
from feems.system_model import ElectricPowerSystem, FuelOption
from feems.types_for_feems import EngineCycleType, TypeComponent, TypePower
from MachSysS.convert_to_feems import convert_proto_propulsion_system_to_feems
from MachSysS.gymir_result_pb2 import (
    GymirResult,
    PropulsionPowerInstance,
    PropulsionPowerInstanceForMultiplePropulsors,
    SimulationInstance,
    TimeSeriesResult,
    TimeSeriesResultForMultiplePropulsors,
)
from MachSysS.utility import retrieve_machinery_system_from_file
from RunFeemsSim.machinery_calculation import (
    MachineryCalculation,
    convert_gymir_result_to_propulsion_power_series,
)

# Set seed for reproducibility
random.seed(42)
np.random.seed(42)

def create_gymir_result() -> GymirResult:
    return GymirResult(
        name="test",
        auxiliary_load_kw=random.random() * 500,
        result=[
            SimulationInstance(epoch_s=100 * index + 1, power_kw=2000 * random.random())
            for index, _ in enumerate(range(10))
        ],
    )

def test_convert_gymir_result_to_propulsion_power_series():
    gymir_result = create_gymir_result()
    propulsion_power = convert_gymir_result_to_propulsion_power_series(gymir_result)
    assert len(gymir_result.result) == len(propulsion_power)

def test_machinery_calculation_from_gymir_result():
    gymir_result = create_gymir_result()
    package_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(package_dir, "system_proto.mss")
    
    system_proto = retrieve_machinery_system_from_file(path)
    system_feems = convert_proto_propulsion_system_to_feems(system_proto)
    machinery_calculation = MachineryCalculation(feems_system=system_feems)
    
    res = machinery_calculation.calculate_machinery_system_output_from_gymir_result(
        gymir_result=gymir_result
    )
    
    average_power_consumption = 0
    running_hours_mean = 0
    for power_source in machinery_calculation.electric_system.power_sources:
        running_hours_mean += (power_source.power_output > 0).mean()
    for propulsor in machinery_calculation.electric_system.propulsion_drives:
        average_power_consumption += propulsor.power_input.mean()
    
    # Avoid division by zero if duration or consumption is 0 (though unlikely with random)
    if average_power_consumption > 0 and res.duration_s > 0:
        average_bsfc_for_engines = res.fuel_consumption_total_kg / (
            res.duration_s / 3600000 * average_power_consumption / 0.95
        )
        assert 200 < average_bsfc_for_engines < 385

def test_machinery_calculation_formats_and_consistency():
    gymir_result = create_gymir_result()
    propulsion_power = convert_gymir_result_to_propulsion_power_series(gymir_result)
    
    package_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(package_dir, "system_proto.mss")
    system_proto = retrieve_machinery_system_from_file(path)
    system_feems = convert_proto_propulsion_system_to_feems(system_proto)
    machinery_calculation = MachineryCalculation(feems_system=system_feems)
    
    # 1. Scalar Auxiliary Power
    auxiliary_power_kw = 100
    res_scalar_aux = (
        machinery_calculation.calculate_machinery_system_output_from_propulsion_power_time_series(
            propulsion_power=propulsion_power, auxiliary_power_kw=auxiliary_power_kw
        )
    )
    
    # 2. Array Auxiliary Power
    auxiliary_power_kw_array = np.ones(len(propulsion_power)) * 100
    res_array_aux = (
        machinery_calculation.calculate_machinery_system_output_from_propulsion_power_time_series(
            propulsion_power=propulsion_power, auxiliary_power_kw=auxiliary_power_kw_array
        )
    )
    
    # 3. DataFrame
    propulsor_names = [propulsion_drive.name for propulsion_drive in system_feems.propulsion_drives]
    # Distribute power equally (just for test structure)
    data = np.array([propulsion_power.values / len(propulsor_names) for _ in propulsor_names])
    propulsion_power_df = pd.DataFrame(
        data=data.T,
        index=propulsion_power.index,
        columns=propulsor_names,
    )
    res_df = machinery_calculation.calculate_machinery_system_output_from_propulsion_power_time_series(
        propulsion_power=propulsion_power_df,
        auxiliary_power_kw=auxiliary_power_kw_array,
    )
    
    # 4. Proto
    time_series = TimeSeriesResultForMultiplePropulsors(
        propulsion_power_timeseries=[
            PropulsionPowerInstanceForMultiplePropulsors(
                epoch_s=index,
                propulsion_power_kw=row.values.tolist(),
                auxiliary_power_kw=each_aux_power,
            )
            for (index, row), each_aux_power in zip(propulsion_power_df.iterrows(), auxiliary_power_kw_array)
        ],
        propulsor_names=propulsion_power_df.columns.tolist(),
    )
    res_proto = machinery_calculation.calculate_machinery_system_output_from_time_series_result(
        time_series=time_series,
        fuel_specified_by=FuelSpecifiedBy.IMO,
    )
    
    # Assertions
    assert np.allclose(
        res_scalar_aux.fuel_consumption_total_kg,
        res_array_aux.fuel_consumption_total_kg,
    ), "Fuel consumption for scalar and array auxiliary power should be the same."

    assert np.allclose(
        res_scalar_aux.fuel_consumption_total_kg,
        res_df.fuel_consumption_total_kg,
    ), "Fuel consumption for scalar auxiliary power and dataframe should be the same."

    assert np.allclose(
        res_scalar_aux.fuel_consumption_total_kg,
        res_proto.fuel_consumption_total_kg,
    ), "Fuel consumption for scalar auxiliary power and proto should be the same."

def test_machinery_calculation_proto_time_series_result():
    package_dir = os.path.dirname(os.path.abspath(__file__))
    path_to_system = os.path.join(package_dir, "mechanical_propulsion_with_electric_system.mss")
    system_proto = retrieve_machinery_system_from_file(path_to_system)
    system_feems = convert_proto_propulsion_system_to_feems(system_proto)

    path_to_result = os.path.join(package_dir, "time_series_result.pb")
    with open(path_to_result, "rb") as file:
        time_series_result = TimeSeriesResult()
        time_series_result.ParseFromString(file.read())

    machinery_calculation = MachineryCalculation(feems_system=system_feems)
    res = machinery_calculation.calculate_machinery_system_output_from_time_series_result(
        time_series=time_series_result
    )
    
    total_energy_consumption_kwh = (
        np.array(
            [
                [prop_power_inst.propulsion_power_kw, prop_power_inst.auxiliary_power_kw]
                for prop_power_inst in time_series_result.propulsion_power_timeseries
            ]
        )
        * 60
        / 3600
    )
    total_propulsion_energy_consumption_kwh = np.sum(total_energy_consumption_kwh[:, 0])
    total_auxiliary_energy_consumption_kwh = np.sum(total_energy_consumption_kwh[:, 1])
    
    average_bsfc_for_main_engine = (
        res.mechanical_system.multi_fuel_consumption_total_kg.natural_gas
        / total_propulsion_energy_consumption_kwh
        * 1000
    )
    average_pilot_bsfc_for_main_engine = (
        res.mechanical_system.multi_fuel_consumption_total_kg.diesel
        / total_propulsion_energy_consumption_kwh
        * 1000
    )
    average_bsfc_for_auxiliary_engines = (
        res.electric_system.multi_fuel_consumption_total_kg.natural_gas
        / total_auxiliary_energy_consumption_kwh
        * 1000
        * 0.95
    )
    
    assert 150 > average_bsfc_for_main_engine > 140
    assert 1.0 > average_pilot_bsfc_for_main_engine > 0.7
    assert 224 > average_bsfc_for_auxiliary_engines > 210

def test_machinery_calculation_multifuel():
    package_dir = os.path.dirname(os.path.abspath(__file__))
    path_to_system = os.path.join(package_dir, "mechanical_propulsion_with_electric_system.mss")
    system_proto = retrieve_machinery_system_from_file(path_to_system)
    system_feems = convert_proto_propulsion_system_to_feems(system_proto)
    
    # --- Config Multi-Fuel ---
    main_engine = system_feems.mechanical_system.main_engines[0]
    bsfc_vlsfo = main_engine.engine.specific_fuel_consumption_points.copy()
    bsfc_vlsfo[:, 1] *= 48 / 41  # Assume 41.7 MJ/kg for VLSFO
    multi_fuel_main_engine = EngineMultiFuel(
        type_=TypeComponent.MAIN_ENGINE,
        name=main_engine.engine.name,
        rated_power=main_engine.engine.rated_power,
        rated_speed=main_engine.engine.rated_speed,
        multi_fuel_characteristics=[
            FuelCharacteristics(
                main_fuel_type=TypeFuel.NATURAL_GAS,
                main_fuel_origin=FuelOrigin.FOSSIL,
                pilot_fuel_type=TypeFuel.DIESEL,
                pilot_fuel_origin=FuelOrigin.FOSSIL,
                bsfc_curve=main_engine.engine.specific_fuel_consumption_points,
                bspfc_curve=main_engine.engine.specific_pilot_fuel_consumption_points,
                engine_cycle_type=EngineCycleType.OTTO,
            ),
            FuelCharacteristics(
                main_fuel_type=TypeFuel.VLSFO,
                main_fuel_origin=FuelOrigin.FOSSIL,
                bsfc_curve=bsfc_vlsfo,
                engine_cycle_type=EngineCycleType.OTTO,
            ),
        ],
    )
    main_engine.engine = multi_fuel_main_engine

    aux_engine = system_feems.electric_system.power_sources[0].aux_engine
    bspfc_curve = np.array([[0, 0], [0.25, 1.7], [0.5, 1.2], [0.75, 0.8], [1.0, 0.6]])
    bsfc_vlsfo_aux = aux_engine.specific_fuel_consumption_points.copy()
    bsfc_vlsfo_aux[:, 1] *= 48 / 41
    
    for power_source in system_feems.electric_system.power_sources:
        if power_source.type == TypeComponent.GENSET:
            genset: Genset = power_source
            multi_fuel_genset = EngineMultiFuel(
                type_=TypeComponent.AUXILIARY_ENGINE,
                name=genset.name,
                rated_power=genset.aux_engine.rated_power,
                rated_speed=genset.aux_engine.rated_speed,
                multi_fuel_characteristics=[
                    FuelCharacteristics(
                        main_fuel_type=TypeFuel.NATURAL_GAS,
                        main_fuel_origin=FuelOrigin.FOSSIL,
                        pilot_fuel_type=TypeFuel.DIESEL,
                        pilot_fuel_origin=FuelOrigin.FOSSIL,
                        bsfc_curve=genset.aux_engine.specific_fuel_consumption_points,
                        bspfc_curve=bspfc_curve,
                        engine_cycle_type=EngineCycleType.OTTO,
                    ),
                    FuelCharacteristics(
                        main_fuel_type=TypeFuel.VLSFO,
                        main_fuel_origin=FuelOrigin.FOSSIL,
                        bsfc_curve=bsfc_vlsfo_aux,
                        engine_cycle_type=EngineCycleType.DIESEL,
                    ),
                ],
            )
            genset.aux_engine = multi_fuel_genset
    
    # --- Prepare Time Series ---
    path_to_result = os.path.join(package_dir, "time_series_result.pb")
    with open(path_to_result, "rb") as file:
        time_series_result = TimeSeriesResult()
        time_series_result.ParseFromString(file.read())

    machinery_calculation = MachineryCalculation(feems_system=system_feems)
    
    # 1. Default (IMO spec) -> Should be Natural Gas (primary)
    res_no_option_imo = (
        machinery_calculation.calculate_machinery_system_output_from_time_series_result(
            time_series=time_series_result,
            fuel_specified_by=FuelSpecifiedBy.IMO,
        )
    )
    
    # 2. Force VLSFO
    res_VLSFO_imo = machinery_calculation.calculate_machinery_system_output_from_time_series_result(
        time_series=time_series_result,
        fuel_specified_by=FuelSpecifiedBy.IMO,
        fuel_option=FuelOption(
            fuel_type=TypeFuel.VLSFO, fuel_origin=FuelOrigin.FOSSIL, for_pilot=False, primary=False
        ),
    )
    
    # 3. Force Natural Gas
    res_NATURAL_GAS_imo = (
        machinery_calculation.calculate_machinery_system_output_from_time_series_result(
            time_series=time_series_result,
            fuel_specified_by=FuelSpecifiedBy.IMO,
            fuel_option=FuelOption(
                fuel_type=TypeFuel.NATURAL_GAS,
                fuel_origin=FuelOrigin.FOSSIL,
                for_pilot=False,
                primary=True,
            ),
        )
    )
    
    # Assertions
    
    # Default behavior checks
    # Assuming default priority picks LNG/Natural Gas? Or whatever is first/configured?
    # The notebook says: "Assert that there is no VLSFO consumption"
    assert (
        list(filter(lambda fuel: fuel.fuel_type == TypeFuel.VLSFO,
                    res_no_option_imo.mechanical_system.multi_fuel_consumption_total_kg.fuels))
        == []
    ), "VLSFO consumption should be zero when no fuel option is specified."

    # When VLSFO forced, no Natural Gas
    assert (
        list(filter(lambda fuel: fuel.fuel_type == TypeFuel.NATURAL_GAS,
                    res_VLSFO_imo.mechanical_system.multi_fuel_consumption_total_kg.fuels))
        == []
    ), "Natural gas consumption should be zero when VLSFO is specified."

    # Energy Consistency Checks
    total_energy_consumption_default_gj = sum(
        f.mass_or_mass_fraction * f.lhv_mj_per_g 
        for f in res_no_option_imo.mechanical_system.multi_fuel_consumption_total_kg.fuels
    )
    total_energy_consumption_vlsfo_gj = sum(
        f.mass_or_mass_fraction * f.lhv_mj_per_g 
        for f in res_VLSFO_imo.mechanical_system.multi_fuel_consumption_total_kg.fuels
    )
    total_energy_consumption_natural_gas_gj = sum(
        f.mass_or_mass_fraction * f.lhv_mj_per_g 
        for f in res_NATURAL_GAS_imo.mechanical_system.multi_fuel_consumption_total_kg.fuels
    )
    
    # Notebook equality assertions
    assert np.isclose(total_energy_consumption_default_gj, total_energy_consumption_natural_gas_gj)
    
    # Notebook relative error assertion for VLSFO variance
    assert (
        abs(total_energy_consumption_default_gj - total_energy_consumption_vlsfo_gj)
        / total_energy_consumption_default_gj
        < 1e-2
    )


def _build_coges_electric_system(eff_curve: np.ndarray) -> ElectricPowerSystem:
    """Build a minimal ElectricPowerSystem with a multi-fuel COGES (LNG + H2) and an other_load."""
    generator = ElectricMachine(
        type_=TypeComponent.GENERATOR,
        name="COGES Gen",
        rated_power=1000,
        rated_speed=3000,
        power_type=TypePower.POWER_SOURCE,
        switchboard_id=1,
    )
    cogas = COGAS(
        name="COGAS",
        rated_power=1000,
        rated_speed=3000,
        eff_curve=eff_curve,
        fuel_type=TypeFuel.NATURAL_GAS,
        fuel_origin=FuelOrigin.FOSSIL,
        multi_fuel_characteristics=[
            FuelCharacteristics(
                main_fuel_type=TypeFuel.NATURAL_GAS,
                main_fuel_origin=FuelOrigin.FOSSIL,
                eff_curve=eff_curve,
                engine_cycle_type=EngineCycleType.BRAYTON,
            ),
            FuelCharacteristics(
                main_fuel_type=TypeFuel.HYDROGEN,
                main_fuel_origin=FuelOrigin.RENEWABLE_NON_BIO,
                eff_curve=eff_curve,
                engine_cycle_type=EngineCycleType.BRAYTON,
            ),
        ],
    )
    coges_component = COGES(name="COGES unit", cogas=cogas, generator=generator)

    other_load = ElectricComponent(
        type_=TypeComponent.OTHER_LOAD,
        name="Aux load",
        rated_power=500,
        power_type=TypePower.POWER_CONSUMER,
        switchboard_id=1,
        eff_curve=np.array([[0.0, 1.0], [1.0, 1.0]]),
    )
    return ElectricPowerSystem(
        name="COGES test system",
        power_plant_components=[coges_component, other_load],
        bus_tie_connections=[],
    )


def test_machinery_calculation_multifuel_coges():
    eff_curve = np.array([[0.0, 0.30], [0.5, 0.40], [1.0, 0.44]])
    system = _build_coges_electric_system(eff_curve)

    machinery_calculation = MachineryCalculation(feems_system=system)

    run_kwargs = dict(
        propulsion_power=np.array([0.0]),
        frequency=np.array([3600.0]),
        auxiliary_power_kw=500.0,
        fuel_specified_by=FuelSpecifiedBy.IMO,
    )

    # Default (no fuel_option) → first mode = LNG
    res_default = machinery_calculation.calculate_machinery_system_output_from_statistics(
        **run_kwargs
    )

    # Force H2
    res_h2 = machinery_calculation.calculate_machinery_system_output_from_statistics(
        **run_kwargs,
        fuel_option=FuelOption(
            fuel_type=TypeFuel.HYDROGEN,
            fuel_origin=FuelOrigin.RENEWABLE_NON_BIO,
            for_pilot=False,
            primary=False,
        ),
    )

    # Force LNG explicitly
    res_lng = machinery_calculation.calculate_machinery_system_output_from_statistics(
        **run_kwargs,
        fuel_option=FuelOption(
            fuel_type=TypeFuel.NATURAL_GAS,
            fuel_origin=FuelOrigin.FOSSIL,
            for_pilot=False,
            primary=True,
        ),
    )

    fuels_default = res_default.multi_fuel_consumption_total_kg.fuels
    fuels_h2 = res_h2.multi_fuel_consumption_total_kg.fuels

    # Default = LNG: natural_gas consumed, no hydrogen
    assert any(f.fuel_type == TypeFuel.NATURAL_GAS and f.mass_or_mass_fraction > 0
               for f in fuels_default), "Default mode should consume natural gas"
    assert not any(f.fuel_type == TypeFuel.HYDROGEN and f.mass_or_mass_fraction > 0
                   for f in fuels_default), "Default mode should not consume hydrogen"

    # H2 forced: hydrogen consumed, no natural_gas
    assert any(f.fuel_type == TypeFuel.HYDROGEN and f.mass_or_mass_fraction > 0
               for f in fuels_h2), "H2 mode should consume hydrogen"
    assert not any(f.fuel_type == TypeFuel.NATURAL_GAS and f.mass_or_mass_fraction > 0
                   for f in fuels_h2), "H2 mode should not consume natural gas"

    # LNG forced matches default
    assert np.isclose(
        res_default.fuel_consumption_total_kg,
        res_lng.fuel_consumption_total_kg,
        rtol=1e-6,
    ), "Explicit LNG option should match default"



# --- Boiler steam demand carried through TimeSeriesResult ---------------------------------
#
# These tests cover boiler_steam_demand_kg_per_h on the TimeSeriesResult proto: the value is
# read back by the converter and applied to the system boiler, producing boiler fuel/CO2 that
# matches the equivalent table-mode path (calculate_..._from_propulsion_power_time_series with
# the same steam_demand_kg_per_h array). Both paths use a timestamp series, so the last point is
# dropped during integration; the helper that builds the proto and the table array shares the
# same epochs/steam values, so they stay aligned.

_BOILER_EPOCHS = [0, 60, 120, 180]
_BOILER_PROPULSION_KW = [1500.0, 1600.0, 1700.0, 1800.0]
_BOILER_AUX_KW = 200.0


def _make_steam_boiler() -> SteamBoiler:
    flat_eff = np.array([[0.25, 0.85], [0.50, 0.85], [0.75, 0.85], [1.00, 0.85]])
    return SteamBoiler(
        name="test boiler",
        rated_steam_production_kg_per_h=10_000.0,
        working_pressure_barg=6.0,
        thermal_efficiency_curve=flat_eff,
        fuel_type=TypeFuel.HFO,
        fuel_origin=FuelOrigin.FOSSIL,
        feed_water_temperature_c=80.0,
        uid="boiler-uid-ts",
    )


def _build_boiler_machinery_calculation() -> MachineryCalculation:
    """Fresh MachineryCalculation (electric system) with a standalone boiler attached.

    A fresh instance is required per run because boiler.steam_out_kg_per_h is mutated in place.
    """
    package_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(package_dir, "system_proto.mss")
    system_feems = convert_proto_propulsion_system_to_feems(retrieve_machinery_system_from_file(path))
    system_feems.boiler = _make_steam_boiler()
    return MachineryCalculation(feems_system=system_feems)


def _table_mode_boiler_result(steam_demand_kg_per_h: np.ndarray):
    series = pd.Series(index=_BOILER_EPOCHS, data=_BOILER_PROPULSION_KW)
    return _build_boiler_machinery_calculation().calculate_machinery_system_output_from_propulsion_power_time_series(
        propulsion_power=series,
        auxiliary_power_kw=_BOILER_AUX_KW,
        steam_demand_kg_per_h=steam_demand_kg_per_h,
    )


def test_time_series_result_per_instance_boiler_steam_matches_table_mode():
    """AC1: per-timestep boiler_steam_demand_kg_per_h matches the table-mode path."""
    steam = np.array([2000.0, 3000.0, 4000.0, 5000.0])
    time_series = TimeSeriesResult(
        propulsion_power_timeseries=[
            PropulsionPowerInstance(
                epoch_s=epoch,
                propulsion_power_kw=prop,
                auxiliary_power_kw=_BOILER_AUX_KW,
                boiler_steam_demand_kg_per_h=s,
            )
            for epoch, prop, s in zip(_BOILER_EPOCHS, _BOILER_PROPULSION_KW, steam)
        ],
    )
    res_proto = _build_boiler_machinery_calculation().calculate_machinery_system_output_from_time_series_result(
        time_series=time_series
    )
    res_table = _table_mode_boiler_result(steam)

    # Boiler actually ran (guards against a silently-zero comparison).
    assert res_proto.fuel_consumption_boiler_total.total_fuel_consumption > 0
    assert res_proto.steam_production_boiler_total_kg > 0
    # Independent absolute check so a bug in the shared steam-alignment helper can't be hidden by
    # the proto==table comparison (both route through it). The last timestamp is dropped, so the
    # integrated steam is [2000, 3000, 4000] kg/h over three 60 s intervals = 9000/3600*60 = 150 kg.
    assert np.isclose(res_proto.steam_production_boiler_total_kg, 150.0)
    assert np.isclose(
        res_proto.fuel_consumption_boiler_total.total_fuel_consumption,
        res_table.fuel_consumption_boiler_total.total_fuel_consumption,
    )
    assert np.isclose(
        res_proto.fuel_consumption_boiler_total.get_total_co2_emissions().tank_to_wake_kg_or_gco2eq_per_gfuel,
        res_table.fuel_consumption_boiler_total.get_total_co2_emissions().tank_to_wake_kg_or_gco2eq_per_gfuel,
    )
    assert np.isclose(
        res_proto.steam_production_boiler_total_kg,
        res_table.steam_production_boiler_total_kg,
    )


def test_time_series_result_constant_boiler_steam_fallback():
    """AC2: all-zero per-instance values + non-zero top-level constant behaves as a constant."""
    constant = 3500.0
    time_series = TimeSeriesResult(
        propulsion_power_timeseries=[
            PropulsionPowerInstance(
                epoch_s=epoch,
                propulsion_power_kw=prop,
                auxiliary_power_kw=_BOILER_AUX_KW,
                # boiler_steam_demand_kg_per_h left at 0 on every instance
            )
            for epoch, prop in zip(_BOILER_EPOCHS, _BOILER_PROPULSION_KW)
        ],
        boiler_steam_demand_kg_per_h=constant,
    )
    res_proto = _build_boiler_machinery_calculation().calculate_machinery_system_output_from_time_series_result(
        time_series=time_series
    )
    res_table = _table_mode_boiler_result(np.full(len(_BOILER_EPOCHS), constant))

    assert res_proto.fuel_consumption_boiler_total.total_fuel_consumption > 0
    assert np.isclose(
        res_proto.fuel_consumption_boiler_total.total_fuel_consumption,
        res_table.fuel_consumption_boiler_total.total_fuel_consumption,
    )
    assert np.isclose(
        res_proto.steam_production_boiler_total_kg,
        res_table.steam_production_boiler_total_kg,
    )


def test_time_series_result_zero_boiler_steam_no_contribution():
    """AC3: all fields zero produces zero boiler contribution (no regression)."""
    time_series = TimeSeriesResult(
        propulsion_power_timeseries=[
            PropulsionPowerInstance(
                epoch_s=epoch,
                propulsion_power_kw=prop,
                auxiliary_power_kw=_BOILER_AUX_KW,
            )
            for epoch, prop in zip(_BOILER_EPOCHS, _BOILER_PROPULSION_KW)
        ],
    )
    res_proto = _build_boiler_machinery_calculation().calculate_machinery_system_output_from_time_series_result(
        time_series=time_series
    )
    assert res_proto.fuel_consumption_boiler_total.total_fuel_consumption == 0.0
    assert res_proto.steam_production_boiler_total_kg == 0.0


def test_time_series_result_explicit_steam_demand_overrides_proto():
    """The explicit steam_demand_kg_per_h argument takes precedence over the proto value."""
    explicit = np.array([2000.0, 3000.0, 4000.0, 5000.0])
    # Proto carries a different (constant) value that must be ignored when the arg is given.
    time_series = TimeSeriesResult(
        propulsion_power_timeseries=[
            PropulsionPowerInstance(
                epoch_s=epoch,
                propulsion_power_kw=prop,
                auxiliary_power_kw=_BOILER_AUX_KW,
            )
            for epoch, prop in zip(_BOILER_EPOCHS, _BOILER_PROPULSION_KW)
        ],
        boiler_steam_demand_kg_per_h=9999.0,
    )
    res_override = _build_boiler_machinery_calculation().calculate_machinery_system_output_from_time_series_result(
        time_series=time_series,
        steam_demand_kg_per_h=explicit,
    )
    res_table = _table_mode_boiler_result(explicit)
    assert np.isclose(
        res_override.fuel_consumption_boiler_total.total_fuel_consumption,
        res_table.fuel_consumption_boiler_total.total_fuel_consumption,
    )


def test_time_series_result_multiple_propulsors_boiler_steam():
    """Per-instance boiler steam is carried through the multi-propulsor time-series path.

    The boiler depends only on steam demand and the integration intervals, not on how propulsion
    power is split across drives, so the boiler fuel/steam must match the single-propulsor
    table-mode result for the same epochs and steam profile.
    """
    steam = np.array([2000.0, 3000.0, 4000.0, 5000.0])
    machinery_calculation = _build_boiler_machinery_calculation()
    propulsor_names = [drive.name for drive in machinery_calculation.electric_system.propulsion_drives]
    # Split the same total propulsion power equally across the drives.
    per_drive_power = [[prop / len(propulsor_names)] * len(propulsor_names) for prop in _BOILER_PROPULSION_KW]
    time_series = TimeSeriesResultForMultiplePropulsors(
        propulsion_power_timeseries=[
            PropulsionPowerInstanceForMultiplePropulsors(
                epoch_s=epoch,
                propulsion_power_kw=power_row,
                auxiliary_power_kw=_BOILER_AUX_KW,
                boiler_steam_demand_kg_per_h=s,
            )
            for epoch, power_row, s in zip(_BOILER_EPOCHS, per_drive_power, steam)
        ],
        propulsor_names=propulsor_names,
    )
    res_proto = machinery_calculation.calculate_machinery_system_output_from_time_series_result(
        time_series=time_series
    )
    res_table = _table_mode_boiler_result(steam)

    assert res_proto.fuel_consumption_boiler_total.total_fuel_consumption > 0
    assert np.isclose(res_proto.steam_production_boiler_total_kg, 150.0)
    assert np.isclose(
        res_proto.fuel_consumption_boiler_total.total_fuel_consumption,
        res_table.fuel_consumption_boiler_total.total_fuel_consumption,
    )
    assert np.isclose(
        res_proto.steam_production_boiler_total_kg,
        res_table.steam_production_boiler_total_kg,
    )
