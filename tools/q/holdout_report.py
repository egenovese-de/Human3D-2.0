"""Evaluate Q on frozen held-out identities and paired forearm bends."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

from benchmark_geometry import compare, silhouette
from circumference import circumference
from evaluate import camera_for, load_mask, metric_distance, sample_surface
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session


def evaluate(folder, native, pose_results, visuals):
    metadata = json.loads((folder / "manifest.json").read_text())
    mesh_path = folder / "mesh.json"
    assert sha256(mesh_path.read_bytes()).hexdigest() == metadata["mesh_sha256"]
    truth = json.loads(mesh_path.read_text())
    vertices = np.asarray(truth["vertices"])
    height = np.ptp(vertices[:, 2])
    truth_samples = sample_surface(vertices, truth['faces'], 12000, 2473)
    truth_tree = cKDTree(truth_samples)
    bands = {"head": (.86 * height, height + 1e-8),
             "torso_and_arms": (.54 * height, .86 * height), "lower_body": (-1e-8, .54 * height)}
    names = [1] if metadata["left_forearm_bend_deg"] else [1, 4]
    reports = {}
    for n in names:
        run_path = native / f"{folder.name}-{n}"
        result_path = run_path / "benchmark.json"
        if not result_path.exists():
            reports[str(n)] = {"failure": (native / f"{folder.name}-{n}.log").read_text()[-800:]}
            continue
        result = json.loads(result_path.read_text())
        if "fit" not in result:
            reports[str(n)] = {"failure": result.get("error", "fit_missing"), "detections": result["detections"]}
            continue
        session = Session(run_path / "project")
        body = load_project_body(session.store)
        faces = [tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"]
        base = np.asarray(deform_vertices(body, {}))
        rest_y = base[np.unique(np.concatenate(faces)), 1]
        factor = height / np.ptp(rest_y)
        fit = session.current_shared_fit()
        deformed = deform_vertices(body, fit.fit.controls)
        joints = rebind_joints(body["rig"], deformed)
        alignment = fit.alignments[result["photo_ids"]["rgb-yaw-0.png"]]
        posed = skin_vertices(deformed, body["rig"]["skin"],
                             pose_transforms(body["rig"], joints, alignment))

        def align(points):
            x, y, z = np.asarray(points).T
            return np.column_stack((x, -z, y - rest_y.min())) * factor

        def measure(points):
            world = align(points)
            samples = sample_surface(world, faces, 12000, 2473)
            distances = metric_distance(truth_samples, truth_tree, samples, bands)
            x, y, z = world.T
            model = np.column_stack((x, z, -y)) * 10
            ious = {}
            for row in metadata["images"]:
                if row["held_out"] or row["yaw"] == 0:
                    expected = load_mask(folder / row["file"])
                    predicted = silhouette(model, faces, camera_for(row["yaw"], height), expected.size)
                    ious[str(row["yaw"])] = compare(expected, predicted)["iou"]
            return distances | {"iou": ious}

        record = {"fit_iou": result["fit"]["fitted_iou"], "fit_seconds": result["fit_seconds"],
                  "bootstrap_digest": result["frozen_sha256"], "used_views": len(result["fit"]["per_view_iou"]),
                  "uv_fraction": result["observed_uv_fraction"], "posed": measure(posed)}
        if not metadata["left_forearm_bend_deg"]:
            record |= {"neutral": measure(deformed), "bootstrap": measure(base)}
            cut = height * .71
            record["chest_section_mm"] = {
                "truth": circumference(vertices, truth["faces"], cut),
                "native": circumference(align(deformed), faces, cut),
            }
        reports[str(n)] = record
        if n == 1 and metadata["left_forearm_bend_deg"] and metadata["identity"] in ("f_af01", "m_la01"):
            (visuals / f"{metadata['identity']}.json").write_text(json.dumps({
                "height": height, "meshes": {"ground-truth": truth,
                                            "native-posed": {"vertices": align(posed).tolist(), "faces": faces}}}))
    diagnostic = pose_results / f"{folder.name}.json"
    pose = json.loads(diagnostic.read_text()) if diagnostic.exists() else None
    if pose:
        pose.pop("ground_truth_joint_anchors_xyz_m", None)
    metadata.pop("joint_anchors", None)
    return {"fixture": metadata, "native": reports, "pose": pose}


def main(holdout, native, pose, visuals, output):
    visuals.mkdir(exist_ok=True)
    rows = [evaluate(folder, native, pose, visuals) for folder in sorted(holdout.iterdir())]
    output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    print(f"Measured {len(rows)} fixtures")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("holdout", "native", "pose", "visuals", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
