"""Rebind native joint locators and evaluate bounded image-plane pose."""
from math import atan2, cos, pi, radians, sin

import numpy as np


def rebind_joints(rig, vertices):
    points = np.asarray(vertices, dtype=float)
    return {name: points[indices].mean(axis=0) for name, indices in rig["joint_vertices"].items()}


def pose_transforms(rig, joints, alignment):
    bones = rig["bones"]
    transforms = {}
    yaw = radians(alignment.camera.yaw_degrees)
    axis = np.asarray((-sin(yaw), 0.0, cos(yaw)))
    x, y, z = axis
    skew = np.asarray(((0, -z, y), (z, 0, -x), (-y, x, 0)))

    def solve(name):
        if name in transforms:
            return transforms[name]
        bone = bones[name]
        parent = bone["parent"]
        rotation, translation = solve(parent) if parent else (np.eye(3), np.zeros(3))
        head = rotation @ joints[bone["head"]] + translation
        tail = rotation @ joints[bone["tail"]] + translation
        if name in alignment.limb_angles:
            direction = alignment.camera.project(tail) - alignment.camera.project(head)
            if abs(direction) > 1:
                delta = alignment.limb_angles[name] - atan2(direction.imag, direction.real)
                delta = (delta + pi) % (2 * pi) - pi
                turn = np.eye(3) + sin(delta) * skew + (1 - cos(delta)) * (skew @ skew)
                translation = head + turn @ (translation - head)
                rotation = turn @ rotation
        transforms[name] = (rotation, translation)
        return transforms[name]

    for name in bones:
        solve(name)
    return transforms


def posed_segments(rig, joints, alignment):
    transforms = pose_transforms(rig, joints, alignment)
    return {
        name: tuple(rotation @ joints[bone[endpoint]] + translation for endpoint in ("head", "tail"))
        for name, bone in rig["bones"].items()
        for rotation, translation in (transforms[name],)
    }


def skin_vertices(vertices, skin, transforms):
    result = np.asarray(vertices, dtype=float).copy()
    unweighted = np.ones(len(result), dtype=bool)
    groups = {}
    for index, influences in enumerate(skin):
        if influences:
            unweighted[index] = False
            for name, weight in influences.items():
                groups.setdefault(name, []).append((index, weight))
    result[~unweighted] = 0
    points = np.asarray(vertices, dtype=float)
    for name, influences in groups.items():
        indices, weights = zip(*influences)
        rotation, translation = transforms[name]
        result[list(indices)] += (points[list(indices)] @ rotation.T + translation) * np.asarray(weights)[:, None]
    return result


def validate_rebind(body, vertices):
    """Verify one neutral revision and rebind its unchanged skeleton topology."""
    mesh, rig = body["mesh"], body["rig"]
    base = np.asarray(mesh["vertices"], dtype=float)
    current = np.asarray(vertices, dtype=float)
    if current.shape != base.shape or not np.isfinite(current).all():
        raise ValueError("invalid_neutral_vertices")
    faces = [face["corners"] for face in mesh["faces"] if face["group"] == "body"]
    if not faces:
        raise ValueError("missing_body_topology")
    triangles = np.asarray([[face[0][0], face[i][0], face[i + 1][0]]
                            for face in faces for i in range(1, len(face) - 1)])

    def areas(points):
        a, b, c = points[triangles].transpose((1, 0, 2))
        return np.linalg.norm(np.cross(b - a, c - a), axis=1)

    if np.any((areas(base) > 1e-10) & (areas(current) <= 1e-10)):
        raise ValueError("deformation_collapsed_body_face")
    bones = rig["bones"]
    for index in np.unique(triangles):
        weights = rig["skin"][index]
        if (not weights or any(name not in bones or not np.isfinite(weight) or weight < 0
                               for name, weight in weights.items())
                or abs(sum(weights.values()) - 1.0) > 1e-4):
            raise ValueError("invalid_body_skin_weights")
    joints = rebind_joints(rig, current)
    for bone in bones.values():
        if np.linalg.norm(joints[bone["head"]] - joints[bone["tail"]]) <= 1e-10:
            raise ValueError("deformation_collapsed_bone")
    return joints
