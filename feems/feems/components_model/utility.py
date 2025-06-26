import logging
from dataclasses import fields
from enum import unique, Enum
from typing import Union, List, Callable, Tuple, Optional

import numpy as np
import pandas as pd
from numpy import cumsum
from scipy.integrate import trapezoid, simpson
from scipy.interpolate import PchipInterpolator

from feems import get_logger
from feems.exceptions import InputError
from feems.fuel import FuelConsumption
from feems.types_for_feems import TimeIntervalList, EmissionCurvePoint

logger = get_logger(__name__)


@unique
class IntegrationMethod(Enum):
    simpson = "simpson"
    trapezoid = "trapezoid"
    sum_with_time = "sum_with_time"


class IntegrationError(Exception):
    pass


def data_is_valid_for_variable_time_interval(
    *, time_interval_s: Optional[TimeIntervalList], data_to_integrate: np.ndarray
) -> bool:
    """Check if the data for integration is valid"""
    test_1_ok = False
    test_2_ok = False
    if isinstance(time_interval_s, np.ndarray):
        if np.array_equal(time_interval_s.shape, data_to_integrate.shape):
            test_1_ok = True
    if np.isscalar(time_interval_s):
        if len(data_to_integrate) == 1:
            test_2_ok = True
    return test_1_ok or test_2_ok


def integrate_data(
    *,
    data_to_integrate: np.ndarray,
    time_interval_s: Optional[TimeIntervalList] = None,
    integration_method: IntegrationMethod = IntegrationMethod.simpson,
) -> float:
    """
    Integrates the data with a regular(constant) time step or given time step array.

    :param data_to_integrate: Data samples to integrate, numpy float array
    :param time_interval_s: Time interval of the data samples in seconds must be a float for
        simpson or trapezoid, and an array for 'sum_with_time'. sum_with_times is the dot product
        of data_to_integrate and time_interval_s
    :param integration_method: Numerical integration method. Choose among `IntegrationMethod`
    :return: Integrated value
    """
    data_to_integrate = np.atleast_1d(data_to_integrate)
    time_interval_s_is_scalar_number = np.isscalar(time_interval_s) and isinstance(
        time_interval_s, (float, int)
    )
    if len(data_to_integrate) == 1 and integration_method != IntegrationMethod.sum_with_time:
        logger.warning(
            "The integration method is not 'sum_with_time' while the data to integrate "
            "has only one point. 'sum_with_time' will be used for integration to avoid "
            "getting 0 value."
        )
        integration_method = IntegrationMethod.sum_with_time
    if integration_method == IntegrationMethod.simpson:
        if not time_interval_s_is_scalar_number:
            msg = f"The time interval for {integration_method.value} must be a scalar value"
            logger.error(msg)
            raise IntegrationError(msg)
        return simpson(data_to_integrate) * time_interval_s
    elif integration_method == IntegrationMethod.trapezoid:
        if not time_interval_s_is_scalar_number:
            msg = f"The time interval for {integration_method.value} must be a scalar value"
            logger.error(msg)
            raise IntegrationError(msg)
        return trapezoid(data_to_integrate) * time_interval_s
    elif integration_method == IntegrationMethod.sum_with_time:
        if not data_is_valid_for_variable_time_interval(
            time_interval_s=time_interval_s, data_to_integrate=data_to_integrate
        ):
            err_msg = (
                "The data is not compatible with the given time step. "
                "Either the data should have the same shape as time step "
                "if time step is given as an array or the data should be scalar."
            )
            logger.error(err_msg)
            raise IntegrationError(err_msg)
        result = np.dot(data_to_integrate, time_interval_s)  # type: ignore[arg-type]
        if not np.isscalar(result):
            result = result[0]
        return result
    else:
        msg = "The given method (%s) for the integration is not valid" % integration_method
        logging.error(msg)
        raise TypeError(msg)


def integrate_multi_fuel_consumption(
    fuel_consumption_kg_per_s: FuelConsumption,
    time_interval_s: Optional[TimeIntervalList] = None,
    integration_method: IntegrationMethod = IntegrationMethod.simpson,
) -> FuelConsumption:
    """
    Integrates fuel consumption rate of each fuel component.
    """
    fuel_consumption_kg = FuelConsumption(
        fuels=[fuel.copy_except_mass_or_mass_fraction for fuel in fuel_consumption_kg_per_s.fuels]
    )
    for each_fuel_rate, each_fuel_mass in zip(
        fuel_consumption_kg_per_s.fuels, fuel_consumption_kg.fuels
    ):
        each_fuel_mass.mass_or_mass_fraction = integrate_data(
            data_to_integrate=each_fuel_rate.mass_or_mass_fraction,
            time_interval_s=time_interval_s,
            integration_method=integration_method,
        )
    return fuel_consumption_kg


