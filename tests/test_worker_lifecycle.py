import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import unittest
from threading import get_ident
from time import sleep
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
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
        finally:
            timer.stop()
            window.close()
