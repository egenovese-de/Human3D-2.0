"""Measure independent pilot geometry and held-out silhouettes using release routines."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import resource
from time import perf_counter

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from benchmark_geometry import compare, silhouette
from human3d.alignment import Alignment, Camera
from human3d.proportions import length_controls
from human3d.bootstrap import freeze_neutral
from human3d.fitting import _optimize, _scorer
from human3d.frozen_body import deform_vertices, load_frozen_body, morph_controls
from human3d.mask_review import SubjectMask
from human3d.regional_morphs import regional_controls


CONFIGURATIONS = {
    "front": [0], "front-profile": [0, 90], "front-rear": [0, 180],
    "three": [0, 90, 180], "four": [0, 90, 180, 270], "eight": list(range(0, 360, 45)),
}


def load_mask(path):
    return Image.open(path).getchannel("A").point(lambda x: 255 if x >= 128 else 0).convert("1")


def camera_for(yaw, height):
    scale = 384 / 2.16
    return Camera(-yaw, scale / 10, complex(192, 192 + scale * height / 2), 1)


def sample_surface(vertices, faces, count, seed):
    triangles = np.asarray([(f[0], f[i], f[i + 1]) for f in faces for i in range(1, len(f) - 1)])
    a, b, c = vertices[triangles].transpose(1, 0, 2)
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1)
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(area), count, p=area / area.sum())
    u, v = rng.random((2, count))
    reflect = u + v > 1
    u[reflect], v[reflect] = 1 - u[reflect], 1 - v[reflect]
    return a[indices] + (b - a)[indices] * u[:, None] + (c - a)[indices] * v[:, None]


def metric_distance(truth, truth_tree, prediction, regions):
    pred_to_truth = truth_tree.query(prediction)[0]
    truth_to_pred = cKDTree(prediction).query(truth)[0]
    distances = np.concatenate((pred_to_truth, truth_to_pred)) * 1000
    return {
        "symmetric_mean_mm": float(distances.mean()),
        "sampled_chamfer_mm2": float(np.mean(distances ** 2)),
        "p95_mm": float(np.quantile(distances, .95)),
        "truth_to_prediction_region_mean_mm": {
            label: float(truth_to_pred[(truth[:, 2] >= low) & (truth[:, 2] < high)].mean() * 1000)
            for label, (low, high) in regions.items()},
    }


def main(args):
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    key = freeze_neutral(args.assets, output / "frozen", with_morphs=True)
    body = load_frozen_body(output / "frozen" / f"{key}.json")
    faces = [tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"]
    vertices = np.asarray(deform_vertices(body, {}))
    valid = np.unique(np.concatenate(faces))
    floor = vertices[valid, 1].min()
    neutral_height = np.ptp(vertices[valid, 1]) / 10
    controls = (*morph_controls(body), *length_controls(body), *regional_controls(body))
    for manifest in sorted(args.pilot.glob("*/manifest.json")):
        report_path = output / (manifest.parent.name + ".json")
        prior = json.loads(report_path.read_text()) if report_path.exists() else None
        if prior is not None and not args.metrics_only:
            continue
        if prior is None and args.metrics_only:
            continue
        started = perf_counter()
        meta = json.loads(manifest.read_text())
        mesh_path = manifest.parent / "mesh.json"
        assert sha256(mesh_path.read_bytes()).hexdigest() == meta["mesh_sha256"]
        mesh = json.loads(mesh_path.read_text())
        gt = np.asarray(mesh["vertices"])
        height = np.ptp(gt[:, 2])
        scale = height / neutral_height
        samples = sample_surface(gt, mesh["faces"], 12000, 2473)
        truth_tree = cKDTree(samples)
        bands = {"head": (.86 * height, height + 1e-8), "torso_and_arms": (.54 * height, .86 * height),
                 "lower_body": (-1e-8, .54 * height)}

        def aligned(deformed):
            x, y, z = np.asarray(deformed).T
            return np.column_stack((x, -z, y - floor)) * scale / 10

        def surface(deformed, count=12000):
            return sample_surface(aligned(deformed), faces, count, 2473)

        def objective(deformed):
            return {"surface": -float(truth_tree.query(surface(deformed, 2000))[0].mean() * 100)}

        def assess(deformed):
            world = aligned(deformed)
            # Convert the aligned mesh back to the release Camera's decimeter coordinates.
            model = np.column_stack((world[:, 0], world[:, 2], -world[:, 1])) * 10
            result = metric_distance(samples, truth_tree, surface(deformed), bands)
            result["held_out"] = {}
            for row in meta["images"]:
                if not row["held_out"]:
                    continue
                yaw = row["yaw"]
                expected = load_mask(manifest.parent / row["file"])
                prediction = silhouette(model, faces, camera_for(yaw, height), expected.size)
                result["held_out"][str(yaw)] = compare(expected, prediction)
            return result

        masks, cameras = {}, {}
        for row in meta["images"]:
            yaw = row["yaw"]
            if row["held_out"]:
                continue
            png = BytesIO()
            load_mask(manifest.parent / row["file"]).save(png, format="PNG")
            masks[yaw] = SubjectMask(row["sha256"], 0, png.getvalue())
            c = camera_for(yaw, height)
            cameras[yaw] = Alignment(Camera(c.yaw_degrees, c.similarity * scale,
                                            c.origin + c.similarity * complex(0, floor * scale), 1), 0, {})
        if prior is not None:
            results = prior["results"]
        else:
            results = {"bootstrap": assess(vertices)}
            for name, yaws in CONFIGURATIONS.items():
                start = perf_counter()
                score = _scorer(body, {yaw: masks[yaw] for yaw in yaws},
                                {yaw: cameras[yaw] for yaw in yaws}, vertices)
                fitted, train = _optimize(body, score, {}, controls, (.25, .125))
                results[name] = assess(deform_vertices(body, fitted)) | {
                    "controls": fitted, "input_yaws": yaws, "training_iou": train,
                    "fit_seconds": perf_counter() - start,
                }
            for label, steps in {"direct_coarse": (.25, .125),
                                 "direct_refined": (.25, .125, .0625, .03125)}.items():
                start = perf_counter()
                fitted, _ = _optimize(body, objective, {}, controls, steps)
                results[label] = assess(deform_vertices(body, fitted)) | {
                    "controls": fitted, "fit_seconds": perf_counter() - start,
                    "saturated": sorted(key for key, value in fitted.items() if abs(value) == .5),
                }
        for pattern in sorted(args.native.glob(manifest.parent.name + "-*/benchmark.json")):
            raw = json.loads(pattern.read_text())
            if "fit" in raw:
                results["native_" + pattern.parent.name.rsplit("-", 1)[-1]] = (
                    assess(deform_vertices(body, raw["fit"]["controls"])) | {"native_report": raw})
        report_path.write_text(json.dumps({
            "subject": meta["subject"], "source_family": meta["source_family"],
            "duration_seconds": prior["duration_seconds"] if prior else perf_counter() - started,
            "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "height_alignment_scale": scale, "truth_height_m": height, "release_neutral_height_m": neutral_height,
            "results": results,
        }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("assets", "pilot", "native", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--metrics-only", action="store_true", help="Refresh native metrics without refitting.")
    main(parser.parse_args())
