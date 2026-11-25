"""Minimal photo overlay and mask correction controls."""
from dataclasses import replace

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
                               QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from .alignment import initialize_alignment
from .mask_review import MaskDraft
from .native_rig import posed_segments, rebind_joints


class MaskCanvas(QWidget):
    def __init__(self, photo):
        super().__init__()
        self.photo = photo
        self.draft = None
        self.add = True
        self.previous = None
        self.overlay_segments = ()
        self.setMinimumSize(480, 360)

    def frame(self):
        return self.photo.rect().size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)

    def paintEvent(self, event):
        from PySide6.QtCore import QRect

        size = self.frame()
        frame = QRect(0, 0, size.width(), size.height())
        painter = QPainter(self)
        painter.drawImage(frame, self.photo)
        if self.draft:
            overlay = Image.new("RGBA", self.draft.image.size, (8, 215, 180))
            overlay.putalpha(self.draft.image.point(lambda value: value * 100 // 255))
            painter.drawImage(frame, ImageQt(overlay))
            painter.setPen(QColor("yellow"))
            for landmark in self.draft.evidence.candidates[self.draft.candidate]:
                if landmark.observed:
                    painter.drawEllipse(int(landmark.x * size.width()) - 2,
                                        int(landmark.y * size.height()) - 2, 4, 4)

        painter.setPen(QColor("cyan"))
        for head, tail in self.overlay_segments:
            points = [QPointF(point.real * size.width() / self.photo.width(),
                              point.imag * size.height() / self.photo.height())
                      for point in (head, tail)]
            painter.drawLine(*points)

    def point(self, event):
        size = self.frame()
        x, y = event.position().x(), event.position().y()
        if 0 <= x < size.width() and 0 <= y < size.height():
            return (int(x * self.photo.width() / size.width()),
                    int(y * self.photo.height() / size.height()))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and (point := self.point(event)) is not None:
            self.draft.begin_stroke()
            self.previous = point
            self.stroke(point)

    def mouseMoveEvent(self, event):
        if self.previous is not None and (point := self.point(event)) is not None:
            self.stroke(point)

    def mouseReleaseEvent(self, event):
        self.previous = None

    def stroke(self, point):
        radius = max(1, round(8 * self.photo.width() / self.frame().width()))
        self.draft.paint(self.previous, point, radius, add=self.add)
        self.previous = point
        self.update()


class MaskDialog(QDialog):
    def __init__(self, photo, evidence, apply, parent=None, *, body=None, fit=None):
        super().__init__(parent)
        self.setWindowTitle("Review subject mask")
        self.resize(760, 620)
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        layout.addLayout(controls)
        self.canvas = MaskCanvas(photo)
        layout.addWidget(self.canvas, 1)
        self.body = body
        self.alignment = None
        self.adjusted_alignment = None
        self.offsets = []
        self.drafts = [MaskDraft(evidence, index) for index in range(len(evidence.candidates))]
        subjects = QComboBox()
        for index in range(len(self.drafts)):
            subjects.addItem(f"Subject {index + 1}")
        controls.addWidget(subjects)
        subjects.currentIndexChanged.connect(self.select_candidate)
        self.select_candidate(0)
        mode = QComboBox()
        mode.addItems(["Add foreground", "Remove foreground"])
        mode.currentIndexChanged.connect(self.set_mode)
        controls.addWidget(mode)
        undo = QPushButton("Undo")
        undo.clicked.connect(self.undo)
        controls.addWidget(undo)
        if body is not None:
            for label, limit, default in (("Horizontal", photo.width(), 0),
                                           ("Vertical", photo.height(), 0),
                                           ("Scale %", 200, 100)):
                adjust = QSpinBox()
                adjust.setRange(-limit if default == 0 else 25, limit)
                adjust.setValue(default)
                adjust.setPrefix(label + " ")
                adjust.valueChanged.connect(self.update_overlay)
                self.offsets.append(adjust)
                controls.addWidget(adjust)
            self.update_overlay()
        self.message = QLabel("")
        layout.addWidget(self.message)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Apply mask")
        buttons.accepted.connect(lambda: self.apply(apply))
        buttons.rejected.connect(self.reject)
        if fit is not None and body is not None:
            run_fit = buttons.addButton("Approve alignment and fit", QDialogButtonBox.ButtonRole.ActionRole)
            run_fit.clicked.connect(lambda: self.fit(fit))
        layout.addWidget(buttons)

    def select_candidate(self, index):
        self.canvas.draft = self.drafts[index]
        self.alignment = None
        if self.body is not None:
            try:
                self.alignment = initialize_alignment(self.body, self.canvas.draft.evidence, index)
            except ValueError:
                pass
        self.update_overlay()

    def update_overlay(self):
        self.canvas.overlay_segments = ()
        self.adjusted_alignment = None
        if self.alignment is not None:
            x, y, scale = (control.value() for control in self.offsets) if len(self.offsets) == 3 else (0, 0, 100)
            camera = self.alignment.camera
            center = complex(self.canvas.photo.width(), self.canvas.photo.height()) / 2
            factor = scale / 100
            camera = replace(camera, similarity=camera.similarity * factor,
                             origin=center + (camera.origin - center) * factor + complex(x, y))
            rig = self.body["rig"]
            joints = rebind_joints(rig, self.body["mesh"]["vertices"])
            self.adjusted_alignment = replace(self.alignment, camera=camera)
            segments = posed_segments(rig, joints, self.adjusted_alignment)
            self.canvas.overlay_segments = tuple(
                (camera.project(head), camera.project(tail)) for head, tail in segments.values()
            )
        self.canvas.update()

    def set_mode(self, index):
        self.canvas.add = index == 0

    def undo(self):
        self.canvas.draft.undo()
        self.canvas.update()

    def apply(self, operation):
        try:
            operation(self.canvas.draft)
        except ValueError as error:
            self.message.setText(str(error))
        else:
            self.accept()

    def fit(self, operation):
        if self.adjusted_alignment is None:
            self.message.setText("Select a subject with visible torso landmarks.")
            return
        draft = self.canvas.draft
        single = replace(draft.evidence, candidates=(draft.evidence.candidates[draft.candidate],))
        if single.review_reason:
            self.message.setText("Use a full-body view with visible shoulders, hips, knees and ankles.")
            return
        try:
            result = operation(draft, self.adjusted_alignment)
        except (ValueError, RuntimeError) as error:
            self.message.setText(str(error))
        else:
            self.message.setText(f"Silhouette overlap: {result.bootstrap_iou:.1%} → {result.fitted_iou:.1%}")
