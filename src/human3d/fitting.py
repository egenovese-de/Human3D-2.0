"""Bounded silhouette fitting against independently aligned project views."""
from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw

from .alignment import Alignment, refine_views
from .frozen_body import deform_vertices, morph_controls
from .native_rig import pose_transforms, rebind_joints, skin_vertices, validate_rebind
from .proportions import length_controls


@dataclass(frozen=True)
class Fit:
    controls: dict[str, float]
    bootstrap_iou: float
    fitted_iou: float


@dataclass(frozen=True)
class SharedFit:
    fit: Fit
    alignments: dict[str, Alignment]
    evidence_digest: str
    scores: dict[str, float]


def _scorer(body, masks, alignments, reference_vertices):
    mesh, rig = body["mesh"], body["rig"]
    faces = [tuple(index for index, _ in face["corners"])
             for face in mesh["faces"] if face["group"] == "body"]
    joints = rebind_joints(rig, reference_vertices)
    views = {}
    for key, mask in masks.items():
        alignment = alignments[key]
        with Image.open(BytesIO(mask.png)) as source:
            scale = min(1.0, 256 / max(source.size))
            size = tuple(max(1, round(value * scale)) for value in source.size)
            observed = np.asarray(source.resize(size, Image.Resampling.NEAREST)) > 0
        if not observed.any() or observed.all():
            raise ValueError("insufficient_silhouette_at_fit_resolution")
        views[key] = (scale, size, observed, pose_transforms(rig, joints, alignment), alignment.camera)

    def score(vertices):
        scores = {}
        for key, (scale, size, observed, transforms, camera) in views.items():
            posed = skin_vertices(vertices, rig["skin"], transforms)
            points = [camera.project(vertex) * scale for vertex in posed]
            output = Image.new("1", size)
            draw = ImageDraw.Draw(output)
            for face in faces:
                draw.polygon([(points[index].real, points[index].imag) for index in face], fill=1)
            predicted = np.asarray(output)
            scores[key] = np.count_nonzero(predicted & observed) / np.count_nonzero(predicted | observed)
        return scores

    return score


def _mean(scores):
    return sum(scores.values()) / len(scores)


def _optimize(body, score, controls, supported, steps):
    best = score(deform_vertices(body, controls))
    for step in steps:
        for name in supported:
            center = controls.get(name, 0)
            for value in (center - step, center + step):
                if abs(value) > 0.5:
                    continue
                candidate = controls | {name: value}
                vertices = deform_vertices(body, candidate)
                result = score(vertices)
                if _mean(result) > _mean(best) + 1e-6:
                    try:
                        validate_rebind(body, vertices)
                    except ValueError:
                        continue
                    best, controls = result, candidate
    return controls, best


def fit_body(body, mask, alignment):
    neutral = deform_vertices(body, {})
    scorer = _scorer(body, {"target": mask}, {"target": alignment}, neutral)
    baseline = _mean(scorer(neutral))
    controls, best = _optimize(body, scorer, {}, morph_controls(body), (0.25, 0.125))
    return Fit(controls, baseline, _mean(best))


def fit_shared(body, evidence):
    alignments, _ = refine_views(body, evidence)
    masks = {view.ref.photo_id: view.mask for view in evidence.views
             if view.mask is not None and view.ref.photo_id in alignments}
    if not masks:
        raise ValueError("no_aligned_subject_masks")
    neutral = deform_vertices(body, {})
    scorer = _scorer(body, masks, alignments, neutral)
    baseline_scores = scorer(neutral)
    supported = (*morph_controls(body), *length_controls(body))
    controls, _ = _optimize(body, scorer, {}, supported, (0.25, 0.125))
    vertices = deform_vertices(body, controls)
    best = _scorer(body, masks, alignments, vertices)(vertices)
    if _mean(best) < _mean(baseline_scores):
        controls, best, vertices = {}, baseline_scores, neutral

    # One additional camera/body iteration. Reject missing views and score regressions.
    rebound = validate_rebind(body, vertices)
    adjusted = body | {"rig": body["rig"] | {"joints": rebound}}
    refined, _ = refine_views(adjusted, evidence)
    if masks.keys() <= refined.keys():
        second = _scorer(body, masks, refined, vertices)
        candidate, _ = _optimize(body, second, controls, supported, (0.125,))
        revised = deform_vertices(body, candidate)
        scores = _scorer(body, masks, refined, revised)(revised)
        if _mean(scores) > _mean(best) + 1e-6:
            controls, best, alignments = candidate, scores, refined
    return SharedFit(Fit(controls, _mean(baseline_scores), _mean(best)), alignments,
                     evidence.dependency_digest, best)
