import unittest
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
from human3d.alignment import Camera
from human3d.appearance import AppearanceView
from human3d.texture_bake import bake_atlas

class TextureContract(unittest.TestCase):
    def test_synthetic_atlas_and_invalid_inputs(self):
        body = {"mesh":{"vertices":[[0,0,0],[1,0,0],[0,1,0]],
                        "texcoords":[[0,0],[1,0],[0,1]],
                        "faces":[{"group":"body","corners":[[0,0],[1,1],[2,2]]}]},
                "rig":{"bones":{"root":{"head":"a","tail":"b","parent":None}},
                       "joint_vertices":{"a":[0],"b":[1]},
                       "skin":[{"root":1.}]*3}}
        alignment = SimpleNamespace(camera=Camera(0,40,10+50j,1),limb_angles={},limb_depth_ratios={},wrist_cross_axes={})
        rgb = np.full((64,64,3),[120,80,40],dtype=np.uint8)
        mask = np.ones((64,64),dtype=bool)
        view = AppearanceView(rgb,mask,mask,alignment)
        views = {"target":(view,(64,64))}
        atlas = bake_atlas(body,{},views,"target",size=64)
        observed = np.asarray(atlas.coverage)==255
        self.assertGreater(atlas.observed_fraction,.8)
        self.assertTrue(np.all(np.asarray(atlas.color)[observed]==[120,80,40]))
        self.assertTrue(np.all(np.asarray(atlas.skin_candidate)[observed]==255))
        for bad in (replace(view,rgb=rgb[:32]),replace(view,foreground=mask.astype(np.uint8)),replace(view,hair_candidate=mask[:32])):
            with self.assertRaisesRegex(ValueError,"invalid_appearance_view"):
                bake_atlas(body,{},{"target":(bad,(64,64))},"target",size=64)
        with self.assertRaisesRegex(ValueError,"invalid_appearance_view"):
            bake_atlas(body,{},{"target":(view,(0,64))},"target",size=64)
        with self.assertRaisesRegex(ValueError,"invalid_appearance_target_or_size"):
            bake_atlas(body,{},views,"target",size=64.5)
        body["mesh"]["texcoords"][0]=[-.1,0]
        with self.assertRaisesRegex(ValueError,"invalid_texture_uv"):
            bake_atlas(body,{},views,"target",size=64)
