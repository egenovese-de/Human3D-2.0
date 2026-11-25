import unittest

import numpy as np

from human3d.alignment import Alignment, Camera
from human3d.native_rig import pose_transforms, skin_vertices, validate_pose


class ArticulationTests(unittest.TestCase):
    def test_spatial_swing_keeps_bone_lengths_and_propagates_to_child(self):
        rig = {"bones": {
            "upperarm01.L": {"head": "shoulder", "tail": "elbow", "parent": None},
            "lowerarm01.L": {"head": "elbow", "tail": "wrist", "parent": "upperarm01.L"},
        }}
        joints = {name: np.array(point, dtype=float) for name, point in {
            "shoulder": (0, 0, 0), "elbow": (1, 0, 0), "wrist": (2, 0, 0),
        }.items()}
        camera = Camera(20, 30 + 2j, 200 + 250j)
        for depth in (-2.0, 0.0, 2.0):
            alignment = Alignment(camera, 0, {"upperarm01.L": 1.0, "lowerarm01.L": -1.0},
                                  {"upperarm01.L": depth, "lowerarm01.L": -depth})
            transforms = pose_transforms(rig, joints, alignment)
            upper, lower = transforms["upperarm01.L"], transforms["lowerarm01.L"]
            elbow = upper[0] @ joints["elbow"] + upper[1]
            np.testing.assert_allclose(elbow, lower[0] @ joints["elbow"] + lower[1], atol=1e-9)
            self.assertAlmostEqual(np.linalg.norm(elbow), 1)
            vertices = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])
            posed = skin_vertices(vertices, [{"upperarm01.L": 1}] * 3, transforms)
            body = {"mesh": {"faces": [{"group": "body", "corners": [(0, 0), (1, 0), (2, 0)]}]}}
            validate_pose(body, vertices, posed)
            with self.assertRaisesRegex(ValueError, "pose_collapsed_body_face"):
                validate_pose(body, vertices, np.zeros_like(posed))
