"""Native close-fitting garments with explicit body correspondence."""
from dataclasses import dataclass, replace

import numpy as np
from scipy.spatial import cKDTree

from .native_rig import rebind_joints, skin_vertices

CATEGORIES = ("top", "shorts", "trousers")
BASE_CLEARANCE = 0.06  # decimeters, 6 mm
LAYER_CLEARANCE = 0.04
TOLERANCE = 0.01


@dataclass(frozen=True)
class Garment:
    name: str
    category: str
    layer: int
    points: np.ndarray
    faces: tuple
    uv: tuple
    skin: tuple
    body_indices: tuple
    clearance: float


@dataclass(frozen=True)
class GarmentAsset:
    garment: Garment
    texture: object
    observed_fraction: float


@dataclass(frozen=True)
class ClearanceReport:
    violations: int
    minimum: float


def _body_faces(body):
    return [face["corners"] for face in body["mesh"]["faces"] if face["group"] == "body"]


def _normals(points, faces):
    normals = np.zeros_like(points)
    for i, j, k in ((f[0][0], f[n][0], f[n + 1][0]) for f in faces for n in range(1, len(f) - 1)):
        normal = np.cross(points[j] - points[i], points[k] - points[i])
        normals[[i, j, k]] += normal
    return normals / np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-10)


def prototype(body, neutral, category, *, layer=0, ease_mm=0.0, hem=0.0):
    """Cut a separate shell from the neutral body surface without altering the body."""
    if (category not in CATEGORIES or layer not in (0, 1) or (layer and category != "top")
            or not 0 <= ease_mm <= 10 or not -0.25 <= hem <= 0.25):
        raise ValueError("unsupported_garment_parameters")
    points = np.asarray(neutral, dtype=float)
    faces = _body_faces(body)
    rig = body["rig"]
    joints = rebind_joints(rig, points)

    def head(name):
        return joints[rig["bones"][name]["head"]]

    hip = np.mean([head("upperleg01.L")[1], head("upperleg01.R")[1]])
    knee = np.mean([head("lowerleg01.L")[1], head("lowerleg01.R")[1]])
    shoulder = np.mean([head("upperarm01.L")[1], head("upperarm01.R")[1]])
    waist = hip + 0.26 * (shoulder - hip)
    neck = head("head")[1] - 0.5
    ankles = np.mean([head("foot.L")[1], head("foot.R")[1]])
    if category == "top":
        low, high = waist + hem, neck
        sleeve = max(abs(head("upperarm01.L")[0]), abs(head("upperarm01.R")[0])) + 0.65
    else:
        low = (knee + 0.2 * (hip - knee) if category == "shorts" else ankles + 0.35) + hem
        high, sleeve = waist - 0.06, np.inf

    selected = []
    for face in faces:
        center = points[[index for index, _ in face]].mean(axis=0)
        if low <= center[1] <= high and abs(center[0]) <= sleeve:
            selected.append(face)
    if not selected:
        raise ValueError("garment_region_empty")

    used = tuple(sorted({i for face in selected for i, _ in face}))
    texels = tuple(sorted({t for face in selected for _, t in face}))
    vertex_map = {old: new for new, old in enumerate(used)}
    uv_map = {old: new for new, old in enumerate(texels)}
    shell_faces = tuple(tuple((vertex_map[i], uv_map[t]) for i, t in face) for face in selected)
    coordinates = tuple(body["mesh"]["texcoords"][i] for i in texels)
    normals = _normals(points, faces)
    clearance = BASE_CLEARANCE + layer * LAYER_CLEARANCE + ease_mm / 100
    indices = list(used)
    if np.any(np.linalg.norm(normals[indices], axis=1) < 0.5):
        raise ValueError("garment_source_normal_unavailable")
    shell = points[indices] + clearance * normals[indices]
    name = f"{category}_{'outer' if layer else 'base'}"
    return Garment(name, category, layer, shell, shell_faces, coordinates,
                   tuple(rig["skin"][i] for i in used), used, clearance)


def posed_garment(garment, transforms):
    return skin_vertices(garment.points, garment.skin, transforms)


def _triangulate(faces):
    return np.asarray([(face[0][0], face[i][0], face[i + 1][0])
                       for face in faces for i in range(1, len(face) - 1)])


def _signed_gaps(surface, triangles, samples, *, with_normals=False):
    corners = surface[triangles]
    a, b, c = corners.transpose(1, 0, 2)
    normals = np.cross(b - a, c - a)
    norm = np.linalg.norm(normals, axis=1)
    valid = norm > 1e-10
    corners = corners[valid]
    directions = normals[valid] / norm[valid, None]
    if not len(corners):
        raise ValueError("empty_collision_surface")
    _, nearest = cKDTree(corners.mean(axis=1)).query(samples, k=min(20, len(corners)))
    nearest = nearest.reshape(len(samples), -1)
    a, b, c = corners[nearest].transpose(2, 0, 1, 3)
    direction = directions[nearest]
    points = samples[:, None, :]
    signed = np.sum((points - a) * direction, axis=2)
    projection = points - signed[:, :, None] * direction
    inside = np.ones(signed.shape, dtype=bool)
    for first, last in ((a, b), (b, c), (c, a)):
        inside &= np.sum(np.cross(last - first, projection - first) * direction, axis=2) >= -1e-10
    distances = np.where(inside, signed ** 2, np.inf)
    for first, last in ((a, b), (b, c), (c, a)):
        vector = last - first
        length = np.sum(vector * vector, axis=2)
        ratio = np.clip(np.sum((points - first) * vector, axis=2) / np.maximum(length, 1e-20), 0, 1)
        closest = first + ratio[:, :, None] * vector
        distances = np.minimum(distances, np.sum((points - closest) ** 2, axis=2))
    index = np.argmin(distances, axis=1)
    rows = np.arange(len(samples))
    gaps = np.sqrt(distances[rows, index]) * np.sign(signed[rows, index])
    return (gaps, direction[rows, index]) if with_normals else gaps


