"""Measure voxel-carved visual hulls on the calibrated synthetic fixture."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from benchmark_geometry import silhouette
from human3d.alignment import Camera
from human3d.frozen_body import deform_vertices, load_frozen_body

def carve(points, cameras, masks):
    inside = np.ones(len(points), dtype=bool)
    for key, camera in cameras.items():
        image = masks[key]
        pixel = np.asarray([camera.project(point) for point in points])
        x, y = np.rint(pixel.real).astype(int), np.rint(pixel.imag).astype(int)
        height, width = image.shape
        valid = (x >= 0) & (x < width) & (y >= 0) & (y < height)
        inside &= valid & image[np.clip(y, 0, height - 1), np.clip(x, 0, width - 1)]
    return inside

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--edge", type=int, default=36, choices=range(8, 65))
    args = parser.parse_args()
    report = json.loads((args.run / "geometry.json").read_text())
    body = load_frozen_body(args.run / "frozen" / f"{report['frozen_sha256']}.json")
    cameras = {}
    for key in report["training_views"]:
        camera = report["views"][key]
        cameras[key] = Camera(camera["yaw"], camera["scale"], complex(*camera["origin"]), 1)
    masks = {}
    for key in cameras:
        with Image.open(args.run / f"{key}_truth.png") as image:
            masks[key] = np.asarray(image.convert("1"))
    neutral = np.asarray(deform_vertices(body, {}))
    axes = [np.linspace(low, high, args.edge) for low, high in zip(neutral.min(axis=0), neutral.max(axis=0))]
    points = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    truth_hull = carve(points, cameras, masks)
    faces = [tuple(index for index, _ in face["corners"])
             for face in body["mesh"]["faces"] if face["group"] == "body"]
    results = {}
    for label, controls in (("bootstrap", {}), ("fitted", report["fitted_controls"])):
        vertices = deform_vertices(body, controls)
        rendered = {key: np.asarray(silhouette(vertices, faces, camera, masks[key].shape[::-1]))
                    for key, camera in cameras.items()}
        hull = carve(points, cameras, rendered)
        results[label] = {"occupied_voxels": int(hull.sum()),
                          "visual_hull_iou": float(np.count_nonzero(hull & truth_hull) / np.count_nonzero(hull | truth_hull))}
    print(json.dumps({"grid": args.edge, "training_views": list(cameras), "truth_voxels": int(truth_hull.sum()),
                      "results": results}, indent=2))

if __name__ == "__main__":
    main()
