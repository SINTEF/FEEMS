# AUTOGENERATED! DO NOT EDIT! File to edit: ../05_ConvertTimeSeriesResultProtoToPandas.ipynb.

# %% auto 0
__all__ = [
    "logger",
    "ch",
    "formatter",
    "convert_proto_timeseries_to_pd_series",
    "convert_proto_timeseries_to_pd_dataframe",
    "convert_proto_timeseries_for_multiple_propulsors_to_pd_dataframe",
]

# %% ../05_ConvertTimeSeriesResultProtoToPandas.ipynb 3
import pandas as pd
import numpy as np
import MachSysS.gymir_result_pb2 as proto
import logging


# Define logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

logger.addHandler(ch)


def convert_proto_timeseries_to_pd_series(
    proto_timeseries: proto.TimeSeriesResult,
) -> pd.Series:
    """Convert a TimeSeriesResult proto message to a pandas Series for propulsion power"""
    time = map(lambda each: each.epoch_s, proto_timeseries.propulsion_power_timeseries)
    propulsion_power = map(
        lambda each: each.propulsion_power_kw,
        proto_timeseries.propulsion_power_timeseries,
    )
    return pd.Series(index=time, data=propulsion_power)


def convert_proto_timeseries_to_pd_dataframe(
    proto_timeseries: proto.TimeSeriesResult,
) -> pd.DataFrame:
    """
    Convert a TimeSeriesResult proto message to a pandas DataFrame
    for propulsion and auxiliary power and other operational parameters such as speed and draft
    """
    time = list(
        map(lambda each: each.epoch_s, proto_timeseries.propulsion_power_timeseries)
    )
    propulsion_power = list(
        map(
            lambda each: each.propulsion_power_kw,
            proto_timeseries.propulsion_power_timeseries,
        )
    )
    auxiliary_power = list(
        map(
            lambda each: each.auxiliary_power_kw,
            proto_timeseries.propulsion_power_timeseries,
        )
    )
    if (np.array(auxiliary_power) == 0).all():
        auxiliary_power = [proto_timeseries.auxiliary_power_kw] * len(time)
    df = pd.DataFrame(
        index=time,
        data=dict(
            propulsion_power_kw=propulsion_power,
            auxiliary_power_kw=auxiliary_power,
        ),
    )
    if len(proto_timeseries.operation_profile) > 0:
        time_operation_profile = list(
            map(lambda each: each.epoch_s, proto_timeseries.operation_profile)
        )
        speed_array = np.array(
            list(map(lambda each: each.speed_kn, proto_timeseries.operation_profile))
        )
        draft_array = np.array(
            list(map(lambda each: each.draft_m, proto_timeseries.operation_profile))
        )

        if time_operation_profile != time:
            logger.warning(
                "Time in operation profile is not the same as in propulsion power."
                "The operation profile will be interpolated to match the propulsion power time."
            )
            time_array = np.array(time_operation_profile)
            time_array_ref = np.array(time)
            speed_array = np.interp(time_array_ref, time_array, speed_array)
            draft_array = np.interp(time_array_ref, time_array, draft_array)

        df["speed_kn"] = speed_array
        df["draft_m"] = draft_array
    return df


def convert_proto_timeseries_for_multiple_propulsors_to_pd_dataframe(
    proto_timeseries: proto.TimeSeriesResultForMultiplePropulsors,
) -> pd.DataFrame:
    """
    Convert a TimeSeriesResult proto message to a pandas DataFrame
    for propulsion and auxiliary power and other operational parameters such as speed and draft
    """
    time = list(
        map(lambda each: each.epoch_s, proto_timeseries.propulsion_power_timeseries)
    )
    propulsor_names = list(map(lambda each: each, proto_timeseries.propulsor_names))
    propulsion_power = np.array(
        list(
            map(
                lambda each_instance: list(
                    map(
                        lambda each_power: each_power, each_instance.propulsion_power_kw
                    )
                ),
                proto_timeseries.propulsion_power_timeseries,
            )
        )
    )
    assert propulsion_power.shape[0] == len(
        time
    ), "Time and propulsion power length mismatch"
    assert propulsion_power.shape[1] == len(
        propulsor_names
    ), "Propulsion power and propulsor names length mismatch"
    data = {
        propulsor_name: propulsion_power[:, i]
        for i, propulsor_name in enumerate(propulsor_names)
    }
    auxiliary_power = list(
        map(
            lambda each: each.auxiliary_power_kw,
            proto_timeseries.propulsion_power_timeseries,
        )
    )
    if (np.array(auxiliary_power) == 0).all():
        auxiliary_power = [proto_timeseries.auxiliary_power_kw] * len(time)
    data["auxiliary_power_kw"] = auxiliary_power
    df = pd.DataFrame(
        index=time,
        data=data,
    )
    if len(proto_timeseries.operation_profile) > 0:
        time_operation_profile = list(
            map(lambda each: each.epoch_s, proto_timeseries.operation_profile)
        )
        speed_array = np.array(
            list(map(lambda each: each.speed_kn, proto_timeseries.operation_profile))
        )
        draft_array = np.array(
            list(map(lambda each: each.draft_m, proto_timeseries.operation_profile))
        )

        if time_operation_profile != time:
            logger.warning(
                "Time in operation profile is not the same as in propulsion power."
                "The operation profile will be interpolated to match the propulsion power time."
            )
            time_array = np.array(time_operation_profile)
            time_array_ref = np.array(time)
            speed_array = np.interp(time_array_ref, time_array, speed_array)
            draft_array = np.interp(time_array_ref, time_array, draft_array)

        df["speed_kn"] = speed_array
        df["draft_m"] = draft_array
    return df
