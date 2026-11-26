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

    def test_application_coordinate_contract(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from hashlib import sha256
        from types import SimpleNamespace as NS
        from human3d.project_store import ProjectStore
        from human3d.originals import OriginalStore
        from human3d.ingestion import import_photos
        from human3d.thumbnails import thumbnail
        from human3d.appearance import prepare_view

        with TemporaryDirectory() as directory:
            root = Path(directory)
            store = ProjectStore(root / "project")
            store.create()
            originals = OriginalStore(store.directory)
            for orientation in range(1,9):
                with self.subTest(orientation=orientation):
                    photo = root / f"fixture-{orientation}.png"
                    source = Image.new("RGB",(19,31),(180,120,90))
                    source.putpixel((0,0),(255,0,0))
                    exif = source.getexif()
                    exif[274] = orientation
                    source.save(photo,exif=exif)
                    raw = photo.read_bytes()
                    digest = sha256(raw).hexdigest()
                    self.assertEqual(import_photos(store,[photo])[0].status,"accepted")
                    self.assertEqual(originals.verify(digest).read_bytes(),raw)
                    self.assertEqual(import_photos(store,[photo])[0].status,"duplicate")
                    expected = ImageOps.exif_transpose(Image.open(photo)).convert("RGB")
                    with Image.open(BytesIO(thumbnail(originals,digest,64))) as thumb:
                        self.assertEqual(thumb.convert("RGB").tobytes(),expected.tobytes())
                    native = _NativePoseLandmarker.__new__(_NativePoseLandmarker)
                    native._segmentation = True
                    native._array = np.asarray
                    native._format = None
                    native._image = lambda **kw: kw["data"]
                    def detect(array):
                        h,w = array.shape[:2]
                        self.assertTrue(np.array_equal(array[:,:expected.width],np.asarray(expected)))
                        p = NS(x=.25*expected.width/w,y=.5,visibility=1.,presence=1.,z=0.)
                        mask = np.zeros((h,w),np.float32)
                        mask[:,:expected.width//2] = 1
                        return NS(pose_landmarks=[[p]*33],pose_world_landmarks=[[p]*33],
                                  segmentation_masks=[NS(is_contiguous=lambda:True,numpy_view=lambda:mask)])
                    native._detector = NS(detect=detect)
                    evidence = native.detect(originals.verify(digest),digest)
                    self.assertEqual(evidence.image_size,expected.size)
                    self.assertAlmostEqual(evidence.candidates[0][0].x,.25)
                    self.assertAlmostEqual(evidence.candidates[0][0].y,.5)
                    reviewed = MaskDraft(evidence,0).validate()
                    view = NS(ref=NS(photo_digest=digest),mask=reviewed,detection=evidence,candidate=0)
                    appearance = prepare_view(originals,view,NS(camera=NS(yaw_degrees=0)))
                    self.assertTrue(np.array_equal(appearance.rgb,np.asarray(expected)))
                    self.assertTrue(appearance.foreground[:,0].all())
                    self.assertFalse(appearance.foreground[:,-1].any())
