"""Separate native geometry and texture reference sets on persisted native fits."""
import argparse
import json
from pathlib import Path
import shutil
from statistics import mean
from time import perf_counter

import numpy as np
from scipy.spatial import cKDTree

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask, metric_distance, sample_surface
from human3d.appearance import prepare_view
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.originals import OriginalStore
from human3d.session import Session
from human3d.texture_bake import bake_atlas


def run(previous, work, output, identity, treatment):
    results = []
    fixture = next((previous / "holdout").glob(f"*_{identity}_bend0"))
    meta = json.loads((fixture / "manifest.json").read_text())
    mesh = json.loads((fixture / "mesh.json").read_text())
    vertices = np.asarray(mesh["vertices"])
    height = np.ptp(vertices[:, 2])
    points = sample_surface(vertices, mesh["faces"], 12000, 2473)
    tree = cKDTree(points)
    held = {v["yaw"]: load_mask(fixture / v["file"]) for v in meta["images"] if v["held_out"]}
    mixed = previous / "holdout-mixed" / f"{identity}-{treatment}"
    report = json.loads((mixed / "benchmark.json").read_text())
    target = report["photo_ids"]["rgb-yaw-0.png"]
    alternate = report["photo_ids"][f"{treatment}-yaw-90.png"]
    filtered = work / f"{identity}-{treatment}"
    shutil.copytree(mixed / "project", filtered)
    filtered_session = Session(filtered)
    filtered_session.include_reference(alternate, False)
    start = perf_counter()
    filtered_session.fit_shared()
    refit_seconds = perf_counter() - start

    geometry = {}
    for label, session in (("omit_profile", filtered_session), ("all_references", Session(mixed / "project"))):
        current = session.current_shared_fit()
        body = load_project_body(session.store)
        faces = [tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"] if face["group"] == "body"]
        base = np.asarray(deform_vertices(body, {}))
        vertical = base[np.unique(np.concatenate(faces)), 1]
        neutral = np.asarray(deform_vertices(body, current.fit.controls))
        neutral[:, 1] -= vertical.min()
        neutral *= height / np.ptp(vertical)
        x, y, z = neutral.T
        distance = metric_distance(points, tree, sample_surface(
            np.column_stack((x, -z, y)), faces, 12000, 2473), {})["symmetric_mean_mm"]
        iou = mean(compare(mask, silhouette(neutral * 10, faces, camera_for(yaw, height), mask.size))["iou"]
                   for yaw, mask in held.items())
        geometry[label] = (current.fit.controls, body, {"neutral_surface_mm": distance,
                                                       "held_out_iou": iou,
                                                       "fit_seconds": refit_seconds if label == "omit_profile" else report["fit_seconds"],
                                                       "geometry_views": len(current.scores)})

    session = Session(mixed / "project")
    current = session.current_shared_fit()
    originals = OriginalStore(session.store.directory)
    inputs = {view.ref.photo_id: (
        prepare_view(originals, view, current.alignments[view.ref.photo_id]), view.detection.image_size)
        for view in session.shared_evidence().views if view.ref.photo_id in current.alignments}
    for name, (controls, body, scores) in geometry.items():
        for include in (True, False):
            selected = {key: value for key, value in inputs.items() if include or key != alternate}
            start = perf_counter()
            atlas = bake_atlas(body, controls, selected, target, size=256)
            results.append({"identity": identity, "treatment": treatment, "geometry_set": name,
                            "appearance_set": "all" if include else "omit_profile",
                            "texture_views": len(selected), "observed_uv_fraction": atlas.observed_fraction,
                            "bake_seconds": perf_counter() - start, "texture_rgb_mae": None, **scores})
    output.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("identity", choices=("f_af01", "m_la01"))
    parser.add_argument("treatment", choices=("different-pose", "contradictory"))
    run(**vars(parser.parse_args()))
