import numpy as np
from scipy.interpolate import PchipInterpolator

from .types_for_feems import NOxCalculationMethod

hhv_hydrogen_mj_per_kg = 141.8
lhv_hydrogen_mj_per_kg = 119.96

#: NOx factor
nox_factor_imo_slow_speed_g_kWh = {
    NOxCalculationMethod.TIER_1.value: 17.0,
    NOxCalculationMethod.TIER_2.value: 14.4,
    NOxCalculationMethod.TIER_3.value: 3.4,
}
nox_tier_slow_speed_max_rpm = 130
nox_factor_imo_medium_speed_g_hWh = {
    NOxCalculationMethod.TIER_1.value: (45, -9.2),
    NOxCalculationMethod.TIER_2.value: (44, -0.23),
    NOxCalculationMethod.TIER_3.value: (9, -0.2),
}

#: Saturated steam specific enthalpy h_g (kJ/kg) vs. pressure (bar), IAPWS-IF97
_SATURATED_STEAM_HG_TABLE = np.array([
    [1.0,  2675.6],
    [2.0,  2706.3],
    [3.0,  2724.9],
    [4.0,  2737.6],
    [5.0,  2747.5],
    [6.0,  2756.1],
    [7.0,  2763.1],
    [8.0,  2769.1],
    [9.0,  2774.3],
    [10.0, 2778.9],
    [12.0, 2786.5],
    [15.0, 2792.2],
    [20.0, 2798.3],
])

_SATURATED_STEAM_PRESSURE_MIN_BAR: float = 1.0
_SATURATED_STEAM_PRESSURE_MAX_BAR: float = 20.0

_saturated_steam_h_g_interp = PchipInterpolator(
    _SATURATED_STEAM_HG_TABLE[:, 0],
    _SATURATED_STEAM_HG_TABLE[:, 1],
    extrapolate=False,
)


def get_saturated_steam_h_g_kj_per_kg(pressure_bar: float) -> float:
    """Return saturated vapour enthalpy h_g (kJ/kg) at pressure_bar using IAPWS-IF97 table.

    Raises InputError if pressure_bar is outside [1, 20] bar.
    """
    from .exceptions import InputError

    if pressure_bar < _SATURATED_STEAM_PRESSURE_MIN_BAR or pressure_bar > _SATURATED_STEAM_PRESSURE_MAX_BAR:
        raise InputError(
            f"Working pressure {pressure_bar} bar is outside the supported range "
            f"[{_SATURATED_STEAM_PRESSURE_MIN_BAR}, {_SATURATED_STEAM_PRESSURE_MAX_BAR}] bar."
        )
    return float(_saturated_steam_h_g_interp(pressure_bar))
