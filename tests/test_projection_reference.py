import unittest
from human3d.alignment import Camera
from human3d.fitting import _resize_projection

class ProjectionReference(unittest.TestCase):
    def test_cardinal_projection_reference(self):
        # Vertex (2,3,5), scale 10, image origin (100,200).
        for yaw, expected in [(0,120+170j),(90,150+170j),(-90,50+170j),(180,80+170j)]:
            with self.subTest(yaw=yaw):
                self.assertAlmostEqual(abs(Camera(yaw,10,100+200j,1).project((2,3,5))-expected),0.,places=10)
        self.assertEqual(Camera(0,10,100+200j,-1).project((2,3,5)),80+170j)
        self.assertEqual(Camera(0,10j,100+200j,1).project((2,3,5)),130+220j)

    def test_rounded_raster_reference(self):
        # A 301x1000 source becomes 77x256, not 77.056x256.
        scale = (77/301,256/1000)
        self.assertAlmostEqual(abs(_resize_projection(301+1000j,scale)-(77+256j)),0.,places=10)
        self.assertAlmostEqual(abs(_resize_projection(150.5+500j,scale)-(38.5+128j)),0.,places=10)
