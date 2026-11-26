"""Build, inspect and export the current close-fitting outfit."""
from dataclasses import replace

import numpy as np
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QDoubleSpinBox,
                               QFormLayout, QHBoxLayout, QLabel, QListWidget, QSlider,
                               QPushButton, QVBoxLayout)

from .garment_fit import fit_garment
from .garments import CATEGORIES, GarmentAsset, posed_garment, verify_layers
from .frozen_body import deform_vertices
from .native_rig import pose_transforms, skin_vertices, validate_rebind
from .texture_bake import bake_atlas, neutralize_covered_body_color


class GarmentDialog(QDialog):
    def __init__(self, body, fit, views, target, export, parent=None, worker=None):
        super().__init__(parent)
        self.setWindowTitle("Garment assembly")
        self.resize(660, 660)
        self.results = {}
        self.body, self.fit, self.views, self.target = body, fit, views, target
        self.export = export
        self.worker = worker or (lambda operation: operation())
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)
        self.category = QComboBox()
        self.category.addItems([*CATEGORIES, "outer top"])
        form.addRow("Garment &category", self.category)
        self.ease = QDoubleSpinBox()
        self.ease.setRange(0, 10)
        self.ease.setSuffix(" mm")
        form.addRow("&Ease", self.ease)
        self.hem = QDoubleSpinBox()
        self.hem.setRange(-25, 25)
        self.hem.setSuffix(" mm")
        form.addRow("&Hem offset", self.hem)
        buttons = QHBoxLayout()
        for text, action in (("&Fit garment", lambda: self.fit_current(True)),
                             ("&Apply edits", lambda: self.fit_current(False)),
                             ("&Remove garment", self.remove_selected)):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, action=action: self.run(action))
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.list = QListWidget()
        self.list.setAccessibleName("Fitted garments")
        self.list.currentTextChanged.connect(self.inspect)
        layout.addWidget(self.list, 1)
        self.coverage = QLabel("Fit a garment to inspect its candidate photo coverage.")
        self.coverage.setAccessibleName("Garment candidate photo coverage")
        self.coverage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.coverage, 2)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setAccessibleName("Garment fit status and clearance")
        layout.addWidget(self.message)
        preview = QPushButton("Inspect outfit in &3D")
        preview.clicked.connect(lambda: self.run(self.preview_outfit))
        layout.addWidget(preview)
        self.save = QPushButton("Export garment &assembly")
        self.save.setDisabled(True)
        self.save.clicked.connect(lambda: self.run(self.export_current))
        layout.addWidget(self.save)

    def run(self, operation):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            operation()
        except (ValueError, OSError, RuntimeError) as error:
            self.message.setText(str(error))
        finally:
            QApplication.restoreOverrideCursor()

    def fit_current(self, optimize):
        category = self.category.currentText()
        layer = int(category == "outer top")
        if layer:
            if "top_base" not in self.results:
                raise ValueError("Fit a base top before adding an outer top.")
            category = "top"
        if category in ("shorts", "trousers"):
            alternate = "shorts_base" if category == "trousers" else "trousers_base"
            if alternate in self.results:
                raise ValueError("Remove the current lower garment before fitting another.")
        view, size = self.views[self.target]
        ease, hem = self.ease.value(), self.hem.value() / 100
        result = self.worker(lambda: fit_garment(self.body, self.fit, view, size, category,
                             ease_mm=ease, hem=hem, layer=layer, optimize=optimize))
        self.results[result.garment.name] = result
        self.refresh(result.garment.name)

    def remove_selected(self):
        item = self.list.currentItem()
        if item is not None:
            name = item.text()
            if name == "top_base" and "top_outer" in self.results:
                raise ValueError("Remove the outer top before removing its base layer.")
            del self.results[name]
            self.refresh()

    def refresh(self, selected=None):
        self.list.clear()
        self.list.addItems(self.results)
        if self.results:
            self.list.setCurrentRow(list(self.results).index(selected) if selected else 0)
        else:
            self.coverage.clear()
            self.message.setText("No garments in the assembly.")
        self.save.setEnabled(bool(self.results) and not any(item.report.violations for item in self.results.values()))

    def inspect(self, name):
        if name not in self.results:
            return
        result = self.results[name]
        image = result.coverage.copy()
        image.thumbnail((480, 260))
        self.coverage.setPixmap(QPixmap.fromImage(ImageQt(image.convert("RGB"))))
        self.message.setText(f"Candidate-mask overlap {result.overlap:.1%}. "
                             f"{result.report.violations} penetration samples. "
                             f"Minimum signed gap {result.report.minimum * 100:.1f} mm."
                             + (" Adjust ease, hem or pose and retry before export." if result.report.violations else ""))

    def preview_outfit(self):
        from .body_preview import MeshCanvas

        if not self.results:
            raise ValueError("Fit a garment before opening the 3D preview.")
        neutral = deform_vertices(self.body, self.fit.controls)
        rig = self.body["rig"]
        joints = validate_rebind(self.body, neutral)
        transforms = pose_transforms(rig, joints, self.views[self.target][0].alignment)
        rest_points = np.asarray(neutral).tolist()
        posed_points = skin_vertices(neutral, rig["skin"], transforms).tolist()
        faces = [face for face in self.body["mesh"]["faces"] if face["group"] == "body"]
        colors = [QColor("#a3afb6")] * len(faces)
        palette = ("#28788b", "#8d673b", "#76518f")
        for index, item in enumerate(self.results.values()):
            shell = item.garment
            start = len(rest_points)
            rest_points.extend(shell.points.tolist())
            posed_points.extend(posed_garment(shell, transforms).tolist())
            faces.extend({"group": "body", "corners": [(vertex + start, uv) for vertex, uv in face]}
                         for face in shell.faces)
            colors.extend([QColor(palette[index % len(palette)])] * len(shell.faces))
        preview = QDialog(self)
        preview.setWindowTitle("Inspect posed outfit")
        container = QVBoxLayout(preview)
        canvas = MeshCanvas({"vertices": rest_points, "faces": faces}, rest_points, posed_points, colors)
        canvas.setAccessibleName("Posed body and separately colored garment meshes")
        canvas.set_posed(True)
        container.addWidget(canvas)
        orbit = QSlider(Qt.Orientation.Horizontal)
        orbit.setRange(-180, 180)
        orbit.setAccessibleName("Outfit orbit angle")
        orbit.valueChanged.connect(canvas.set_angle)
        container.addWidget(orbit)
        QApplication.restoreOverrideCursor()
        try:
            preview.exec()
        finally:
            preview.deleteLater()
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

    def export_current(self):
        color, assets = self.worker(self.prepare_export)
        self.export(color, assets)

    def prepare_export(self):
        if not self.results:
            raise ValueError("Fit at least one garment first.")
        fitted = list(self.results.values())
        garments = [result.garment for result in fitted]
        view, size = self.views[self.target]
        neutral = deform_vertices(self.body, self.fit.controls)
        rig = self.body["rig"]
        joints = validate_rebind(self.body, neutral)
        transforms = pose_transforms(rig, joints, view.alignment)
        layer = verify_layers(garments, self.body, skin_vertices(neutral, rig["skin"], transforms), transforms)
        if layer is not None and layer.violations:
            raise ValueError(f"{layer.violations} layer clearance samples failed. Adjust ease and retry.")

        assets = []
        for result in fitted:
            garment = result.garment
            if garment.category == "top" and garment.layer == 0 and "top_outer" in self.results:
                assets.append(GarmentAsset(garment, Image.new("RGB", (256, 256), (145, 145, 145)), 0.0))
                continue
            regional = replace(view, foreground=np.asarray(result.coverage) > 0)
            atlas = bake_atlas(self.body, self.fit.controls, {self.target: (regional, size)},
                               self.target, size=256, garment=garment)
            assets.append(GarmentAsset(garment, atlas.color, atlas.observed_fraction))
        base = bake_atlas(self.body, self.fit.controls, self.views, self.target)
        body_color = neutralize_covered_body_color(self.body, base.color, garments)
        return body_color, assets
