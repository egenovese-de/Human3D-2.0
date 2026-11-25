"""Initial weak-perspective camera and image-plane pose observations."""
from dataclasses import dataclass
from math import atan2, cos, radians, sin

from .vision import SubjectEvidence

TORSO = {
    11: "upperarm01.L", 12: "upperarm01.R",
    23: "upperleg01.L", 24: "upperleg01.R",
}
LIMBS = {
    "upperarm01.L": (11, 13), "lowerarm01.L": (13, 15),
    "upperarm01.R": (12, 14), "lowerarm01.R": (14, 16),
    "upperleg01.L": (23, 25), "lowerleg01.L": (25, 27),
    "upperleg01.R": (24, 26), "lowerleg01.R": (26, 28),
}


@dataclass(frozen=True)
class Camera:
    yaw_degrees: int
    similarity: complex
    origin: complex

    def project(self, vertex):
        x, y, z = vertex
        yaw = radians(self.yaw_degrees)
        return self.similarity * complex(-x * cos(yaw) - z * sin(yaw), -y) + self.origin


@dataclass(frozen=True)
class Alignment:
    camera: Camera
    torso_rms_pixels: float
    limb_angles: dict[str, float]


def initialize_alignment(body: dict, evidence: SubjectEvidence, candidate: int) -> Alignment:
    if not 0 <= candidate < len(evidence.candidates):
        raise ValueError("invalid_subject_candidate")
    pose = evidence.candidates[candidate]
    if len(pose) != 33 or not all(pose[index].observed for index in TORSO):
        raise ValueError("insufficient_torso_evidence")
    width, height = evidence.image_size
    observed = [complex(landmark.x * width, landmark.y * height) for landmark in pose]
    targets = [observed[index] for index in TORSO]
    target_center = sum(targets) / len(targets)
    rig = body["rig"]
    rest = [rig["joints"][rig["bones"][bone]["head"]] for bone in TORSO.values()]
    best = None
    for yaw in range(-45, 46, 5):
        unit_camera = Camera(yaw, 1, 0)
        points = [unit_camera.project(vertex) for vertex in rest]
        center = sum(points) / len(points)
        centered = [point - center for point in points]
        variance = sum(abs(point) ** 2 for point in centered)
        if variance <= 1e-12:
            continue
        similarity = sum(point.conjugate() * (target - target_center)
                         for point, target in zip(centered, targets)) / variance
        if similarity.real <= 1e-6:
            continue
        camera = Camera(yaw, similarity, target_center - similarity * center)
        rms = (sum(abs(camera.project(vertex) - target) ** 2
                   for vertex, target in zip(rest, targets)) / len(rest)) ** 0.5
        if best is None or rms < best[0]:
            best = (rms, camera)
    if best is None:
        raise ValueError("camera_initialization_failed")
    angles = {}
    for name, (first, last) in LIMBS.items():
        if pose[first].observed and pose[last].observed:
            direction = observed[last] - observed[first]
            if abs(direction) > 1:
                angles[name] = atan2(direction.imag, direction.real)
    return Alignment(best[1], best[0], angles)
