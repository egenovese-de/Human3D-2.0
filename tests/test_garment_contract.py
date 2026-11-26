import unittest
from dataclasses import replace
import numpy as np
from human3d.garments import Garment, measure_clearance, posed_garment, verify_layers

class GarmentContract(unittest.TestCase):
    def test_signed_clearance_and_invalid_geometry(self):
        points = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
        face = ((0,0),(1,1),(2,2))
        body = {"mesh":{"vertices":points,"faces":[{"group":"body","corners":face}]},"rig":{"bones":{"root":{}}}}
        garment = Garment("top_base","top",0,points+[0,0,.06],(face,),((0,0),(1,0),(0,1)),({"root":1.},)*3,(0,1,2),.06)
        transforms = {"root":(np.eye(3),np.zeros(3))}
        report = measure_clearance(garment,body,points,posed_garment(garment,transforms))
        self.assertEqual(report.violations,0)
        self.assertAlmostEqual(report.minimum,.06)
        report = measure_clearance(garment,body,points,points-[0,0,.02])
        self.assertEqual(report.violations,4)
        self.assertAlmostEqual(report.minimum,-.02)
        for bad in (replace(garment,skin=({"root":.5},)*3),replace(garment,body_indices=(0,0,2)),replace(garment,faces=(((-1,0),(1,1),(2,2)),))):
            with self.assertRaises(ValueError):
                posed_garment(bad,transforms)
        with self.assertRaisesRegex(ValueError,"invalid_collision_geometry"):
            measure_clearance(garment,body,points,np.full((3,3),np.nan))
        with self.assertRaisesRegex(ValueError,"unsupported_layer_combination"):
            verify_layers([garment,replace(garment,name="duplicate")],body,points,transforms)
