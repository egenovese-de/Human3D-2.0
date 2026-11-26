"""Compare height-normalized bone dimensions and held-out silhouette regions."""
import argparse
import json
from pathlib import Path

import numpy as np

from benchmark_geometry import silhouette
from evaluate import camera_for, load_mask
from human3d.frozen_body import deform_vertices, load_frozen_body
from human3d.native_rig import rebind_joints


def main(pilot, native, pose, evaluation, frozen, output):
    output.mkdir(exist_ok=True)
    body = load_frozen_body(frozen)
    faces = [tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"]
    base = np.asarray(deform_vertices(body, {}))
    body_y = base[np.unique(np.concatenate(faces)), 1]
    rig = body["rig"]
    for path in sorted(pose.glob("*.json")):
        folder = pilot / path.stem
        data = json.loads((evaluation / path.name).read_text())
        height = data["truth_height_m"]
        truth = {key: np.asarray(value) for key, value in
                 json.loads(path.read_text())["ground_truth_joint_anchors_xyz_m"].items()}
        camera_scale = height / np.ptp(body_y)
        fit = json.loads((native / f"{path.stem}-4" / "benchmark.json").read_text())
        rows = {}
        for name, controls in {"base": {}, "native-four": fit["fit"]["controls"],
                               "calibrated-four": data["results"]["four"]["controls"],
                               "direct-3d": data["results"]["direct_refined"]["controls"]}.items():
            model = np.asarray(deform_vertices(body, controls))
            joints = rebind_joints(rig, model)
            segments = {key: np.asarray([joints[rig["bones"][key][end]] for end in ("head", "tail")])
                        for key in truth}
            x, y, z = model.T
            vertices = np.column_stack((x, y - body_y.min(), z)) * camera_scale * 10
            regions = {}
            for yaw in (22.5, 112.5):
                camera = camera_for(yaw, height)
                gt = np.asarray(load_mask(folder / f"yaw-{yaw:g}.png"))
                pred = np.asarray(silhouette(vertices, faces, camera, gt.shape[::-1]))
                band = {}
                for label, lo, hi in (("cranial", .86, 1.03), ("torso_and_arms", .54, .86),
                                       ("lower_body", -.03, .54)):
                    start = round(camera.project((0, hi * height * 10, 0)).imag)
                    end = round(camera.project((0, lo * height * 10, 0)).imag)
                    truth_band, prediction_band = gt[start:end], pred[start:end]
                    band[label] = int(np.count_nonzero(truth_band & prediction_band)) / int(
                        np.count_nonzero(truth_band | prediction_band))
                regions[str(yaw)] = band
            distance = lambda t, a, b: np.linalg.norm(t[a][0] - t[b][0])
            spans = {
                "shoulder_span_error_ratio_of_height": (distance(segments, "upperarm01.L", "upperarm01.R")
                    * camera_scale - distance(truth, "upperarm01.L", "upperarm01.R")) / height,
                "hip_span_error_ratio_of_height": (distance(segments, "upperleg01.L", "upperleg01.R")
                    * camera_scale - distance(truth, "upperleg01.L", "upperleg01.R")) / height,
            }
            rows[name] = {"held_out_region_iou": regions, "proportion_errors": spans}
        (output / path.name).write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("pilot", "native", "pose", "evaluation", "frozen", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
