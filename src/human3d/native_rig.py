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
