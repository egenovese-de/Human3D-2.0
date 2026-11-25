"""Inspect projected appearance, observation coverage and export settings."""
from PIL import ImageEnhance
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QDoubleSpinBox, QFormLayout, QLabel, QPushButton,
                               QScrollArea, QTabWidget, QVBoxLayout, QWidget)


class AppearanceDialog(QDialog):
    def __init__(self, atlas, export, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Body appearance")
        self.resize(620, 700)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Observed UV coverage: {atlas.observed_fraction:.1%}"))
        tabs = QTabWidget()
        layout.addWidget(tabs)
        self.texture = QLabel()
        for name, label, image, description in (
            ("Texture", self.texture, atlas.color, "Target-biased color with exposure-balanced references."),
            ("Coverage", QLabel(), atlas.coverage, "White: observed. Gray: padded from adjacent color. Black: unobserved."),
            ("Skin candidates", QLabel(), atlas.skin_candidate, "White: face-seeded skin-color candidate."),
        ):
            label.setPixmap(QPixmap.fromImage(ImageQt(image.convert("RGB"))))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setAccessibleName(description)
            page = QScrollArea()
            page.setWidget(label)
            page.setWidgetResizable(True)
            panel = QWidget()
            content = QVBoxLayout(panel)
            explanation = QLabel(description)
            explanation.setWordWrap(True)
            content.addWidget(explanation)
            content.addWidget(page)
            tabs.addTab(panel, name)
        settings = QFormLayout()
        brightness = QDoubleSpinBox()
        brightness.setRange(0.7, 1.4)
        brightness.setSingleStep(0.05)
        brightness.setValue(1.0)
        roughness = QDoubleSpinBox()
        roughness.setRange(0.05, 1.0)
        roughness.setSingleStep(0.05)
        roughness.setValue(0.65)
        settings.addRow("Exposure gain", brightness)
        settings.addRow("Material roughness", roughness)
        layout.addLayout(settings)
        save = QPushButton("Export textured USDZ")
        layout.addWidget(save)

        def color():
            return ImageEnhance.Brightness(atlas.color).enhance(brightness.value())

        brightness.valueChanged.connect(lambda: self.texture.setPixmap(QPixmap.fromImage(ImageQt(color()))))
        save.clicked.connect(lambda: export(color(), roughness.value()))
