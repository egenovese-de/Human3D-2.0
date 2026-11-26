"""Evaluate 3/4/8/16 camera scaling and duplicates under an identical short Lab schedule."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask
from human3d.alignment import Alignment, Camera
from human3d.fitting import _optimize, _scorer
from human3d.frozen_body import deform_vertices, load_frozen_body, morph_controls
from human3d.mask_review import SubjectMask
from human3d.proportions import length_controls
from human3d.regional_morphs import regional_controls


def main(pilot, extra, frozen, output):
    output.mkdir(exist_ok=True)
    body = load_frozen_body(frozen)
    rest = np.asarray(deform_vertices(body, {}))
    faces = [tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"]
    model_y = rest[np.unique(np.concatenate(faces)), 1]
    controls = (*morph_controls(body), *length_controls(body), *regional_controls(body))
    for extension in sorted(extra.iterdir()):
        target = output / (extension.name + ".json")
        if target.exists():
            continue
        fixture = pilot / extension.name
        source = json.loads((fixture / "manifest.json").read_text())
        truth = np.asarray(json.loads((fixture / "mesh.json").read_text())["vertices"])
        height = np.ptp(truth[:, 2])
        factor = 10 * height / np.ptp(model_y)
        paths = {}
        for folder, rows in ((fixture, source["images"]), (extension, json.loads((extension / "manifest.json").read_text()))):
            for row in rows:
                path = folder / row["file"]
                assert sha256(path.read_bytes()).hexdigest() == row["sha256"]
                paths[row["yaw"]] = (path, row["sha256"])
        held = [row["yaw"] for row in source["images"] if row["held_out"]]
        base = list(range(0, 360, 45))
        extra_yaws = [11.25 + step * 45 for step in range(8)]
        conditions = {"three": [0, 90, 180], "four": [0, 90, 180, 270], "eight": base,
                      "eight_repeat": base, "sixteen": base + extra_yaws, "duplicate_front": [0, 90, 180, 0]}
        results = {}
        for label, orientations in conditions.items():
            assert set(orientations).isdisjoint(held)
            masks, views = {}, {}
            started = perf_counter()
            for id, yaw in enumerate(orientations):
                path, digest = paths[yaw]
                image = BytesIO()
                load_mask(path).save(image, format="PNG")
                masks[id] = SubjectMask(digest, 0, image.getvalue())
                c = camera_for(yaw, height)
                views[id] = Alignment(Camera(c.yaw_degrees, c.similarity * factor,
                                             c.origin + c.similarity * complex(0, model_y.min() * factor), 1), 0, {})
            score = _scorer(body, masks, views, rest, edge=128)
            fitted, _ = _optimize(body, score, {}, controls, (.25,))
            model = np.asarray(deform_vertices(body, fitted))
            model[:, 1] -= model_y.min()
            model *= factor
            results[label] = {"controls": fitted, "seconds": perf_counter() - started, "input_yaws": orientations,
                              "held_out": {str(yaw): compare(load_mask(paths[yaw][0]), silhouette(
                                  model, faces, camera_for(yaw, height), (384, 384)))["iou"] for yaw in held}}
        target.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("pilot", "extra", "frozen", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
