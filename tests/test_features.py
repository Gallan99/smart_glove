import unittest

import numpy as np

from ml.features import extract_features


class FeatureTests(unittest.TestCase):
    def test_mean_and_standard_deviation_order(self):
        frames = np.array([[1, 2, 3, 4, 5], [3, 4, 5, 6, 7]], dtype=float)
        features = extract_features(frames)
        np.testing.assert_allclose(features[:5], [2, 3, 4, 5, 6])
        np.testing.assert_allclose(features[5:], [1, 1, 1, 1, 1])

    def test_rejects_wrong_sensor_count(self):
        with self.assertRaises(ValueError):
            extract_features(np.ones((10, 4)))


if __name__ == "__main__":
    unittest.main()
