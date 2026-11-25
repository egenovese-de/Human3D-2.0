"""Smooth depth controls in the frozen rig's canonical coordinate system."""
import numpy as np

from .native_rig import rebind_joints

TORSO_CONTROLS = {
    "abdomen_depth": ("spine02", ("spine02", "spine03", "spine04"), 0.85, 0.32, 1),
    "glute_depth": ("spine05", ("root", "spine05", "spine04", "upperleg01"), 0.78, 0.32, -1),
}
LIMB_CONTROLS = {
    "forearm_depth": ("lowerarm01", "wrist", ("lowerarm01", "lowerarm02"), .11),
    "shin_depth": ("lowerleg01", "foot", ("lowerleg01", "lowerleg02"), .14),
}


def regional_controls(body):
    bones = body["rig"]["bones"]
    torso = tuple(name for name, (anchor, *_rest) in TORSO_CONTROLS.items() if anchor in bones)
    limbs = tuple(name for name, (start, end, _, _) in LIMB_CONTROLS.items()
                  if all(f"{joint}.{side}" in bones for side in ("L", "R") for joint in (start, end)))
    return torso + limbs


def _support(rig, names):
    return np.asarray([sum(weights.get(name, 0) for name in names) for weights in rig["skin"]])


def apply_regional_controls(body, vertices, controls):
    rig = body["rig"]
    bones = rig["bones"]
    points = np.asarray(vertices, dtype=float)
    joints = rebind_joints(rig, vertices)
    result = points.copy()
    for name, amount in controls.items():
        if not amount:
            continue
        if name in TORSO_CONTROLS:
            anchor, groups, radius, strength, direction = TORSO_CONTROLS[name]
            center = joints[bones[anchor]["head"]]
            midline = np.clip(direction * (points[:, 2] - center[2]) / .8, 0, 1)
            section = np.exp(-0.5 * ((points[:, 1] - center[1]) / radius) ** 2)
            support = _support(rig, [bone for bone in bones if bone.split(".")[0] in groups])
            result[:, 2] += direction * amount * strength * midline * section * support
        else:
            start, end, groups, strength = LIMB_CONTROLS[name]
            for side in ("L", "R"):
                head, tail = (joints[bones[f"{bone}.{side}"]["head"]] for bone in (start, end))
                axis = tail - head
                length_squared = axis @ axis
                if length_squared < 1e-12:
                    raise ValueError("degenerate_regional_morph_segment")
                fraction = np.clip((points - head) @ axis / length_squared, 0, 1)
                center_depth = head[2] + fraction * axis[2]
                support = _support(rig, [f"{group}.{side}" for group in groups])
                result[:, 2] += amount * strength * np.sin(np.pi * fraction) * support * (points[:, 2] - center_depth)
    return result.tolist()
