import unittest

import numpy as np

from human3d.garments import _signed_gaps


class GarmentClearanceTests(unittest.TestCase):
    def test_signed_triangle_distance_handles_second_side_and_edges(self):
        points = np.array([(0., 0., 0.), (1., 0., 0.), (0., 1., 0.)])
        samples = np.array([(0.25, 0.25, 0.04), (0.25, 0.25, -0.02), (1.2, 0., 0.1)])
        measurements = _signed_gaps(points, np.array([[0, 1, 2]]), samples)
        np.testing.assert_allclose(measurements, (0.04, -0.02, np.hypot(0.2, 0.1)), atol=1e-10)
