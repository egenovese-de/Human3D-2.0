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


def forearm_ratio_penalty(body, evidence, aligned_keys):
    """Return an optional penalty for the supported subject-local arm ratios."""
    definition = "arm.forearm_to_upperarm@v1"
    constraints = {}
    bones = body["rig"]["bones"]
    contradictory = {key for key, reason in evidence.unresolved if reason == "inconsistent_anatomical_ratios"}
    for view in evidence.views:
        key = view.ref.photo_id
        if key not in aligned_keys or key in contradictory:
            continue
        supplied = view.detection.anatomical
        if supplied is None or supplied.candidate != view.candidate:
            continue
        for item in supplied.observations:
            if (item.definition != definition or item.kind != "proportion" or item.frame != "subject_local"
                    or item.region not in ("left_arm", "right_arm") or item.region not in view.observed_regions
                    or item.uncertainty is None
                    or item.uncertainty <= 0 or item.visibility is None or item.visibility < .8):
                continue
            if item.interval is not None:
                low, high = item.interval
            elif item.value is not None:
                low = high = item.value
            else:
                continue
            if not .25 <= low <= high <= 2. or item.uncertainty > .5:
                continue
            side = "L" if item.region == "left_arm" else "R"
            names = tuple(f"{bone}.{side}" for bone in ("upperarm01", "lowerarm01", "wrist"))
            if all(name in bones for name in names):
                by_family = constraints.setdefault(names, {})
                by_family.setdefault(item.source_family, []).append((max(0., low - item.uncertainty),
                                                                     high + item.uncertainty))
    supported = {}
    for names, groups in constraints.items():
        ranges = [bounds for records in groups.values() for bounds in records]
        # Conflict cancels the regional constraint. Compatible sources widen
        # the tolerated envelope instead of tightening it through repetition.
        if max(low for low, _ in ranges) <= min(high for _, high in ranges):
            supported[tuple(bones[name]["head"] for name in names)] = (
                min(low for low, _ in ranges), max(high for _, high in ranges),
            )
    if not supported:
        return None

    def penalty(vertices):
        joints = rebind_joints(body["rig"], vertices)
        errors = []
        for (shoulder, elbow, wrist), (low, high) in supported.items():
            upperarm = np.linalg.norm(joints[elbow] - joints[shoulder])
            if upperarm <= 1e-8:
                errors.append(.02)
                continue
            ratio = np.linalg.norm(joints[wrist] - joints[elbow]) / upperarm
            errors.append(min(.02, .05 * max(low - ratio, ratio - high, 0.)))
        return sum(errors) / len(errors)

    return penalty
