from typing import Union, List, Tuple, Optional, TypeVar, Dict
from dataclasses import dataclass, field
from uuid import uuid4

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
from scipy.optimize import newton, root, least_squares

from .utility import (
    get_efficiency_curve_from_dataframe,
    get_efficiency_curve_from_points,
)
from .. import get_logger
from ..exceptions import InputError
from ..types_for_feems import (
    EmissionType,
    TypeComponent,
    TypePower,
    Power_kW,
    Speed_rpm,
    Numeric,
    NumericT,
)
from ..fuel import FuelConsumption, FuelConsumerClassFuelEUMaritime

# Define logger
logger = get_logger(__name__)


T = TypeVar("T", float, np.ndarray)


@dataclass(kw_only=True)
class ComponentRunPoint:
    load_ratio: np.ndarray
    efficiency: np.ndarray
    fuel_flow_rate_kg_per_s: FuelConsumption
    emissions_g_per_s: Dict[EmissionType, np.ndarray] = field(default_factory=dict)


class Component:
    """
    class for a component that contains a basic information
    """

    status: np.ndarray

    def __init__(
        self,
        name: str,
        type_: TypeComponent,
        power_type: TypePower,
        rated_power: Power_kW = Power_kW(0.0),
        rated_speed: Speed_rpm = Speed_rpm(0.0),
        uid: Optional[str] = None,
    ):
        self.type = type_
        self.power_type = power_type
        self.name = name
        self.rated_power = rated_power
        self.rated_speed = rated_speed
        self.status = np.ones(1).astype(bool)  # Status on/off
        self.power_input = np.array([0])  # power input
        self.power_output = np.array([0])  # power output
        # if uid is not given, create a random uid
        self.uid = str(uuid4()) if uid is None else uid

    def get_type_name(self) -> str:
        return self.type.name

    def get_load(self, power: Optional[T] = None) -> T:
        if power is None:
            return np.abs(self.power_input) / self.rated_power
        else:
            return np.abs(power) / self.rated_power

    @property
    def rated_capacity(self) -> Union[Power_kW, float]:
        return self.rated_power

    @property
    def rated_capacity_unit(self) -> str:
        return "kW"

    @property
    def fuel_consumer_type_fuel_eu_maritime(self) -> FuelConsumerClassFuelEUMaritime:
        return None


