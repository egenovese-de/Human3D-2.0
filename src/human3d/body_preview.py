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
                current = pose_transforms(rig, joints, candidate)
                vertices = skin_vertices(neutral, rig["skin"], current)
                try:
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
