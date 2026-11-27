import unittest

import numpy as np

from human3d.garment_repair import MAX_DISPLACEMENT, repair_shell
from human3d.triangle_collision import triangle_contacts


class GarmentRepairTests(unittest.TestCase):
    def test_crossing_is_removed_with_fixed_topology_and_local_displacement(self):
        floor = np.array([[[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]]])
        points = np.array([[.3, .3, -.01], [.8, .3, .03], [.3, .8, .03],
                           [4., 4., .1], [5., 4., .1], [4., 5., .1]])
        faces = np.array([[0, 1, 2], [3, 4, 5]])
        identity = np.broadcast_to(np.eye(3), (len(points), 3, 3))
        offsets = np.zeros_like(points)
        repaired = repair_shell(points, faces, [(floor, identity, offsets)])
        self.assertEqual(triangle_contacts(floor, points[faces]).crossing, 1)
        self.assertEqual(triangle_contacts(floor, repaired[faces]).crossing, 0)
        np.testing.assert_array_equal(repaired[3:], points[3:])
        np.testing.assert_array_equal(points[0], [.3, .3, -.01])
        self.assertLessEqual(np.linalg.norm(repaired - points, axis=1).max(), MAX_DISPLACEMENT)

    def test_repair_accounts_for_the_posed_affine_skin_map(self):
        floor = np.array([[[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]]])
        points = np.array([[.3, .3, .05], [.8, .3, .08], [.3, .8, .08]])
        faces = np.array([[0, 1, 2]])
        identity = np.broadcast_to(np.eye(3), (len(points), 3, 3))
        offsets = np.tile([0., 0., -.06], (len(points), 1))
        repaired = repair_shell(points, faces, [(floor, identity, np.zeros_like(points)),
                                               (floor, identity, offsets)])
        self.assertEqual(triangle_contacts(floor, (repaired + offsets)[faces]).crossing, 0)
        self.assertGreater(repaired[0, 2], points[0, 2])

    def test_unsatisfiable_displacement_returns_original(self):
        floor = np.array([[[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]]])
        points = np.array([[.3, .3, -.4], [.8, .3, .03], [.3, .8, .03]])
        faces = np.array([[0, 1, 2]])
        identity = np.broadcast_to(np.eye(3), (len(points), 3, 3))
        self.assertIs(repair_shell(points, faces, [(floor, identity, np.zeros_like(points))]), points)

    def test_transverse_self_crossing_can_extend_beyond_a_shared_vertex(self):
        from human3d.triangle_collision import triangle_contact_pairs

        first = [[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]
        second = [[0., 0., 0.], [.4, .3, -.1], [.1, .7, .1]]
        triangles = np.asarray([first, second])
        self.assertEqual(list(triangle_contact_pairs(triangles, triangles, self_query=True)),
                         [(0, 1, "crossing")])
