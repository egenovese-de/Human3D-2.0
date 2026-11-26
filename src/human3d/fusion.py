"""Gather target-independent, local observations for shared anatomical fitting."""
from dataclasses import dataclass
from hashlib import sha256
import json
from math import dist, isfinite
from statistics import median

from .mask_review import SubjectMask
from .observations import ObservationRef, ObservationStore
from .project import Project
from .vision import SubjectEvidence

REGIONS = {
    "torso": (11, 12, 23, 24),
    "left_arm": (11, 13, 15),
    "right_arm": (12, 14, 16),
    "left_leg": (23, 25, 27),
    "right_leg": (24, 26, 28),
}


@dataclass(frozen=True)
class ViewEvidence:
    ref: ObservationRef
    detection: SubjectEvidence
    candidate: int
    mask: SubjectMask | None
    observed_regions: tuple[str, ...]
    geometry_only: bool = False


@dataclass(frozen=True)
class SharedEvidence:
    dependency_digest: str
    views: tuple[ViewEvidence, ...]
    unresolved: tuple[tuple[str, str], ...]

    def supporting_views(self, region: str) -> tuple[str, ...]:
        if region not in REGIONS:
            raise ValueError("unknown_anatomical_region")
        return tuple(view.ref.photo_id for view in self.views if region in view.observed_regions)


def _segment_profile(view):
    world = view.detection.world_landmarks
    if view.candidate >= len(world) or len(world[view.candidate]) != 33:
        return {}
    points = world[view.candidate]
    scale = (dist(points[11], points[23]) + dist(points[12], points[24])) / 2
    if not isfinite(scale) or scale <= 1e-6 or "torso" not in view.observed_regions:
        return {}
    profile = {}
    for name in view.observed_regions:
        if name == "torso":
            continue
        indices = REGIONS[name]
        for first, last in zip(indices, indices[1:]):
            length = dist(points[first], points[last]) / scale
            if isfinite(length) and length > .02:
                profile[first, last] = length
    return profile


def inconsistent_references(views):
    """Flag large, independent segment-ratio outliers for review."""
    profiles = {view.ref.photo_id: _segment_profile(view) for view in views}
    measurements = {}
    for profile in profiles.values():
        for segment, ratio in profile.items():
            measurements.setdefault(segment, []).append(ratio)
    medians = {segment: median(values) for segment, values in measurements.items() if len(values) >= 3}
    flags = {}
    for key, profile in profiles.items():
        outliers = [segment for segment, value in profile.items()
                    if segment in medians and not .55 <= value / medians[segment] <= 1.8]
        if len(outliers) >= 2:
            flags[key] = tuple(outliers)
    return flags


def fuse_observations(project: Project, store: ObservationStore) -> SharedEvidence:
    views = []
    unresolved = []
    dependencies = []
    for photo in sorted(project.photos.photos, key=lambda item: item.id):
        if not photo.included:
            continue
        ref = project.observation(photo.id)
        dependencies.append((photo.id, photo.digest, ref.detection if ref else None,
                             ref.correction if ref else None))
        if ref is None:
            unresolved.append((photo.id, "observation_missing"))
            continue
        detection = store.read_detection(ref)
        mask = store.read_correction(ref)
        if mask is None and len(detection.candidates) != 1:
            unresolved.append((photo.id, "subject_review_required" if detection.candidates else "no_subject_detected"))
            continue
        candidate = mask.candidate if mask is not None else 0
        if not 0 <= candidate < len(detection.candidates):
            raise ValueError("invalid_observation_candidate")
        pose = detection.visible_pose(candidate)
        if len(pose) != 33:
            unresolved.append((photo.id, "invalid_landmark_count"))
            continue
        if mask is None and detection.masks and detection.masks[candidate] is not None:
            mask = SubjectMask(photo.digest, candidate, detection.masks[candidate])
        regions = tuple(name for name, indices in REGIONS.items()
                        if all(pose[index].observed for index in indices))
        # In-frame but unsupported feet can be hallucinated on studio objects.
        # Preserve the detection for manual review and keep cropped views usable.
        feet = pose[27:29]
        if (ref.correction is None and detection.masks
                and all(0 <= foot.x <= 1 and 0 <= foot.y <= 1 for foot in feet)
                and not any(foot.observed for foot in feet)):
            unresolved.append((photo.id, "subject_review_required"))
            continue
        if not regions:
            unresolved.append((photo.id, "insufficient_visible_landmarks"))
            continue
        geometry_only = detection.review_reason is not None and (
            detection.lateral_geometry_only(candidate)
        )
        views.append(ViewEvidence(ref, detection, candidate, mask, regions, geometry_only))
        if geometry_only:
            unresolved.append((photo.id, "geometry_only_pose_review_required"))
    unresolved.extend((key, "inconsistent_anatomical_ratios") for key in inconsistent_references(views))
    key = json.dumps({"algorithm_version": 2, "included": dependencies}, separators=(",", ":"))
    return SharedEvidence(sha256(key.encode("utf-8")).hexdigest(), tuple(views), tuple(unresolved))
