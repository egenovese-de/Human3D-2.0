"""Bounded silhouette fitting at a locked camera and initial pose."""
from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw

from .frozen_body import deform_vertices
from .native_rig import pose_transforms, rebind_joints, skin_vertices


@dataclass(frozen=True)
class Fit:
    controls: dict[str, float]
    bootstrap_iou: float
    fitted_iou: float


def fit_body(body, mask, alignment):
    with Image.open(BytesIO(mask.png)) as source:
        scale = min(1.0, 256 / max(source.size))
        size = tuple(max(1, round(value * scale)) for value in source.size)
        observed = np.asarray(source.resize(size, Image.Resampling.NEAREST)) > 0
    if not observed.any() or observed.all():
        raise ValueError("insufficient_silhouette_at_fit_resolution")
    mesh, rig = body["mesh"], body["rig"]
    faces = [tuple(index for index, _ in face["corners"]) for face in mesh["faces"] if face["group"] == "body"]
    joints = rebind_joints(rig, mesh["vertices"])
    transforms = pose_transforms(rig, joints, alignment)

    def score(controls):
        vertices = deform_vertices(body, controls)
        posed = skin_vertices(vertices, rig["skin"], transforms)
        points = [alignment.camera.project(vertex) * scale for vertex in posed]
        output = Image.new("1", size)
        draw = ImageDraw.Draw(output)
        for face in faces:
            draw.polygon([(points[index].real, points[index].imag) for index in face], fill=1)
        predicted = np.asarray(output)
        return np.count_nonzero(predicted & observed) / np.count_nonzero(predicted | observed)

    controls = {}
    best = baseline = score(controls)
    for step in (0.25, 0.125):
        for name in ("hips", "thigh", "calf", "upperarm"):
            if f"{name}-circ-incr" not in body.get("morph_targets", {}):
                continue
            center = controls.get(name, 0)
            for value in (center - step, center + step):
                candidate = controls | {name: value}
                result = score(candidate)
                if result > best + 1e-6:
                    best, controls = result, candidate
    return Fit(controls, baseline, best)
