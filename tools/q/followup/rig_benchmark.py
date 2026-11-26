"""Measure calibrated articulated MB-Lab fixtures against release alignment and pose."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask, metric_distance, sample_surface
from human3d.alignment import initialize_alignment
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import infer_support_plane, pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session
from human3d.vision import PoseLandmarker
from pose_camera import BONES


BASIS = np.array(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
MAPPING = {f"{mb}_{side}": f"{native}.{side}" for mb, native in BONES.items() for side in "LR"}
MAPPING |= {"pelvis": "pelvis.L", "spine01": "spine01", "spine02": "spine02", "head": "head"}


def degrees_rotation(matrix):
    return float(np.degrees(Rotation.from_matrix(matrix).magnitude()))


def degrees_direction(a, b):
    return float(np.degrees(np.arccos(np.clip(a @ b / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))


def rotational_delta(bone):
    rest = np.array(bone["rest_global"])[:3, :3]
    posed = np.array(bone["posed_global"])[:3, :3]
    return posed @ rest.T


def evaluate(folder, body, detector, work, reference, upstream, yaw):
    meta = json.loads((folder / "manifest.json").read_text())
    mesh_path = folder / "mesh.json"
    if sha256(mesh_path.read_bytes()).hexdigest() != meta["mesh_sha256"]:
        raise ValueError("Independent mesh hash mismatch")
    mesh = json.loads(mesh_path.read_text())
    image = next(row for row in meta["images"] if row["yaw"] == yaw)
    image_path = folder / image["file"]
    if sha256(image_path.read_bytes()).hexdigest() != image["sha256"]:
        raise ValueError("Independent image hash mismatch")
    front = Image.open(image_path).convert("RGBA")
    photo = Image.new("RGBA", front.size, (230, 230, 230, 255))
    photo.alpha_composite(front)
    path = work / f"{folder.name}-{yaw:g}.png"
    photo.convert("RGB").save(path)
    item = detector.detect(path, sha256(path.read_bytes()).hexdigest())
    result = dict(fixture=folder.name, identity=meta["identity"], condition=meta["pose"],
                  morphology_asymmetry=meta["morphology_asymmetry"], mesh_sha256=meta["mesh_sha256"],
                  input_yaw=yaw, image_sha256=image["sha256"], candidates=len(item.candidates),
                  review_reason=item.review_reason,
                  observed_landmarks=[i for i,p in enumerate(item.visible_pose(0)) if p.observed]
                                     if len(item.candidates)==1 else [])
    if len(item.masks) == 1 and item.masks[0] is not None:
        result["mask_iou"] = compare(load_mask(image_path), Image.open(BytesIO(item.masks[0])).convert("1"))["iou"]
    try:
        alignment = initialize_alignment(body, item, 0, refine=True)
    except ValueError as error:
        return result | {"alignment_error": str(error)}
    height = meta["height_m"]
    rig = body["rig"]
    points = np.asarray(deform_vertices(body, {}))
    faces = [tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"] if face["group"] == "body"]
    rest_y = points[np.unique(np.concatenate(faces)), 1]
    scale = height / np.ptp(rest_y)
    offset = np.array((0, 0, rest_y.min()))
    joints = rebind_joints(rig, points)
    transforms = pose_transforms(rig, joints, alignment)

    def world(values):
        return (np.asarray(values) @ BASIS.T - offset) * scale

    lifted = skin_vertices(points, rig["skin"], transforms)
    posed = world(lifted)
    body_indices = np.unique(np.concatenate(faces))
    support = infer_support_plane(rig,lifted,body_indices.tolist())
    source_mesh = np.asarray(mesh["vertices"])
    source_groups = json.loads((upstream/"data/vgroups"/f"{meta['source_family']}_vgroups_base.json").read_text())
    sole = {}
    for side in "LR":
        source_weights = {}
        for tag in (f"foot_{side}",f"toes_{side}"):
            for index,value in source_groups.get(tag,[]):
                source_weights[index] = source_weights.get(index,0)+value
        truth_idx = [i for i,value in source_weights.items() if value>=.8]
        pred_idx = [i for i in body_indices if sum(w for name,w in rig["skin"][i].items()
                    if name==f"foot.{side}" or name.startswith("toe") and name.endswith(f".{side}"))>=.8]
        sole[side] = {"reference_sole_floor_mm": float(1000*source_mesh[truth_idx,2].min()),
                      "native_sole_floor_mm": float(1000*posed[pred_idx,2].min())}
    truth_gap = abs(sole["L"]["reference_sole_floor_mm"]-sole["R"]["reference_sole_floor_mm"])
    estimated_gap = abs(sole["L"]["native_sole_floor_mm"]-sole["R"]["native_sole_floor_mm"])
    result["ground_diagnostics"] = dict(sole=sole, reference_interfoot_clearance_mm=truth_gap,
        native_interfoot_clearance_mm=estimated_gap,
        release_support_plane_mm=float(1000*(support-rest_y.min())*scale) if support is not None else None)
    model = posed @ BASIS * 10
    if yaw==0 and meta["pose"] in {"pelvis_spine_flex", "seated"}:
        (work / f"{folder.name}-comparison.json").write_text(json.dumps({
            "height": height, "meshes": {"Independent": mesh,
            "Native": {"vertices": posed.tolist(), "faces": faces}}}))
    samples = sample_surface(np.asarray(mesh["vertices"]), mesh["faces"], 12000, 2473)
    bands = {"head": (.86 * height, height + 1e-8), "torso_and_arms": (.54 * height, .86 * height),
             "lower_body": (-1e-8, .54 * height)}
    result["surface"] = metric_distance(samples, cKDTree(samples), sample_surface(posed, faces, 12000, 2473), bands)
    result["fixed_camera_iou"] = {image["yaw"]: compare(load_mask(folder / image["file"]),
        silhouette(model, faces, camera_for(image["yaw"], height), (384, 384)))["iou"] for image in meta["images"]}
    bones = {}
    for mb_name, native_name in MAPPING.items():
        if native_name not in transforms or mb_name not in meta["bones"]:
            continue
        record = meta["bones"][mb_name]
        native = rig["bones"][native_name]
        rot, trans = transforms[native_name]
        head, tail = (np.asarray(joints[native[k]]) for k in ("head", "tail"))
        a, b = world((rot @ head + trans, rot @ tail + trans))
        source_a, source_b = (np.asarray(record[k]) for k in ("head", "tail"))
        actual = rotational_delta(record)
        estimated = BASIS @ rot @ BASIS.T
        parent_mb = record["parent"]
        parent_native = native["parent"]
        actual_parent = rotational_delta(meta["bones"][parent_mb]) if parent_mb else np.eye(3)
        estimated_parent = BASIS @ transforms[parent_native][0] @ BASIS.T if parent_native else np.eye(3)
        raw_global_error = degrees_rotation(actual.T @ estimated)
        bones[mb_name] = dict(native=native_name, head_error_mm=float(1000 * np.linalg.norm(a - source_a)),
            direction_error_deg=degrees_direction(b - a, source_b - source_a),
            global_rotation_change_error_deg=raw_global_error,
            parent_relative_rotation_change_error_deg=degrees_rotation(
                (actual_parent.T @ actual).T @ (estimated_parent.T @ estimated)),
            native_length_change_mm=float(1000 * abs(np.linalg.norm(a-b) - scale * np.linalg.norm(head-tail))),
            reference_length_change_mm=float(1000 * abs(np.linalg.norm(source_a-source_b) -
                np.linalg.norm(np.diff([reference["bones"][mb_name][k] for k in ("head", "tail")], axis=0)))))
    result["bones"] = bones
    return result


def run(dataset, previous, work, output, yaw):
    work.mkdir(parents=True, exist_ok=True)
    detector = PoseLandmarker(previous / "assets/pose.task", segmentation=True)
    rows = []
    try:
        for identity in ("f_af01", "m_la01"):
            project = next((previous / "holdout-native").glob(f"*_{identity}_bend0-1")) / "project"
            body = load_project_body(Session(project).store)
            reference = json.loads((dataset / f"{identity}_neutral" / "manifest.json").read_text())
            for folder in sorted(dataset.glob(f"{identity}_*")):
                if not (folder / "manifest.json").exists():
                    continue
                rows.append(evaluate(folder, body, detector, work, reference, previous/"mblab",yaw))
                output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    finally:
        detector.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("dataset", "previous", "work", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--yaw",type=float,default=0)
    run(**vars(parser.parse_args()))
