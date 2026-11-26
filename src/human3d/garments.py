"""Native close-fitting garments with explicit body correspondence."""
from dataclasses import dataclass, replace

import numpy as np
from scipy.spatial import cKDTree

from .native_rig import rebind_joints, skin_vertices
from .triangle_collision import TriangleContacts, triangle_contacts

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


def validate_garment(garment, body=None):
    points = np.asarray(garment.points, dtype=float)
    uv = np.asarray(garment.uv, dtype=float)
    if (points.ndim != 2 or points.shape[1] != 3 or not len(points)
            or not np.isfinite(points).all() or len(garment.skin) != len(points)
            or len(garment.body_indices) != len(points)
            or len(set(garment.body_indices)) != len(points)
            or uv.ndim != 2 or uv.shape[1] != 2 or not np.isfinite(uv).all()
            or np.any((uv < 0) | (uv > 1)) or not garment.faces):
        raise ValueError("invalid_garment_geometry")
    if any(type(i) is not int or i < 0 or (body is not None and i >= len(body["mesh"]["vertices"]))
           for i in garment.body_indices):
        raise ValueError("invalid_garment_correspondence")
    for face in garment.faces:
        if len(face) < 3 or any(not 0 <= i < len(points) or not 0 <= t < len(uv) for i, t in face):
            raise ValueError("invalid_garment_face")
    for weights in garment.skin:
        if (not weights or any(not np.isfinite(w) or w < 0 for w in weights.values())
                or abs(sum(weights.values()) - 1) > 1e-4
                or (body is not None and any(n not in body["rig"]["bones"] for n in weights))):
            raise ValueError("invalid_garment_skin")


def posed_garment(garment, transforms):
    validate_garment(garment)
    if any(name not in transforms for weights in garment.skin for name in weights):
        raise ValueError("invalid_garment_skin")
    posed = skin_vertices(garment.points, garment.skin, transforms)
    if not np.isfinite(posed).all():
        raise ValueError("invalid_garment_pose")
    return posed


def _triangulate(faces):
    return np.asarray([(face[0][0], face[i][0], face[i + 1][0])
                       for face in faces for i in range(1, len(face) - 1)])


def _signed_gaps(surface, triangles, samples, *, with_normals=False):
    if not np.isfinite(surface).all() or not np.isfinite(samples).all() or not len(samples) or not len(triangles):
        raise ValueError("invalid_collision_geometry")
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
    validate_garment(garment, body)
    body_points = np.asarray(posed_body, dtype=float)
    shell = np.asarray(posed_shell, dtype=float)
    if body_points.shape != np.shape(body["mesh"]["vertices"]) or shell.shape != np.shape(garment.points) or not np.isfinite(shell).all():
        raise ValueError("invalid_collision_geometry")
    faces = _body_faces(body)
    triangles = _triangulate(faces)
    centers = shell[_triangulate(garment.faces)].mean(axis=1)
    gaps = _signed_gaps(body_points, triangles, np.concatenate((shell, centers)))
    return ClearanceReport(int(np.count_nonzero(gaps < -TOLERANCE)), float(gaps.min()))



@dataclass(frozen=True)
class GarmentContactReport:
    neutral: TriangleContacts
    posed: TriangleContacts

    @property
    def intersections(self):
        return (self.neutral.crossing + self.neutral.coplanar_overlap +
                self.posed.crossing + self.posed.coplanar_overlap)

    def describe(self):
        return (f"Neutral: {self.neutral.crossing} crossing, {self.neutral.coplanar_overlap} overlapping, "
                f"{self.neutral.touching} touching pairs. Posed: {self.posed.crossing} crossing, "
                f"{self.posed.coplanar_overlap} overlapping, {self.posed.touching} touching pairs.")


def measure_garment_contacts(garment, body, neutral_body, posed_body, posed_shell):
    """Check the corrected rest and posed shell against the matching body."""
    validate_garment(garment, body)
    body_indices = _triangulate(_body_faces(body))
    shell_indices = _triangulate(garment.faces)
    rest_body = np.asarray(neutral_body, dtype=float)
    target_body = np.asarray(posed_body, dtype=float)
    target_shell = np.asarray(posed_shell, dtype=float)
    if (rest_body.shape != np.shape(body["mesh"]["vertices"]) or
            target_body.shape != rest_body.shape or target_shell.shape != np.shape(garment.points)):
        raise ValueError("invalid_collision_geometry")
    rest = triangle_contacts(rest_body[body_indices], garment.points[shell_indices])
    target = triangle_contacts(target_body[body_indices], target_shell[shell_indices])
    return GarmentContactReport(rest, target)


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



@dataclass(frozen=True)
class LayerClearanceReport:
    sampled: ClearanceReport | None
    pairs: tuple[tuple[str, str, GarmentContactReport], ...]

    @property
    def violations(self):
        return self.sampled.violations if self.sampled is not None else 0

    @property
    def minimum(self):
        return self.sampled.minimum if self.sampled is not None else None

    @property
    def blocked(self):
        return bool(self.violations or
                    any(report.intersections for _, _, report in self.pairs))

    def describe(self):
        messages = []
        if self.sampled and self.sampled.violations:
            messages.append(f"{self.sampled.violations} layer clearance samples failed.")
        messages.extend(f"{base} and {cover}. {report.describe()}"
                        for base, cover, report in self.pairs if report.intersections)
        return " ".join(messages)


def verify_layers(garments, body, posed_body, transforms):
    """Validate supported combinations and corresponding overlap clearance."""
    for garment in garments:
        validate_garment(garment, body)
    names = {garment.name for garment in garments}
    if len({(g.category, g.layer) for g in garments}) != len(garments) or any(g.category not in CATEGORIES or g.layer not in (0, 1) or (g.layer and g.category != "top") for g in garments):
        raise ValueError("unsupported_layer_combination")
    if len(names) != len(garments) or sum(garment.category in ("shorts", "trousers") for garment in garments) > 1:
        raise ValueError("unsupported_layer_combination")
    inner = next((garment for garment in garments if garment.category == "top" and garment.layer == 0), None)
    outer = next((garment for garment in garments if garment.layer == 1), None)
    lower = next((garment for garment in garments if garment.category in ("shorts", "trousers")), None)
    if outer is not None and inner is None:
        raise ValueError("outer_top_requires_base_top")
    if len(garments) < 2:
        return None
    normals = _normals(np.asarray(posed_body), _body_faces(body))
    gaps = []
    layer_contacts = []
    posed_shells = {g.name: posed_garment(g, transforms) for g in garments}

    def check_pair(base, cover, *, require_overlap=False):
        base_faces, cover_faces = _triangulate(base.faces), _triangulate(cover.faces)
        a, b = posed_shells[base.name], posed_shells[cover.name]
        neutral = triangle_contacts(base.points[base_faces], cover.points[cover_faces])
        posed = triangle_contacts(a[base_faces], b[cover_faces])
        layer_contacts.append((base.name, cover.name, GarmentContactReport(neutral, posed)))
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
        gaps.extend(float((b[index] - a[positions[source]]) @ normals[source]) for index, source in shared)

    if outer is not None:
        check_pair(inner, outer, require_overlap=True)
    if lower is not None:
        for top in (inner, outer):
            if top is not None:
                check_pair(lower, top)
    if not layer_contacts:
        return None
    sampled = ClearanceReport(sum(gap < LAYER_CLEARANCE - TOLERANCE for gap in gaps),
                              min(gaps)) if gaps else None
    return LayerClearanceReport(sampled, tuple(layer_contacts))
