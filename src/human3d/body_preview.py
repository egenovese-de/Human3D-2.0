"""Interactive orthographic inspection of fitted neutral and posed geometry."""
from dataclasses import replace
from math import cos, radians, sin

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget

from .frozen_body import deform_vertices
from .native_rig import foot_height_difference, pose_transforms, validate_pose, validate_rebind, skin_vertices


class MeshCanvas(QWidget):
    def __init__(self, mesh, neutral, posed, face_colors=None, *, minimum=(600, 480)):
        super().__init__()
        self.setMinimumSize(*minimum)
        self.vertices = (np.asarray(neutral), np.asarray(posed))
        self.faces = np.asarray([
            [index for index, _ in face["corners"]] for face in mesh["faces"] if face["group"] == "body"
        ])
        self.face_colors = face_colors
        self.angle = 0
        self.elevation = 0
        self.zoom = 1
        self.pan = QPointF()
        self.pointer = None
        self.posed = False
        self.bootstrap = np.asarray(mesh["vertices"])
        self.show_bootstrap = False
        self.mode = "Clay"
        self.garment = None
        self.show_garment = True

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#18222c"))
        if not len(self.faces):
            return
        vertices = self.bootstrap if self.show_bootstrap else self.vertices[int(self.posed)]
        angle, tilt = radians(self.angle), radians(self.elevation)

        def project(points):
            horizontal = points[:, 0] * cos(angle) + points[:, 2] * sin(angle)
            depth = -points[:, 0] * sin(angle) + points[:, 2] * cos(angle)
            return np.stack((horizontal, points[:, 1] * cos(tilt) - depth * sin(tilt),
                             points[:, 1] * sin(tilt) + depth * cos(tilt)), axis=1)

        projected = project(vertices)
        visible = projected[self.faces.ravel(), :2]
        low, high = visible.min(axis=0), visible.max(axis=0)
        ratio = 0.88 * self.zoom * min(self.width() / max(high[0] - low[0], .001),
                                      self.height() / max(high[1] - low[1], .001))
        center = (low + high) / 2
        polygons = projected[self.faces]
        depths = polygons[:, :, 2].mean(axis=1)
        normals = np.cross(polygons[:, 1] - polygons[:, 0], polygons[:, 2] - polygons[:, 0])
        shading = .55 + .45 * np.abs(normals[:, 2]) / np.maximum(np.linalg.norm(normals, axis=1), 1e-9)
        layers = [(depths, polygons, shading)]
        if self.posed and self.show_garment and self.garment is not None:
            points, faces = self.garment
            shells = project(points)[faces]
            layers.append((shells[:, :, 2].mean(axis=1), shells, np.ones(len(shells))))
        order = sorted((z, layer, index) for layer, (values, _, _) in enumerate(layers)
                       for index, z in enumerate(values))
        wireframe = self.mode == "Wireframe"
        painter.setPen(QColor("#647685") if wireframe else Qt.PenStyle.NoPen)
        for _, layer, index in order:
            _, shapes, light = layers[layer]
            if wireframe:
                painter.setBrush(Qt.BrushStyle.NoBrush)
            elif layer:
                painter.setBrush(QColor("#546f9d"))
            elif self.face_colors is not None and self.mode == "Textured":
                painter.setBrush(self.face_colors[index])
            else:
                shade = light[index]
                painter.setBrush(QColor(int(177 * shade), int(203 * shade), int(216 * shade)))
            coords = (shapes[index, :, :2] - center) * ratio
            painter.drawPolygon(QPolygonF([
                QPointF(float(x) + self.width() / 2 + self.pan.x(),
                        self.height() / 2 - float(y) + self.pan.y()) for x, y in coords
            ]))

    def reset_camera(self, angle=0):
        self.angle, self.elevation, self.zoom = angle, 0, 1
        self.pan = QPointF()
        self.update()

    def set_angle(self, angle):
        self.angle = angle
        self.update()

    def mousePressEvent(self, event):
        self.pointer = event.position()

    def mouseReleaseEvent(self, event):
        self.pointer = None

    def mouseMoveEvent(self, event):
        if self.pointer is None:
            return
        delta = event.position() - self.pointer
        self.pointer = event.position()
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.angle += delta.x() * .6
            self.elevation = min(89, max(-89, self.elevation + delta.y() * .5))
        elif event.buttons() & (Qt.MouseButton.RightButton | Qt.MouseButton.MiddleButton):
            self.pan += delta
        self.update()

    def wheelEvent(self, event):
        self.zoom = min(8, max(.25, self.zoom * 1.15 ** (event.angleDelta().y() / 120)))
        self.update()

    def set_bootstrap(self, checked):
        self.show_bootstrap = checked
        self.update()

    def set_posed(self, checked):
        self.posed = checked
        self.update()


