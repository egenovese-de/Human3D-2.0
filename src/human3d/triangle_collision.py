"""Broad-phase candidates and contact classification for two triangulated surfaces."""
from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree


@dataclass(frozen=True)
class TriangleContacts:
    crossing: int = 0
    coplanar_overlap: int = 0
    touching: int = 0


def _plane_section(triangle, distances, epsilon):
    """Collect vertices and edge crossings of a triangle against a plane."""
    section = list(triangle[np.abs(distances) <= epsilon])
    for i, j in ((0, 1), (1, 2), (2, 0)):
        first, second = distances[i], distances[j]
        if min(first, second) < -epsilon and max(first, second) > epsilon:
            section.append(triangle[i] + (triangle[j] - triangle[i]) * first / (first - second))
    return np.asarray(section)


def _coplanar_contact(first, second, normal, epsilon):
    minimum_depth = np.inf
    for triangle in (first, second):
        edges = np.roll(triangle, -1, axis=0) - triangle
        axes = np.cross(normal, edges)
        axes /= np.linalg.norm(axes, axis=1)[:, None]
        a, b = first @ axes.T, second @ axes.T
        depth = np.minimum(a.max(axis=0), b.max(axis=0)) - np.maximum(a.min(axis=0), b.min(axis=0))
        minimum_depth = min(minimum_depth, depth.min())
    if minimum_depth < -epsilon:
        return None
    return "coplanar_overlap" if minimum_depth > epsilon else "touching"


def _classify(first, second, normal_a, normal_b, epsilon):
    distance_a = (first - second[0]) @ normal_b
    distance_b = (second - first[0]) @ normal_a
    if any(d.min() > epsilon or d.max() < -epsilon for d in (distance_a, distance_b)):
        return None
    if max(np.abs(distance_a).max(), np.abs(distance_b).max()) <= epsilon:
        return _coplanar_contact(first, second, normal_a, epsilon)
    line = np.cross(normal_a, normal_b)
    norm = np.linalg.norm(line)
    if norm <= np.finfo(float).eps:
        return None
    line /= norm
    section_a = _plane_section(first, distance_a, epsilon)
    section_b = _plane_section(second, distance_b, epsilon)
    if not len(section_a) or not len(section_b):
        return None
    a, b = (section_a - first[0]) @ line, (section_b - first[0]) @ line
    overlap = min(a.max(), b.max()) - max(a.min(), b.min())
    if overlap < -epsilon:
        return None
    if overlap > epsilon and all(d.min() < -epsilon and d.max() > epsilon for d in (distance_a, distance_b)):
        return "crossing"
    return "touching"


def _triangles(values, epsilon):
    triangles = np.asarray(values, dtype=float)
    if triangles.shape == (0,):
        triangles = triangles.reshape(0, 3, 3)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or not np.isfinite(triangles).all():
        raise ValueError("invalid_collision_triangles")
    edges = triangles - np.roll(triangles, -1, axis=1)
    normals = np.cross(edges[:, 0], edges[:, 1])
    area_twice = np.linalg.norm(normals, axis=1)
    if np.any(area_twice <= epsilon * np.linalg.norm(edges, axis=2).max(axis=1)):
        raise ValueError("degenerate_collision_triangle")
    return triangles, normals / area_twice[:, None]


def triangle_contact_pairs(first, second, *, epsilon=1e-7, self_query=False):
    """Yield indexed contacts, counting each pair once in a self-contact query."""
    if not np.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("invalid_collision_epsilon")
    first, normals_a = _triangles(first, epsilon)
    second, normals_b = _triangles(second, epsilon)
    if not len(first) or not len(second):
        return
    low_a, high_a = first.min(axis=1), first.max(axis=1)
    low_b, high_b = second.min(axis=1), second.max(axis=1)
    center_a, center_b = (low_a + high_a) / 2, (low_b + high_b) / 2
    radius_a = np.linalg.norm(high_a - center_a, axis=1)
    radius_b = np.linalg.norm(high_b - center_b, axis=1)
    tree = cKDTree(center_b)
    neighborhoods = tree.query_ball_point(center_a, radius_a + radius_b.max() + np.sqrt(3) * epsilon)
    for i, nearby in enumerate(neighborhoods):
        candidates = np.asarray(nearby, dtype=int)
        within = ((high_b[candidates] >= low_a[i] - epsilon) &
                  (low_b[candidates] <= high_a[i] + epsilon)).all(axis=1)
        candidates = candidates[within]
        if self_query:
            candidates = candidates[candidates > i]
        for j in candidates:
            contact = _classify(first[i], second[j], normals_a[i], normals_b[j], epsilon)
            if contact:
                yield i, int(j), contact


def triangle_contacts(first, second, *, epsilon=1e-7):
    """Count transverse crossings, coplanar area overlap, and boundary contact."""
    counts = dict(crossing=0, coplanar_overlap=0, touching=0)
    for _, _, kind in triangle_contact_pairs(first, second, epsilon=epsilon):
        counts[kind] += 1
    return TriangleContacts(**counts)
