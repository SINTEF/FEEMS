import random
import unittest

import numpy as np

from feems.components_model.utility import (
    get_list_random_distribution_numbers_for_total_number,
)
from feems.types_for_feems import TypePower
from tests.utility import (
    create_random_monotonic_eff_curve,
    create_switchboard_with_components,
)


class TestUtilityForTest(unittest.TestCase):
    def test_create_random_monotonic_eff_curve(self):
        #: Test with no input argument
        for _ in range(1000):
            eff_curve = create_random_monotonic_eff_curve()

            #: Check shape
            self.assertTrue(np.equal(eff_curve.shape, np.array([4, 2])).all())

            #: Check if the curve is monotonic
            diff = np.diff(eff_curve, axis=0)
            self.assertTrue((diff > 0).all() or (diff < 0).all())

        #: Test with input argument
        for _ in range(1000):
            minimum_efficiency = random.random()
            maximum_efficiency = random.random()
            try:
                eff_curve = create_random_monotonic_eff_curve(
                    minimum_efficiency, maximum_efficiency
                )
                #: Check if the minimum efficiency is larger than specified
                self.assertGreaterEqual(eff_curve[0, 1], minimum_efficiency)
                #: Check if the maximum efficiency is smaller than specified
                self.assertLessEqual(eff_curve[-1, 1], maximum_efficiency)
            except AssertionError:
                self.assertLess(maximum_efficiency, minimum_efficiency)

    def test_create_switchboard_with_components(self):
        for _ in range(100):
            #: Set the random parameters for creating the switchboard component
            number_components = random.randint(4, 100)
            number_components_list = (
                get_list_random_distribution_numbers_for_total_number(
                    4, number_components
                )
            )
            rated_power_avail = random.random() * 5000
            rated_speed_max = random.random() * 1000
            switchboard_id = random.randint(1, 10)

            #: Create a switchboard component
            switchboard = create_switchboard_with_components(
                switchboard_id,
                rated_power_avail,
                number_components_list[0],
                number_components_list[1],
                number_components_list[2],
                number_components_list[3],
            )

            #: Check if the number of components created is correct
            type_power = [type_power for type_power in TypePower]
            self.assertEqual(switchboard.no_power_sources, number_components_list[0])
            self.assertEqual(switchboard.no_consumers, number_components_list[1])
            self.assertEqual(switchboard.no_pti_pto, number_components_list[2])
            self.assertEqual(switchboard.no_energy_storage, number_components_list[3])

            #: Check if all the components have the right switchboard number
            for component in switchboard.components:
                self.assertEqual(component.switchboard_id, switchboard_id)

            #: Check if the sum of the all power sources is equal to the specified value
            power_avail_total = sum(
                [
                    component.rated_power
                    for component in switchboard.component_by_power_type[
                        TypePower.POWER_SOURCE.value
                    ]
                ]
            )
            self.assertAlmostEqual(power_avail_total, rated_power_avail, 1)


if __name__ == "__main__":
    unittest.main()
