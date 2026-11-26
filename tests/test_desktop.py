import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
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