class BasicComponent(Component):
    """
    Class for basic information and efficiency interpolation
    """

    def __init__(
        self,
        type_: TypeComponent,
        power_type: TypePower,
        name: str = "",
        rated_power: Power_kW = Power_kW(0.0),
        eff_curve: np.ndarray = np.array([1]),
        rated_speed: Speed_rpm = Speed_rpm(0.0),
        file_name: str = None,
        uid: Optional[str] = None,
    ):
        super(BasicComponent, self).__init__(
            name=name,
            type_=type_,
            power_type=power_type,
            rated_power=rated_power,
            rated_speed=rated_speed,
            uid=uid,
        )
        if file_name is not None:
            df = pd.read_csv(file_name, index_col=0)
            self.rated_power = df["Rated Power"].values[0]
            self.rated_speed = df["Rated Speed"].values[0]
            (
                self._efficiency_interp,
                self._efficiency_points,
            ) = get_efficiency_curve_from_dataframe(df, "Efficiency")
            self.name = df.index[0]
        else:
            if eff_curve is None:
                self._efficiency_interp = None
                self._efficiency_points = None
            else:
                (
                    self._efficiency_interp,
                    self._efficiency_points,
                ) = get_efficiency_curve_from_points(eff_curve)
        if self.rated_power <= 0:
            err_msg = (
                f"The rated power of the component, {self.name}, has not been "
                f"defined or is 0. It must be a positive number"
            )
            logger.error(err_msg)
            raise InputError(err_msg)

        #: Make a mapping between the power in to out
        power_out = np.arange(-self.rated_power, self.rated_power, self.rated_power * 0.01)
        load = self.get_load(power_out)
        power_in = power_out / self.get_efficiency_from_load_percentage(load)

        #: see the power_in is monotonic
        diff_power_in = np.diff(power_in)
        is_monotonic = (diff_power_in > 0).all() or (diff_power_in < 0).all()
        if not is_monotonic:
            msg = (
                f"Mapping between the power output to power input is not monotonic for "
                f"the component, {name}. This will cause an efficiency calculation incorrect."
                f"You should check your efficiency values."
            )
            logger.error(msg)
            raise InputError(msg)
        self._power_out_interp = PchipInterpolator(
            power_in, power_out, extrapolate=True
        )  # Interpolation function

    def _get_power_input_and_load_from_output(
        self, power_output: NumericT
    ) -> Tuple[NumericT, NumericT]:
        load = self.get_load(power_output)
        return power_output / self.get_efficiency_from_load_percentage(load), load

    def _get_power_output_and_load_from_input(
        self, power_input: NumericT, strict_power_balance: bool = False
    ) -> Tuple[NumericT, NumericT]:
        power_output = self._power_out_interp(power_input)
        if strict_power_balance:
            if type(power_input) is not np.ndarray:
                power_output = newton(self._power_balance, power_output, args=(power_input,))
            else:
                no_points_per_batch = 50
                no_points = len(power_input)
                no_iter = int(np.floor(no_points / no_points_per_batch))
                start_idx = 0
                end_idx = no_points_per_batch
                for i in range(no_iter):
                    res = root(
                        self._power_balance_with_jac,
                        power_output[start_idx:end_idx],
                        args=(power_input[start_idx:end_idx],),
                        jac=True,
                    )
                    power_output[start_idx:end_idx] = res.x
                    start_idx += no_points_per_batch
                    end_idx += no_points_per_batch
                if start_idx < no_points:
                    res = least_squares(
                        self._power_balance,
                        x0=power_output[start_idx:],
                        args=(power_input[start_idx:],),
                    )
                    power_output[start_idx:] = res.x
        return power_output, self.get_load(power_output)

    def get_power_input_from_bidirectional_output(
        self, power_output: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """
        Calculate power input from the power output which is bidirectional. Positive
        power output means power out from the component and negative means power in (reverse power).
        @param: power_output: power output in kW
        @param: strict_power_balance: if True and the power is reverse, it will calculate the
            power input by Newton's method. Otherwise, it uses reverse interpolation function.
            Default is False.
        @returns: power input, power load (0-1)
        """
        if type(power_output) is not np.ndarray:
            if power_output >= 0:
                return self._get_power_input_and_load_from_output(power_output)
            else:
                return self._get_power_output_and_load_from_input(
                    power_output, strict_power_balance
                )
        else:
            idx_forward_power = power_output > 0
            idx_reverse_power = np.bitwise_not(idx_forward_power)
            power_input = power_output.copy()
            load = np.zeros(len(power_input))
            (
                power_input[idx_forward_power],
                load[idx_forward_power],
            ) = self._get_power_input_and_load_from_output(power_output[idx_forward_power])
            (
                power_input[idx_reverse_power],
                load[idx_reverse_power],
            ) = self._get_power_output_and_load_from_input(
                power_output[idx_reverse_power], strict_power_balance
            )
            return power_input, load

    def get_power_output_from_bidirectional_input(
        self, power_input: Union[float, np.ndarray], strict_power_balance: bool = False
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        if type(power_input) is not np.ndarray:
            if power_input > 0:
                return self._get_power_output_and_load_from_input(power_input)
            else:
                return self._get_power_input_and_load_from_output(power_input)
        else:
            idx_forward_power = power_input > 0
            idx_reverse_power = np.bitwise_not(idx_forward_power)
            power_output = power_input.copy()
            load = np.zeros(len(power_output))
            (
                power_output[idx_forward_power],
                load[idx_forward_power],
            ) = self._get_power_output_and_load_from_input(
                power_input[idx_forward_power], strict_power_balance
            )
            (
                power_output[idx_reverse_power],
                load[idx_reverse_power],
            ) = self._get_power_input_and_load_from_output(power_input[idx_reverse_power])
        return power_output, load

    def set_power_input_from_output(
        self, power_output: Union[float, np.ndarray]
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """
        Sets power input from the switchboard side to the component from the given power output.
        Positive power output means that it provides power to the consumer (Power consumption).
        Negative means that the power is supplied by the consumer and to the switchboard
        (Power generation).

        :param power_output: float or np.ndarray
        :return: power_input, load
        """
        #: First sets the power output of the component
        self.power_output = power_output

        #: Calculate the power input and %load considering the efficiency
        self.power_input, load = self.get_power_input_from_bidirectional_output(power_output)

        #: Return the result
        return self.power_input, load

    def set_power_output_from_input(
        self, power_input: Union[float, np.ndarray]
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """
        Sets power output to the consumer side from the given power input from the switchboard side.
        Positive power input means that it consumes power from the switchboard (Power consumption).
        Negative means that the power is supplied by the consumer and to the switchboard
        (Power generation).

        :param power_input: float or np.ndarray
        :return: power_output, load
        """
        #: First sets the power input of the component
        self.power_input = power_input

        #: Calculate the power output and %load considering the efficiency
        self.power_output, load = self.get_power_output_from_bidirectional_input(power_input)

        #: Return the result
        return self.power_output, load

    def _power_balance_power_output(
        self, x: np.ndarray, power_input: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate the power balance(difference) between power input and output with efficiency in
        consideration. The function is used to find the root of the power balance.

        :param x: power_output
        :param power_input:
        :return: power_balance = power_output - efficiency * power_input
        """
        load = self.get_load(x)
        power_output = power_input * self.get_efficiency_from_load_percentage(load)
        d_power_output = power_input * self._get_d_efficiency(x, 0.001 * x)
        return power_output, d_power_output

    def _power_balance(self, x: np.ndarray, power_input: np.ndarray) -> np.ndarray:
        power_output, d_power_output = self._power_balance_power_output(x, power_input)
        return x - power_output

    def _power_balance_with_jac(
        self, x: np.ndarray, power_input: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        power_output, d_power_output = self._power_balance_power_output(x, power_input)
        power_balance = x - power_output
        return power_balance, np.diag(1 - d_power_output)

    def _d_power_balance(self, x: np.ndarray, power_input: Numeric) -> float:
        """
        Calculate the power balance(difference) between power input and output with efficiency in
        consideration. The function is used to find the root of the power balance.

        :param x: power_output
        :param power_input:
        :return: power_balance = power_output - efficiency * power_input, jacobian(power_balance)
        """
        load = self.get_load(x)
        if not isinstance(power_input, np.ndarray):
            if power_input > 0:
                power_output = power_input * self.get_efficiency_from_load_percentage(load)
                d_power_output = power_input * self._get_d_efficiency(x, 0.001 * x)
            else:
                power_output = power_input / self.get_efficiency_from_load_percentage(load)
                d_power_output = (
                    -power_input
                    * self._get_d_efficiency(x, 0.001 * x)
                    / (self.get_efficiency_from_load_percentage(load)) ** 2
                )
        else:
            power_output = power_input.copy()
            d_power_output = power_output.copy()
            idx_reverse_power = power_input < 0
            idx_forward_power = np.bitwise_not(idx_reverse_power)
            power_output[idx_forward_power] = power_input[
                idx_forward_power
            ] * self.get_efficiency_from_load_percentage(load[idx_forward_power])
            d_power_output[idx_forward_power] = power_input[
                idx_forward_power
            ] * self._get_d_efficiency(x[idx_forward_power], 0.001 * x[idx_forward_power])
            power_output[idx_reverse_power] = power_input[
                idx_reverse_power
            ] / self.get_efficiency_from_load_percentage(load[idx_reverse_power])
            d_power_output[idx_reverse_power] = (
                -power_input[idx_reverse_power]
                * self._get_d_efficiency(x[idx_reverse_power], 0.001 * x[idx_reverse_power])
                / (self.get_efficiency_from_load_percentage(load[idx_reverse_power])) ** 2
            )
        power_balance = x - power_output
        return (power_balance * (1 - d_power_output)).sum()

    def _get_d_efficiency(self, power: np.ndarray, power_delta: np.ndarray) -> np.ndarray:
        load = self.get_load(power)
        load_delta = self.get_load(power + power_delta)
        return (
            self.get_efficiency_from_load_percentage(load_delta)
            - self.get_efficiency_from_load_percentage(load)
        ) / power_delta

    def get_efficiency_from_load_percentage(
        self, load_percentage: Union[float, np.ndarray]
    ) -> Union[float, np.ndarray]:
        if self._efficiency_interp is None:
            raise ValueError("The efficiency curves not defined.")
        return np.clip(self._efficiency_interp(load_percentage), 0.01, 1)


class SerialSystem(BasicComponent):
    """Component for serial systems
    class for serial system with basic information and efficiency interpolation
    the list of components should follow the order of connection from the terminal to the
    switchboard to the other end.

    :param `type_`: Type of the component.
    :param power_type: Type of the power.
    :param name: Name
    :param components: List of components. The component should be listed in the order from the
        switchboard (power input side) to the other
    :param rated_power: (optional) Rated Power should be the same as the first component in the list
    :param rated_speed: (optional) Rated speed should be the same as the first component in the list
    """

    def __init__(
        self,
        type_: TypeComponent,
        power_type: TypePower,
        name: str,
        components: List[BasicComponent],
        rated_power: Power_kW = None,
        rated_speed: Speed_rpm = None,
        uid: Optional[str] = None,
    ):
        self.component_names = []
        self.components = components
        #: Calculate the total efficiency
        load = np.arange(0, 1.01, 0.1)
        efficiency_total = np.ones(len(load))
        for i, component in enumerate(components):
            self.component_names.append(component.name)
            if i > 0:
                load = component.get_load(components[i - 1].rated_power * load)
            efficiency_total *= component.get_efficiency_from_load_percentage(load)
        efficiency_points = np.append(
            np.reshape(load, (-1, 1)), np.reshape(efficiency_total, (-1, 1)), axis=1
        )

        #: If rated_power is not given, it is set to be the same as the first component
        if rated_power is None:
            rated_power = components[0].rated_power
        if rated_speed is None:
            rated_speed = components[0].rated_speed

        super(SerialSystem, self).__init__(
            name=name,
            type_=type_,
            power_type=power_type,
            rated_power=rated_power,
            rated_speed=rated_speed,
            eff_curve=efficiency_points,
            uid=uid,
        )
