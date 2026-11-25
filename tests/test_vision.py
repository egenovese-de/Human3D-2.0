import unittest
from dataclasses import replace

from human3d.vision import Landmark, SubjectEvidence


class SubjectEvidenceTests(unittest.TestCase):
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
        from human3d.vision import PoseLandmarker

        mask = np.array([[0., 1., 0.], [1., 1., 0.]], dtype=np.float32)
        expected = PoseLandmarker._mask_png(mask, (3, 2))
        self.assertIsNotNone(expected)
        self.assertEqual(PoseLandmarker._mask_png(mask[:, :, None], (3, 2)), expected)
