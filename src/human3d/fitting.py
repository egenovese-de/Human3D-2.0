"""Bounded silhouette fitting against independently aligned project views."""
from dataclasses import dataclass, replace
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

from .alignment import Alignment, refine_views
from .face import has_head_control
from .frozen_body import deform_vertices, morph_controls
from .native_rig import pose_transforms, rebind_joints, skin_vertices, validate_rebind
from .proportions import length_controls
from .regional_morphs import regional_controls


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


def _region_weights(view, size):
    """Assign confidence to pixels using the nearest measured skeletal segment."""
    from .fusion import REGIONS

    pose = view.detection.visible_pose(view.candidate)
    width, height = size
    y, x = np.ogrid[:height, :width]
    distance = np.full((height, width), np.inf)
    weights = np.ones((height, width))
    for region, indices in REGIONS.items():
        if region not in view.observed_regions:
            continue
        confidence = min(pose[index].visibility * pose[index].presence for index in indices)
        pairs = ((11, 12), (23, 24), (11, 23), (12, 24)) if region == "torso" else zip(indices, indices[1:])
        for first, last in pairs:
            a, b = pose[first], pose[last]
            dx, dy = (b.x - a.x) * width, (b.y - a.y) * height
            ox, oy = x - a.x * width, y - a.y * height
            t = np.clip((ox * dx + oy * dy) / max(dx * dx + dy * dy, 1e-6), 0, 1)
            squared = (ox - t * dx) ** 2 + (oy - t * dy) ** 2
            closer = squared < distance
            distance[closer] = squared[closer]
            weights[closer] = confidence
    return weights


def _scorer(body, masks, alignments, reference_vertices, *, edge=256, evidence=None, carve=False):
    mesh, rig = body["mesh"], body["rig"]
    faces = [tuple(index for index, _ in face["corners"])
             for face in mesh["faces"] if face["group"] == "body"]
    joints = rebind_joints(rig, reference_vertices)
    # A canonical sample should lie inside the volume carved by each
    # silhouette after applying that view's pose. Use face vertices only.
    hull_samples = np.unique([index for face in faces for index in face])[::8]
    views = {}
    observed_views = {view.ref.photo_id: view for view in evidence.views} if evidence else {}
    for key, mask in masks.items():
        alignment = alignments[key]
        with Image.open(BytesIO(mask.png)) as source:
            scale = min(1.0, edge / max(source.size))
            size = tuple(max(1, round(value * scale)) for value in source.size)
            observed = np.asarray(source.resize(size, Image.Resampling.NEAREST)) > 0
        if not observed.any() or observed.all():
            raise ValueError("insufficient_silhouette_at_fit_resolution")
        regional = _region_weights(observed_views[key], size) if key in observed_views else None
        outside = distance_transform_edt(~observed) if (carve or regional is not None) and len(masks) >= 2 else None
        views[key] = (scale, size, observed, pose_transforms(rig, joints, alignment), alignment.camera, regional, outside)

    def score(vertices):
        scores = {}
        for key, (scale, size, observed, transforms, camera, regional, outside) in views.items():
            posed = skin_vertices(vertices, rig["skin"], transforms)
            points = [camera.project(vertex) * scale for vertex in posed]
            output = Image.new("1", size)
            draw = ImageDraw.Draw(output)
            for face in faces:
                draw.polygon([(points[index].real, points[index].imag) for index in face], fill=1)
            predicted = np.asarray(output)
            overlap, union = predicted & observed, predicted | observed
            if regional is None:
                scores[key] = np.count_nonzero(overlap) / np.count_nonzero(union)
            else:
                scores[key] = regional[overlap].sum() / regional[union].sum()
            if outside is not None and len(hull_samples):
                sampled = np.asarray(points)[hull_samples]
                x, y = np.rint(sampled.real).astype(int), np.rint(sampled.imag).astype(int)
                inside_image = (x >= 0) & (x < size[0]) & (y >= 0) & (y < size[1])
                if inside_image.any():
                    distance = outside[y[inside_image], x[inside_image]]
                    scores[key] -= .15 * np.clip(distance / (.03 * max(size)), 0, 1).mean()
        return scores

    return score


