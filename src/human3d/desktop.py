"""Minimal desktop workflow; reconstruction is not yet available."""
from pathlib import Path
from PIL import Image, ImageOps
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QLabel, QMessageBox)
from .session import Session
from .originals import OriginalStore
from .ingestion import folder_inputs
from .thumbnails import thumbnail
from .mask_dialog import MaskDialog
from .vision import PoseLandmarker
from .frozen_body import load_project_body


class PhotosWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.store = None
        self.session = None
        self.setWindowTitle("Human3D 2.0")
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)
        for label, callback in (("New project", self.new_project),
                                ("Open project", self.open_project),
                                ("Add photos", self.add_photos),
                                ("Add folder", self.add_folder),
                                ("Review target mask", self.review_target_mask),
                                ("Freeze rest body", self.freeze_rest_body)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        self.photos = QListWidget()
        self.photos.setViewMode(QListWidget.ViewMode.IconMode)
        from PySide6.QtCore import QSize
        self.photos.setIconSize(QSize(160, 160))
        self.photos.itemClicked.connect(self.select_target)
        layout.addWidget(self.photos)
        self.status = QLabel("Create or open a project. Reconstruction unavailable.")
        layout.addWidget(self.status)

    def guarded(self, operation):
        try:
            operation()
        except (OSError, ValueError, RuntimeError, KeyError, ImportError) as error:
            QMessageBox.warning(self, "Operation failed", str(error))

    def new_project(self):
        directory = QFileDialog.getExistingDirectory(self, "Select project directory")
        if directory:
            self.guarded(lambda: self.attach(directory, True))

    def open_project(self):
        directory = QFileDialog.getExistingDirectory(self, "Open project")
        if directory:
            self.guarded(lambda: self.attach(directory, False))

    def attach(self, directory, create=False):
        session = Session(Path(directory), create)
        self.session = session
        self.store = session.store
        self.refresh()

    def add_photos(self):
        if self.store is None:
            return
        paths, _ = QFileDialog.getOpenFileNames(self, "Add photos")
        if paths:
            self.guarded(lambda: self.ingest([Path(p) for p in paths]))

    def add_folder(self):
        if self.store is None:
            return
        directory = QFileDialog.getExistingDirectory(self, "Add folder")
        if directory:
            self.guarded(lambda: self.ingest(folder_inputs(Path(directory))))

    def ingest(self, paths):
        results = self.session.ingest(paths)
        self.refresh()
        counts = ", ".join(f"{status}: {sum(r.status == status for r in results)}"
                           for status in ("accepted", "duplicate", "rejected"))
        self.status.setText(counts + " | Reconstruction unavailable")
        return results

    def freeze_rest_body(self):
        if self.store is None:
            self.status.setText("Create or open a project first.")
            return
        assets = QFileDialog.getExistingDirectory(self, "Select verified bootstrap assets directory")
        if assets:
            self.guarded(lambda: self.attach_rest_body(Path(assets)))

    def attach_rest_body(self, assets):
        from .bootstrap import freeze_project

        freeze_project(self.store, assets)
        self.status.setText("Rest body attached. Review the target mask to inspect alignment.")

    def review_target_mask(self):
        if self.session is None or self.session.snapshot().project.photos.target is None:
            self.status.setText("Select a target photo first.")
            return
        model, _ = QFileDialog.getOpenFileName(self, "Select local Pose Landmarker model", filter="MediaPipe model (*.task)")
        if model:
            self.guarded(lambda: self.analyze_mask(Path(model)))

    def analyze_mask(self, model):
        detector = PoseLandmarker(model, segmentation=True)
        try:
            evidence = self.session.detect_target(detector)
        finally:
            detector.close()
        if evidence is None or not evidence.candidates:
            self.status.setText("No current subject candidate. Select another photo and retry.")
            return
        original = OriginalStore(self.store.directory).verify(evidence.photo_digest)
        with Image.open(original) as image:
            photo = ImageQt(ImageOps.exif_transpose(image).convert("RGB"))
        body = load_project_body(self.store) if self.store.load().frozen_body_digest else None
        if MaskDialog(photo, evidence, self.session.apply_mask, self, body=body).exec():
            self.status.setText("Subject mask applied for this session.")

    def refresh(self):
        snapshot = self.session.snapshot()
        project = snapshot.project
        self.photos.clear()
        for photo in project.photos.photos:
            pixmap = QPixmap()
            pixmap.loadFromData(thumbnail(OriginalStore(self.store.directory), photo.digest))
            item = QListWidgetItem(QIcon(pixmap), photo.name)
            item.setData(Qt.ItemDataRole.UserRole, photo.id)
            self.photos.addItem(item)
            if photo.id == project.photos.target:
                item.setText(photo.name + " [Target]")
                self.photos.setCurrentItem(item)
        self.status.setText(f"{len(project.photos.photos)} photos | Reconstruction unavailable")

    def select_target(self, item):
        def select():
            self.session.select_target(item.data(Qt.ItemDataRole.UserRole))
            self.refresh()
        self.guarded(select)


def main():
    app = QApplication([])
    window = PhotosWindow()
    window.resize(1000, 700)
    window.show()
    return app.exec()
