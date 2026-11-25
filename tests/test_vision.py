import unittest
from dataclasses import replace

from human3d.vision import Landmark, SubjectEvidence


class SubjectEvidenceTests(unittest.TestCase):
    def test_external_visibility_is_photo_bound_and_can_only_reduce_observation(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from human3d.anatomical_evidence import AnatomicalEvidence, RegionVisibility, yaw_conflicts
        from human3d.observations import ObservationRef, ObservationStore

        visible = Landmark(.5, .5, 1, 1)
        uncertain = Landmark(.5, .5, .5, .5)
        pose = (visible,) * 15 + (uncertain,) + (visible,) * 17
        external = AnatomicalEvidence("photo", "fixture", "v1", 0,
                                      (RegionVisibility("face", False, .95),
                                       RegionVisibility("left_arm", True, .95)), 179, .95)
        detection = SubjectEvidence("photo", "model", (120, 120), (pose,), anatomical=external)
        with self.assertRaisesRegex(ValueError, "binding_mismatch"):
            replace(detection, photo_digest="other")
        with TemporaryDirectory() as directory:
            store = ObservationStore(Path(directory))
            record = ObservationRef("id", "photo", store.write_detection(detection))
            self.assertEqual(store.read_detection(record), detection)
        self.assertFalse(detection.visible_pose(0)[0].observed)
        self.assertFalse(detection.visible_pose(0)[15].observed)
        self.assertFalse(yaw_conflicts(external, -179))
        self.assertTrue(yaw_conflicts(external, 12))

    def test_full_body_coverage_keeps_partial_candidates_for_review(self):
        visible = Landmark(0.5, 0.5, 0.95, 0.95)
        pose = (visible,) * 33
        evidence = SubjectEvidence("photo", "model", (100, 100), (pose,))
        self.assertIsNone(evidence.review_reason)
        for ankle in (replace(visible, y=1.08), replace(visible, visibility=0.53)):
            partial_pose = pose[:27] + (ankle,) + pose[28:]
            partial = replace(evidence, candidates=(partial_pose,))
            self.assertEqual(partial.review_reason, "insufficient_full_body_evidence")
            self.assertEqual(len(partial.candidates), 1)
        self.assertEqual(replace(evidence, candidates=(pose, pose)).review_reason, "multiple_candidates")
        self.assertEqual(replace(evidence, candidates=()).review_reason, "no_subject_detected")

    def test_mask_brush_undo_and_binary_validation(self):
        from io import BytesIO
        from PIL import Image
        from human3d.mask_review import MaskDraft

        draft = MaskDraft(SubjectEvidence("photo", "model", (30, 30), ((),)), 0)
        with self.assertRaises(ValueError):
            draft.validate()
        draft.begin_stroke()
        draft.paint((4, 4), (8, 4), 2, add=True)
        draft.begin_stroke()
        draft.paint((23, 23), (23, 23), 2, add=True)
        with Image.open(BytesIO(draft.validate().png)) as result:
            self.assertEqual(result.getpixel((4, 4)), 255)
            self.assertEqual(result.getpixel((23, 23)), 255)
            self.assertEqual(result.getpixel((15, 15)), 0)
        draft.undo()
        self.assertEqual(draft.image.getpixel((23, 23)), 0)
        draft.begin_stroke()
        draft.paint((4, 4), (8, 4), 3, add=False)
        with self.assertRaises(ValueError):
            draft.validate()

    def test_single_channel_segmentation_with_explicit_channel_axis(self):
        import numpy as np
        from human3d.vision import _NativePoseLandmarker

        mask = np.array([[0., 1., 0.], [1., 1., 0.]], dtype=np.float32)
        expected = _NativePoseLandmarker._mask_png(mask, (3, 2))
        self.assertIsNotNone(expected)
        self.assertEqual(_NativePoseLandmarker._mask_png(mask[:, :, None], (3, 2)), expected)

    def test_inference_pads_float_mask_rows_and_discards_padding(self):
        from io import BytesIO

        import numpy as np
        from PIL import Image
        from human3d.vision import _NativePoseLandmarker, _inference_image

        inference, content = _inference_image(Image.new("RGB", (19, 11)))
        self.assertEqual(inference.size, (32, 11))
        self.assertEqual(content, (19, 11))
        pixels = np.zeros((11, 32), dtype=np.float32)
        pixels[:, 19:] = 1
        self.assertIsNone(_NativePoseLandmarker._mask_png(pixels, inference.size, content, (38, 22)))
        pixels[3:8, 6:12] = 1
        png = _NativePoseLandmarker._mask_png(pixels, inference.size, content, (38, 22))
        with Image.open(BytesIO(png)) as mask:
            self.assertEqual(mask.size, (38, 22))
            self.assertEqual(mask.getbbox(), (12, 6, 24, 16))
