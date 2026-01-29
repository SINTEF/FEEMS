import unittest

import numpy as np
from feems.components_model.utility import get_list_random_distribution_numbers_for_total_number
from feems.exceptions import InputError


class TestUtility(unittest.TestCase):
    def test_get_list_random_distribution_numbers_for_total_number(self):
        for _ in range(10000):
            number_element = np.random.randint(1, 10)
            sum_element = np.random.randint(1, 1000)
            try:
                list_number = get_list_random_distribution_numbers_for_total_number(
                    number_element, sum_element
                )
                self.assertEqual(len(list_number), number_element)
                self.assertEqual(sum(list_number), sum_element)
                self.assertGreater(min(list_number), 0)
            except InputError:
                self.assertGreater(number_element, sum_element)


if __name__ == "__main__":
    unittest.main()
