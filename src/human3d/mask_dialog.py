"""Minimal photo overlay and mask correction controls."""
from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
                               QLabel, QPushButton, QVBoxLayout, QWidget)

from .mask_review import MaskDraft


class MaskCanvas(QWidget):
    def __init__(self, photo):
        super().__init__()
        self.photo = photo
        self.draft = None
        self.add = True
        self.previous = None
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
    def __init__(self, photo, evidence, apply, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Review subject mask")
        self.resize(760, 620)
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        layout.addLayout(controls)
        self.canvas = MaskCanvas(photo)
        layout.addWidget(self.canvas, 1)
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
        self.message = QLabel("")
        layout.addWidget(self.message)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Apply mask")
        buttons.accepted.connect(lambda: self.apply(apply))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def select_candidate(self, index):
        self.canvas.draft = self.drafts[index]
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
