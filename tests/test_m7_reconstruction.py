"""M7 persistence and Qt lifecycle tests with a controllable engine adapter."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread
from time import monotonic, sleep
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from human3d.empirical_desktop import EmpiricalWindow
from human3d.reconstruction import Cancelled, ReconstructionService, StaleRequest
from human3d.session import Session


class FixtureEngine:
    revision = "fixture-v1"

    def __init__(self):
        self.started = Event()
        self.release = Event()
        self.release.set()
        self.error = False

    def reconstruct(self, session, request, output, execution):
        with execution.stage("Fixture computation"):
            self.started.set()
            if not self.release.wait(5):
                raise RuntimeError("Test synchronization timeout.")
            execution.checkpoint()
            if self.error:
                raise ValueError("Fixture failure")
            vertices = np.array([(0., 0., 0.), (1., 0., 0.), (0., 1., 0.)])
            np.savez(output / "preview.npz", canonical=vertices, target=vertices * 2, faces=[[0, 1, 2]])
            (output / "canonical.usd").write_bytes(b"fixture USD")
            (output / "target.usd").write_bytes(b"fixture posed USD")
        return "fixture-canonical-id"


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.photo = self.root / "front.png"
        self.side = self.root / "side.png"
        Image.new("RGB", (24, 40), "red").save(self.photo)
        Image.new("RGB", (24, 40), "blue").save(self.side)
        self.engine = FixtureEngine()
        self.started = self.engine.started
        self.session = Session(self.root / "project", create=True)
        self.session.ingest([self.photo, self.side])
        self.service = ReconstructionService(self.session, {"m6": self.engine}, "fixture-app")

    def generate(self):
        return self.service.generate(self.service.request(), Event(), lambda progress: None)

    @patch("human3d.reconstruction.utc_now", return_value="2026-11-28T12:00:00+00:00")
    def test_atomic_attempts_cancel_failure_reopen_and_private_archive(self, _clock):
        first = self.generate()
        request = self.service.request()
        cancel = Event()
        cancel.set()
        with self.assertRaises(Cancelled):
            self.service.generate(request, cancel, lambda progress: None)
        self.engine.error = True
        with self.assertRaisesRegex(ValueError, "Fixture failure"):
            self.generate()
        reopened = ReconstructionService(Session(self.root / "project"), {"m6": self.engine}, "fixture-app")
        self.assertEqual(reopened.results()[0].id, first.id)
        self.assertEqual([r.metadata["status"] for r in reopened.results(include_failures=True)],
                         ["failed", "cancelled", "complete"])
        self.assertEqual(list(reopened.attempts.glob(".attempt-*")), [])
        export = self.root / "selected.usd"
        reopened.export(first, export, target=False)
        self.assertEqual(export.read_bytes(), b"fixture USD")
        evidence = self.root / "evidence.zip"
        reopened.export_evidence(first, evidence)
        with ZipFile(evidence) as archive:
            self.assertEqual(set(archive.namelist()), {"diagnostics.json", "summary.md"})
        reopened.export_evidence(first, evidence, include_photos=True)
        with ZipFile(evidence) as archive:
            self.assertEqual(len([name for name in archive.namelist() if name.startswith("references/")]), 2)
        first.file("canonical.usd").write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "integrity"):
            reopened.export(first, export, target=False)
        self.assertEqual(export.read_bytes(), b"fixture USD")

    def test_stale_target_rejects_publication_and_keeps_previous_result(self):
        first = self.generate()
        self.engine.started.clear()
        self.engine.release.clear()
        errors = []

        def worker():
            try:
                self.generate()
            except RuntimeError as error:
                errors.append(error)

        thread = Thread(target=worker)
        thread.start()
        try:
            self.assertTrue(self.started.wait(3))
            with self.assertRaisesRegex(RuntimeError, "already running"):
                self.generate()
            project = self.session.store.load()
            Session(self.root / "project").select_target(project.photos.photos[1].id)
        finally:
            self.engine.release.set()
            thread.join(5)
        self.assertIsInstance(errors[0], StaleRequest)
        self.assertEqual(self.service.results()[0].id, first.id)
        self.assertEqual(self.service.results(include_failures=True)[0].metadata["status"], "stale")

    def test_remove_target_preserves_history_and_original(self):
        first = self.generate()
        project = self.session.store.load()
        removed = project.photos.photos[0]
        self.session.remove_photo(removed.id)
        project = self.session.store.load()
        self.assertEqual(project.photos.target, project.photos.photos[0].id)
        self.assertEqual(self.service.results()[0].id, first.id)
        self.assertTrue((self.root / "project" / "originals" / removed.digest).exists())


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait_worker(self, window):
        end = monotonic() + 6
        while window.worker is not None and monotonic() < end:
            self.app.processEvents()
            sleep(.01)
        self.assertIsNone(window.worker)

    def test_main_actions_and_worker_lifecycle(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = QSettings(str(root / "desktop.ini"), QSettings.Format.IniFormat)
            engine = FixtureEngine()
            window = EmpiricalWindow({"m6": engine, "geometry": engine}, "fixture-app", settings=settings, reopen=False)
            self.addCleanup(window.close)
            window.show()
            self.assertFalse(window.actions["Generate 3D"].isEnabled())
            window.attach(root / "project", create=True)
            photo = root / "photo.jpg"
            Image.new("RGB", (30, 45), "white").save(photo)
            self.assertEqual(window.ingest([photo, photo])[1].status, "duplicate")
            self.assertIn("TARGET", window.photos.currentItem().text())
            self.assertTrue(window.actions["Generate 3D"].isEnabled())
            window.engine.setCurrentIndex(1)
            window.actions["Generate 3D"].trigger()
            self.wait_worker(window)
            first = window.active_result
            self.assertEqual(first.metadata["diagnostics"]["executed_engine"], "geometry")
            self.assertTrue(window.actions["Export 3D"].isEnabled())
            self.assertTrue(window.evidence_button.isEnabled())
            engine.release.clear()
            window.actions["Generate 3D"].trigger()
            window.actions["Cancel"].trigger()
            self.assertIn("Cancellation pending", window.status.text())
            engine.release.set()
            self.wait_worker(window)
            self.assertEqual(window.active_result.id, first.id)
            window.close()
            reopened = EmpiricalWindow({"m6": engine, "geometry": engine}, "fixture-app", settings=settings)
            try:
                self.assertEqual(reopened.engine.currentData(), "geometry")
                self.assertEqual(reopened.active_result.id, first.id)
            finally:
                reopened.close()
