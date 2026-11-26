"""Lab-only camera by pose by shape factorial on the four forearm-bend fixtures."""
import argparse
from dataclasses import replace
from itertools import product
from io import BytesIO
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.spatial import cKDTree

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask, metric_distance, sample_surface
from human3d.fitting import _optimize, _scorer
from human3d.frozen_body import deform_vertices, load_project_body, morph_controls
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.proportions import length_controls
from human3d.mask_review import SubjectMask
from human3d.regional_morphs import regional_controls
from human3d.session import Session
BONES = {"upperarm": "upperarm01", "lowerarm": "lowerarm01", "thigh": "upperleg01",
         "calf": "lowerleg01", "hand": "wrist", "foot": "foot"}


def examine(folder, project, *, truth_mask=False):
    meta = json.loads((folder / "manifest.json").read_text())
    mesh = json.loads((folder / "mesh.json").read_text())
    session = Session(project)
    current = session.current_shared_fit()
    view = session.shared_evidence().views[0]
    native = current.alignments[view.ref.photo_id]
    body = load_project_body(session.store)
    rig = body["rig"]
    faces = [tuple(index for index, _ in face["corners"]) for face in body["mesh"]["faces"]
             if face["group"] == "body"]
    base = np.asarray(deform_vertices(body, {}))
    model_y = base[np.unique(np.concatenate(faces)), 1]
    truth = np.asarray(mesh["vertices"])
    height = np.ptp(truth[:, 2])
    factor = height / np.ptp(model_y)
    canonical_camera = camera_for(0, height)
    calibrated = replace(canonical_camera, similarity=canonical_camera.similarity * 10 * factor,
                         origin=canonical_camera.origin + canonical_camera.similarity * complex(0, 10 * factor * model_y.min()))
    samples = sample_surface(truth, mesh["faces"], 12000, 2473)
    tree = cKDTree(samples)
    bands = {"head": (.86 * height, height + 1e-8), "torso_and_arms": (.54 * height, .86 * height),
             "lower_body": (-1e-8, .54 * height)}
    masks = {row["yaw"]: load_mask(folder / row["file"]) for row in meta["images"]
             if row["held_out"] or row["yaw"] == 0}
    supported = (*morph_controls(body), *length_controls(body), *regional_controls(body))
    results = []
    conditions = product(("native", "calibrated"), ("native", "direction_proxy"))
    fit_mask = view.mask
    if truth_mask:
        buffer = BytesIO()
        masks[0].save(buffer, format="PNG")
        fit_mask = SubjectMask(view.ref.photo_digest, view.candidate, buffer.getvalue())
        conditions = (("calibrated", "native"), ("calibrated", "direction_proxy"))
    for camera_kind, pose_kind in conditions:
        camera = native.camera if camera_kind == "native" else calibrated
        alignment = replace(native, camera=camera)
        if pose_kind == "direction_proxy":
            angles, depths = {}, {}
            for part, native_part in BONES.items():
                for side in "LR":
                    segment = np.asarray(meta["joint_anchors"][f"{part}_{side}"])
                    x, y, z = np.diff(segment, axis=0)[0]
                    model = (x, z, -y)
                    direction = camera.project(model) - camera.origin
                    yaw = np.radians(camera.yaw_degrees)
                    depth = -x * np.sin(yaw) - y * np.cos(yaw)
                    angles[f"{native_part}.{side}"] = float(np.angle(direction))
                    depths[f"{native_part}.{side}"] = float(depth / max(abs(direction / camera.similarity), 1e-8))
            alignment = replace(alignment, limb_angles=angles, limb_depth_ratios=depths, wrist_cross_axes={})
        score = _scorer(body, {0: fit_mask}, {0: alignment}, base)
        start = perf_counter()
        controls, _ = _optimize(body, score, {}, supported, (.25, .125))
        duration = perf_counter() - start
        for shape_kind, values in (("bootstrap", {}), ("fitted", controls)):
            points = deform_vertices(body, values)
            joints = rebind_joints(rig, points)
            posed = skin_vertices(points, rig["skin"], pose_transforms(rig, joints, alignment))
            x, y, z = np.asarray(posed).T
            world = np.column_stack((x, -z, y - model_y.min())) * factor
            model = np.column_stack((world[:, 0], world[:, 2], -world[:, 1])) * 10
            iou = {yaw: compare(mask, silhouette(model, faces, camera_for(yaw, height), mask.size))["iou"]
                   for yaw, mask in masks.items()}
            metric = metric_distance(samples, tree, sample_surface(world, faces, 12000, 2473), bands)
            results.append(dict(camera=camera_kind, pose=pose_kind, shape=shape_kind, fixed_camera_iou=iou,
                                training_mask_iou=score(points)[0], fit_seconds=duration if shape_kind=="fitted" else None,
                                controls=values, **metric))
    return {"identity": meta["identity"], "fixture_sha256": meta["mesh_sha256"], "cells": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--truth-mask", action="store_true")
    args = parser.parse_args()
    rows = json.loads(args.output.read_text()) if args.output.exists() else []
    completed = {row["identity"] for row in rows}
    for folder in sorted((args.previous / "holdout").glob("*_bend32")):
        identity = json.loads((folder / "manifest.json").read_text())["identity"]
        if identity in completed:
            continue
        rows.append(examine(folder, args.previous / "holdout-native" / (folder.name + "-1") / "project", truth_mask=args.truth_mask))
        args.output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
