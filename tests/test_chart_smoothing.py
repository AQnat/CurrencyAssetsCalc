import unittest

from gui.main_window import smooth_micro_series


class TestChartSmoothing(unittest.TestCase):
    def test_micro_series_is_smoothed_with_median(self):
        rates = [0.000001, 0.5, 0.000002, 0.000003]
        smoothed = smooth_micro_series(rates, enabled=True)
        self.assertEqual(smoothed[1], 0.000002)

    def test_non_micro_series_is_not_smoothed(self):
        rates = [1.0, 100.0, 2.0]
        smoothed = smooth_micro_series(rates, enabled=True)
        self.assertEqual(smoothed, rates)

    def test_disabled_smoothing_returns_original(self):
        rates = [0.000001, 0.9, 0.000002]
        smoothed = smooth_micro_series(rates, enabled=False)
        self.assertEqual(smoothed, rates)


if __name__ == "__main__":
    unittest.main()

