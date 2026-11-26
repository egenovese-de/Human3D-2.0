"""Compare bounded sampled surface objectives under a frozen rest-pose registration."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.spatial import cKDTree

from evaluate import metric_distance, sample_surface
from human3d.alignment import Alignment
from human3d.fitting import _optimize
from human3d.frozen_body import deform_vertices, load_project_body, morph_controls
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.proportions import length_controls
from human3d.regional_morphs import regional_controls
from human3d.session import Session
from pose_camera import BONES
from evaluate import camera_for


def examine(folder, project):
    meta = json.loads((folder / "manifest.json").read_text())
    mesh_path = folder / "mesh.json"
    if sha256(mesh_path.read_bytes()).hexdigest() != meta["mesh_sha256"]:
        raise ValueError("Frozen mesh hash mismatch")
    mesh = json.loads(mesh_path.read_text())
    truth = np.asarray(mesh["vertices"])
    height = np.ptp(truth[:, 2])
    session = Session(project)
    fit = session.current_shared_fit()
    body = load_project_body(session.store)
    base = np.asarray(deform_vertices(body, {}))
    faces = [tuple(index for index, _ in face["corners"]) for face in body["mesh"]["faces"]
             if face["group"] == "body"]
    rest_y = base[np.unique(np.concatenate(faces)), 1]
    factor = height / np.ptp(rest_y)
    camera = camera_for(0, height)
    angles, depths = {}, {}
    for part, native in BONES.items():
        for side in "LR":
            x, y, z = np.diff(meta["joint_anchors"][f"{part}_{side}"], axis=0)[0]
            angles[f"{native}.{side}"] = float(np.arctan2(-z, x))
            depths[f"{native}.{side}"] = float(-y / max(np.hypot(x, z), 1e-8))
    rig = body["rig"]
    transforms = pose_transforms(rig, rebind_joints(rig, base), Alignment(camera, 0, angles, depths))

    def surface(points, count, seed, registered):
        if registered:
            points = skin_vertices(points, rig["skin"], transforms)
        x, y, z = np.asarray(points).T
        world = np.column_stack((x, -z, y - rest_y.min())) * factor
        return sample_surface(world, faces, count, seed)

    validation = sample_surface(truth, mesh["faces"], 12000, 2474)
    tree = cKDTree(validation)
    train = sample_surface(truth, mesh["faces"], 2200, 2473)
    train_tree = cKDTree(train)
    bands = {"head": (.86 * height, height + 1e-8), "torso_and_arms": (.54 * height, .86 * height),
             "lower_body": (-1e-8, .54 * height)}
    supported = (*morph_controls(body), *length_controls(body), *regional_controls(body))

    def measure(controls, registered):
        prediction = surface(deform_vertices(body, controls), 12000, 2474, registered)
        return metric_distance(validation, tree, prediction, bands)

    def run(label, seed, schedule, symmetric):
        history = []
        elapsed = perf_counter()

        def objective(points):
            prediction = surface(points, 2200, 2473, True)
            forward = train_tree.query(prediction)[0].mean()
            reverse = cKDTree(prediction).query(train)[0].mean() if symmetric else forward
            return {"surface": -50 * (forward + reverse)}

        controls = dict(seed)
        for step in schedule:
            controls, scores = _optimize(body, objective, controls, supported, (step,))
            history.append({"step": step, "surface_objective_mm": -10 * scores["surface"]})
        return {"condition": label, "controls": controls, "convergence": history,
                "seconds": perf_counter() - elapsed, **measure(controls, True)}

    results = [
        {"condition": "bootstrap", **measure({}, False)},
        {"condition": "stance_registered_bootstrap", **measure({}, True)},
        {"condition": "native_four_unregistered", **measure(fit.fit.controls, False)},
        {"condition": "native_four_registered", **measure(fit.fit.controls, True)},
        run("registered_one_sided", {}, (.25, .125, .0625, .03125), False),
        run("registered_symmetric", {}, (.25, .125, .0625, .03125), True),
        run("registered_symmetric_native_seed", fit.fit.controls, (.125, .0625, .03125, .015625), True),
    ]
    return {"identity": meta["identity"], "fixture_sha256": meta["mesh_sha256"], "conditions": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("previous", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = json.loads(args.output.read_text()) if args.output.exists() else []
    completed = {row["identity"] for row in rows}
    for folder in sorted((args.previous / "holdout").glob("*_bend0")):
        identity = json.loads((folder / "manifest.json").read_text())["identity"]
        if identity in completed:
            continue
        rows.append(examine(folder, args.previous / "holdout-native" / (folder.name + "-4") / "project"))
        args.output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
