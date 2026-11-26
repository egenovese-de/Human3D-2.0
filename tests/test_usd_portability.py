import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from math import pi
from zipfile import ZipFile
from PIL import Image
from pxr import Usd, UsdSkel, UsdShade, Gf
from human3d.alignment import Camera
from human3d.usd_export import export_body

class USDPortability(unittest.TestCase):
    def test_relocated_package_and_pose(self):
        body = {"mesh":{"vertices":[[0,0,0],[1,0,0],[0,1,0]],
                        "texcoords":[[0,0],[1,0],[0,1]],
                        "faces":[{"group":"body","corners":[[0,0],[1,1],[2,2]]}]},
                "rig":{"bones":{"root":{"head":"a","tail":"b","parent":None}},
                       "joint_vertices":{"a":[0],"b":[1]},
                       "skin":[{"root":1.}]*3}}
        alignment = SimpleNamespace(camera=Camera(0,40,10+50j,1),limb_angles={"root":-pi/2},limb_depth_ratios={},wrist_cross_axes={})
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/"original"
            source.mkdir()
            destination = source/"asset.usdz"
            export_body(destination,body,SimpleNamespace(controls={}),alignment,texture=Image.new("RGB",(64,64),(120,80,40)))
            relocated = root/"relocated.usdz"
            destination.replace(relocated)
            source.rmdir()
            with ZipFile(relocated) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn("albedo.png",[Path(n).name for n in archive.namelist()])
            stage = Usd.Stage.Open(str(relocated))
            shader = UsdShade.Shader.Get(stage,"/Human/Appearance/Albedo")
            self.assertTrue(shader.GetInput("file").Get().resolvedPath)
            pose = UsdSkel.Animation.Get(stage,"/Human/Pose")
            for frame in (1,2):
                point = pose.GetTransforms(Usd.TimeCode(frame))[0].Transform(Gf.Vec3d(1,0,0))
                self.assertTrue(Gf.IsClose(point,Gf.Vec3d(0,1,0),1e-5))
            with self.assertRaisesRegex(ValueError,"invalid_export_garment_name"):
                export_body(relocated,body,SimpleNamespace(controls={}),alignment,garments=[SimpleNamespace(garment=SimpleNamespace(name="../bad"))])
