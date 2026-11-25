"""Interactive orthographic inspection of fitted neutral and posed geometry."""
from math import cos, radians, sin

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPolygonF
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from .frozen_body import deform_vertices
from .native_rig import pose_transforms, validate_rebind, skin_vertices


class MeshCanvas(QWidget):
    def __init__(self, mesh, neutral, posed):
        super().__init__()
        self.setMinimumSize(600, 480)
        self.vertices = (np.asarray(neutral), np.asarray(posed))
        self.faces = np.asarray([
            [index for index, _ in face["corners"]] for face in mesh["faces"] if face["group"] == "body"
        ])
        self.angle = 0
        self.posed = False
        self.bootstrap = np.asarray(mesh["vertices"])
        self.show_bootstrap = False

    def paintEvent(self, event):
        vertices = self.bootstrap if self.show_bootstrap else self.vertices[int(self.posed)]
        angle = radians(self.angle)
        horizontal = vertices[:, 0] * cos(angle) + vertices[:, 2] * sin(angle)
        depth = -vertices[:, 0] * sin(angle) + vertices[:, 2] * cos(angle)
        vertical = vertices[:, 1]
        visible = self.faces.ravel()
        left, right = horizontal[visible].min(), horizontal[visible].max()
        bottom, top = vertical[visible].min(), vertical[visible].max()
        ratio = 0.88 * min(self.width() / (right - left), self.height() / (top - bottom))
        x = (horizontal - (right + left) / 2) * ratio + self.width() / 2
        y = ((top + bottom) / 2 - vertical) * ratio + self.height() / 2
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#141b24"))
        painter.setPen(QColor("#344652"))
        painter.setBrush(QColor("#8aacbe"))
        for index in np.argsort(depth[self.faces].mean(axis=1)):
            painter.drawPolygon(QPolygonF([QPointF(x[i], y[i]) for i in self.faces[index]]))

    def set_angle(self, angle):
        self.angle = angle
        self.update()

    def set_bootstrap(self, checked):
        self.show_bootstrap = checked
        self.update()

    def set_posed(self, checked):
        self.posed = checked
        self.update()


class BodyPreview(QDialog):
    def __init__(self, body, fit, alignment, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Inspect fitted body")
        self.resize(680, 560)
        layout = QVBoxLayout(self)
        rig = body["rig"]
        neutral = deform_vertices(body, fit.controls)
        joints = validate_rebind(body, neutral)
        posed = skin_vertices(neutral, rig["skin"], pose_transforms(rig, joints, alignment))
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