def integrate_data_accumulative(
    *,
    data_to_integrate: np.ndarray,
    time_interval_s: Union[float, np.ndarray] = None,
    integration_method: IntegrationMethod = IntegrationMethod.simpson,
) -> np.ndarray:
    """
    Integrates the data with a regular(constant) time step

    :param data_to_integrate: Data samples to integrate, numpy float array
    :param time_interval_s: Time interval of the data samples in seconds must be a float for
        simpson or trapezoid, and a array for 'sum_with_time'. sum_with_times is the dot product
        of data_to_integrate and time_interval_s
    :param integration_method: Numerical integration method. Choose among `IntegrationMethod`
    :return: Integrated values for each time step as an array
    """
    if integration_method == IntegrationMethod.sum_with_time:
        if not data_is_valid_for_variable_time_interval(
            time_interval_s=time_interval_s, data_to_integrate=data_to_integrate
        ):
            err_msg = "The data is not compatible with the given time step."
            logger.error(err_msg)
            raise IntegrationError(err_msg)
        res: np.ndarray = cumsum(data_to_integrate * time_interval_s)
        res = np.insert(res, 0, 0, axis=0)
        return res
    else:
        msg = "The given method (%s) for the integration is not valid" % integration_method
        logging.error(msg)
        raise TypeError(msg)


def get_efficiency_curve_from_points(
    eff_curve: np.ndarray,
) -> Tuple[PchipInterpolator, np.ndarray]:
    """
    Returns the efficiency interpolating class object from the points provided
    :param eff_curve: ndarray of shape of (:,2), first column being the percentage load, and the
    second efficiency, can be a single value but should be ndarray with length 1.
    :return: UnivariateSpline or interpolate1d class object and sorted eff_curve
    """
    if len(eff_curve) == 1:  # in case of single efficiency value
        eff = eff_curve[0]
        if not np.isscalar(eff):
            assert len(eff) == 2
            eff = eff[1]
        curve_points = np.append(
            np.array([0, 1]).reshape(-1, 1), np.array([eff, eff]).reshape(-1, 1), axis=1
        )
        function = lambda x: eff
        return function, curve_points
    else:
        eff_curve = eff_curve[eff_curve[:, 0].argsort()]
        return PchipInterpolator(eff_curve[:, 0], eff_curve[:, 1]), eff_curve


def get_emission_curve_from_points(
    emission: List[EmissionCurvePoint],
) -> Callable[[float], float]:
    """
    Returns the emission interpolating class object from the points provided
    :param emission: Emission value or list of EmissionCurvePoint
    :return: PchipInterpolator class object with load ratio as input
    """
    if len(emission) == 1:
        return lambda x: emission[0].emission_g_per_kwh
    else:
        power = np.array([point.load_ratio for point in emission])
        emission = np.array([point.emission_g_per_kwh for point in emission])
        return PchipInterpolator(power, emission, extrapolate=True)


def get_efficiency_curve_from_dataframe(
    df: pd.DataFrame, key_word: str = "efficiency"
) -> Union[PchipInterpolator, np.ndarray]:
    """
    Returns the efficiency interpolating class object from the DataFrame provided
    :param df: DataFrame for the component information
    :param key_word: The keyword for the column names for the efficiency table
    :return: PchipSpline or interpolate1d class object
    """
    #: Find the data for the efficiency
    eff_columns = [s for s in df.columns if key_word in s]

    #: Create a curve_points
    curve_points = np.zeros([len(eff_columns), 2])
    if len(eff_columns) == 1:
        curve_points = np.ravel(df[eff_columns].values)
    else:
        for i, eff_column in enumerate(eff_columns):
            curve_points[i, 0] = float(eff_column[eff_column.find("@") + 1 : eff_column.find("%")])
            curve_points[i, 1] = df[eff_column].values[0]
        curve_points = curve_points[curve_points[:, 0].argsort()]
    return get_efficiency_curve_from_points(curve_points)


def get_list_random_distribution_numbers_for_total_number(
    number_element: int, sum_number: int
) -> List[int]:
    """
    Returns a list of distributed numbers for a given number of elements and sum of the numbers.
    For each element, the number will be greater than 0.
    :param number_element: A number of element = length of the list ex) 4 should be given for list
        [a, b, c, d]
    :param sum_number: Sum of the numbers of each element ex) a + b + c + d should be given for
        list [a, b, c, d]
    :return: A list of the numbers of which total sum is equal to sum_number
    """
    if sum_number < number_element:
        msg = "sum_number can not be smaller than number_element."
        logger.error(msg)
        raise InputError(msg)

    number_of_component_list = np.random.rand(number_element)
    number_of_component_list /= number_of_component_list.sum() / sum_number
    number_of_component_list = np.ceil(number_of_component_list).astype(int)
    while number_of_component_list.sum() > sum_number:
        number_of_component_list[np.argmax(number_of_component_list)] -= 1

    return number_of_component_list.tolist()
