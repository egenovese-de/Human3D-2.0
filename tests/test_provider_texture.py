import unittest
from human3d.texture_bake import _hidden_vertices

class ProviderTexture(unittest.TestCase):
    def test_all_supported_regions_and_native_default(self):
        names = ("head","jaw","eye.L","spine01","pelvis","upperarm01.L","upperarm01.R","upperleg01.L","upperleg01.R")
        rig = {"bones":dict.fromkeys(names), "skin":[{name:1.} for name in names]+[{"head":.5,"spine01":.5}]}
        self.assertEqual(_hidden_vertices(rig,()),set())
        for region, expected in [("face",{0,1,2}),("torso",{3,4}),("left_arm",{5}),("right_arm",{6}),("left_leg",{7}),("right_leg",{8})]:
            with self.subTest(region=region):
                self.assertEqual(_hidden_vertices(rig,{region}),expected)
        self.assertEqual(_hidden_vertices(rig,{"face","torso"}),{0,1,2,3,4,9})
