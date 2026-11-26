"""Fit a named close-fitting shell using an approximate photo coverage mask."""
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, label

from .garments import correct_clearance, posed_garment, prototype
from .native_rig import pose_transforms, skin_vertices, validate_rebind
from .frozen_body import deform_vertices


@dataclass(frozen=True)
class GarmentFit:
    garment: object
    coverage: Image.Image
    overlap: float
    report: object


def _project(shell, points, camera, image_size, size):
    width, height = size
    source_width, source_height = image_size
    coords = [(point.real * width / source_width, point.imag * height / source_height)
              for vertex in points for point in (camera.project(vertex),)]
    raster = Image.new("1", size)
    draw = ImageDraw.Draw(raster)
    for face in shell.faces:
        draw.polygon([coords[index] for index, _ in face], fill=1)
    return np.asarray(raster)


def fit_garment(body, fit, view, image_size, category, *, ease_mm=0, hem=0, layer=0, optimize=True):
    neutral = deform_vertices(body, fit.controls)
    rig = body["rig"]
    joints = validate_rebind(body, neutral)
    transforms = pose_transforms(rig, joints, view.alignment)
    posed = skin_vertices(neutral, rig["skin"], transforms)
    size = view.foreground.shape[::-1]
    camera = view.alignment.camera
    initial = prototype(body, neutral, category, layer=layer, ease_mm=ease_mm, hem=hem)
    envelope = _project(initial, posed_garment(initial, transforms), camera, image_size, size)
    roi = binary_dilation(envelope, iterations=max(3, size[0] // 90))
    coverage = view.foreground & roi & ~view.skin_candidate
    if view.hair_candidate is not None:
        coverage &= ~view.hair_candidate
    # Disconnected color islands in the expanded search band cannot anchor a
    # supported shell. Keep components that actually meet its projection.
    components, _ = label(coverage)
    anchored = np.unique(components[envelope & coverage])
    coverage &= np.isin(components, anchored)
    if np.count_nonzero(coverage) < 25:
        raise ValueError("Garment coverage is too small. Review the subject mask and alignment.")

    def evaluate(shell):
        predicted = _project(shell, posed_garment(shell, transforms), camera, image_size, size)
        union = np.count_nonzero(predicted | coverage)
        return np.count_nonzero(predicted & coverage) / union

    best = initial
    overlap = evaluate(initial)
    if optimize:
        for ease, length in ((min(10, ease_mm + 3), hem), (min(10, ease_mm + 6), hem),
                             (ease_mm, max(-0.25, hem - 0.15)), (ease_mm, min(0.25, hem + 0.15))):
            candidate = prototype(body, neutral, category, layer=layer, ease_mm=ease, hem=length)
            score = evaluate(candidate)
            if score > overlap:
                best, overlap = candidate, score
    best, report = correct_clearance(best, body, posed, transforms)
    return GarmentFit(best, Image.fromarray(coverage).convert("L"), evaluate(best), report)
