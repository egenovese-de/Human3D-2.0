import unittest

import numpy as np

from human3d.alignment import Alignment, Camera
from human3d.appearance import AppearanceView
from human3d.texture_bake import bake_atlas


class TextureBakeTests(unittest.TestCase):
    def test_hidden_face_does_not_receive_observed_color(self):
        vertices = [(0, 0, 0), (1, 0, 0), (0, 1, 0),
                    (0, 0, 1), (1, 0, 1), (0, 1, 1)]
        mesh = {"vertices": vertices,
                "texcoords": [(0.05, .6), (.4, .6), (.05, .95), (.55, .1), (.9, .1), (.55, .45)],
                "faces": [
                    {"group": "body", "corners": [(0, 0), (1, 1), (2, 2)]},
                    {"group": "body", "corners": [(3, 3), (4, 4), (5, 5)]},
                ]}
        rig = {"joint_vertices": {"head": [0], "tail": [2]},
               "bones": {"root": {"head": "head", "tail": "tail", "parent": None}},
               "skin": [{"root": 1.0}] * len(vertices)}
        surface = np.zeros((64, 64, 3), dtype=np.uint8)
        surface[:, :, 0] = 250
        mask = np.ones((64, 64), dtype=bool)
        view = AppearanceView(surface, mask, np.zeros_like(mask), Alignment(Camera(0, 28, 12 + 48j, 1), 0, {}))
        atlas = bake_atlas({"mesh": mesh, "rig": rig}, {}, {"target": (view, (64, 64))}, "target", size=64)
        self.assertEqual(atlas.coverage.getpixel((8, 16)), 0)
        self.assertEqual(atlas.coverage.getpixel((40, 50)), 255)
        self.assertEqual(atlas.color.getpixel((40, 50)), (250, 0, 0))
        self.assertEqual(atlas.color.getpixel((8, 16)), (145, 145, 145))
