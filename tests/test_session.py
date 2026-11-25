import tempfile
import unittest
from pathlib import Path
from PIL import Image
from human3d.session import Session


class SessionTests(unittest.TestCase):
    def test_capabilities_and_invalidation(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            session = Session(root / "project", True)
            self.assertFalse(session.snapshot().select_target.enabled)
            self.assertFalse(session.snapshot().reconstruct.enabled)
            paths = []
            for i in range(2):
                path = root / f"{i}.png"
                Image.new("RGB", (32, 32), (i * 100, 0, 0)).save(path)
                paths.append(path)
            session.ingest(paths)
            snapshot = session.snapshot()
            self.assertTrue(snapshot.select_target.enabled)
            valid = session.coordinator.submit("preview")
            session.coordinator.start(valid.id)
            self.assertTrue(session.coordinator.finish(valid.id, "valid", lambda _: True))
            self.assertEqual(session.snapshot().current_artifacts, ("preview",))
            job = session.coordinator.submit("preview")
            session.coordinator.start(job.id)
            session.select_target(snapshot.project.photos.photos[1].id)
            self.assertFalse(session.coordinator.finish(job.id, "old", lambda _: True))
            invalidated = session.snapshot()
            self.assertEqual(invalidated.jobs[-1].state, "stale")
            self.assertEqual(invalidated.current_artifacts, ())
            self.assertEqual(invalidated.stale_artifacts, ("preview",))
            self.assertEqual(session.coordinator.snapshot()[1]["preview"][1], "valid")
            reopened = Session(root / "project")
            self.assertEqual(reopened.snapshot().project.photos.target,
                             snapshot.project.photos.photos[1].id)

    def test_target_detection_rejects_obsolete_evidence(self):
        from human3d.vision import SubjectEvidence

        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            session = Session(root / "project", True)
            for index in range(2):
                path = root / f"{index}.png"
                Image.new("RGB", (32, 32), (index, 0, 0)).save(path)
                session.ingest([path])
            first, second = session.snapshot().project.photos.photos

            class Detector:
                def detect(self, original, digest):
                    self.digest = digest
                    return SubjectEvidence(digest, "test", (32, 32), ())

            class SwitchingDetector(Detector):
                def detect(self, original, digest):
                    session.select_target(second.id)
                    return super().detect(original, digest)

            self.assertIsNone(session.detect_target(SwitchingDetector()))
            self.assertEqual(session.snapshot().jobs[-1].state, "stale")
            detector = Detector()
            self.assertEqual(session.detect_target(detector).photo_digest, second.digest)
            self.assertNotEqual(detector.digest, first.digest)
            self.assertEqual(session.snapshot().current_artifacts, ("subject_evidence",))
