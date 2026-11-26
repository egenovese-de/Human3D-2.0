"""Evaluate a depth-confidence candidate on fixed Q geometry and evaluation cameras."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
from statistics import mean

import numpy as np

from audit_bind_frames import revision
from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask
from human3d.alignment import LIMBS
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, posed_segments, rebind_joints, skin_vertices
from human3d.session import Session
from human3d.vision import MIN_ANCHOR_CONFIDENCE

SOURCE_NAME = {
    "upperarm01": "upperarm", "lowerarm01": "lowerarm", "upperleg01": "thigh",
    "lowerleg01": "calf", "wrist": "hand", "foot": "foot",
}


def attenuate_depth(alignment, pose):
    """Reduce inferred depth when either landmark nears the native review threshold."""
    depths = {}
    for bone, depth in alignment.limb_depth_ratios.items():
        first, last = LIMBS[bone]
        indices = [first, last]
        if bone.startswith("wrist."):
            fingers = (17, 19, 21) if bone.endswith(".L") else (18, 20, 22)
            observed = [index for index in fingers if pose[index].observed]
            if len(observed) >= 2:
                indices = [first, *observed]
        anchors = [pose[index] for index in indices]
        confidence = min(min(point.visibility or 0., point.presence or 0.) for point in anchors)
        score = np.clip((confidence - MIN_ANCHOR_CONFIDENCE) / (1. - MIN_ANCHOR_CONFIDENCE), 0., 1.)
        depths[bone] = float(score * depth)
    return replace(alignment, limb_depth_ratios=depths)


def examine(folder, project):
    metadata = json.loads((folder / "manifest.json").read_text())
    session = Session(project)
    view = session.shared_evidence().views[0]
    alignment = session.current_shared_fit().alignments[view.ref.photo_id]
    body = load_project_body(session.store)
    vertices = np.asarray(deform_vertices(body, {}))
    rig = body["rig"]
    joints = rebind_joints(rig, vertices)
    faces = [tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"] if face["group"] == "body"]
    elevations = vertices[np.unique(np.concatenate(faces)), 1]
    mesh = json.loads((folder / "mesh.json").read_text())
    height = np.ptp(np.asarray(mesh["vertices"])[:, 2])
    factor = height / np.ptp(elevations)
    floor = elevations.min()
    views = {row["yaw"]: load_mask(folder / row["file"]) for row in metadata["images"] if row["held_out"]}

    def model_to_source(points):
        x, y, z = np.asarray(points).T
        return np.column_stack((x, -z, y - floor)) * factor

    results = {}
    for name, model in (("native", alignment),
                        ("attenuated", attenuate_depth(alignment, view.detection.visible_pose(view.candidate)))):
        segments = posed_segments(rig, joints, model)
        measured = {}
        for bone, source in SOURCE_NAME.items():
            for side in ("L", "R"):
                key = f"{bone}.{side}"
                reference = np.asarray(metadata["joint_anchors"][f"{source}_{side}"])
                predicted = model_to_source(segments[key])
                gold, actual = np.diff(reference, axis=0)[0], np.diff(predicted, axis=0)[0]
                cosine = np.dot(gold, actual) / np.linalg.norm(gold) / np.linalg.norm(actual)
                measured[key] = dict(direction_deg=float(np.degrees(np.arccos(np.clip(cosine, -1., 1.)))),
                                     head_error_mm=float(np.linalg.norm(predicted[0] - reference[0]) * 1000.))
        posed = skin_vertices(vertices, rig["skin"], pose_transforms(rig, joints, model))
        absolute = model_to_source(posed)
        x, y, z = absolute.T
        canonical = np.column_stack((x, z, -y)) * 10.
        iou = {yaw: compare(mask, silhouette(canonical, faces, camera_for(yaw, height), mask.size))["iou"]
               for yaw, mask in views.items()}
        results[name] = dict(segments=measured, held_out_iou=iou,
                             mean_direction_deg=mean(row["direction_deg"] for row in measured.values()),
                             mean_head_error_mm=mean(row["head_error_mm"] for row in measured.values()))
    return dict(identity=metadata["identity"], mesh_sha256=metadata["mesh_sha256"],
                bend_deg=metadata["left_forearm_bend_deg"], results=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "original_q_workspace", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    root = args.original_q_workspace
    cases = [examine(folder, root / "holdout-native" / (folder.name + "-1") / "project")
             for folder in sorted((root / "holdout").glob("*_bend*"))]
    report = dict(candidate_sha=revision(args.candidate), lab_sha=revision(Path(__file__).parents[2]),
                  promotion_min_mean_direction_improvement_deg=1., promotion_min_held_out_iou_delta=0.,
                  cases=cases)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
