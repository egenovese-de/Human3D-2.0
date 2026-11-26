"""Audit independently defined joint centers and source-rig coordinate closure."""
import argparse
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image

from benchmark_geometry import compare, silhouette
from human3d.alignment import initialize_alignment
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session
from human3d.vision import PoseLandmarker

JOINTS = {
    11: "upperarm_L", 12: "upperarm_R", 13: "lowerarm_L", 14: "lowerarm_R",
    15: "hand_L", 16: "hand_R", 23: "thigh_L", 24: "thigh_R",
    25: "calf_L", 26: "calf_R", 27: "foot_L", 28: "foot_R",
}
IDENTITIES = ("f_af01", "m_la01")
BONES = ("pelvis", "spine01", "spine02", "spine03", "neck", "head", *JOINTS.values())


def project(camera, scale, size, world):
    camera_point = np.linalg.solve(camera, [*world, 1])
    normalized = np.array([.5 + camera_point[0] / scale, .5 - camera_point[1] / scale])
    recovered = camera @ np.array([(normalized[0] - .5) * scale, (.5 - normalized[1]) * scale,
                                   camera_point[2], 1])
    return normalized, normalized * size, float(np.linalg.norm(recovered[:3] - world))


def rig_audit(bones):
    rows = {}
    for name in BONES:
        bone = bones[name]
        rest, posed, basis = (np.asarray(bone[key]) for key in ("rest_global", "posed_global", "pose_basis"))
        parent = bones[bone["parent"]]
        rest_local = np.linalg.solve(parent["rest_global"], rest)
        posed_local = np.linalg.solve(parent["posed_global"], posed)
        rows[name] = {
            "parent": bone["parent"],
            "rest_local": rest_local.tolist(),
            "posed_local": posed_local.tolist(),
            "global_change": (posed @ np.linalg.inv(rest)).tolist(),
            "bone_basis": basis.tolist(),
            "parent_chain_max_abs_residual": float(np.max(np.abs(rest_local @ basis - posed_local))),
        }
    return rows


def run(dataset, previous, work, output):
    work.mkdir(parents=True, exist_ok=True)
    detector = PoseLandmarker(previous / "assets/pose.task", segmentation=True)
    rows = []
    try:
        for identity in IDENTITIES:
            path = next((previous / "holdout-native").glob(f"*_{identity}_bend0-1"))
            body = load_project_body(Session(path / "project").store)
            points = deform_vertices(body, {})
            rig = body["rig"]
            joints = rebind_joints(rig, points)
            faces = [tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"]
            for folder in sorted(dataset.glob(f"{identity}_*")):
                metadata = json.loads((folder / "manifest.json").read_text())
                if metadata["morphology_asymmetry"]:
                    continue
                bones = metadata["bones"]
                record = {"fixture": folder.name, "mesh_sha256": metadata["mesh_sha256"],
                          "rig": rig_audit(bones), "views": []}
                for view in metadata["images"]:
                    source = folder / view["file"]
                    assert sha256(source.read_bytes()).hexdigest() == view["sha256"]
                    image = Image.open(source).convert("RGBA")
                    mask = image.getchannel("A").point(lambda value: 255 if value >= 128 else 0).convert("1")
                    photo = Image.new("RGBA", image.size, (230, 230, 230, 255))
                    photo.alpha_composite(image)
                    rendered = work / f"{folder.name}-{view['file']}"
                    photo.convert("RGB").save(rendered)
                    detection = detector.detect(rendered, sha256(rendered.read_bytes()).hexdigest())
                    result = {"yaw_deg": view["yaw"], "render_sha256": view["sha256"],
                              "review_reason": detection.review_reason, "anchors": []}
                    camera = np.asarray(view["camera_to_world"])
                    native = detection.candidates[0] if len(detection.candidates) == 1 else None
                    proxy = list(native) if native is not None else []
                    for index, bone in JOINTS.items():
                        world = bones[bone]["head"]
                        normalized, pixels, residual = project(camera, metadata["camera_scale_m"],
                                                               np.asarray(image.size), world)
                        in_frame = bool(np.all((normalized >= 0) & (normalized < 1)))
                        observed = native is not None and native[index].observed
                        error = None
                        if observed and in_frame:
                            point = native[index]
                            error = float(np.linalg.norm(pixels - np.asarray(image.size) * [point.x, point.y]))
                            proxy[index] = replace(point, x=float(normalized[0]), y=float(normalized[1]))
                        result["anchors"].append({"index": index, "bone": bone, "xyz_m": world,
                                                  "xy_normalized": normalized.tolist(), "xy_px": pixels.tolist(),
                                                  "in_frame": in_frame, "detector_observed": observed,
                                                  "occlusion": None, "semantic_uncertainty_mm": None,
                                                  "projection_roundtrip_m": residual,
                                                  "detector_to_joint_proxy_px": error})
                    result["silhouette_iou"] = {}
                    if native is not None:
                        for label, evidence in (("native", detection),
                                                ("joint_proxy_xy", replace(detection, candidates=(tuple(proxy),)))):
                            try:
                                alignment = initialize_alignment(body, evidence, 0, refine=True)
                                posed = skin_vertices(points, rig["skin"], pose_transforms(rig, joints, alignment))
                                value = compare(mask, silhouette(posed, faces, alignment.camera, image.size))["iou"]
                            except ValueError as error:
                                value = {"error": str(error)}
                            result["silhouette_iou"][label] = value
                    record["views"].append(result)
                rows.append(record)
                output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    finally:
        detector.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for argument in ("dataset", "previous", "work", "output"):
        parser.add_argument(argument, type=Path)
    run(**vars(parser.parse_args()))
