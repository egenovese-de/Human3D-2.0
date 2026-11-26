import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import weakref
import unittest
from pathlib import Path
from PIL import Image
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from human3d.desktop import PhotosWindow


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_create_import_click_reopen(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            paths = []
            for i in range(3):
                path = root / f"{i}.png"
                Image.new("RGB", (80, 120), (i * 80, 0, 0)).save(path)
                paths.append(path)
            window = PhotosWindow()
            window.resize(1000, 700)
            window.show()
            try:
                window.attach(root / "project", True)
                window.ingest(paths)
                self.app.processEvents()
                self.assertEqual(window.photos.count(), 3)
                item = window.photos.item(1)
                target = item.data(Qt.ItemDataRole.UserRole)
                QTest.mouseClick(window.photos.viewport(), Qt.MouseButton.LeftButton,
                                 pos=window.photos.visualItemRect(item).center())
                self.assertEqual(window.store.load().photos.target, target)
                window.attach(root / "project")
                self.assertEqual(window.photos.currentItem().data(Qt.ItemDataRole.UserRole), target)
                self.assertIn("Freeze a rest body first", window.status.text())
            finally:
                window.close()

    def test_repeated_target_switching_and_reopen(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            sources = [root / f"{i}.png" for i in range(3)]
            for i, path in enumerate(sources):
                Image.new("RGB", (32, 48), (i * 80, 0, 0)).save(path)
            window = PhotosWindow()
            self.addCleanup(window.close)
            project_path = root / "project"
            window.attach(project_path, True)
            window.ingest(sources)
            project = window.store.load()
            project = window.store.save(project.with_shared_fit("a" * 64))
            immutable_files = set(p for p in project_path.rglob("*") if p.is_file())
            for i in range(36):
                target = project.photos.photos[(i + 1) % 3].id
                item = window.photos.item((i + 1) % 3)
                before = window.store.load()
                window.fitted_preview = (before.id, before.revision, object(), object(), object())
                window.pose_correction = (before.id, before.revision, object(), object())
                window.select_target(item)
                self.assertIsNone(window.fitted_preview)
                self.assertIsNone(window.pose_correction)
                self.assertEqual(window.store.load().photos.target, target)
                self.assertEqual(window.photos.count(), 3)
                if i % 6 == 0:
                    previous = weakref.ref(window.session)
                    window.attach(project_path)
                    self.assertIsNone(previous())
                    self.assertEqual(window.photos.currentItem().data(Qt.ItemDataRole.UserRole), target)
                    self.assertEqual(window.session.snapshot().jobs, ())
                self.assertEqual(window.store.load().shared_fit_digest, project.shared_fit_digest)
            self.assertEqual(set(p for p in project_path.rglob("*") if p.is_file()), immutable_files)
