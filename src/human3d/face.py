"""Limited head-width refinement from visible frontal eye landmarks."""
from statistics import median

import numpy as np

EYE_CENTERS = (("eye.L", 5), ("eye.R", 2))


def has_head_control(body):
    return {"head", "eye.L", "eye.R"} <= body["rig"]["bones"].keys()


def widen_head(body, vertices, amount):
    from .native_rig import rebind_joints

    rig = body["rig"]
    bones = rig["bones"]
    head_chain = {"head"}
    frontier = {"head"}
    while frontier:
        frontier = {name for name, bone in bones.items() if bone["parent"] in frontier}
        head_chain.update(frontier)
    joints = rebind_joints(rig, vertices)
    center = joints[bones["head"]["head"]][0]
    points = np.array(vertices, dtype=float)
    weights = np.asarray([sum(skin.get(name, 0) for name in head_chain) for skin in rig["skin"]])
    points[:, 0] += (points[:, 0] - center) * (0.1 * amount) * weights
    return points.tolist()


def propose_head_width(body, evidence, current):
    from .frozen_body import deform_vertices
    from .native_rig import rebind_joints

    if not has_head_control(body):
        raise ValueError("head_control_unavailable")
    samples = []
    for view in evidence.views:
        alignment = current.alignments.get(view.ref.photo_id)
        if alignment is None or abs(alignment.camera.yaw_degrees) > 20:
            continue
        face = view.detection.candidates[view.candidate]
        eyes = [face[index] for _, index in EYE_CENTERS]
        if not all(eye.observed for eye in eyes):
            continue
        width, height = view.detection.image_size
        a, b = (complex(eye.x * width, eye.y * height) for eye in eyes)
        if abs(a - b) >= 8:
            samples.append((alignment.camera, abs(a - b)))
    if not samples:
        raise ValueError("No near-frontal view has two reliable visible eyes.")

    original = current.fit.controls.get("head_width", 0)
    rig = body["rig"]

    def residual(value):
        vertices = deform_vertices(body, current.fit.controls | {"head_width": value})
        joints = rebind_joints(rig, vertices)
        eyes = [joints[rig["bones"][bone]["head"]] for bone, _ in EYE_CENTERS]
        return median(abs(abs(camera.project(eyes[0]) - camera.project(eyes[1])) - observed) / observed
                      for camera, observed in samples)

    choices = (original, -0.5, -0.25, 0.0, 0.25, 0.5)
    proposal = min(choices, key=residual)
    return proposal, len(samples)
