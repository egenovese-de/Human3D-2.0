"""S0-002 characterization probes: PASS means observed baseline behavior, not fixed."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import time
import threading
import tempfile
import unittest
import subprocess
from pathlib import Path
from hashlib import sha256
from unittest.mock import Mock, patch
from PIL import Image
from human3d.session import Session
from human3d.orchestration import Coordinator
from human3d.vision import Landmark, SubjectEvidence, PoseLandmarker
from human3d.anatomical_evidence import EvidenceAdapter
from human3d.mask_review import MaskDraft

class AuditProbes(unittest.TestCase):
    def test_aud01_provider_failure_and_offline(self):
        detector, provider = Mock(), Mock()
        evidence = SubjectEvidence("photo", "fixture", (32,32), ((Landmark(.5,.5,1,1),)*33,))
        detector.detect.return_value = evidence
        provider.observe.return_value = None
        adapter = EvidenceAdapter(detector, provider)
        self.assertEqual(adapter.detect(Path("fixture.png"), "photo"), evidence)
        provider.observe.side_effect = RuntimeError("offline")
        with self.assertRaisesRegex(RuntimeError, "offline"):
            adapter.detect(Path("fixture.png"), "photo")
        self.assertEqual(detector.detect(Path("fixture.png"), "photo"), evidence)

    def test_aud02_gui_status_and_action(self):
        from PySide6.QtWidgets import QApplication, QPushButton
        from human3d.desktop import PhotosWindow
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as root:
            window = PhotosWindow()
            try:
                window.attach(Path(root)/"project", True)
                self.assertFalse(window.session.snapshot().reconstruct.enabled)
                self.assertIn("Reconstruction unavailable", window.status.text())
                button = next(b for b in window.findChildren(QPushButton) if b.text()=="Fit included photos")
                self.assertTrue(button.isEnabled())
                with patch.object(window, "run_shared_fit") as fit:
                    button.click()
                    fit.assert_called_once()
            finally:
                window.close()

    def test_aud05_same_photo_mask_revision(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            session = Session(root/"project", True)
            photo = root/"fixture.png"
            Image.new("RGB",(32,32)).save(photo)
            session.ingest([photo])
            detector = Mock()
            detector.detect.side_effect = lambda p,d: SubjectEvidence(d,"fixture",(32,32),((Landmark(.5,.5,1,1),)*33,))
            evidence = session.detect_target(detector)
            draft = MaskDraft(evidence,0)
            draft.paint((8,8),(24,24),2,add=True)
            session.apply_mask(draft)
            before = session.shared_evidence().dependency_digest
            job = session.coordinator.submit("preview")
            session.coordinator.start(job.id)
            generation = session.coordinator.generation
            draft.paint((2,2),(5,5),1,add=True)
            session.apply_mask(draft)
            self.assertNotEqual(before, session.shared_evidence().dependency_digest)
            self.assertEqual(generation, session.coordinator.generation)
            self.assertTrue(session.coordinator.finish(job.id,"old",lambda _: True))
            self.assertIn("preview",session.snapshot().current_artifacts)

    def test_aud06_retention(self):
        import tracemalloc
        c = Coordinator("fixture")
        tracemalloc.start()
        try:
            for i in range(1000):
                j=c.submit("preview")
                c.start(j.id)
                c.finish(j.id,i,lambda _: True)
            current, peak = tracemalloc.get_traced_memory()
            jobs, artifacts=c.snapshot()
            self.assertEqual(len(jobs),1000)
            self.assertEqual(len(artifacts),1)
            print(f"AUD-06 jobs={len(jobs)} active={len(artifacts)} traced_current={current} traced_peak={peak}",flush=True)
        finally:
            tracemalloc.stop()

    def test_aud07_real_child_logical_cancel(self):
        c=Coordinator("fixture")
        j=c.submit("detect")
        c.start(j.id)
        started=threading.Event()
        results=[]
        real_run=subprocess.run
        def child(command, **kwargs):
            started.set()
            return real_run([sys.executable,"-c","import time; time.sleep(1.5)"],**kwargs)
        with tempfile.TemporaryDirectory() as root:
            model=Path(root)/"model.task"
            model.write_bytes(b"fixture")
            with patch("human3d.vision.MODEL_SHA256",sha256(b"fixture").hexdigest()):
                detector=PoseLandmarker(model)
            def worker():
                try:
                    detector.detect(Path(root)/"photo.png","photo")
                except Exception as e:
                    results.append(type(e).__name__)
                finally:
                    results.append(c.finish(j.id,"old",lambda _: True))
            with patch("human3d.vision.subprocess.run",side_effect=child):
                t=threading.Thread(target=worker)
                t.start()
                try:
                    self.assertTrue(started.wait(5))
                    c.cancel(j.id)
                    t.join(.2)
                    self.assertTrue(t.is_alive())
                finally:
                    t.join(10)
            self.assertFalse(t.is_alive())
            self.assertEqual(results[-1],False)
            self.assertEqual(c.snapshot()[0][0].state,"cancelled")
            print("AUD-07 real synthetic child not interrupted; stale publication rejected",flush=True)
