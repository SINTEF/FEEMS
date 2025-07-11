# AUTOGENERATED! DO NOT EDIT! File to edit: ../00_machinery_calculation.ipynb.

# %% auto 0
__all__ = [
    "Numeric",
    "convert_gymir_result_to_propulsion_power_series",
    "MachineryCalculation",
]

# %% ../00_machinery_calculation.ipynb 3
from typing import List, Union, Type, TypeVar

import MachSysS.gymir_result_pb2 as proto_gymir
from MachSysS.convert_proto_timeseries import (
    convert_proto_timeseries_to_pd_dataframe,
    convert_proto_timeseries_for_multiple_propulsors_to_pd_dataframe,
)
import numpy as np
import pandas as pd
from feems.components_model.utility import IntegrationMethod
from feems.system_model import (
    ElectricPowerSystem,
    HybridPropulsionSystem,
    MechanicalPropulsionSystemWithElectricPowerSystem,
    FEEMSResultForMachinerySystem,
)
from feems.types_for_feems import FEEMSResult, TypePower
from feems.simulation_interface import SimulationInterface
from feems.fuel import FuelSpecifiedBy

from RunFeemsSim.pms_basic import (
    PmsLoadTable,
    get_min_load_table_dict_from_feems_system,
    PmsLoadTableSimulationInterface,
)

Numeric = TypeVar("Numeric", int, float, np.ndarray)


def convert_gymir_result_to_propulsion_power_series(
    gymir_result: proto_gymir.GymirResult,
) -> pd.Series:
    time = map(lambda each: each.epoch_s, gymir_result.result)
    power = map(lambda each: each.power_kw, gymir_result.result)
    return pd.Series(index=time, data=power)


