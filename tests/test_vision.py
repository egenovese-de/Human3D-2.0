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
