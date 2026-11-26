import unittest

import numpy as np

from human3d.triangle_collision import TriangleContacts, triangle_contacts


class TriangleCollisionTests(unittest.TestCase):
    def test_labeled_pairs_in_both_orders_and_windings(self):
        horizontal = [[0, 0, 0], [2, 0, 0], [0, 2, 0]]
        cases = (
            ("separated planes", [[0, 0, 1], [2, 0, 1], [0, 2, 1]], TriangleContacts()),
            ("coplanar separation", [[2, 2, 0], [3, 2, 0], [2, 3, 0]], TriangleContacts()),
            ("crossing", [[.5, .5, -1], [.5, .5, 1], [.5, 1.5, 1]], TriangleContacts(crossing=1)),
            ("shared vertex", [[0, 0, 0], [0, 0, 1], [-1, 0, 0]], TriangleContacts(touching=1)),
            ("shared edge", [[0, 0, 0], [2, 0, 0], [0, -2, 0]], TriangleContacts(touching=1)),
            ("interior overlap", [[.2, .2, 0], [.4, .2, 0], [.2, .4, 0]],
             TriangleContacts(coplanar_overlap=1)),
        )
        for name, triangle, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(triangle_contacts([horizontal], [triangle]), expected)
                self.assertEqual(triangle_contacts([triangle[::-1]], [horizontal]), expected)

    def test_accelerated_filter_keeps_only_nearby_pairs(self):
        triangle = np.asarray([[0, 0, 0], [2, 0, 0], [0, 2, 0]])
        offsets = np.arange(40)[:, None, None] * np.array([10, 0, 0])
        surface = triangle + offsets
        self.assertEqual(triangle_contacts(surface, surface), TriangleContacts(coplanar_overlap=40))
        self.assertEqual(triangle_contacts(surface, []), TriangleContacts())

    def test_degenerate_surface_cannot_report_clear(self):
        with self.assertRaisesRegex(ValueError, "degenerate_collision_triangle"):
            triangle_contacts([[[0, 0, 0], [1, 0, 0], [2, 0, 0]]], [])
