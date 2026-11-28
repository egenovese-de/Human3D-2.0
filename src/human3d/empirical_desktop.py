"""PySide6 workspace for the three-action empirical reconstruction workflow."""
import argparse
import json
import os
from pathlib import Path
import sys
from threading import Event
from time import monotonic

import numpy as np
from PIL import Image, ImageOps
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QBuffer, QIODevice, QSettings, QSize, QStandardPaths, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QSlider, QSplitter, QToolBar, QVBoxLayout, QWidget,
)

from . import __version__
from .body_preview import MeshCanvas
from .garments import CATEGORIES
from .originals import OriginalStore
from .reconstruction import BASELINE, M6Engine, ReconstructionService, sha_file
from .session import Session
from .thumbnails import thumbnail


ENGINE_NAMES = {BASELINE: "Engine A · M6 Baseline", "geometry": "Engine B · Geometry-driven experimental"}


class Worker(QThread):
    progress = Signal(object)
    successful = Signal(object)
    unsuccessful = Signal(str)

    def __init__(self, service, request):
        super().__init__()
        self.service, self.request = service, request
        self.cancel = Event()

    def run(self):
        try:
            result = self.service.generate(self.request, self.cancel, self.progress.emit)
        except Exception as error:
            self.unsuccessful.emit(str(error))
        else:
            self.successful.emit(result)


