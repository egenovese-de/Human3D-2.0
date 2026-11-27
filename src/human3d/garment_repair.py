"""Bounded rest-space repair of contacts in neutral and skinned geometry."""
import numpy as np

from .triangle_collision import triangle_contact_pairs

CLEARANCE = .004  # native decimetres, 0.4 mm
MAX_DISPLACEMENT = .20  # native decimetres, 20 mm


def _patch_constraints(original, current, shell_faces, obstacles):
    """Map obstacle half-spaces on colliding faces back to rest vertices."""
    constraints = {}
    total = 0
    for posed, rotations, translation in obstacles:
        shell_points = np.einsum("ijk,ik->ij", rotations, current) + translation
        current_triangles = shell_points[shell_faces]
        for i, j, kind in triangle_contact_pairs(posed, current_triangles):
            if kind == "touching":
                continue
            total += 1
            a, b, c = posed[i]
            normal = np.cross(b - a, c - a)
            normal /= np.linalg.norm(normal)
            indices = shell_faces[j]
            rest_normal = rotations[indices].transpose(0, 2, 1) @ normal
            height = (shell_points[indices] - a) @ normal
            for vertex, direction, gap in zip(indices, rest_normal, height):
                if gap >= CLEARANCE or direction @ direction <= 1e-8:
                    continue
                lower_bound = float(direction @ (current[vertex] - original[vertex]) + CLEARANCE - gap)
                constraints.setdefault(vertex, []).append((direction, lower_bound))
    return total, constraints


def _solve_patch(constraints, displacement):
    trial = displacement.copy()
    for index, planes in constraints.items():
        point = trial[index]
        for _ in range(16):
            for normal, intercept in planes:
                deficit = intercept - normal @ point
                if deficit > 0:
                    point += deficit * normal / (normal @ normal)
            length = np.linalg.norm(point)
            if length > MAX_DISPLACEMENT:
                point *= MAX_DISPLACEMENT / length
    return trial


def _self_contacts(vertices, faces):
    triangles = vertices[faces]
    return {(i, j) for i, j, kind in triangle_contact_pairs(triangles, triangles, self_query=True)
            if kind != "touching"}


def _valid_update(before, after, faces, states):
    edges = np.unique(np.sort(np.concatenate((faces[:, (0, 1)], faces[:, (1, 2)], faces[:, (2, 0)])), axis=1), axis=0)
    for rotations, translation in states:
        old = np.einsum("ijk,ik->ij", rotations, before) + translation
        new = np.einsum("ijk,ik->ij", rotations, after) + translation
        old_edges = np.linalg.norm(old[edges[:, 1]] - old[edges[:, 0]], axis=1)
        new_edges = np.linalg.norm(new[edges[:, 1]] - new[edges[:, 0]], axis=1)
        if not np.isfinite(new).all() or ((new_edges < .5 * old_edges) | (new_edges > 1.5 * old_edges)).any():
            return False
        old_a, old_b, old_c = old[faces].transpose(1, 0, 2)
        new_a, new_b, new_c = new[faces].transpose(1, 0, 2)
        old_norm = np.cross(old_b - old_a, old_c - old_a)
        new_norm = np.cross(new_b - new_a, new_c - new_a)
        if (np.einsum("ij,ij->i", old_norm, new_norm) <= 0).any():
            return False
        if _self_contacts(new, faces) - _self_contacts(old, faces):
            return False
    return True


def _energy(original, current, count, constraints):
    displacement = current - original
    depth = sum(max(0., bound - normal @ displacement[index]) ** 2
                for index, planes in constraints.items() for normal, bound in planes)
    return count, depth


def repair_shell(points, faces, obstacles):
    """Repair local triangle contacts, or return the original shell on failure.

    Each obstacle supplies its triangles and the shell's affine skin map in
    that state. Body and layer geometry serve only as fixed constraints.
    """
    if not obstacles:
        return points
    current = points
    count, constraints = _patch_constraints(points, current, faces, obstacles)
    for _ in range(8):
        if not count or not constraints:
            break
        cost = _energy(points, current, count, constraints)
        proposal = points + _solve_patch(constraints, current - points)
        for factor in (1., .5, .25):
            trial = current + factor * (proposal - current)
            remaining, active = _patch_constraints(points, trial, faces, obstacles)
            if _energy(points, trial, remaining, active) < cost:
                current, count, constraints = trial, remaining, active
                break
        else:
            break
    states = [(r, t) for _, r, t in obstacles[:2]]
    if not count and (current is points or _valid_update(points, current, faces, states)):
        return current
    return points