def _confidence_weights(evidence, keys):
    """Aggregate reliable anatomical regions without treating hidden points as measurements."""
    from .fusion import REGIONS

    weights = {}
    contradictory = {key for key, reason in evidence.unresolved if reason == "inconsistent_anatomical_ratios"}
    for view in evidence.views:
        key = view.ref.photo_id
        if key not in keys:
            continue
        pose = view.detection.visible_pose(view.candidate)
        region_scores = [
            min(pose[index].visibility * pose[index].presence for index in indices)
            for name, indices in REGIONS.items() if name in view.observed_regions
        ]
        confidence = sum(region_scores) / len(REGIONS) if region_scores else .25
        weights[key] = confidence * (.35 if key in contradictory else 1)
    return weights


def _mean(scores, weights=None):
    if weights is None:
        return sum(scores.values()) / len(scores)
    return sum(value * weights[key] for key, value in scores.items()) / sum(weights[key] for key in scores)


def _optimize(body, score, controls, supported, steps, *, weights=None):
    best = score(deform_vertices(body, controls))
    def objective(scores, values):
        return _mean(scores, weights) - .0005 * sum(value ** 2 for value in values.values())

    best_objective = objective(best, controls)
    for step in steps:
        for name in supported:
            center = controls.get(name, 0)
            for value in (center - step, center + step):
                if abs(value) > 0.5:
                    continue
                candidate = controls | {name: value}
                vertices = deform_vertices(body, candidate)
                result = score(vertices)
                candidate_objective = objective(result, candidate)
                if candidate_objective > best_objective + 1e-6:
                    try:
                        validate_rebind(body, vertices)
                    except ValueError:
                        continue
                    best, controls = result, candidate
                    best_objective = candidate_objective
    return controls, best


def fit_body(body, mask, alignment):
    neutral = deform_vertices(body, {})
    scorer = _scorer(body, {"target": mask}, {"target": alignment}, neutral)
    baseline = _mean(scorer(neutral))
    controls, best = _optimize(body, scorer, {}, (*morph_controls(body), *regional_controls(body)), (0.25, 0.125))
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
    weights = _confidence_weights(evidence, masks)
    supported = (*morph_controls(body), *length_controls(body), *regional_controls(body))
    coarse = _scorer(body, masks, alignments, neutral, edge=128, evidence=evidence)
    objective = _scorer(body, masks, alignments, neutral, evidence=evidence)
    seed, _ = _optimize(body, coarse, {}, supported, (0.25,), weights=weights)
    if _mean(scorer(deform_vertices(body, seed)), weights) < _mean(baseline_scores, weights):
        seed = {}
    controls, _ = _optimize(body, objective, seed, supported, (0.25, 0.125), weights=weights)
    vertices = deform_vertices(body, controls)
    best = _scorer(body, masks, alignments, vertices)(vertices)
    if _mean(best) < _mean(baseline_scores):
        controls, best, vertices = {}, baseline_scores, neutral

    # One additional camera/body iteration. Reject missing views and score regressions.
    rebound = validate_rebind(body, vertices)
    adjusted = body | {"rig": body["rig"] | {"joints": rebound}}
    refined, _ = refine_views(adjusted, evidence)
    if masks.keys() <= refined.keys():
        second = _scorer(body, masks, refined, vertices, evidence=evidence)
        candidate, _ = _optimize(body, second, controls, supported, (0.125,), weights=weights)
        revised = deform_vertices(body, candidate)
        scores = _scorer(body, masks, refined, revised)(revised)
        if _mean(scores) > _mean(best) + 1e-6:
            controls, best, alignments = candidate, scores, refined
    return SharedFit(Fit(controls, _mean(baseline_scores), _mean(best)), alignments,
                     evidence.dependency_digest, best)

def edit_fit(body, evidence, current, name, value):
    supported = (*morph_controls(body), *length_controls(body), *regional_controls(body))
    if has_head_control(body):
        supported += ("head_width",)
    if "jaw" in body["rig"]["bones"]:
        supported += ("jaw_width",)
    if name not in supported:
        raise ValueError("unsupported_body_control")
    if not -0.5 <= value <= 0.5:
        raise ValueError("body_control_out_of_range")
    if current.fit.controls.get(name, 0) == value:
        return current
    controls = current.fit.controls | {name: value}
    vertices = deform_vertices(body, controls)
    validate_rebind(body, vertices)
    masks = {view.ref.photo_id: view.mask for view in evidence.views if view.ref.photo_id in current.scores}
    scores = _scorer(body, masks, current.alignments, vertices)(vertices)
    return replace(current, fit=Fit(controls, current.fit.bootstrap_iou, _mean(scores)), scores=scores)
