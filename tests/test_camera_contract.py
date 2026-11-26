import unittest
from dataclasses import replace
from math import nan, inf
from human3d.alignment import Camera, initialize_alignment, TORSO
from human3d.vision import Landmark, SubjectEvidence
from human3d.anatomical_evidence import AnatomicalEvidence

class CameraContract(unittest.TestCase):
    def test_invalid_transform(self):
        camera = Camera(0,100+0j,50+50j,1)
        for fields in ({"yaw_degrees":nan},{"similarity":0j},{"similarity":complex(inf,0)},{"origin":complex(0,nan)},{"horizontal_sign":0}):
            with self.subTest(fields=fields):
                with self.assertRaisesRegex(ValueError,"invalid_camera_transform"):
                    replace(camera,**fields)

    def test_projection_and_alignment(self):
        joints = [(0.2,0.5,0.03),(-0.2,0.5,-0.02),(0.13,0.,-0.04),(-0.13,0.,0.02)]
        body = {"rig":{"joints":joints,"bones":{name:{"head":i} for i,name in enumerate(TORSO.values())}}}
        for yaw in (0,90,-90,179,-179,130):
            with self.subTest(yaw=yaw):
                truth = Camera(yaw,120+7j,150+150j,1)
                pose = [Landmark(.5,.5,1.,1.)]*33
                for index,vertex in zip(TORSO,joints):
                    point = truth.project(vertex)
                    pose[index] = Landmark(point.real/300,point.imag/300,1.,1.)
                evidence = SubjectEvidence("photo","model",(300,300),(tuple(pose),),anatomical=AnatomicalEvidence("photo","fixture","v1",0,yaw=yaw,yaw_confidence=1.))
                alignment = initialize_alignment(body,evidence,0,refine=True)
                self.assertLess(alignment.torso_rms_pixels,1e-7)
                for vertex in joints:
                    self.assertAlmostEqual(abs(alignment.camera.project(vertex)-truth.project(vertex)),0.,places=6)
                with self.assertRaisesRegex(ValueError,"invalid_camera_image_size"):
                    initialize_alignment(body,replace(evidence,image_size=(0,300)),0)
                invalid = {"rig":body["rig"]|{"joints":[(nan,0,0)]*4}}
                with self.assertRaisesRegex(ValueError,"camera_initialization_failed"):
                    initialize_alignment(invalid,evidence,0)
