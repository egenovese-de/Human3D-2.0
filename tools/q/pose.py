"""Compare recovered joint positions and limb directions with MB-Lab rig anchor proxies."""
import argparse
import json
from pathlib import Path

import numpy as np

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, posed_segments, skin_vertices, validate_rebind
from human3d.session import Session


BONES = {"upperarm01": "upperarm", "lowerarm01": "lowerarm",
         "upperleg01": "thigh", "lowerleg01": "calf", "wrist": "hand", "foot": "foot"}


def main(pilot, upstream, native, output):
    output.mkdir(parents=True, exist_ok=True)
    for source in sorted(native.glob("*-1/benchmark.json")):
        run = json.loads(source.read_text())
        if "fit" not in run:
            continue
        folder = pilot / source.parent.name.removesuffix("-1")
        meta = json.loads((folder / "manifest.json").read_text())
        truth = np.asarray(json.loads((folder / "mesh.json").read_text())["vertices"])
        family = meta["source_family"].removeprefix("MBLab_")
        calibration = json.loads((upstream / f"data/joints/{family}_joints.json").read_text())
        offsets = json.loads((upstream / f"data/joints/{family}_joints_offset.json").read_text())
        truth_bones = {
            native_bone + "." + side: np.array([
                truth[calibration[key]].mean(axis=0) + offsets.get(key, [0, 0, 0])
                for end in ("head", "tail") for key in [f"{mb_bone}_{side}_{end}"]
            ])
            for native_bone, mb_bone in BONES.items() for side in ("L", "R")
        }
        if "joint_anchors" in meta:
            truth_bones = {native_bone + "." + side: np.asarray(meta["joint_anchors"][f"{mb_bone}_{side}"])
                           for native_bone, mb_bone in BONES.items() for side in ("L", "R")}
        session = Session(source.parent / "project")
        body = load_project_body(session.store)
        fit = session.current_shared_fit()
        alignment = fit.alignments[run["photo_ids"]["rgb-yaw-0.png"]]
        neutral = np.asarray(deform_vertices(body, fit.fit.controls))
        base = np.asarray(deform_vertices(body, {}))
        faces = [tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"]
        model_y = base[np.unique(np.concatenate(faces)), 1]
        height = np.ptp(truth[:, 2])
        factor = height / np.ptp(model_y)

        def world(p):
            x, y, z = np.asarray(p).T
            return factor * np.column_stack((x, -z, y - model_y.min()))

        joints = validate_rebind(body, neutral)
        rig = body["rig"]
        native_segments = posed_segments(rig, joints, alignment)
        mask = load_mask(folder / "yaw-0.png")
        camera = camera_for(0, height)

        def iou(vertices):
            x, y, z = world(vertices).T
            return compare(mask, silhouette(np.column_stack((x, z, -y)) * 10, faces, camera, mask.size))["iou"]

        from dataclasses import replace
        angles, depths = {}, {}
        controls = {}
        for name, segment in truth_bones.items():
            gt = segment[1] - segment[0]
            estimated = world(native_segments[name])
            diff = estimated[1] - estimated[0]
            direction_cos = np.dot(diff, gt) / np.linalg.norm(diff) / np.linalg.norm(gt)
            controls[name] = {"head_distance_mm": float(np.linalg.norm(estimated[0] - segment[0]) * 1000),
                              "direction_error_deg": float(np.degrees(np.arccos(np.clip(direction_cos, -1, 1))))}
            angles[name] = float(np.arctan2(-gt[2], gt[0]))
            depths[name] = float(-gt[1] / max(np.hypot(gt[0], gt[2]), 1e-8))
        polar = replace(alignment, camera=camera, limb_angles=angles,
                        limb_depth_ratios=depths, wrist_cross_axes={})
        native_mesh = skin_vertices(neutral, rig["skin"], pose_transforms(rig, joints, alignment))
        oracle_mesh = skin_vertices(neutral, rig["skin"], pose_transforms(rig, joints, polar))
        (output / (folder.name + ".json")).write_text(json.dumps({
            "joint_anchor_proxies": controls,
            "ground_truth_joint_anchors_xyz_m": {name: points.tolist() for name, points in truth_bones.items()},
            "native_pose_calibrated_evaluation_iou": iou(native_mesh),
            "oracle_limb_directions_fixed_shape_iou": iou(oracle_mesh),
        }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("pilot", "upstream", "native", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
