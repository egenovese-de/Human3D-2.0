"""Minimal desktop workflow; reconstruction is not yet available."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QLabel, QMessageBox)
from .project_store import ProjectStore
from .originals import OriginalStore
from .ingestion import import_photos, folder_inputs
from .thumbnails import thumbnail


class PhotosWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.store = None
        self.setWindowTitle("Human3D 2.0")
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)
        for label, callback in (("New project", self.new_project),
                                ("Open project", self.open_project),
                                ("Add photos", self.add_photos),
                                ("Add folder", self.add_folder)):
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
        except (OSError, ValueError, RuntimeError, KeyError) as error:
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
        store = ProjectStore(Path(directory))
        if create:
            store.create()
        else:
            store.load()
        self.store = store
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
        results = import_photos(self.store, paths)
        self.refresh()
        counts = ", ".join(f"{status}: {sum(r.status == status for r in results)}"
                           for status in ("accepted", "duplicate", "rejected"))
        self.status.setText(counts + " | Reconstruction unavailable")
        return results

    def refresh(self):
        project = self.store.load()
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
            project = self.store.load()
            self.store.save(project.with_photos(
                project.photos.select(item.data(Qt.ItemDataRole.UserRole))))
            self.refresh()
        self.guarded(select)


def main():
    app = QApplication([])
    window = PhotosWindow()
    window.resize(1000, 700)
    window.show()
    return app.exec()