def measure_clearance(garment, body, posed_body, posed_shell):
    """Sample signed surface gaps at garment vertices and face centroids."""
    body_points = np.asarray(posed_body, dtype=float)
    shell = np.asarray(posed_shell, dtype=float)
    faces = _body_faces(body)
    triangles = _triangulate(faces)
    centers = shell[_triangulate(garment.faces)].mean(axis=1)
    gaps = _signed_gaps(body_points, triangles, np.concatenate((shell, centers)))
    return ClearanceReport(int(np.count_nonzero(gaps < -TOLERANCE)), float(gaps.min()))


def correct_clearance(garment, body, posed_body, transforms):
    """Relax penetrations locally in rest space with a bounded displacement."""
    surface = np.asarray(posed_body, dtype=float)
    triangles = _triangulate(_body_faces(body))
    garment_triangles = _triangulate(garment.faces)
    original = garment.points
    rotations = np.asarray([
        sum((weight * transforms[name][0] for name, weight in weights.items()), np.zeros((3, 3)))
        for weights in garment.skin
    ])
    inverse = np.linalg.pinv(rotations, rcond=0.06)
    current = best = garment
    best_report = measure_clearance(garment, body, posed_body, posed_garment(garment, transforms))
    for _ in range(12):
        if best_report.violations == 0:
            break
        posed = posed_garment(current, transforms)
        centers = posed[garment_triangles].mean(axis=1)
        gaps, direction = _signed_gaps(surface, triangles, np.concatenate((posed, centers)), with_normals=True)
        amount = np.where(gaps < -TOLERANCE, np.minimum(0.10, 0.012 - gaps), 0)
        proposals = amount[:, None] * direction
        shifts = proposals[:len(posed)].copy()
        counts = (amount[:len(posed)] > 0).astype(float)
        center_shifts = proposals[len(posed):]
        center_hits = amount[len(posed):] > 0
        for index in range(3):
            np.add.at(shifts, garment_triangles[:, index], center_shifts)
            np.add.at(counts, garment_triangles[:, index], center_hits.astype(float))
        shifts /= np.maximum(counts[:, None], 1)
        rest_shift = np.einsum("ijk,ik->ij", inverse, shifts)
        displacement = current.points + rest_shift - original
        lengths = np.linalg.norm(displacement, axis=1)
        displacement *= np.minimum(1, 0.20 / np.maximum(lengths, 1e-10))[:, None]
        current = replace(garment, points=original + displacement)
        report = measure_clearance(current, body, posed_body, posed_garment(current, transforms))
        if (report.violations, -report.minimum) < (best_report.violations, -best_report.minimum):
            best, best_report = current, report
    return best, best_report


def verify_layers(garments, body, posed_body, transforms):
    """Validate supported combinations and corresponding overlap clearance."""
    names = {garment.name for garment in garments}
    if len(names) != len(garments) or sum(garment.category in ("shorts", "trousers") for garment in garments) > 1:
        raise ValueError("unsupported_layer_combination")
    inner = next((garment for garment in garments if garment.category == "top" and garment.layer == 0), None)
    outer = next((garment for garment in garments if garment.layer == 1), None)
    lower = next((garment for garment in garments if garment.category in ("shorts", "trousers")), None)
    if outer is not None and inner is None:
        raise ValueError("outer_top_requires_base_top")
    normals = _normals(np.asarray(posed_body), _body_faces(body))
    gaps = []

    def check_pair(base, cover, *, require_overlap=False):
        positions = {source: index for index, source in enumerate(base.body_indices)}
        shared = [(index, source) for index, source in enumerate(cover.body_indices) if source in positions]
        if not shared:
            if require_overlap:
                raise ValueError("layer_overlap_not_observed")
            return
        if not require_overlap:
            def source_faces(garment):
                return {tuple(sorted(garment.body_indices[index] for index, _ in face)) for face in garment.faces}

            if not source_faces(base) & source_faces(cover):
                return
        a, b = posed_garment(base, transforms), posed_garment(cover, transforms)
        gaps.extend(float((b[index] - a[positions[source]]) @ normals[source]) for index, source in shared)

    if outer is not None:
        check_pair(inner, outer, require_overlap=True)
    if lower is not None:
        for top in (inner, outer):
            if top is not None:
                check_pair(lower, top)
    if not gaps:
        return None
    return ClearanceReport(sum(gap < LAYER_CLEARANCE - TOLERANCE for gap in gaps), min(gaps))
