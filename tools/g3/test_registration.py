from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import numpy as np
from PIL import Image, ImageOps
from projection import Camera
from registration import Frame, Observation, FIT_SIZE, image_metadata, scale_certificate, deduplicate

class RegistrationContracts(unittest.TestCase):
    def test_all_exif_orientations_agree_with_pillow_centres(self):
        source = np.arange(24,dtype=np.uint8).reshape(4,6)
        yy,xx = np.indices(source.shape)
        xy = np.column_stack([xx.ravel()+.5, yy.ravel()+.5])
        for orientation in range(1,9):
            image = Image.fromarray(source)
            image.getexif()[274] = orientation
            rendered = np.asarray(ImageOps.exif_transpose(image))
            frame = Frame.create(6,4,orientation)
            mapped = frame.map(xy)
            ix,iy = np.floor(mapped).astype(int).T
            np.testing.assert_array_equal(rendered[iy,ix],source.ravel())
            np.testing.assert_allclose(frame.map(mapped,True),xy,atol=1e-12)

    def test_crop_resize_roundtrip(self):
        frame = Frame.create(384,384,6,(7,15,320,300),(128,180))
        xy = np.array([[32.,40.],[128.5,79.5]])
        np.testing.assert_allclose(frame.map(frame.map(xy),True),xy,atol=1e-12)

    def test_perspective_scale_gauge(self):
        rng=np.random.default_rng(741)
        xyz=rng.normal(size=(32,3))*15
        camera=Camera(39,distance=288,perspective=True,elevation=8,roll=4,dx=.07)
        scaled=Camera(39,distance=576,span=430,perspective=True,elevation=8,roll=4,dx=.07)
        np.testing.assert_allclose(camera.project(xyz,FIT_SIZE)[:,:2],scaled.project(2*xyz,FIT_SIZE)[:,:2])
        empty=np.array([])
        self.assertIsNone(scale_certificate(Observation(empty,empty,empty,empty),camera)['distance_cm'])
        self.assertEqual(scale_certificate(Observation(empty,empty,empty,empty,660.,2.),camera)['distance_cm'],576)

    def test_real_jpeg_exif_roundtrip(self):
        with TemporaryDirectory() as temp:
            path = Path(temp)/'oriented.jpg'
            im=Image.new('RGB',(640,480))
            exif=Image.Exif()
            exif[274]=6
            exif[37386]=28.
            exif[41989]=50
            im.save(path,exif=exif)
            meta=image_metadata(path)
            self.assertEqual(meta['orientation'],6)
            self.assertEqual(meta['oriented_size'],(480,640))
            self.assertEqual(meta['focal_mm'],28.)
            self.assertAlmostEqual(meta['approximate_raw_focal_px'],924.500327,places=4)

    def test_duplicate_retains_complementary_view(self):
        mask=np.eye(20,dtype=bool)
        items=[{'id':'first','yaw':0,'mask':mask,'weight':.7},
               {'id':'good','yaw':3,'mask':mask,'weight':.9},
               {'id':'side','yaw':90,'mask':mask,'weight':.4}]
        kept,duplicates=deduplicate(items)
        self.assertEqual([k['id'] for k in kept],['good','side'])
        self.assertEqual(duplicates,[('first','good')])

if __name__=='__main__':
    unittest.main()
