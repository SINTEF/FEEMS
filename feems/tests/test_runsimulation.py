from unittest import TestCase

import numpy as np

from feems.components_model import SwbId
from feems.runsimulation import EqualEngineSizeAllClosedSimulationInterface


# noinspection DuplicatedCode
class EqualEngineSizeTest(TestCase):
    def setUp(self) -> None:
        self.pms = EqualEngineSizeAllClosedSimulationInterface(
            swb2n_gensets={SwbId(1): 1, SwbId(2): 2},
            rated_power_gensets=1000.0,
            n_bus_ties=1,
            maximum_allowable_genset_load_percentage=0.8,
        )

    def test__ideal_number_of_gensets_on(self):
        power = np.asarray([-100, 0, 500, 1500, 1999, 2500, 3500])
        expected = np.asarray([1, 1, 1, 2, 3, 3, 3])
        actual = self.pms._ideal_number_of_gensets_on(
            total_power_kw=power, n_datapoints=len(power)
        )
        np.testing.assert_array_equal(expected, actual)

    def test__convert_number_of_engines_on_to_status_matrix(self):
        n_genset_on = np.asarray([1, 2, 3])
        expected = {
            SwbId(1): np.asarray([[1], [1], [1]]),
            SwbId(2): np.asarray([[0, 0], [1, 0], [1, 1]]),
        }
        actual = self.pms._convert_number_of_engines_on_to_status_matrix(
            ideal_number_genset=n_genset_on, n_datapoints=len(n_genset_on)
        )
        np.testing.assert_array_equal(expected.keys(), actual.keys())
        for swb_id in expected.keys():
            np.testing.assert_array_equal(expected[swb_id], actual[swb_id])


# noinspection DuplicatedCode
class BatteryOnly(TestCase):
    def setUp(self) -> None:
        self.pms = EqualEngineSizeAllClosedSimulationInterface(
            swb2n_gensets={SwbId(1): 1, SwbId(2): 2},
            rated_power_gensets=1000.0,
            n_bus_ties=1,
            maximum_allowable_genset_load_percentage=0.8,
        )

    def test__ideal_number_of_gensets_on(self):
        power = np.asarray([-100, 0, 500, 1500, 1999, 2500, 3500])
        expected = np.asarray([1, 1, 1, 2, 3, 3, 3])
        actual = self.pms._ideal_number_of_gensets_on(
            total_power_kw=power, n_datapoints=len(power)
        )
        np.testing.assert_array_equal(expected, actual)

    def test__convert_number_of_engines_on_to_status_matrix(self):
        n_genset_on = np.asarray([1, 2, 3])
        expected = {
            SwbId(1): np.asarray([[1], [1], [1]]),
            SwbId(2): np.asarray([[0, 0], [1, 0], [1, 1]]),
        }
        actual = self.pms._convert_number_of_engines_on_to_status_matrix(
            ideal_number_genset=n_genset_on, n_datapoints=len(n_genset_on)
        )
        np.testing.assert_array_equal(expected.keys(), actual.keys())
        for swb_id in expected.keys():
            np.testing.assert_array_equal(expected[swb_id], actual[swb_id])
