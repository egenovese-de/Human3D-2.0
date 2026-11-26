"""Rebind native joint locators and evaluate bounded target articulation."""
from math import atan2, cos, pi, radians, sin

import numpy as np


def rebind_joints(rig, vertices):
    points = np.asarray(vertices, dtype=float)
    return {name: points[indices].mean(axis=0) for name, indices in rig["joint_vertices"].items()}


def _rotation(axis, angle):
    x, y, z = axis
    skew = np.asarray(((0, -z, y), (z, 0, -x), (-y, x, 0)))
    return np.eye(3) + sin(angle) * skew + (1 - cos(angle)) * (skew @ skew)


def _swing(source, target):
    source_norm = np.linalg.norm(source)
    target_norm = np.linalg.norm(target)
    if min(source_norm, target_norm) < 1e-10:
        return np.eye(3)
    source, target = source / source_norm, target / target_norm
    axis = np.cross(source, target)
    sine = np.linalg.norm(axis)
    cosine = np.clip(source @ target, -1, 1)
    if sine < 1e-10:
        if cosine > 0:
            return np.eye(3)
        axis = np.cross(source, np.eye(3)[np.argmin(np.abs(source))])
        return _rotation(axis / np.linalg.norm(axis), pi)
    return _rotation(axis / sine, atan2(sine, cosine))


def _wrist_roll(axis, from_vector, to_vector):
    length = np.linalg.norm(axis)
    if length <= 1e-8:
        return np.eye(3)
    axis = axis / length
    source = from_vector - (from_vector @ axis) * axis
    target = to_vector - (to_vector @ axis) * axis
    if min(np.linalg.norm(source), np.linalg.norm(target)) <= .005:
        return np.eye(3)
    angle = atan2(axis @ np.cross(source, target), source @ target)
    return _rotation(axis, float(np.clip(angle, -pi / 4, pi / 4)))


def pose_transforms(rig, joints, alignment):
    bones = rig["bones"]
    transforms = {}
    yaw = radians(alignment.camera.yaw_degrees)
    axis = np.asarray((-sin(yaw), 0.0, cos(yaw)))
    right = alignment.camera.horizontal_sign * np.asarray((cos(yaw), 0.0, sin(yaw)))
    down = np.asarray((0.0, -1.0, 0.0))

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
            angle = alignment.limb_angles[name]
            depth = alignment.limb_depth_ratios.get(name)
            turn = None
            if depth is not None:
                image = complex(cos(angle), sin(angle)) / alignment.camera.similarity
                image /= abs(image)
                turn = _swing(tail - head, image.real * right + image.imag * down + depth * axis)
            elif abs(direction) > 1:
                delta = (angle - atan2(direction.imag, direction.real) + pi) % (2 * pi) - pi
                turn = _rotation(axis, -alignment.camera.horizontal_sign * delta)
            if turn is not None:
                cross_axis = alignment.wrist_cross_axes.get(name)
                if cross_axis is not None:
                    side = name[-2:]
                    index, pinky = bones.get("finger2-1" + side), bones.get("finger5-1" + side)
                    if index and pinky:
                        canonical = joints[index["head"]] - joints[pinky["head"]]
                        a, b, c = cross_axis
                        roll = _wrist_roll(turn @ (tail - head), turn @ rotation @ canonical,
                                           a * right + b * down + c * axis)
                        turn = roll @ turn
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

    baseline_areas = areas(base)
    adjusted_areas = areas(current)
    if np.any((baseline_areas > 1e-10) & (adjusted_areas <= 1e-10)):
        raise ValueError("deformation_collapsed_body_face")
    stable = baseline_areas > 1e-6
    if np.any((adjusted_areas[stable] < .03 * baseline_areas[stable])
              | (adjusted_areas[stable] > 30 * baseline_areas[stable])):
        raise ValueError("deformation_excessive_face_area_change")
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


def validate_pose(body, neutral, posed):
    vertices = np.asarray(posed, dtype=float)
    if vertices.shape != np.shape(neutral) or not np.isfinite(vertices).all():
        raise ValueError("invalid_posed_vertices")
    faces = [face["corners"] for face in body["mesh"]["faces"] if face["group"] == "body"]
    triangles = np.asarray([[face[0][0], face[i][0], face[i + 1][0]]
                            for face in faces for i in range(1, len(face) - 1)])

    def areas(points):
        a, b, c = np.asarray(points)[triangles].transpose((1, 0, 2))
        return np.linalg.norm(np.cross(b - a, c - a), axis=1)

    if np.any((areas(neutral) > 1e-10) & (areas(vertices) <= 1e-10)):
        raise ValueError("pose_collapsed_body_face")


def foot_height_difference(rig, joints, transforms, body_height):
    """Relative foot-height diagnostic. A floor plane is not inferred."""
    if body_height <= 0 or any(f"foot.{side}" not in rig["bones"] for side in ("L", "R")):
        return None
    heights = []
    for side in ("L", "R"):
        name = f"foot.{side}"
        rotation, shift = transforms[name]
        head = joints[rig["bones"][name]["head"]]
        heights.append((rotation @ head + shift)[1])
    return abs(heights[0] - heights[1]) / body_height


def infer_support_plane(rig, posed, body_vertices):
    """Return the horizontal plane at the lowest supported sole in model units.

    The result normalizes asset placement. Photographs without calibration do
    not establish world elevation or whether the person is airborne.
    """
    points = np.asarray(posed)
    soles = []
    for side in ("L", "R"):
        foot = f"foot.{side}"
        indices = [
            index for index in body_vertices
            if sum(weight for name, weight in rig["skin"][index].items()
                   if name == foot or (name.startswith("toe") and name.endswith(f".{side}"))) >= .8
        ]
        if indices:
            soles.append(float(points[indices, 1].min()))
    if not soles:
        return None
    height = float(np.ptp(points[body_vertices, 1]))
    floor = min(soles)
    # A lower hand or knee indicates a different support configuration.
    if floor - float(points[body_vertices, 1].min()) > .005 * height:
        return None
    return min(floor, float(points[body_vertices, 1].min()))
