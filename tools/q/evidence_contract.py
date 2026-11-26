"""Probe ground-truth yaw and partial joint evidence through supported release contracts."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask
from human3d.alignment import initialize_alignment
from human3d.anatomical_evidence import AnatomicalEvidence, yaw_conflicts
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session
from human3d.vision import estimate_world_yaw


ANCHORS = {
    11: "upperarm01.L", 12: "upperarm01.R", 13: "lowerarm01.L", 14: "lowerarm01.R",
    15: "wrist.L", 16: "wrist.R", 23: "upperleg01.L", 24: "upperleg01.R",
    25: "lowerleg01.L", 26: "lowerleg01.R", 27: "foot.L", 28: "foot.R",
}


def main(pilot, native, pose, output):
    output.mkdir(exist_ok=True)
    for path in sorted(pose.glob("*.json")):
        name = path.stem
        truth = json.loads(path.read_text())["ground_truth_joint_anchors_xyz_m"]
        folder = pilot / name
        references = {row["sha256"]: row for row in json.loads((folder / "native-4.json").read_text())["images"]}
        session = Session(native / (name + "-4") / "project")
        body = load_project_body(session.store)
        model = deform_vertices(body, {})
        rig = body["rig"]
        joints = rebind_joints(rig, model)
        faces = [tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"]
        mesh = json.loads((folder / "mesh.json").read_text())
        height = np.ptp(np.asarray(mesh["vertices"])[:, 2])
        out = []
        for view in session.shared_evidence().views:
            detection = view.detection
            index = view.candidate
            row = references[view.ref.photo_digest]
            width, height_px = detection.image_size
            cam = camera_for(row["yaw"], height)
            yaw = (cam.yaw_degrees + 180) % 360 - 180
            provider = AnatomicalEvidence(detection.photo_digest, "blender-calibration", "orthographic-v1",
                                          index, yaw=yaw, yaw_confidence=1.0)
            original = detection.candidates[index]
            worlds = detection.world_landmarks[index] if len(detection.world_landmarks) > index else ()
            estimated_yaw = estimate_world_yaw(original, worlds)
            mask = load_mask(folder / row["truth_mask"])
            partial = list(original)
            localization = []
            for key, bone in ANCHORS.items():
                x, y, z = truth[bone][0]
                point = cam.project((10 * x, 10 * z, -10 * y))
                prior = original[key]
                if prior.observed:
                    localization.append(abs(point - complex(prior.x * width, prior.y * height_px)))
                partial[key] = replace(prior, x=point.real / width, y=point.imag / height_px)
            candidates = tuple(tuple(partial) if i == index else item for i, item in enumerate(detection.candidates))
            checks = {"native": detection, "provider_yaw": replace(detection, anatomical=provider),
                      "partial_2d_joint_proxy": replace(detection, candidates=candidates)}
            results = {}
            for label, item in checks.items():
                try:
                    result = initialize_alignment(body, item, index, refine=True)
                except ValueError as exc:
                    results[label] = {"reason": str(exc)}
                    continue
                posed = skin_vertices(model, rig["skin"], pose_transforms(rig, joints, result))
                projected = silhouette(posed, faces, result.camera, mask.size)
                if np.asarray(projected).any():
                    iou = compare(mask, projected)["iou"]
                else:
                    iou = 0.0
                results[label] = {"independent_silhouette_iou": iou,
                                  "yaw_estimate": result.camera.yaw_degrees,
                                  "yaw_error_abs_deg": abs((result.camera.yaw_degrees - yaw + 180) % 360 - 180)}
            out.append({"yaw_truth": yaw, "detector_yaw": estimated_yaw,
                        "yaw_contract_conflict": yaw_conflicts(provider, estimated_yaw),
                        "observed_joint_proxy_rmse_px": float(np.sqrt(np.mean(np.square(localization)))) if localization else None,
                        "observed_joint_proxy_count": len(localization), "alignment": results})
        (output / (name + ".json")).write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("pilot", "native", "pose", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