class Comparison(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(160, 200)
        self.photo, self.overlay, self.opacity = QPixmap(), QPixmap(), .65

    def set_images(self, photo, overlay):
        self.photo, self.overlay = photo, overlay
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#18222c"))
        if not self.photo.isNull():
            size = self.photo.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            frame = self.rect()
            frame.setSize(size)
            frame.moveCenter(self.rect().center())
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(frame, self.photo)
            if not self.overlay.isNull():
                painter.setOpacity(self.opacity)
                painter.drawPixmap(frame, self.overlay)

    def set_opacity(self, value):
        self.opacity = value / 100
        self.update()


class EmpiricalWindow(QMainWindow):
    def __init__(self, engines, revision, *, settings=None, reopen=True):
        super().__init__()
        self.engines, self.revision = engines, revision
        self.settings = settings if settings is not None else QSettings("Human3D", "Empirical Desktop")
        self.service = None
        self.worker = None
        self.active_result = None
        self.canvas = None
        self.photo_icons = {}
        self.stage = ""
        self.started = 0
        self.setWindowTitle(f"Human3D · Empirical Desktop {__version__}")
        self.setAcceptDrops(True)
        self.resize(1110, 730)
        self.setMinimumSize(760, 480)
        workspace = QWidget()
        self.setCentralWidget(workspace)
        page = QVBoxLayout(workspace)
        toolbar = QToolBar("Project")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        actions = [
            ("New Project", self.new_project), ("Open Project", self.open_project),
            ("Import Photos", self.import_dialog), ("Generate 3D", self.generate),
            ("Cancel", self.cancel), ("Export 3D", self.export_dialog),
        ]
        self.actions = {}
        for text, handler in actions:
            action = toolbar.addAction(text)
            action.triggered.connect(handler)
            self.actions[text] = action
        primary = toolbar.widgetForAction(self.actions["Generate 3D"])
        primary.setObjectName("generate3d")
        primary.setStyleSheet(
            "QToolButton#generate3d:enabled {background:#1769ad;color:white;padding:6px 9px;border-radius:3px;}"
            "QToolButton#generate3d:hover {background:#105685;}"
        )

        split = QSplitter()
        page.addWidget(split, 1)
        references = QWidget()
        references.setMinimumWidth(140)
        refs_layout = QVBoxLayout(references)
        refs_layout.addWidget(QLabel("Reference photographs"))
        self.photos = QListWidget()
        self.photos.setIconSize(QSize(60, 75))
        self.photos.currentItemChanged.connect(self.target_changed)
        refs_layout.addWidget(self.photos)
        self.remove = QPushButton("Remove Selected Photo")
        self.remove.clicked.connect(self.remove_photo)
        refs_layout.addWidget(self.remove)
        split.addWidget(references)

        inspection = QWidget()
        inspect = QVBoxLayout(inspection)
        self.results = QComboBox()
        self.results.currentIndexChanged.connect(self.show_result)
        inspect.addWidget(self.results)
        controls = QHBoxLayout()
        self.pose = QComboBox()
        self.pose.setMinimumContentsLength(11)
        self.pose.currentIndexChanged.connect(self.update_preview)
        controls.addWidget(self.pose)
        self.style = QComboBox()
        self.style.addItems(("Clay", "Wireframe"))
        self.style.currentTextChanged.connect(self.update_preview)
        controls.addWidget(self.style)
        self.orbit = QComboBox()
        self.orbit.addItems(("Front", "Side", "Rear", "Three-quarter"))
        self.orbit.currentIndexChanged.connect(self.set_orbit)
        controls.addWidget(self.orbit)
        reset = QPushButton("Reset View")
        reset.clicked.connect(lambda: self.set_orbit(self.orbit.currentIndex()))
        controls.addWidget(reset)
        self.layers = QCheckBox("Garment layer")
        self.layers.setChecked(True)
        self.layers.toggled.connect(self.update_preview)
        controls.addWidget(self.layers)
        self.compare_toggle = QCheckBox("Compare Photo")
        self.compare_toggle.toggled.connect(self.toggle_comparison)
        controls.addWidget(self.compare_toggle)
        controls.addStretch()
        inspect.addLayout(controls)

        viewport_split = QSplitter()
        viewport_split.setChildrenCollapsible(False)
        inspect.addWidget(viewport_split, 1)
        self.preview = QWidget()
        self.preview_layout = QVBoxLayout(self.preview)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.placeholder = QLabel("Import photos to generate a 3D reconstruction.")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("background:#18222c;color:#d4e0ea;padding:14px")
        self.preview_layout.addWidget(self.placeholder, 1)
        viewport_split.addWidget(self.preview)

        self.comparison_panel = QWidget()
        compare_layout = QVBoxLayout(self.comparison_panel)
        self.comparison = Comparison()
        compare_layout.addWidget(self.comparison, 1)
        self.compare_label = QLabel()
        self.compare_label.setWordWrap(True)
        compare_layout.addWidget(self.compare_label)
        opacity = QSlider(Qt.Orientation.Horizontal)
        opacity.setRange(0, 100)
        opacity.setValue(65)
        opacity.setAccessibleName("Overlay opacity")
        opacity.valueChanged.connect(self.comparison.set_opacity)
        compare_layout.addWidget(QLabel("Overlay opacity"))
        compare_layout.addWidget(opacity)
        viewport_split.addWidget(self.comparison_panel)
        viewport_split.setStretchFactor(0, 2)
        viewport_split.setStretchFactor(1, 1)
        self.comparison_panel.hide()
        split.addWidget(inspection)
        split.setSizes([190, 920])
        split.setStretchFactor(1, 1)

        status_row = QHBoxLayout()
        self.status = QLabel("Ready")
        self.status.setWordWrap(True)
        status_row.addWidget(self.status, 1)
        self.diagnostics_toggle = QPushButton("Diagnostics & Settings")
        self.diagnostics_toggle.setCheckable(True)
        status_row.addWidget(self.diagnostics_toggle)
        page.addLayout(status_row)
        self.details = QFrame()
        detail_layout = QVBoxLayout(self.details)
        settings_row = QHBoxLayout()
        self.engine = QComboBox()
        for engine in engines:
            self.engine.addItem(ENGINE_NAMES.get(engine, engine), engine)
        requested = self.engine.findData(self.settings.value("engine", BASELINE))
        self.engine.setCurrentIndex(max(requested, 0))
        self.engine.currentIndexChanged.connect(self.settings_changed)
        settings_row.addWidget(QLabel("Reconstruction engine"))
        settings_row.addWidget(self.engine)
        self.garment = QComboBox()
        self.garment.addItem("Body only", None)
        for category in CATEGORIES:
            self.garment.addItem(category.capitalize(), category)
        self.garment.setCurrentIndex(max(self.garment.findData(self.settings.value("garment", "")), 0))
        self.garment.currentIndexChanged.connect(self.settings_changed)
        settings_row.addWidget(QLabel("Optional garment"))
        settings_row.addWidget(self.garment)
        self.calibration = None
        self.calibration_button = QPushButton("Calibration Manifest")
        self.calibration_button.clicked.connect(self.choose_calibration)
        settings_row.addWidget(self.calibration_button)
        settings_row.addStretch()
        self.evidence_button = QPushButton("Export Evidence")
        self.evidence_button.clicked.connect(self.evidence_dialog)
        settings_row.addWidget(self.evidence_button)
        detail_layout.addLayout(settings_row)
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setMaximumHeight(156)
        detail_layout.addWidget(self.diagnostics)
        page.addWidget(self.details)
        self.details.hide()
        self.diagnostics_toggle.toggled.connect(self.details.setVisible)

        self.clock = QTimer(self)
        self.clock.setInterval(250)
        self.clock.timeout.connect(self.tick)
        self.update_actions()
        previous = self.settings.value("last_project", "") if reopen else ""
        if previous and (Path(previous) / "project.json").exists():
            self.guard(lambda: self.attach(previous))

    def guard(self, operation):
        try:
            return operation()
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(str(error))

    def attach(self, directory, *, create=False):
        if self.worker is not None:
            raise RuntimeError("Wait for the reconstruction to stop.")
        session = Session(Path(directory).resolve(), create=create)
        self.service = ReconstructionService(session, self.engines, self.revision)
        project_id = session.store.load().id
        self.calibration = self.settings.value("calibration/" + project_id, "") or None
        for control, key in ((self.engine, "engine"), (self.garment, "garment")):
            value = self.settings.value(f"{key}/{project_id}", self.settings.value(key, ""))
            control.blockSignals(True)
            control.setCurrentIndex(max(control.findData(value), 0))
            control.blockSignals(False)
        self.calibration_button.setText("Manifest Loaded" if self.calibration else "Calibration Manifest")
        self.photo_icons.clear()
        self.settings.setValue("last_project", str(session.store.directory))
        self.refresh_photos()
        self.refresh_results()
        self.status.setText(f"Project · {session.store.directory.name}")

    def new_project(self):
        directory = QFileDialog.getExistingDirectory(self, "Choose an empty project folder")
        if directory:
            self.guard(lambda: self.attach(directory, create=True))

    def open_project(self):
        file, _ = QFileDialog.getOpenFileName(self, "Open project.json", "", "Human3D project (project.json)")
        if file:
            self.guard(lambda: self.attach(Path(file).parent))

    def import_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Import photographs", "",
                                                "Photographs (*.jpg *.jpeg *.png *.webp *.tif *.tiff *.bmp);;All files (*)")
        if paths:
            self.guard(lambda: self.ingest(paths))

    def ingest(self, paths):
        if self.worker is not None:
            raise RuntimeError("Wait for the reconstruction to stop before importing.")
        if self.service is None:
            from datetime import datetime
            from uuid import uuid4
            root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation))
            self.attach(root / "Human3D" / f"Project-{datetime.now():%Y%m%d-%H%M%S}-{uuid4().hex[:5]}", create=True)
        results = self.service.session.ingest(paths)
        self.refresh_photos()
        accepted = sum(item.status == "accepted" for item in results)
        duplicates = sum(item.status == "duplicate" for item in results)
        errors = [f"{item.name} — use a readable JPEG, PNG, WebP, TIFF or BMP"
                  for item in results if item.status == "rejected"]
        self.status.setText(f"{accepted} imported · {duplicates} duplicates" + (" · " + " · ".join(errors) if errors else ""))
        self.update_actions()
        return results

    def dragEnterEvent(self, event):
        if self.worker is None and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.guard(lambda: self.ingest(paths))
            event.acceptProposedAction()

    def refresh_photos(self):
        session = self.service.session
        project = session.store.load()
        originals = OriginalStore(session.store.directory)
        self.photos.blockSignals(True)
        try:
            self.photos.clear()
            for photo in project.photos.photos:
                target = photo.id == project.photos.target
                if photo.digest not in self.photo_icons:
                    try:
                        image = QPixmap()
                        image.loadFromData(thumbnail(originals, photo.digest, 160))
                        self.photo_icons[photo.digest] = QIcon(image)
                    except (OSError, ValueError):
                        self.photo_icons[photo.digest] = QIcon()
                item = QListWidgetItem(self.photo_icons[photo.digest], photo.name + ("\nTARGET" if target else ""))
                item.setData(Qt.ItemDataRole.UserRole, photo.id)
                self.photos.addItem(item)
                if target:
                    self.photos.setCurrentItem(item)
        finally:
            self.photos.blockSignals(False)
        self.update_actions()

    def target_changed(self, current, previous):
        if current is None or self.worker is not None:
            return
        photo_id = current.data(Qt.ItemDataRole.UserRole)
        self.guard(lambda: self.service.session.select_target(photo_id))
        self.refresh_photos()
        self.status.setText("Target selected. Generate 3D to update the result.")

    def remove_photo(self):
        item = self.photos.currentItem()
        if item is None or self.worker is not None:
            return
        self.guard(lambda: self.service.session.remove_photo(item.data(Qt.ItemDataRole.UserRole)))
        self.refresh_photos()
        self.status.setText("Photo removed. Previous reconstructions remain available.")

    def choose_calibration(self):
        if self.calibration:
            self.calibration = None
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Load G4 calibrated views", "", "JSON manifest (*.json)")
            self.calibration = path or None
        if self.service is not None:
            self.settings.setValue("calibration/" + self.service.session.store.load().id, self.calibration or "")
        self.calibration_button.setText("Manifest Loaded" if self.calibration else "Calibration Manifest")
        self.calibration_button.setToolTip(self.calibration or "Optional Engine B calibrated reference input. Click to load or clear.")

    def settings_changed(self):
        self.settings.setValue("engine", self.engine.currentData())
        self.settings.setValue("garment", self.garment.currentData() or "")
        if self.service is not None:
            project_id = self.service.session.store.load().id
            self.settings.setValue("engine/" + project_id, self.engine.currentData())
            self.settings.setValue("garment/" + project_id, self.garment.currentData() or "")
        self.update_actions()

    def update_actions(self):
        ready = self.worker is None
        for text in ("New Project", "Open Project", "Import Photos"):
            self.actions[text].setEnabled(ready)
        self.actions["Generate 3D"].setEnabled(ready and self.photos.count() > 0)
        self.actions["Cancel"].setEnabled(not ready and not self.worker.cancel.is_set())
        self.actions["Export 3D"].setEnabled(ready and self.active_result is not None)
        self.evidence_button.setEnabled(ready and self.results.count() > 0 and self.results.currentData() is not None)
        self.photos.setEnabled(ready)
        self.remove.setEnabled(ready and self.photos.currentItem() is not None)
        self.engine.setEnabled(ready)
        self.calibration_button.setEnabled(ready and self.service is not None and self.engine.currentData() == "geometry")
        self.garment.setEnabled(ready)
        self.results.setEnabled(ready)

    def generate(self):
        if self.worker is not None or self.service is None:
            return

        def start():
            engine = self.engine.currentData()
            request = self.service.request(engine, self.garment.currentData(),
                                           self.calibration if engine == "geometry" else None)
            self.worker = Worker(self.service, request)
            self.worker.progress.connect(self.on_progress)
            self.worker.successful.connect(self.on_success)
            self.worker.unsuccessful.connect(self.on_failure)
            self.worker.finished.connect(self.on_finished)
            self.started = monotonic()
            self.stage = "Starting reconstruction"
            self.clock.start()
            self.tick()
            self.update_actions()
            self.worker.start()
        return self.guard(start)

    def on_progress(self, event):
        if event.outcome == "running":
            self.stage = event.stage
            self.tick()
        if event.message:
            self.diagnostics.appendPlainText(f"{event.stage} — {event.message}")

    def tick(self):
        if self.worker is not None:
            label = "Cancellation pending" if self.worker.cancel.is_set() else self.stage
            self.status.setText(f"{label} · {monotonic() - self.started:.1f} s")

    def cancel(self):
        if self.worker is not None:
            self.worker.cancel.set()
            self.tick()
            self.update_actions()

    def on_success(self, result):
        self.clock.stop()
        self.refresh_results(result.id)
        warnings = len(result.metadata["diagnostics"]["warnings"])
        self.status.setText(f"Reconstruction complete · {result.metadata['duration_seconds']:.1f} s · {warnings} warnings")

    def on_failure(self, message):
        self.clock.stop()
        selected = self.active_result.id if self.active_result else None
        self.refresh_results(selected)
        self.status.setText(message)

    def on_finished(self):
        self.clock.stop()
        self.worker.deleteLater()
        self.worker = None
        self.update_actions()

    def refresh_results(self, selected=None):
        self.results.blockSignals(True)
        try:
            self.results.clear()
            results = self.service.results(include_failures=True)
            if not results:
                self.results.addItem("No completed reconstructions")
            for result in results:
                info = result.metadata
                request = info["request"]
                name = ENGINE_NAMES.get(request["engine"], request["engine"])
                time = info["finished_at"].replace("T", " ")[:19]
                target = next(photo["name"] for photo in request["photos"]["photos"]
                              if photo["id"] == request["photos"]["target"])
                self.results.addItem(f"{name} · {target} · {time} UTC · {info['status']}", result)
            index = next((i for i, result in enumerate(results) if result.id == selected), None)
            if index is None:
                index = next((i for i, result in enumerate(results) if result.metadata["status"] == "complete"), 0)
            self.results.setCurrentIndex(index)
        finally:
            self.results.blockSignals(False)
        self.show_result()

    def show_result(self, *_):
        selected = self.results.currentData()
        self.active_result = None
        if self.canvas is not None:
            self.preview_layout.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()
            self.canvas = None
        self.placeholder.show()
        self.pose.clear()
        self.layers.hide()
        self.style.clear()
        self.style.addItems(("Clay", "Wireframe"))
        self.diagnostics.clear()
        if selected is not None:
            info = selected.metadata
            diagnostics = info["diagnostics"]
            metrics = diagnostics["metrics"]
            target = next((photo["name"] for photo in info["request"]["photos"]["photos"]
                           if photo["id"] == info["request"]["photos"]["target"]), "Unavailable")
            lines = [
                f"{ENGINE_NAMES.get(info['request']['engine'], info['request']['engine'])} · {info['status']} · {info['duration_seconds']:.1f} s",
                f"Target: {target} · Camera: {metrics.get('target_camera', 'unavailable')} · "
                f"Scale: {metrics.get('metric_scale', 'unavailable')} · "
                f"Target pose: {metrics.get('target_pose', 'unavailable')}",
                *diagnostics["warnings"],
            ]
            if info["error"]:
                lines.append(info["error"])
            self.diagnostics.setPlainText("\n".join(lines) + "\n\n" + json.dumps(info, indent=2, ensure_ascii=False))
            if info["status"] == "complete":
                self.guard(lambda: self.load_preview(selected))
        self.refresh_comparison()
        self.update_actions()

    def load_preview(self, result):
        path = result.file("preview.npz")
        if sha_file(path) != result.metadata["artifacts"]["preview.npz"]["sha256"]:
            raise ValueError("The stored viewport asset failed its integrity check.")
        with np.load(path, allow_pickle=False) as preview:
            rest = preview["canonical"]
            posed = preview.get("target", rest)
            faces = [{"corners": [(index, 0) for index in row], "group": "body"} for row in preview["faces"]]
            colors = [QColor(*map(int, rgb)) for rgb in preview["colors"]] if "colors" in preview else None
            self.canvas = MeshCanvas({"vertices": rest, "faces": faces}, rest, posed, colors, minimum=(220, 190))
            if "garment" in preview:
                self.canvas.garment = preview["garment"], preview["garment_faces"]
                self.layers.show()
            if colors:
                self.style.addItem("Textured")
            self.pose.addItem("Canonical", False)
            if "target" in preview:
                self.pose.addItem("Target Pose", True)
                self.pose.setCurrentIndex(1)
        self.placeholder.hide()
        self.preview_layout.addWidget(self.canvas, 1)
        self.active_result = result
        self.set_orbit(self.orbit.currentIndex())
        self.update_preview()

    def update_preview(self, *_):
        if self.canvas is not None:
            self.canvas.mode = self.style.currentText()
            self.canvas.show_garment = self.layers.isChecked()
            self.canvas.set_posed(bool(self.pose.currentData()))

    def set_orbit(self, index):
        if self.canvas is not None:
            self.canvas.reset_camera((0, 90, 180, 45)[index])

    def toggle_comparison(self, checked):
        self.comparison_panel.setVisible(checked)
        if checked:
            self.refresh_comparison()

    def refresh_comparison(self):
        if not self.compare_toggle.isChecked():
            return
        photo, overlay = QPixmap(), QPixmap()
        label = "Generate 3D to compare a photo with its projected model."
        try:
            if self.active_result is not None:
                info = self.active_result.metadata
                photos = info["request"]["photos"]
                target = next(photo for photo in photos["photos"] if photo["id"] == photos["target"])
                originals = OriginalStore(self.service.session.store.directory)
                with Image.open(originals.verify(target["digest"])) as img:
                    frame = ImageOps.exif_transpose(img).convert("RGBA")
                    frame.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                    photo = QPixmap.fromImage(ImageQt(frame))
                label = f"{target['name']} · Projection unavailable"
                if "overlay.png" in info["artifacts"]:
                    overlay.load(str(self.active_result.file("overlay.png")))
                    camera = info["diagnostics"]["metrics"]["camera_model"]
                    label = (f"{target['name']} · {camera}. Green: overlap. Coral: projected only. "
                             "Blue: observed only. Gold: observed landmarks. "
                             "Silhouette alignment cannot establish 3D accuracy.")
        except (OSError, ValueError) as error:
            label = str(error)
        self.compare_label.setText(label)
        self.comparison.set_images(photo, overlay)

    def export_dialog(self):
        result = self.active_result
        if result is None:
            return
        use_target = bool(self.pose.currentData())
        prefix = "target." if use_target else "canonical."
        name = next(name for name in result.metadata["artifacts"] if name.startswith(prefix + "usd"))
        suffix = Path(name).suffix
        destination, _ = QFileDialog.getSaveFileName(self, "Export 3D", name, f"OpenUSD (*{suffix})")
        if destination:
            path = Path(destination)
            if not path.suffix:
                path = path.with_suffix(suffix)
            def export():
                self.service.export(result, path, target=use_target)
                self.status.setText(f"Exported {path.name}")
            self.guard(export)

    def evidence_dialog(self):
        result = self.results.currentData()
        if result is None:
            return
        destination, _ = QFileDialog.getSaveFileName(self, "Export Evidence", "human3d-diagnostics.zip", "ZIP archive (*.zip)")
        if destination:
            include = QMessageBox.question(self, "Include original photographs?",
                                           "Add the full-resolution original photographs to this evidence archive?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No)
            def export():
                screenshot = None
                if self.canvas is not None and self.active_result is not None and self.active_result.id == result.id:
                    buffer = QBuffer()
                    if buffer.open(QIODevice.OpenModeFlag.WriteOnly) and self.canvas.grab().save(buffer, "PNG"):
                        screenshot = bytes(buffer.data())
                    buffer.close()
                self.service.export_evidence(result, Path(destination),
                                             include_photos=include == QMessageBox.StandardButton.Yes,
                                             viewport_png=screenshot)
                self.status.setText("Evidence archive exported.")
            self.guard(export)

    def closeEvent(self, event):
        if self.worker is not None:
            self.cancel()
            event.ignore()
        else:
            super().closeEvent(event)


def configured_engines(assets):
    engines = {BASELINE: M6Engine(assets / "makehuman", assets / "pose.task")}
    if (assets / "native-registry.json").is_file():
        from .experimental import EXPERIMENTAL, GeometryEngine

        engines[EXPERIMENTAL] = GeometryEngine(assets)
    return engines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(os.environ.get("HUMAN3D_ROOT", Path.cwd()))
    parser.add_argument("--assets", type=Path, default=root / "local-data" / "m7-runtime")
    parser.add_argument("--smoke", type=Path, help="Save a screenshot of the shown window and exit")
    args = parser.parse_args()
    stamp = root / "M7-REVISION.txt"
    revision = os.environ.get("HUMAN3D_REVISION") or (stamp.read_text(encoding="utf-8").strip()
                                                      if stamp.exists() else "unrecorded source checkout")
    app = QApplication([sys.argv[0]])
    window = EmpiricalWindow(configured_engines(args.assets), revision, reopen=args.smoke is None)
    window.show()
    if args.smoke is not None:
        def finish():
            app.exit(0 if window.isVisible() and window.grab().save(str(args.smoke)) else 1)
        QTimer.singleShot(350, finish)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
