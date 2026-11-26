"""Initial weak-perspective camera and image-plane pose observations."""
from dataclasses import dataclass, field
from math import atan2, cos, hypot, isfinite, radians, sin

from .anatomical_evidence import yaw_conflicts
from .vision import SubjectEvidence, estimate_world_yaw

TORSO = {
    11: "upperarm01.L", 12: "upperarm01.R",
    23: "upperleg01.L", 24: "upperleg01.R",
}
LIMBS = {
    "upperarm01.L": (11, 13), "lowerarm01.L": (13, 15),
    "upperarm01.R": (12, 14), "lowerarm01.R": (14, 16),
    "upperleg01.L": (23, 25), "lowerleg01.L": (25, 27),
    "upperleg01.R": (24, 26), "lowerleg01.R": (26, 28),
    "wrist.L": (15, 19), "wrist.R": (16, 20),
    "foot.L": (27, 31), "foot.R": (28, 32),
}


@dataclass(frozen=True)
class Camera:
    yaw_degrees: float
    similarity: complex
    origin: complex
    horizontal_sign: int = -1

    def __post_init__(self):
        if (not isfinite(self.yaw_degrees) or self.horizontal_sign not in (-1, 1)
                or not all(isfinite(v) for v in (self.similarity.real, self.similarity.imag, self.origin.real, self.origin.imag))
                or abs(self.similarity) <= 1e-12):
            raise ValueError("invalid_camera_transform")

    def project(self, vertex):
        x, y, z = vertex
        yaw = radians(self.yaw_degrees)
        return self.similarity * complex(self.horizontal_sign * (x * cos(yaw) + z * sin(yaw)), -y) + self.origin


@dataclass(frozen=True)
class Alignment:
    camera: Camera
    torso_rms_pixels: float
    limb_angles: dict[str, float]
    limb_depth_ratios: dict[str, float] = field(default_factory=dict)
    wrist_cross_axes: dict[str, tuple[float, float, float]] = field(default_factory=dict)


def initialize_alignment(body: dict, evidence: SubjectEvidence, candidate: int, *, refine=False) -> Alignment:
    if not 0 <= candidate < len(evidence.candidates):
        raise ValueError("invalid_subject_candidate")
    pose = evidence.visible_pose(candidate)
    if len(pose) != 33 or not all(pose[index].observed for index in TORSO):
        raise ValueError("insufficient_torso_evidence")
    width, height = evidence.image_size
    if not (isfinite(width) and isfinite(height) and width > 0 and height > 0):
        raise ValueError("invalid_camera_image_size")
    observed = [complex(landmark.x * width, landmark.y * height) for landmark in pose]
    targets = [observed[index] for index in TORSO]
    weights = [pose[index].visibility * pose[index].presence for index in TORSO]
    total_weight = sum(weights)
    target_center = sum(weight * point for weight, point in zip(weights, targets)) / total_weight
    rig = body["rig"]
    rest = [rig["joints"][rig["bones"][bone]["head"]] for bone in TORSO.values()]
    world = evidence.world_landmarks[candidate] if candidate < len(evidence.world_landmarks) else ()
    yaw = estimate_world_yaw(pose, world)
    external = evidence.anatomical
    if external and external.candidate == candidate and external.yaw is not None and external.yaw_confidence >= .8:
        if not yaw_conflicts(external, yaw):
            yaw = external.yaw
    lower, upper = (-45, 45) if yaw is None else (yaw - 15, yaw + 15)

    def evaluate(yaw):
        yaw = (yaw + 180) % 360 - 180
        unit_camera = Camera(yaw, 1, 0, 1)
        points = [unit_camera.project(vertex) for vertex in rest]
        center = sum(weight * point for weight, point in zip(weights, points)) / total_weight
        centered = [point - center for point in points]
        variance = sum(weight * abs(point) ** 2 for weight, point in zip(weights, centered))
        if not isfinite(variance) or variance <= 1e-12:
            return None
        similarity = sum(weight * point.conjugate() * (target - target_center)
                         for weight, point, target in zip(weights, centered, targets)) / variance
        if not all(isfinite(v) for v in (similarity.real, similarity.imag)) or similarity.real <= 1e-6:
            return None
        camera = Camera(yaw, similarity, target_center - similarity * center, 1)
        rms = (sum(weight * abs(camera.project(vertex) - target) ** 2
                   for weight, vertex, target in zip(weights, rest, targets)) / total_weight) ** 0.5
        return rms, camera

    candidates = [result for offset in range(round((upper - lower) / 5) + 1)
                  if (result := evaluate(lower + 5 * offset)) is not None]
    if not candidates:
        raise ValueError("camera_initialization_failed")
    best = min(candidates, key=lambda result: result[0])
    if refine:
        for step in (1.0, 0.2, 0.04):
            center = best[1].yaw_degrees
            center += 360 * round(((lower + upper) / 2 - center) / 360)
            candidates = [result for offset in range(-4, 5)
                          if lower <= (angle := center + step * offset) <= upper
                          and (result := evaluate(angle)) is not None]
            best = min([best, *candidates], key=lambda result: result[0])
    angles = {}
    depths = {}
    wrist_axes = {}
    for name, (first, last) in LIMBS.items():
        if name not in rig["bones"] or not pose[first].observed:
            continue
        if name.startswith("wrist."):
            fingers = (17, 19, 21) if name.endswith(".L") else (18, 20, 22)
            endpoints = [index for index in fingers if pose[index].observed]
            if len(endpoints) < 2:
                endpoints = [last] if pose[last].observed else []
        else:
            endpoints = [last] if pose[last].observed else []
        if not endpoints:
            continue
        direction = sum(observed[index] for index in endpoints) / len(endpoints) - observed[first]
        if abs(direction) <= 1:
            continue
        angles[name] = atan2(direction.imag, direction.real)
        if len(world) != 33:
            continue
        dx, dy, dz = (sum(world[index][axis] for index in endpoints) / len(endpoints) - world[first][axis]
                      for axis in range(3))
        if name.startswith("wrist.") and len(endpoints) == 3:
            pinky, index = endpoints[:2]
            a, b, c = (world[index][axis] - world[pinky][axis] for axis in range(3))
            if all(map(isfinite, (a, b, c))) and .015 < hypot(hypot(a, b), c) < .2:
                wrist_axes[name] = (a, b, -c)
        if all(map(isfinite, (dx, dy, dz))) and hypot(hypot(dx, dy), dz) > .01:
            lateral = hypot(dx, dy)
            depths[name] = max(-4.0, min(4.0, -dz / max(lateral, .005)))
    return Alignment(best[1], best[0], angles, depths, wrist_axes)

def refine_views(body, evidence):
    """Solve each usable photo in its own image coordinates and pose."""
    alignments = {}
    unavailable = {}
    for view in evidence.views:
        try:
            alignments[view.ref.photo_id] = initialize_alignment(
                body, view.detection, view.candidate, refine=True,
            )
        except ValueError as error:
            unavailable[view.ref.photo_id] = str(error)
    return alignments, unavailable
