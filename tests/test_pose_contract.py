import unittest
from types import SimpleNamespace
from math import nan, inf, pi
import numpy as np
from human3d.alignment import Camera
from human3d.native_rig import pose_transforms, skin_vertices, validate_pose

class PoseContract(unittest.TestCase):
    def test_pose_parameters_and_analytic_rotation(self):
        rig = {"bones":{"root":{"head":"a","tail":"b","parent":None}}}
        joints = {"a":np.array([0.,0.,0.]),"b":np.array([1.,0.,0.])}
        alignment = SimpleNamespace(camera=Camera(0,100,0,1),limb_angles={"root":-pi/2},limb_depth_ratios={},wrist_cross_axes={})
        transforms = pose_transforms(rig,joints,alignment)
        np.testing.assert_allclose(skin_vertices([[1.,0.,0.]],[{"root":1.}],transforms),[[0.,1.,0.]],atol=1e-10)
        for field,value in (("limb_angles",nan),("limb_depth_ratios",inf),("wrist_cross_axes",(0.,nan,0.))):
            with self.subTest(field=field):
                candidate = SimpleNamespace(**vars(alignment))
                setattr(candidate,field,{"root":value})
                with self.assertRaisesRegex(ValueError,"invalid_pose_parameters"):
                    pose_transforms(rig,joints,candidate)

    def test_pose_geometry_validation(self):
        neutral = [[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]]
        body = {"mesh":{"faces":[{"group":"body","corners":[[0,0],[1,1],[2,2]]}]}}
        validate_pose(body,neutral,neutral)
        with self.assertRaisesRegex(ValueError,"pose_collapsed_body_face"):
            validate_pose(body,neutral,[[0.,0.,0.]]*3)
        with self.assertRaisesRegex(ValueError,"invalid_posed_vertices"):
            validate_pose(body,[[nan,0.,0.],*neutral[1:]],neutral)
        with self.assertRaisesRegex(ValueError,"missing_body_topology"):
            validate_pose({"mesh":{"faces":[]}},neutral,neutral)
