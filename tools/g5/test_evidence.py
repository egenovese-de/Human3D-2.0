"""G5 channel-specific regressions that run without proprietary model assets."""
import unittest

import numpy as np

from evidence import affine_inverse, aligned_depth, dsine_to_camera, perspective_normals


class Camera:
    distance = 420
    span = 215
    dx = .02
    dy = -.03


class EvidenceTests(unittest.TestCase):
    def test_perspective_depth_recovers_tilted_plane_normal(self):
        size = 48
        y, x = np.indices((size, size)) + .5
        normal = np.array([.2, -.13, 1.])
        normal /= np.linalg.norm(normal)
        focal = size * Camera.distance / Camera.span
        ray = np.stack(((x - size * (.5 + Camera.dx)) / focal,
                        -(y - size * (.5 + Camera.dy)) / focal, -np.ones_like(x)), -1)
        depth = -400 / (ray @ normal)
        expected = np.broadcast_to(normal, (size - 2, size - 2, 3))
        np.testing.assert_allclose(perspective_normals(depth, Camera), expected, atol=1e-11)

    def test_dsine_normal_conversion_preserves_outward_front_and_tilt(self):
        stored = np.array([[-.6, 0., .8], [0, 0, 1.]])
        np.testing.assert_allclose(dsine_to_camera(stored), [[.6, 0, .8], [0, 0, 1.]])

    def test_single_affine_alignment_recovers_depth(self):
        prediction = np.arange(1, 20, dtype=np.float32)
        ideal = 1 / (prediction * .000004 + .002)
        mapped = aligned_depth(prediction, *affine_inverse(prediction, ideal))
        np.testing.assert_allclose(mapped, ideal, rtol=1e-6)

    def test_invalid_inverse_depth_remains_unavailable(self):
        self.assertTrue(np.isinf(aligned_depth(np.array([0.]), 1., 0.))[0])


if __name__ == '__main__':
    unittest.main()
