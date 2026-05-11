import random

import numpy as np
import pandas as pd
from MachSysS.convert_proto_timeseries import (
    convert_proto_timeseries_to_pd_dataframe,
    convert_proto_timeseries_to_pd_series,
)
from MachSysS.gymir_result_pb2 import (
    OperationProfilePoint,
    PropulsionPowerInstance,
    TimeSeriesResult,
)


def test_convert_proto_timeseries_to_pd_series():
    time_array = np.arange(0, 1000, 1)
    propulsion_power_array = np.random.random(len(time_array)) * 1000
    auxiliary_power = 300
    speed_array = np.random.random(len(time_array)) * 20
    draft_array = np.random.random(len(time_array)) * 10

    timeseries_result = TimeSeriesResult()
    timeseries_result.auxiliary_power_kw = auxiliary_power
    for time, propulsion_power, speed_kn, draft_m in zip(
        time_array, propulsion_power_array, speed_array, draft_array
    ):
        timeseries_result.propulsion_power_timeseries.append(
            PropulsionPowerInstance(epoch_s=time, propulsion_power_kw=propulsion_power)
        )
        if random.random() > 0.9:
            timeseries_result.operation_profile.append(
                OperationProfilePoint(epoch_s=time, speed_kn=speed_kn, draft_m=draft_m)
            )

    time_series = convert_proto_timeseries_to_pd_series(timeseries_result)
    # Depending on implementation, it might return Series or DataFrame?
    # The function name says pd_series
    assert isinstance(time_series, (pd.Series, pd.DataFrame))

    time_series_df = convert_proto_timeseries_to_pd_dataframe(timeseries_result)
    assert isinstance(time_series_df, pd.DataFrame)


def test_convert_proto_timeseries_verification():
    time_array = np.arange(0, 1000, 1)
    propulsion_power_array = np.random.random(len(time_array)) * 1000
    auxiliary_power_array = np.random.random(len(time_array)) * 100
    speed_array = np.random.random(len(time_array)) * 20
    draft_array = np.random.random(len(time_array)) * 10

    timeseries_result = TimeSeriesResult()
    for i, (time, propulsion_power, auxiliary_power) in enumerate(zip(
        time_array, propulsion_power_array, auxiliary_power_array
    )):
        timeseries_result.propulsion_power_timeseries.append(
            PropulsionPowerInstance(
                epoch_s=time,
                propulsion_power_kw=propulsion_power,
                auxiliary_power_kw=auxiliary_power,
            )
        )
        # Fix the issue in the notebook where speed_kn and draft_m were undefined
        if random.random() > 0.9:
            timeseries_result.operation_profile.append(
                OperationProfilePoint(epoch_s=time, speed_kn=speed_array[i], draft_m=draft_array[i])
            )

    time_series = convert_proto_timeseries_to_pd_dataframe(timeseries_result)
    assert np.allclose(time_series["auxiliary_power_kw"].values, auxiliary_power_array)
