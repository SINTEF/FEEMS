import os
import random
import numpy as np
import pandas as pd
import pytest
from feems.components_model.component_electric import Genset
from feems.components_model.component_mechanical import (
    EngineMultiFuel,
    FuelCharacteristics,
)
from feems.fuel import FuelOrigin, FuelSpecifiedBy, TypeFuel
from feems.system_model import FuelOption
from feems.types_for_feems import EngineCycleType, TypeComponent
from MachSysS.convert_to_feems import convert_proto_propulsion_system_to_feems
from MachSysS.gymir_result_pb2 import (
    GymirResult,
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
        [f.mass_or_mass_fraction * f.lhv_mj_per_g for f in res_no_option_imo.mechanical_system.multi_fuel_consumption_total_kg.fuels]
    )
    total_energy_consumption_vlsfo_gj = sum(
        [f.mass_or_mass_fraction * f.lhv_mj_per_g for f in res_VLSFO_imo.mechanical_system.multi_fuel_consumption_total_kg.fuels]
    )
    total_energy_consumption_natural_gas_gj = sum(
        [f.mass_or_mass_fraction * f.lhv_mj_per_g for f in res_NATURAL_GAS_imo.mechanical_system.multi_fuel_consumption_total_kg.fuels]
    )
    
    # Notebook equality assertions
    assert np.isclose(total_energy_consumption_default_gj, total_energy_consumption_natural_gas_gj)
    
    # Notebook relative error assertion for VLSFO variance
    assert (
        abs(total_energy_consumption_default_gj - total_energy_consumption_vlsfo_gj)
        / total_energy_consumption_default_gj
        < 1e-2
    )

