from .fuel import TypeFuel
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
