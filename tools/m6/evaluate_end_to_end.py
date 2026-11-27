"""Score a completed native replay against fixed independent Q evaluation views."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask, metric_distance, sample_surface
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session


def score(folder, run):
    report_path = run / "benchmark.json"
    report = json.loads(report_path.read_text())
    meta = json.loads((folder / "manifest.json").read_text())
    mesh_bytes = (folder / "mesh.json").read_bytes()
    if sha256(mesh_bytes).hexdigest() != meta["mesh_sha256"]:
        raise ValueError("invalid Q fixture mesh digest")
    truth = json.loads(mesh_bytes)
    height = np.ptp(np.asarray(truth["vertices"])[:, 2])
    session = Session(run / "project")
    fit = session.current_shared_fit()
    body = load_project_body(session.store)
    rig = body["rig"]
    faces = [tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"] if face["group"] == "body"]
    base = np.asarray(deform_vertices(body, {}))
    y_bounds = base[np.unique(np.concatenate(faces)), 1]
    scale = height / np.ptp(y_bounds)
    photo_id = report["photo_ids"]["rgb-yaw-0.png"]
    alignment = fit.alignments[photo_id]
    vertices = deform_vertices(body, fit.fit.controls)
    joints = rebind_joints(rig, vertices)
    posed = skin_vertices(vertices, rig["skin"], pose_transforms(rig, joints, alignment))
    x, y, z = np.asarray(posed).T
    world = np.column_stack((x, -z, y - y_bounds.min())) * scale
    canonical = np.column_stack((world[:, 0], world[:, 2], -world[:, 1])) * 10.
    overlap = {}
    for frame in meta["images"]:
        if frame["held_out"]:
            yaw = frame["yaw"]
            image = folder / frame["file"]
            if sha256(image.read_bytes()).hexdigest() != frame["sha256"]:
                raise ValueError("invalid held-out image digest")
            mask = load_mask(image)
            overlap[yaw] = compare(mask, silhouette(canonical, faces, camera_for(yaw, height), mask.size))["iou"]
    reference = sample_surface(np.asarray(truth["vertices"]), truth["faces"], 12000, 2473)
    surface = metric_distance(reference, cKDTree(reference), sample_surface(world, faces, 12000, 2473), {})
    usd = run / "native.usdz"
    return dict(case=folder.name, fixture_sha256=meta["mesh_sha256"],
                project_fit_digest=session.store.load().shared_fit_digest, held_out_iou=overlap,
                posed_surface_mm=surface, observed_uv_fraction=report["observed_uv_fraction"],
                native_usdz_bytes=usd.stat().st_size, native_usdz_sha256=sha256(usd.read_bytes()).hexdigest(),
                garment=report.get("garment"), benchmark=report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fixture_root", "run_root", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    rows = [score(args.fixture_root / run.name, run)
            for run in sorted(args.run_root.iterdir()) if (run / "benchmark.json").is_file()]
    args.output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
