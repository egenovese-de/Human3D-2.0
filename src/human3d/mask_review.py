"""Editable subject-mask draft, bound to one detection result."""
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageDraw

from .vision import SubjectEvidence


@dataclass(frozen=True)
class SubjectMask:
    photo_digest: str
    candidate: int
    png: bytes


class MaskDraft:
    def __init__(self, evidence: SubjectEvidence, candidate: int):
        if not 0 <= candidate < len(evidence.candidates):
            raise ValueError("invalid_subject_candidate")
        self.evidence = evidence
        self.candidate = candidate
        self.image = Image.new("L", evidence.image_size)
        if evidence.masks and (mask := evidence.masks[candidate]) is not None:
            with Image.open(BytesIO(mask)) as source:
                self.image = source.convert("L")
        self._history = []

    def begin_stroke(self):
        self._history.append(self.image.copy())
        if len(self._history) > 10:
            self._history.pop(0)

    def paint(self, start, end, radius: int, *, add: bool):
        if radius < 1:
            raise ValueError("invalid_brush_radius")
        color = 255 if add else 0
        draw = ImageDraw.Draw(self.image)
        draw.line((start, end), fill=color, width=2 * radius)
        for x, y in (start, end):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    def undo(self):
        if self._history:
            self.image = self._history.pop()

    def validate(self) -> SubjectMask:
        if self.image.size != self.evidence.image_size or self.image.getextrema() != (0, 255):
            raise ValueError("mask_requires_foreground_and_background")
        if any(self.image.histogram()[1:255]):
            raise ValueError("mask_requires_binary_pixels")
        buffer = BytesIO()
        self.image.save(buffer, format="PNG")
        return SubjectMask(self.evidence.photo_digest, self.candidate, buffer.getvalue())
