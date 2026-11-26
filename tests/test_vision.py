import unittest
from dataclasses import replace

from human3d.vision import Landmark, SubjectEvidence


class SubjectEvidenceTests(unittest.TestCase):
    def test_provider_adapter_rejects_mismatched_and_ambiguous_evidence(self):
        from pathlib import Path
        from unittest.mock import Mock

        from human3d.anatomical_evidence import AnatomicalEvidence, EvidenceAdapter

        photo = Path("fixture.png")
        pose = (Landmark(.5, .5, .95, .95),) * 33
        subject = SubjectEvidence("hash", "detector", (100, 100), (pose,))
        detector = Mock()
        provider = Mock()
        adapter = EvidenceAdapter(detector, provider)
        detector.detect.return_value = replace(subject, candidates=(pose, pose))
        self.assertIs(adapter.detect(photo, "hash"), detector.detect.return_value)
        provider.observe.assert_not_called()
        detector.detect.return_value = subject
        provider.observe.return_value = AnatomicalEvidence("other", "fixture", "v1", 0)
        with self.assertLogs("human3d.anatomical_evidence", level="WARNING"):
            self.assertIs(adapter.detect(photo, "hash"), subject)
        provider.observe.return_value = replace(provider.observe.return_value, photo_digest="hash")
        self.assertEqual(adapter.detect(photo, "hash").anatomical, provider.observe.return_value)

    def test_unsupported_torso_form_does_not_reject_cropped_limbs(self):
        from human3d.vision import _unsupported_torso_form

        pose = [Landmark(.5, .5, .3, .9)] * 33
        self.assertTrue(_unsupported_torso_form(pose))
        cropped = pose.copy()
        cropped[27] = Landmark(.5, 1.05, .3, .9)
        self.assertFalse(_unsupported_torso_form(cropped))
        pose[15] = Landmark(.5, .5, .95, .95)
        self.assertFalse(_unsupported_torso_form(pose))

    def test_native_worker_failure_does_not_poison_detector_retry(self):
        from hashlib import sha256
        from pathlib import Path
        from subprocess import CompletedProcess
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from human3d.observations import ObservationStore
        from human3d.vision import PoseLandmarker

        with TemporaryDirectory() as directory:
            model = Path(directory) / "model.task"
            model.write_bytes(b"fixture")
            photo = Path(directory) / "photo.png"
            immutable = SubjectEvidence("photo", "model", (120, 120), ())

            def recover(command, **kwargs):
                record = ObservationStore(Path(command[6])).write_detection(immutable)
                return CompletedProcess(command, 0, record, "")

            with patch("human3d.vision.MODEL_SHA256", sha256(b"fixture").hexdigest()):
                detector = PoseLandmarker(model, segmentation=True)
            with patch("human3d.vision.run_cancellable", return_value=CompletedProcess([], -6, "", "")):
                with self.assertRaisesRegex(RuntimeError, "detector failed"):
                    detector.detect(photo, "photo")
            with patch("human3d.vision.run_cancellable", side_effect=recover):
                self.assertEqual(detector.detect(photo, "photo"), immutable)

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


class VisionSuitabilityTests(unittest.TestCase):
    def test_mask_and_landmarks_can_pass_while_full_pose_requires_review(self):
        from dataclasses import replace
        from io import BytesIO

        from PIL import Image, ImageDraw

        from human3d.vision import Landmark, SubjectEvidence, VisionSuitability

        mask = Image.new("L", (32, 32))
        ImageDraw.Draw(mask).rectangle((12, 2, 19, 29), fill=255)
        buffer = BytesIO()
        mask.save(buffer, format="PNG")
        pose = [Landmark(.5, .5, 1., 1.)] * 33
        pose[27] = Landmark(.5, .9, .5, 1.)
        result = SubjectEvidence("a" * 64, "b" * 64, (32, 32), (tuple(pose),), (buffer.getvalue(),))
        self.assertEqual(result.suitability(0), VisionSuitability(None, None, "insufficient_full_body_evidence"))
        self.assertEqual(replace(result, candidates=result.candidates * 2).suitability(0),
                         VisionSuitability("multiple_candidates", "multiple_candidates", "multiple_candidates"))
        self.assertEqual(replace(result, masks=(b"invalid",)).suitability(0).mask_reason, "invalid_mask_geometry")
        ImageDraw.Draw(mask).rectangle((12, 0, 19, 2), fill=255)
        clipped = BytesIO()
        mask.save(clipped, format="PNG")
        self.assertEqual(replace(result, masks=(clipped.getvalue(),)).suitability(0).mask_reason, "mask_touches_frame")