class MachineryCalculation:
    def __init__(
        self,
        feems_system: Union[
            ElectricPowerSystem,
            MechanicalPropulsionSystemWithElectricPowerSystem,
            HybridPropulsionSystem,
        ],
        pms: SimulationInterface = None,
        maximum_allowed_power_source_load_percentage: float = 80,
    ):
        self.system_feems = feems_system
        if pms is None:
            load_table = PmsLoadTable(
                min_load2on_pattern=get_min_load_table_dict_from_feems_system(
                    system=feems_system,
                    maximum_allowed_genset_load_percentage=maximum_allowed_power_source_load_percentage,
                )
            )
            self.pms = PmsLoadTableSimulationInterface(
                n_bus_ties=1, pms_load_table=load_table
            )
        else:
            self.pms = pms
        self._set_equal_load_sharing_on_power_sources(n_datapoints=1)

    @property
    def electric_system(self) -> ElectricPowerSystem:
        if self.system_is_not_electric:
            return self.system_feems.electric_system
        else:
            return self.system_feems

    @property
    def system_is_not_electric(self) -> bool:
        return hasattr(self.system_feems, "electric_system")

    def _set_input_load_from_gymir_result(
        self,
        *,
        gymir_result: proto_gymir.GymirResult,
    ) -> None:
        propulsion_power_timeseries = convert_gymir_result_to_propulsion_power_series(
            gymir_result
        )
        self._set_input_load_time_interval_from_propulsion_power_time_series(
            propulsion_power_time_series=propulsion_power_timeseries,
            auxiliary_load_kw=gymir_result.auxiliary_load_kw,
        )

    def _set_input_load_time_interval_from_propulsion_power_time_series(
        self,
        *,
        propulsion_power_time_series: Union[pd.Series, pd.DataFrame],
        auxiliary_load_kw: Numeric,
        time_is_given_as_interval: bool = False,
    ) -> None:
        """Set the input load time interval from the propulsion power time series.
        Args:
            propulsion_power_time_series (Union[pd.Series, pd.DataFrame]): The propulsion power time series.
                If it is a DataFrame, it should contain the propulsion power for each propulsion drive.
            auxiliary_load_kw (Numeric): The auxiliary load in kW. It can be a single value or an array.
            time_is_given_as_interval (bool): If True, the time series index is given as intervals.
                Default is False, meaning the index is given as timestamps.
        """
        if not isinstance(propulsion_power_time_series, (pd.Series, pd.DataFrame)):
            raise TypeError(
                "propulsion_power_time_series must be a pandas Series or DataFrame."
            )
        if isinstance(propulsion_power_time_series, pd.Series):
            if time_is_given_as_interval:
                propulsion_power = propulsion_power_time_series.values
                time_interval_s = propulsion_power_time_series.index.to_numpy()
            else:
                propulsion_power = propulsion_power_time_series.values[:-1]
                time_interval_s = np.diff(propulsion_power_time_series.index.to_numpy())
            number_points = len(propulsion_power)
            # set power load
            if self.system_is_not_electric:
                number_of_propulsors = (
                    self.system_feems.mechanical_system.no_mechanical_loads
                )
            else:
                number_of_propulsors = len(self.electric_system.propulsion_drives)
            if self.system_is_not_electric:
                for propulsor in self.system_feems.mechanical_system.mechanical_loads:
                    propulsor.set_power_input_from_output(
                        propulsion_power / number_of_propulsors
                    )
            else:
                for propulsor in self.electric_system.propulsion_drives:
                    propulsor.set_power_input_from_output(
                        propulsion_power / number_of_propulsors
                    )
        else:
            if time_is_given_as_interval:
                time_interval_s = propulsion_power_time_series.index.to_numpy()
            else:
                time_interval_s = np.diff(propulsion_power_time_series.index.to_numpy())
                propulsion_power_time_series = propulsion_power_time_series.iloc[:-1]
            number_points = len(propulsion_power_time_series)
            for propulsor_name in propulsion_power_time_series.columns:
                propulsor = None
                if self.system_is_not_electric:
                    for (
                        each_shaft_line
                    ) in self.system_feems.mechanical_system.shaft_line:
                        try:
                            propulsor = (
                                each_shaft_line.get_component_by_name_power_type(
                                    name=propulsor_name,
                                    power_type=TypePower.POWER_CONSUMER,
                                )
                            )
                        except ValueError:
                            continue
                else:
                    for (
                        swb_id,
                        each_switchboard,
                    ) in self.electric_system.switchboards.items():
                        try:
                            propulsor = (
                                each_switchboard._get_component_by_type_and_name(
                                    name=propulsor_name,
                                    power_type=TypePower.POWER_CONSUMER,
                                )
                            )
                        except ValueError:
                            continue
                if propulsor is None:
                    raise ValueError(
                        f"Propulsor with name {propulsor_name} not found in the system."
                    )
                propulsor.set_power_input_from_output(
                    propulsion_power_time_series[propulsor_name].values
                )
        auxiliary_load_kw = np.atleast_1d(auxiliary_load_kw)
        if len(auxiliary_load_kw) > 1:
            auxiliary_load_kw = auxiliary_load_kw[:number_points]
        else:
            auxiliary_load_kw = np.repeat(auxiliary_load_kw, number_points)
        number_of_other_loads = len(self.electric_system.other_load)
        if number_of_other_loads == 0:
            assert np.all(
                np.atleast_1d(auxiliary_load_kw) == 0
            ), "Auxiliary load is not zero while other loads are not defined in the system."
        for other_load in self.electric_system.other_load:
            other_load.power_input = auxiliary_load_kw / number_of_other_loads
        self.electric_system.set_time_interval(
            time_interval_s=time_interval_s,
            integration_method=IntegrationMethod.sum_with_time,
        )
        if self.system_is_not_electric:
            self.system_feems.mechanical_system.set_time_interval(
                time_interval_s=time_interval_s,
                integration_method=IntegrationMethod.sum_with_time,
            )

    def _set_equal_load_sharing_on_power_sources(self, n_datapoints: int) -> None:
        for power_source in self.electric_system.power_sources:
            power_source.load_sharing_mode = np.zeros(shape=[n_datapoints])
        if self.system_is_not_electric:
            for power_source in self.system_feems.mechanical_system.main_engines:
                power_source.load_sharing_mode = np.zeros(shape=[n_datapoints])

    def _set_status_for_mechanical_system(self) -> None:
        """Set the status of main engines for the mechanical system, turning all the gensets on.
        The main engines that are not used for propulsion after the power balance calculation
        will be turned off.
        """
        if np.isscalar(self.system_feems.mechanical_system.time_interval_s):
            n_data_points = 1
        else:
            n_data_points = len(self.system_feems.mechanical_system.time_interval_s)
        for main_engine in self.system_feems.mechanical_system.main_engines:
            main_engine.status = np.ones(n_data_points).astype(bool)

    def _run_simulation(
        self,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        ignore_power_balance: bool = False,
    ) -> Union[FEEMSResult, FEEMSResultForMachinerySystem]:
        """Run the simulation and return the result.

        Args:
            fuel_specified_by(FuelSpecifiedBy): The fuel specified by IMO/EU/USER. Default is IMO.
            ignore_power_balance(bool): If True, the power balance calculation will be ignored.

        Returns:
            The result of the simulation. FEEMSResult or FEEMSResultForMachinery system.
        """
        if ignore_power_balance:
            if self.system_is_not_electric:
                return self.system_feems.get_fuel_energy_consumption_running_time(
                    time_interval_s=self.system_feems.mechanical_system.time_interval_s,
                    integration_method=IntegrationMethod.sum_with_time,
                    fuel_specified_by=fuel_specified_by,
                )
            else:
                return self.system_feems.get_fuel_energy_consumption_running_time(
                    fuel_specified_by=fuel_specified_by
                )

        power_kw_per_switchboard = (
            self.electric_system.get_sum_consumption_kw_sources_switchboard()
        )
        self.pms.set_status(
            power_kw_per_switchboard=power_kw_per_switchboard,
            electric_power_system=self.electric_system,
            time_interval_s=self.electric_system.time_interval_s,
            power_source_priority=None,
        )
        if self.system_is_not_electric:
            self._set_status_for_mechanical_system()
            self.system_feems.do_power_balance_calculation()
            return self.system_feems.get_fuel_energy_consumption_running_time(
                time_interval_s=self.system_feems.mechanical_system.time_interval_s,
                integration_method=IntegrationMethod.sum_with_time,
                fuel_specified_by=fuel_specified_by,
            )
        else:
            self.system_feems.do_power_balance_calculation()
            return self.system_feems.get_fuel_energy_consumption_running_time(
                fuel_specified_by=fuel_specified_by
            )

    def calculate_machinery_system_output_from_gymir_result(
        self,
        *,
        gymir_result: proto_gymir.GymirResult,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        ignore_power_balance: bool = False,
    ) -> Union[FEEMSResult, FEEMSResultForMachinerySystem]:
        """
        Calculate the machinery system output from a Gymir result.

        Args:
            gymir_result(GymirResult): Gymir result given as protobuf message.
            fuel_specified_by(FuelSpecifiedBy): The fuel specified by IMO/EU/USER. Default is IMO.
            ignore_power_balance(bool): If True, the power balance calculation will be ignored.

        Returns:
            The result of the calculation. FEEMSResult or FEEMSResultForMachinerySystem.
        """
        self._set_input_load_from_gymir_result(gymir_result=gymir_result)
        return self._run_simulation(
            fuel_specified_by=fuel_specified_by,
            ignore_power_balance=ignore_power_balance,
        )

    def calculate_machinery_system_output_from_propulsion_power_time_series(
        self,
        *,
        propulsion_power: Union[pd.Series, pd.DataFrame],
        auxiliary_power_kw: Numeric,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        ignore_power_balance: bool = False,
    ) -> Union[FEEMSResult, FEEMSResultForMachinerySystem]:
        """
        Calculate the machinery system output from a time series of the propulsion power and
        auxiliary power.

        Args:
            propulsion_power: The propulsion power time series. It can be a pandas Series if the
                data is the total propulsion power that is equally shared by all propulsion drives,
                or a pandas DataFrame if the data is given for each propulsion drive separately.
            auxiliary_power_kw(Numeric): The auxiliary power in kW. It can be a single value or
                a numpy array with the same length as the propulsion power.
            fuel_specified_by(FuelSpecifiedBy): The fuel specified by IMO/EU/USER. Default is IMO.
            ignore_power_balance(bool): If True, the power balance calculation will be ignored.

        Returns:
            The result of the calculation. FEEMSResult or FEEMSResultForMachinerySystem.
        """
        # Check if the propulsion power is a pandas Series or DataFrame
        if not isinstance(propulsion_power, (pd.Series, pd.DataFrame)):
            raise TypeError("propulsion_power must be a pandas Series or DataFrame.")
        # If it's a DataFrame, ensure column names match the propulsion drives
        if isinstance(propulsion_power, pd.DataFrame):
            # Check for electric propulsion system
            if self.system_is_not_electric:
                names_for_propulsion_drives = [
                    drive.name
                    for drive in self.system_feems.mechanical_system.mechanical_loads
                ]
                for name in propulsion_power.columns:
                    assert (
                        name in names_for_propulsion_drives
                    ), f"Column '{name}' not found in mechanical loads."
            else:
                names_for_propulsion_drives = [
                    drive.name for drive in self.electric_system.propulsion_drives
                ]
                for name in propulsion_power.columns:
                    assert (
                        name in names_for_propulsion_drives
                    ), f"Column '{name}' not found in propulsion drives."
        # Check if auxiliary_power_kw is a scalar or an array
        if not np.isscalar(auxiliary_power_kw):
            assert (
                len(propulsion_power) == len(auxiliary_power_kw)
                or len(auxiliary_power_kw) == 1
            ), f"The length of the auxiliary power({len(auxiliary_power_kw)}) must be 1 or the same as the propulsion power ({len(propulsion_power)})"

        self._set_input_load_time_interval_from_propulsion_power_time_series(
            propulsion_power_time_series=propulsion_power,
            auxiliary_load_kw=auxiliary_power_kw,
        )
        return self._run_simulation(
            fuel_specified_by=fuel_specified_by,
            ignore_power_balance=ignore_power_balance,
        )

    def calculate_machinery_system_output_from_time_series_result(
        self,
        *,
        time_series: Union[
            proto_gymir.TimeSeriesResult,
            proto_gymir.TimeSeriesResultForMultiplePropulsors,
        ],
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        ignore_power_balance: bool = False,
    ) -> Union[FEEMSResult, FEEMSResultForMachinerySystem]:
        """
        Calculate the machinery system output from statistics of the propulsion power.
        Args:
            time_series(TimeSeriesResult): Time series result given as protobuf message.
            fuel_specified_by(FuelSpecifiedBy): The fuel specified by IMO/EU/USER. Default is IMO.
            ignore_power_balance(bool): If True, the power balance calculation will be ignored.

        Returns:
            The result of the simulation. FEEMSResult or FEEMSResultForMachinery system.
        """
        if isinstance(time_series, proto_gymir.TimeSeriesResult):
            df = convert_proto_timeseries_to_pd_dataframe(time_series)
            self._set_input_load_time_interval_from_propulsion_power_time_series(
                propulsion_power_time_series=df["propulsion_power_kw"],
                auxiliary_load_kw=df["auxiliary_power_kw"].values,
            )
        elif isinstance(time_series, proto_gymir.TimeSeriesResultForMultiplePropulsors):
            df = convert_proto_timeseries_for_multiple_propulsors_to_pd_dataframe(
                time_series
            )
            propulsor_names = list(map(lambda each: each, time_series.propulsor_names))
            self._set_input_load_time_interval_from_propulsion_power_time_series(
                propulsion_power_time_series=df[propulsor_names],
                auxiliary_load_kw=df["auxiliary_power_kw"].values,
            )
        else:
            raise TypeError(
                "time_series must be a TimeSeriesResult or TimeSeriesResultForMultiplePropulsors."
            )

        return self._run_simulation(
            fuel_specified_by=fuel_specified_by,
            ignore_power_balance=ignore_power_balance,
        )

    def calculate_machinery_system_output_from_statistics(
        self,
        *,
        propulsion_power: np.ndarray,
        frequency: np.ndarray,
        auxiliary_power_kw: Numeric,
        fuel_specified_by: FuelSpecifiedBy = FuelSpecifiedBy.IMO,
        ignore_power_balance: bool = False,
    ) -> Union[FEEMSResult, FEEMSResultForMachinerySystem]:
        """
        Calculate the machinery system output from statistics of the propulsion power.

        Args:
            propulsion_power(np.ndarray): The propulsion power for each mode in kW.
            frequency(np.ndarray): The frequency of each mode in seconds. If the frequency is
                given as normalized value, the output should be interpreted as per second value.
            auxiliary_power_kw(Numeric): The auxiliary power for each mode in kW. It is also
                possible to give a single value for all modes.
            fuel_specified_by(FuelSpecifiedBy): The fuel specified by IMO/EU/USER. Default is IMO.
            ignore_power_balance(bool): If True, the power balance calculation will be ignored.

        Returns:
            The result of the simulation. FEEMSResult or FEEMSResultForMachinery system.
        """
        if not np.isscalar(auxiliary_power_kw):
            assert (
                len(propulsion_power) == len(auxiliary_power_kw)
                or len(auxiliary_power_kw) == 1
            ), "The length of the auxiliary power must be 1 or the same as the propulsion power"
        self._set_input_load_time_interval_from_propulsion_power_time_series(
            propulsion_power_time_series=pd.Series(
                data=propulsion_power, index=frequency
            ),
            auxiliary_load_kw=auxiliary_power_kw,
            time_is_given_as_interval=True,
        )
        return self._run_simulation(
            fuel_specified_by=fuel_specified_by,
            ignore_power_balance=ignore_power_balance,
        )
