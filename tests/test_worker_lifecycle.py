import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from threading import get_ident
from time import sleep
from PySide6.QtCore import QCoreApplication, QEvent, QTimer
from PySide6.QtWidgets import QApplication, QDialog
from human3d.desktop import PhotosWindow

class WorkerLifecycle(unittest.TestCase):
    def test_gui_timer_and_worker_error(self):
        app = QApplication.instance() or QApplication([])
        window = PhotosWindow()
        ticks = []
        timer = QTimer()
        timer.timeout.connect(lambda: ticks.append(get_ident()))
        timer.start(10)
        try:
            main = get_ident()
            def work():
                sleep(.2)
                return get_ident()
            self.assertNotEqual(window.run_worker(work), main)
            self.assertTrue(ticks)
            self.assertTrue(all(t == main for t in ticks))
            def fail():
                raise ValueError("fixture error")
            with self.assertRaisesRegex(ValueError, "fixture error"):
                window.run_worker(fail)
            self.assertEqual(window.run_worker(lambda: 42), 42)
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.assertEqual(window.findChildren(QDialog), [])
        finally:
            timer.stop()
            window.close()

    def test_cancel_dialog_waits_for_cleanup(self):
        from threading import Event
        from PySide6.QtWidgets import QPushButton
        app = QApplication.instance() or QApplication([])
        window = PhotosWindow()
        cancelled, cleaned = Event(), Event()
        def work():
            if not cancelled.wait(3):
                raise RuntimeError("cancel not delivered")
            sleep(.1)
            cleaned.set()
            raise ValueError("cancelled fixture")
        def click():
            dialog = app.activeModalWidget()
            if dialog:
                next(b for b in dialog.findChildren(QPushButton) if b.text()=="Cancel").click()
        QTimer.singleShot(100, click)
        try:
            with self.assertRaisesRegex(ValueError, "cancelled fixture"):
                window.run_worker(work, cancelled.set)
            self.assertTrue(cleaned.is_set())
            self.assertEqual(window.run_worker(lambda: 7), 7)
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.assertEqual(window.findChildren(QDialog), [])
        finally:
            window.close()

    def test_garment_worker_dispatch(self):
        from unittest.mock import Mock, patch
        from human3d.garment_dialog import GarmentDialog
        app = QApplication.instance() or QApplication([])
        worker = Mock(side_effect=lambda operation: operation())
        export = Mock()
        dialog = GarmentDialog({}, None, {"target": (None, (32,32))}, "target", export, worker=worker)
        try:
            with patch.object(dialog, "prepare_export", return_value=("color", [])):
                dialog.export_current()
            worker.assert_called_once()
            export.assert_called_once_with("color", [])
        finally:
            dialog.close()
