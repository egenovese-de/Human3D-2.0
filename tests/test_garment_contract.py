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

    def test_rest_and_posed_contacts_report_distinct_results(self):
        from human3d.garments import measure_garment_contacts

        points = np.array([[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]])
        face = ((0, 0), (1, 1), (2, 2))
        body = {"mesh": {"vertices": points, "faces": [{"group": "body", "corners": face}]},
                "rig": {"bones": {"root": {}}}}
        shell = Garment("top_base", "top", 0, points + [0, 0, .06], (face,),
                        ((0, 0), (1, 0), (0, 1)), ({"root": 1.},) * 3, (0, 1, 2), .06)
        posed_shell = [[.5, .5, -1], [.5, .5, 1], [.5, 1.5, 1]]
        result = measure_garment_contacts(shell, body, points, points, posed_shell)
        self.assertEqual(result.neutral.crossing, 0)
        self.assertEqual(result.posed.crossing, 1)
        self.assertEqual(result.intersections, 1)
        self.assertIn("Posed: 1 crossing", result.describe())

    def test_layer_intersections_and_separated_control(self):
        points = np.array([[0., 0., 0.], [2., 0., 0.], [0., 2., 0.]])
        face = ((0, 0), (1, 1), (2, 2))
        body = {"mesh": {"vertices": points, "faces": [{"group": "body", "corners": face}]},
                "rig": {"bones": {"root": {}}}}
        base = Garment("top_base", "top", 0, points + [0, 0, .06], (face,),
                       ((0, 0), (1, 0), (0, 1)), ({"root": 1.},) * 3, (0, 1, 2), .06)
        outer = replace(base, name="top_outer", layer=1, points=points + [0, 0, .13])
        transforms = {"root": (np.eye(3), np.zeros(3))}
        clear = verify_layers([base, outer], body, points, transforms)
        self.assertFalse(clear.blocked)

        invalid = replace(outer, points=np.array([[.5, .5, -1], [.5, .5, 1], [.5, 1.5, 1]]))
        colliding = verify_layers([base, invalid], body, points, transforms)
        self.assertTrue(colliding.blocked)
        self.assertEqual(colliding.pairs[0][2].neutral.crossing, 1)
        self.assertEqual(colliding.pairs[0][2].posed.crossing, 1)
        self.assertIn("top_base and top_outer", colliding.describe())

    def test_lower_body_shell_drops_detached_components_across_uv_seams(self):
        from human3d.garments import _largest_shell_component

        lower_a = ((0, 0), (1, 1), (2, 2))
        lower_b = ((2, 7), (1, 8), (3, 9))
        hand = ((4, 4), (5, 5), (6, 6))
        point_contact = ((3, 3), (7, 10), (8, 11))
        self.assertEqual(_largest_shell_component([hand, lower_a, point_contact, lower_b]),
                         [lower_a, lower_b])

    def test_top_prototype_excludes_disconnected_neckline_faces(self):
        from human3d.garments import prototype

        points = np.array([
            [-.6, 3., 0.], [.6, 3., 0.], [-.6, 4., 0.], [.6, 4., 0.],
            [-.1, 4.4, .2], [.1, 4.4, .2], [0., 4.6, .2],
            [0., 1., 0.], [0., 0., 0.], [-.6, 4., 0.], [.6, 4., 0.], [0., 5.5, 0.],
        ])
        anchors = {"upperleg01.L": 7, "upperleg01.R": 7, "lowerleg01.L": 8, "lowerleg01.R": 8,
                   "upperarm01.L": 9, "upperarm01.R": 10, "head": 11, "foot.L": 8, "foot.R": 8}
        faces = [{"group": "body", "corners": tuple((index, index) for index in triangle)}
                 for triangle in ((4, 5, 6), (0, 1, 2), (2, 1, 3))]
        body = {
            "mesh": {"faces": faces, "texcoords": ((0., 0.),) * len(points)},
            "rig": {"joint_vertices": {name: [index] for name, index in anchors.items()},
                    "bones": {name: {"head": name} for name in anchors},
                    "skin": ({"head": 1.},) * len(points)},
        }
        for layer in (0, 1):
            shell = prototype(body, points, "top", layer=layer)
            self.assertEqual(shell.body_indices, (0, 1, 2, 3))
            self.assertEqual(len(shell.faces), 2)
