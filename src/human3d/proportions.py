"""Native symmetric limb-length controls based on frozen skin influences."""
import numpy as np

from .native_rig import rebind_joints

SEGMENTS = {
    "upperarm_length": ("upperarm", "lowerarm01"),
    "forearm_length": ("lowerarm", "wrist"),
    "thigh_length": ("upperleg", "lowerleg01"),
    "calf_length": ("lowerleg", "foot"),
}


def length_controls(body):
    bones = body["rig"]["bones"]
    return tuple(name for name, (start, end) in SEGMENTS.items()
                 if all(f"{bone}.{side}" in bones for side in ("L", "R")
                        for bone in (f"{start}01", f"{start}02", end)))


def lengthen(body, vertices, name, amount):
    start, end = SEGMENTS[name]
    rig = body["rig"]
    joints = rebind_joints(rig, vertices)
    bones = rig["bones"]
    source = np.asarray(vertices, dtype=float)
    result = source.copy()
    for side in ("L", "R"):
        segment = {f"{start}01.{side}", f"{start}02.{side}"}
        distal = f"{end}.{side}"
        descendants = {distal}
        frontier = {distal}
        while frontier:
            frontier = {bone for bone, definition in bones.items() if definition["parent"] in frontier}
            descendants.update(frontier)
        head = joints[bones[f"{start}01.{side}"]["head"]]
        delta = joints[bones[distal]["head"]] - head
        length_squared = delta @ delta
        if length_squared <= 1e-12:
            raise ValueError("degenerate_limb_segment")
        fraction = np.clip((source - head) @ delta / length_squared, 0, 1)
        proximal = np.asarray([sum(skin.get(bone, 0.0) for bone in segment) for skin in rig["skin"]])
        downstream = np.asarray([sum(skin.get(bone, 0.0) for bone in descendants) for skin in rig["skin"]])
        result += (amount * 0.1) * (fraction * proximal + downstream)[:, None] * delta
    return result.tolist()
