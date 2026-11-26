"""Synthetic coordinate-contract regression tests."""
import unittest
from io import BytesIO
import numpy as np
from PIL import Image, ImageOps
from human3d.vision import _inference_image, _NativePoseLandmarker
from human3d.mask_review import MaskDraft
from human3d.vision import SubjectEvidence, Landmark

class ImageCoordinates(unittest.TestCase):
    def test_all_exif_orientations(self):
        source = Image.new("RGB", (3, 2))
        source.putdata([(i * 40, 0, 0) for i in range(6)])
        expected = [
            [0,1,2,3,4,5], [2,1,0,5,4,3],
            [5,4,3,2,1,0], [3,4,5,0,1,2],
            [0,3,1,4,2,5], [3,0,4,1,5,2],
            [5,2,4,1,3,0], [2,5,1,4,0,3],
        ]
        for orientation, order in enumerate(expected, 1):
            with self.subTest(orientation=orientation):
                exif = source.getexif()
                exif[274] = orientation
                buffer = BytesIO()
                source.save(buffer, format="PNG", exif=exif)
                buffer.seek(0)
                with Image.open(buffer) as decoded:
                    oriented = ImageOps.exif_transpose(decoded)
                    self.assertEqual(oriented.size, (3,2) if orientation <= 4 else (2,3))
                    self.assertEqual(list(oriented.getdata()), [(i*40,0,0) for i in order])

    def test_padding_and_resize(self):
        for size, content in [((17,31),(17,31)), ((2050,4100),(1024,2048)), ((4100,2050),(2048,1024))]:
            with self.subTest(size=size):
                image, actual = _inference_image(Image.new("RGB", size, "white"))
                self.assertEqual(actual, content)
                self.assertEqual(image.height, content[1])
                self.assertEqual(image.width % 16, 0)
                self.assertLess(image.width-content[0],16)
                self.assertEqual(image.getpixel((content[0]-1,0)), (255,255,255))
                if image.width > content[0]:
                    self.assertEqual(image.getpixel((content[0],0)), (0,0,0))

    def test_mask_crop_resize_and_draft(self):
        probabilities = np.zeros((8,16), dtype=np.float32)
        probabilities[:, :4] = 1
        probabilities[:, 10:] = 1  # padding must never become foreground
        png = _NativePoseLandmarker._mask_png(probabilities,(16,8),(10,8),(20,16))
        self.assertIsNotNone(png)
        with Image.open(BytesIO(png)) as mask:
            self.assertEqual(mask.size,(20,16))
            self.assertEqual(mask.getpixel((1,8)),255)
            self.assertEqual(mask.getpixel((19,8)),0)
        evidence = SubjectEvidence("fixture","model",(20,16),((Landmark(.5,.5,1,1),)*33,), (png,))
        draft = MaskDraft(evidence,0)
        self.assertEqual(draft.image.size,(20,16))
        self.assertEqual(draft.validate().photo_digest,"fixture")
        self.assertIsNone(_NativePoseLandmarker._mask_png(np.zeros((7,16)),(16,8)))
