"""Measure M6 neutral residuals at the fixed Q stance registration."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.spatial import cKDTree

from audit_bind_frames import revision
from benchmark_geometry import compare, silhouette
from circumference import circumference
from evaluate import camera_for, load_mask, metric_distance, sample_surface
from pose_camera import BONES
from human3d.alignment import Alignment
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session


def examine(folder, project):
    manifest = json.loads((folder / "manifest.json").read_text())
    mesh_bytes = (folder / "mesh.json").read_bytes()
    if sha256(mesh_bytes).hexdigest() != manifest["mesh_sha256"]:
        raise ValueError("mesh hash mismatch")
    truth = json.loads(mesh_bytes)
    height = np.ptp(np.asarray(truth["vertices"])[:, 2])
    session = Session(project)
    fit = session.current_shared_fit()
    body = load_project_body(session.store)
    rig = body["rig"]
    base = np.asarray(deform_vertices(body, {}))
    faces = [tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"] if face["group"] == "body"]
    elevations = base[np.unique(np.concatenate(faces)), 1]
    scale = height / np.ptp(elevations)
    angles, depths = {}, {}
    for upstream, native in BONES.items():
        for side in "LR":
            x, y, z = np.diff(manifest["joint_anchors"][f"{upstream}_{side}"], axis=0)[0]
            name = f"{native}.{side}"
            angles[name] = float(np.arctan2(-z, x))
            depths[name] = float(-y / max(np.hypot(x, z), 1e-8))
    alignment = Alignment(camera_for(0, height), 0., angles, depths)
    transforms = pose_transforms(rig, rebind_joints(rig, base), alignment)
    truth_samples = sample_surface(np.asarray(truth["vertices"]), truth["faces"], 12000, 2474)
    tree = cKDTree(truth_samples)
    bands = {"head": (.86 * height, height + 1e-8), "torso_and_arms": (.54 * height, .86 * height),
             "lower_body": (-1e-8, .54 * height)}
    fractions = {"hip": .52, "waist": .61, "chest": .71}
    truth_sections = {key: circumference(truth["vertices"], truth["faces"], height * level)
                      for key, level in fractions.items()}
    held_out = {row["yaw"]: load_mask(folder / row["file"]) for row in manifest["images"] if row["held_out"]}
    rows = []
    for name, controls in (("registered_bootstrap", {}), ("registered_native_four", fit.fit.controls)):
        start = perf_counter()
        coords = skin_vertices(deform_vertices(body, controls), rig["skin"], transforms)
        x, y, z = coords.T
        world = np.column_stack((x, -z, y - elevations.min())) * scale
        model = np.column_stack((world[:, 0], world[:, 2], -world[:, 1])) * 10.
        sections = {key: circumference(world, faces, height * level) for key, level in fractions.items()}
        errors = {key: value - truth_sections[key] if value is not None and truth_sections[key] is not None else None
                  for key, value in sections.items()}
        scores = {yaw: compare(mask, silhouette(model, faces, camera_for(yaw, height), mask.size))["iou"]
                  for yaw, mask in held_out.items()}
        metrics = metric_distance(truth_samples, tree, sample_surface(world, faces, 12000, 2474), bands)
        rows.append(dict(condition=name, sections_mm=sections, section_error_mm=errors, held_out_iou=scores,
                         saturated_controls=[key for key, value in controls.items() if abs(value) == .5],
                         evaluation_seconds=perf_counter() - start, **metrics))
    return dict(identity=manifest["identity"], fixture_sha256=manifest["mesh_sha256"],
                truth_sections_mm=truth_sections, conditions=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "previous", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    rows = [examine(folder, args.previous / "holdout-native" / (folder.name + "-4") / "project")
            for folder in sorted((args.previous / "holdout").glob("*_bend0"))]
    report = dict(candidate_sha=revision(args.candidate), lab_sha=revision(Path(__file__).parents[2]), cases=rows)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
