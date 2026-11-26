"""Measure canonical morph recovery on calibrated, coherent synthetic views."""
import argparse
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, distance_transform_edt

from benchmark_native import revision
from human3d.alignment import Alignment, Camera
from human3d.bootstrap import freeze_neutral
from human3d.fitting import _optimize, _scorer
from human3d.frozen_body import deform_vertices, load_frozen_body, morph_controls
from human3d.mask_review import SubjectMask
from human3d.native_rig import validate_rebind
from human3d.regional_morphs import regional_controls


def silhouette(vertices, faces, camera, size):
    projected = [camera.project(vertex) for vertex in vertices]
    image = Image.new("1", size)
    draw = ImageDraw.Draw(image)
    for face in faces:
        draw.polygon([(projected[i].real, projected[i].imag) for i in face], fill=1)
    return image


def compare(reference, prediction):
    expected, actual = np.asarray(reference), np.asarray(prediction)
    intersection = np.count_nonzero(expected & actual)
    union = np.count_nonzero(expected | actual)
    expected_edge = expected ^ binary_erosion(expected)
    actual_edge = actual ^ binary_erosion(actual)
    contour = (distance_transform_edt(~expected_edge)[actual_edge].mean()
               + distance_transform_edt(~actual_edge)[expected_edge].mean()) / 2
    return {"iou": intersection / union, "symmetric_contour_px": float(contour)}


def band_iou(reference, prediction, camera, joints, bones):
    """Evaluate fixed vertical bands bounded by known neutral rig landmarks."""
    expected, actual = np.asarray(reference), np.asarray(prediction)
    landmarks = ("head", "upperarm01.L", "upperleg01.L", "lowerleg01.L")
    boundaries = [0]
    boundaries.extend(round(camera.project(joints[bones[name]["head"]]).imag) for name in landmarks)
    boundaries.append(expected.shape[0])
    scores = {}
    for index, label in enumerate(("cranial", "neck", "trunk", "thigh", "lower_leg")):
        low, high = boundaries[index:index + 2]
        target, result = expected[low:high], actual[low:high]
        union = np.count_nonzero(target | result)
        scores[label] = np.count_nonzero(target & result) / union if union else None
    return scores


def sensitivity(body, neutral):
    baseline = np.asarray(neutral)
    report = {}
    for name in (*morph_controls(body), *regional_controls(body)):
        displacement = {}
        for amount in (-.5, .5):
            vertices = deform_vertices(body, {name: amount})
            validate_rebind(body, vertices)
            distance = np.linalg.norm(np.asarray(vertices) - baseline, axis=1)
            displacement[str(amount)] = {
                "moving_vertices": int(np.count_nonzero(distance > 1e-5)),
                "max_displacement_mm": float(100 * distance.max()),
            }
        report[name] = displacement
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("product", "assets", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--regional", action="store_true")
    parser.add_argument("--carve", action="store_true")
    args = parser.parse_args()
    product_sha = revision(args.product)
    lab_sha = revision(Path(__file__).parents[1])
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    frozen = freeze_neutral(args.assets, output / "frozen", with_morphs=True)
    body = load_frozen_body(output / "frozen" / f"{frozen}.json")
    neutral = deform_vertices(body, {})
    truth_controls = {"hips": .375, "waist": -.25, "thigh": .25, "upperarm": .375}
    if args.regional:
        truth_controls |= {"abdomen_depth": .375, "glute_depth": .25, "shin_depth": -.375}
    truth = deform_vertices(body, truth_controls)
    faces = [tuple(index for index, _ in face["corners"])
             for face in body["mesh"]["faces"] if face["group"] == "body"]
    minimum, maximum = np.min(truth, axis=0), np.max(truth, axis=0)
    center = (minimum + maximum) / 2
    scale = float(200 / (maximum[1] - minimum[1]))
    size = (256, 256)
    cameras = {}
    masks = {}
    angles = {"front": 0, "profile": 90, "back": 180, "held_out": 130}
    for name, angle in angles.items():
        unit = Camera(angle, scale, 0, 1)
        cameras[name] = Camera(angle, scale, (128 + 128j) - unit.project(center), 1)
        image = silhouette(truth, faces, cameras[name], size)
        image.save(output / f"{name}_truth.png")
        if name != "held_out":
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            masks[name] = SubjectMask(name, 0, buffer.getvalue())
    alignments = {key: Alignment(cameras[key], 0, {}) for key in masks}
    noisy = {key: Alignment(Camera(camera.yaw_degrees + 12, camera.similarity * .94,
                                   camera.origin + (6 - 4j), 1), 0, {})
             for key, camera in cameras.items() if key in masks}
    score = _scorer(body, masks, alignments, neutral, carve=args.carve)
    available = tuple(morph_controls(body))
    if args.regional:
        available += regional_controls(body)
    controls, _ = _optimize(body, score, {}, available, (.25, .125))
    fitted = deform_vertices(body, controls)
    configurations = {"baseline": (neutral, noisy), "camera_only": (neutral, alignments),
                      "geometry_only": (fitted, noisy), "camera_and_geometry": (fitted, alignments)}
    report = {"product_sha": product_sha, "lab_sha": lab_sha, "frozen_sha256": frozen,
              "visual_hull_objective": args.carve, "truth_controls": truth_controls, "fitted_controls": controls,
              "vertex_rmse_mm": float(100 * np.sqrt(np.mean(np.sum(
                  (np.asarray(fitted) - np.asarray(truth)) ** 2, axis=1)))),
              "held_out_view": "held_out", "training_views": list(masks), "views": {}}
    report["control_sensitivity"] = sensitivity(body, neutral)
    report["saturated_controls"] = sorted(name for name, value in controls.items() if abs(value) == .5)
    ground_truth_joints = validate_rebind(body, truth)
    fitted_joints = validate_rebind(body, fitted)
    report["root_mean_square_joint_error_mm"] = float(100 * np.sqrt(np.mean([
        np.sum((point - ground_truth_joints[name]) ** 2)
        for name, point in fitted_joints.items()
    ])))
    for name, camera in cameras.items():
        reference = silhouette(truth, faces, camera, size)
        metrics = {}
        for case, (vertices, configuration) in configurations.items():
            if name == "held_out" and case in {"baseline", "geometry_only"}:
                continue
            current_camera = configuration[name].camera if name in configuration else camera
            predicted = silhouette(vertices, faces, current_camera, size)
            metrics[case] = compare(reference, predicted)
            metrics[case]["band_iou"] = band_iou(reference, predicted, camera, ground_truth_joints,
                                                 body["rig"]["bones"])
            if case == "camera_and_geometry":
                expected, actual = np.asarray(reference), np.asarray(predicted)
                overlay = np.stack((expected, actual, np.zeros_like(actual)), axis=2)
                Image.fromarray(overlay.astype(np.uint8) * 255).save(output / f"{name}_overlay.png")
        metrics["fitted_projected_joint_rmse_px"] = float(np.sqrt(np.mean([
            abs(camera.project(point) - camera.project(ground_truth_joints[joint])) ** 2
            for joint, point in fitted_joints.items()
        ])))
        report["views"][name] = {"yaw": camera.yaw_degrees, "scale": camera.similarity,
                                 "origin": [camera.origin.real, camera.origin.imag], "metrics": metrics}
    (output / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
