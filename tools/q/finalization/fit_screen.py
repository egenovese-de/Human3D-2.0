"""Screen every articulated holdout identity with native single- and four-view fits."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

import numpy as np
from scipy.spatial import cKDTree

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask, metric_distance, sample_surface
from fit_acceptance import evaluate
from human3d.bootstrap import freeze_project
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session
from human3d.vision import PoseLandmarker


def run(previous, acceptance, work, output):
    rule = json.loads(acceptance.read_text())["rule"]
    detector = PoseLandmarker(previous / "assets/pose.task", segmentation=True)
    rows = []
    try:
        for fixture in sorted((previous / "holdout").glob("*_bend32")):
            meta = json.loads((fixture / "manifest.json").read_text())
            posed_mesh = json.loads((fixture / "mesh.json").read_text())
            neutral_mesh = json.loads((fixture.with_name(fixture.name.replace("bend32", "bend0")) /
                                       "mesh.json").read_text())
            truth = np.asarray(neutral_mesh["vertices"])
            height = np.ptp(np.asarray(posed_mesh["vertices"])[:, 2])
            samples = sample_surface(truth, neutral_mesh["faces"], 12000, 2473)
            tree = cKDTree(samples)
            held = {view["yaw"]: load_mask(fixture / view["file"]) for view in meta["images"] if view["held_out"]}
            for angles in ((0,), (0, 90, 180, 270)):
                row = {"fixture": meta["identity"], "split": "evaluation", "views": len(angles),
                       "pose": "bend32", "training_yaws": angles, "held_out_yaws": list(held),
                       "posed_mesh_sha256": meta["mesh_sha256"], "input_hashes": {}}
                try:
                    session = Session(work / f"{meta['identity']}-{len(angles)}", create=True)
                    paths = [fixture / f"rgb-yaw-{yaw:g}.png" for yaw in angles]
                    row["input_hashes"] = {path.name: sha256(path.read_bytes()).hexdigest() for path in paths}
                    session.ingest(paths)
                    photos = {photo.digest: photo.id for photo in session.store.load().photos.photos}
                    target = photos[row["input_hashes"][paths[0].name]]
                    for digest in row["input_hashes"].values():
                        session.detect_photo(photos[digest], detector)
                    session.select_target(target)
                    freeze_project(session.store, previous / "assets")
                    start = perf_counter()
                    shared = session.fit_shared()
                    row["elapsed_fit_seconds"] = perf_counter() - start
                    alignment = shared.alignments[target]
                    body = load_project_body(session.store)
                    rig = body["rig"]
                    faces = [tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"] if face["group"] == "body"]
                    base = np.asarray(deform_vertices(body, {}))
                    elevations = base[np.unique(np.concatenate(faces)), 1]
                    factor = height / np.ptp(elevations)

                    def world(points):
                        x, y, z = np.asarray(points).T
                        return np.column_stack((x, -z, y - elevations.min())) * factor

                    for label, controls in (("bootstrap", {}), ("fitted", shared.fit.controls)):
                        points = deform_vertices(body, controls)
                        joints = rebind_joints(rig, points)
                        posed = skin_vertices(points, rig["skin"], pose_transforms(rig, joints, alignment))
                        x, y, z = world(posed).T
                        model = np.column_stack((x, z, -y)) * 10
                        scores = {yaw: compare(mask, silhouette(model, faces, camera_for(yaw, height), mask.size))["iou"]
                                  for yaw, mask in held.items()}
                        row[f"{label}_held_out_by_yaw"] = scores
                        row[f"{label}_iou"] = mean(scores.values())
                        row[f"{label}_neutral_surface_mm"] = metric_distance(
                            samples, tree, sample_surface(world(points), faces, 12000, 2473), {})["symmetric_mean_mm"]
                    row.update(training_gain=shared.fit.fitted_iou - shared.fit.bootstrap_iou,
                               min_training_view_iou=min(shared.scores.values()),
                               saturation=sum(abs(v) == .5 for v in shared.fit.controls.values()),
                               control_l2=sum(v*v for v in shared.fit.controls.values()) ** .5,
                               accepted_training_views=len(shared.scores))
                    row = evaluate([row], rule)[0]
                    label = "fitted" if row["accepted"] else "bootstrap"
                    row["selected_neutral_surface_mm"] = row[f"{label}_neutral_surface_mm"]
                except (ValueError, RuntimeError) as error:
                    row["error"] = str(error)
                rows.append(row)
                output.write_text(json.dumps({"frozen_rule": rule, "screening": rows}, indent=2, allow_nan=False) + "\n")
    finally:
        detector.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("previous", "acceptance", "work", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
