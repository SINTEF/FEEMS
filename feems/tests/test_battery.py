from unittest import TestCase

import numpy as np
from feems.components_model import Battery, ElectricComponent
from feems.components_model.component_electric import BatterySystem
from feems.types_for_feems import TypeComponent, TypePower


# input power is power on terminal
class TestBattery(TestCase):
    @staticmethod
    def get_battery_system(battery: Battery):
        converter = ElectricComponent(
            name="Converter for battery",
            rated_power=battery.rated_power,
            power_type=TypePower.POWER_TRANSMISSION,
            type_=TypeComponent.POWER_CONVERTER,
            switchboard_id=1,
            eff_curve=np.array([0.5]),
        )
        return BatterySystem(
            name="Battery system",
            battery=battery,
            converter=converter,
            switchboard_id=battery.switchboard_id,
        )

    def test_charging_battery(self):
        eta = 0.9
        battery = Battery(
            name="Battery",
            eff_charging=eta,
            eff_discharging=1,
            charging_rate_c=1,
            discharge_rate_c=1,
            switchboard_id=1,
            rated_capacity_kwh=1000,
        )
        terminal_power = 100
        internal_power = 90
        self.check_power_input_output_conversion_scalar(battery, internal_power, terminal_power)

    def test_charging_battery_system(self):
        eta = 0.9
        battery = Battery(
            name="Battery",
            eff_charging=eta,
            eff_discharging=1,
            charging_rate_c=1,
            discharge_rate_c=1,
            switchboard_id=1,
            rated_capacity_kwh=1000,
        )
        battery_system = self.get_battery_system(battery)
        terminal_power = 100
        internal_power = 45
        self.check_power_input_output_conversion_scalar(
            battery_system, internal_power, terminal_power
        )

    def test_discharging_battery(self):
        eta = 0.9
        battery = Battery(
            name="Battery",
            eff_charging=1,
            eff_discharging=eta,
            charging_rate_c=1,
            discharge_rate_c=1,
            switchboard_id=1,
            rated_capacity_kwh=1000,
        )
        terminal_power = -90
        internal_power = -100
        self.check_power_input_output_conversion_scalar(battery, internal_power, terminal_power)

    def test_discharging_battery_system(self):
        eta = 0.9
        battery = Battery(
            name="Battery",
            eff_charging=1,
            eff_discharging=eta,
            charging_rate_c=1,
            discharge_rate_c=1,
            switchboard_id=1,
            rated_capacity_kwh=1000,
        )
        battery_system = self.get_battery_system(battery)
        terminal_power = -45
        internal_power = -100
        self.check_power_input_output_conversion_scalar(
            battery_system, internal_power, terminal_power
        )

    def check_power_input_output_conversion_scalar(self, battery, internal_power, terminal_power):
        with self.subTest("Internal power from terminal power"):
            (
                internal_power_calculated,
                _,
            ) = battery.get_power_output_from_bidirectional_input(terminal_power)
            self.assertAlmostEqual(internal_power, internal_power_calculated)
        with self.subTest("Terminal power from internal power"):
            (
                terminal_power_calculated,
                _,
            ) = battery.get_power_input_from_bidirectional_output(internal_power)
            self.assertAlmostEqual(terminal_power, terminal_power_calculated)

    def test_array(self):
        eff_charging = 0.8
        eff_discharging = 0.9
        terminal_power = np.array([100, -90, -180, 200])
        internal_power = np.array([80, -100, -200, 160])
        battery = Battery(
            name="Battery",
            eff_charging=eff_charging,
            eff_discharging=eff_discharging,
            charging_rate_c=1,
            discharge_rate_c=1,
            switchboard_id=1,
            rated_capacity_kwh=1000,
        )
        with self.subTest("Internal power from terminal power"):
            (
                internal_power_calculated,
                _,
            ) = battery.get_power_output_from_bidirectional_input(terminal_power)
            np.testing.assert_almost_equal(internal_power_calculated, internal_power)
        with self.subTest("Terminal power from internal power"):
            (
                terminal_power_calculated,
                _,
            ) = battery.get_power_input_from_bidirectional_output(internal_power)
            np.testing.assert_almost_equal(terminal_power_calculated, terminal_power)

    def test_array_system(self):
        eff_charging = 0.8
        eff_discharging = 0.9
        terminal_power = np.array([100, -45, -90, 200])
        internal_power = np.array([40, -100, -200, 80])
        battery = Battery(
            name="Battery",
            eff_charging=eff_charging,
            eff_discharging=eff_discharging,
            charging_rate_c=1,
            discharge_rate_c=1,
            switchboard_id=1,
            rated_capacity_kwh=1000,
        )
        battery_system = self.get_battery_system(battery)

        with self.subTest("Internal power from terminal power"):
            (
                internal_power_calculated,
                _,
            ) = battery_system.get_power_output_from_bidirectional_input(terminal_power)
            np.testing.assert_almost_equal(internal_power_calculated, internal_power)
        with self.subTest("Terminal power from internal power"):
            (
                terminal_power_calculated,
                _,
            ) = battery_system.get_power_input_from_bidirectional_output(internal_power)
            np.testing.assert_almost_equal(terminal_power_calculated, terminal_power)