class BodyPreview(QDialog):
    def __init__(self, body, fit, alignment, parent=None, *, on_pose_applied=None):
        super().__init__(parent)
        self.setWindowTitle("Inspect fitted body")
        self.resize(680, 560)
        layout = QVBoxLayout(self)
        rig = body["rig"]
        neutral = deform_vertices(body, fit.controls)
        joints = validate_rebind(body, neutral)
        transforms = pose_transforms(rig, joints, alignment)
        posed = skin_vertices(neutral, rig["skin"], transforms)
        validate_pose(body, neutral, posed)
        canvas = MeshCanvas(body["mesh"], neutral, posed)
        controls = QHBoxLayout()
        toggle = QCheckBox("Target pose")
        toggle.toggled.connect(canvas.set_posed)
        controls.addWidget(toggle)
        compare = QCheckBox("Bootstrap neutral")
        compare.toggled.connect(canvas.set_bootstrap)
        compare.toggled.connect(lambda checked: toggle.setDisabled(checked))
        controls.addWidget(compare)
        controls.addWidget(QLabel("Orbit"))
        orbit = QSlider(Qt.Orientation.Horizontal)
        orbit.setRange(-180, 180)
        orbit.valueChanged.connect(canvas.set_angle)
        controls.addWidget(orbit)
        layout.addLayout(controls)
        layout.addWidget(canvas)
        contact = QLabel()
        layout.addWidget(contact)

        def report_contact(current):
            difference = foot_height_difference(rig, joints, current, np.ptp(np.asarray(neutral)[:, 1]))
            if difference is not None:
                contact.setText(f"Relative foot-height difference: {difference:.1%} of body height. Floor unknown.")

        report_contact(transforms)
        if on_pose_applied is not None and alignment.limb_angles:
            edits = QHBoxLayout()
            limb = QComboBox()
            names = tuple(alignment.limb_angles)
            for name in names:
                limb.addItem(name)
            adjustment = QSpinBox()
            adjustment.setRange(-35, 35)
            adjustment.setSuffix("°")
            offsets = {}
            staged = [alignment]
            apply = QPushButton("Apply pose correction")

            def update_pose(value):
                offsets[limb.currentText()] = value
                angles = {name: angle + radians(offsets.get(name, 0)) for name, angle in alignment.limb_angles.items()}
                candidate = replace(alignment, limb_angles=angles)
                try:
                    current = pose_transforms(rig, joints, candidate)
                    vertices = skin_vertices(neutral, rig["skin"], current)
                    validate_pose(body, neutral, vertices)
                except ValueError as error:
                    contact.setText(str(error))
                    apply.setDisabled(True)
                    return
                staged[0] = candidate
                canvas.vertices = (canvas.vertices[0], vertices)
                compare.setChecked(False)
                toggle.setChecked(True)
                canvas.update()
                report_contact(current)
                apply.setEnabled(True)

            def change_limb(name):
                adjustment.blockSignals(True)
                adjustment.setValue(offsets.get(name, 0))
                adjustment.blockSignals(False)

            limb.currentTextChanged.connect(change_limb)
            adjustment.valueChanged.connect(update_pose)
            apply.clicked.connect(lambda: on_pose_applied(staged[0]))
            edits.addWidget(limb)
            edits.addWidget(adjustment)
            edits.addWidget(apply)
            layout.addLayout(edits)
