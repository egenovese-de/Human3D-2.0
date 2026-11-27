"""Separate calibrated silhouette reference-count control for P3/P4."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image

from human3d.alignment import Camera
from x_vlm import SUBJECTS, design, distances, features, fit_features, load_scene, mask_features, silhouette, stable, truth_warp


COUNTS = (1, 2, 4, 8, 15, 30)
FAMILIES = ("front_only", "complementary_clean", "complementary_degraded")


def evaluate(runtime):
    _, body, base, polygons, faces, fields = load_scene(runtime)
    ids = np.unique(faces)
    model = design(base, fields, faces, ids)
    results, views = [], []
    for subject, amplitude in zip(SUBJECTS, (.12, -.10, .18, -.16)):
        truth = truth_warp(base, amplitude)
        exact, _ = features(truth, faces, ids)
        for family in FAMILIES:
            records = []
            for i in range(30):
                axis = "front" if family == "front_only" or i % 2 == 0 else "side"
                yaw = (0 if axis == "front" else 90) + (180 if i % 4 >= 2 else 0)
                scale = 9.25 + i * .083
                origin = complex(128 + (i * 7 % 9 - 4), 128 + (i * 5 % 7 - 3))
                camera = Camera(yaw, scale, origin, 1)
                clean = silhouette(truth, polygons, camera)
                image = np.asarray(clean).copy()
                if family == "complementary_degraded" and i % 3 != 0:
                    # Known asymmetric segmentation bleed below the waist.
                    affected = np.flatnonzero(image.any(axis=1))
                    start = int(affected[-1] - .58 * (affected[-1] - affected[0]))
                    end = int(affected[-1] - .51 * (affected[-1] - affected[0]))
                    for y in range(start, end + 1):
                        support = np.flatnonzero(image[y])
                        if len(support):
                            image[y, support[-1]:min(support[-1] + 8, 256)] = True
                    clean = Image.fromarray(image)
                vector = mask_features(clean)
                keys = (f"{axis}_upper", f"{axis}_hip")
                observations = dict(zip(keys, vector))
                checksum = sha256(clean.tobytes()).hexdigest()
                records.append((checksum, observations))
                views.append({"subject": subject, "family": family, "index": i + 1, "axis": axis,
                              "yaw_deg": yaw, "camera_scale": scale, "screen_shift_xy": [origin.real, origin.imag],
                              "projected_pixels_sha256": checksum, "observations": observations})
            if len({checksum for checksum, _ in records}) != len(records):
                raise ValueError("Reference sweep requires distinct rendered inputs")
            for n in COUNTS:
                fused = {}
                for _, values in records[:n]:
                    for name, value in values.items():
                        fused.setdefault(name, []).append(value)
                observation = {name: (float(np.median(values)), .025) for name, values in fused.items()}
                geometry, scale = stable(body, base, fit_features(base, fields, model, observation))
                result = distances(geometry[ids], truth[ids], {"global": np.ones(len(ids), dtype=bool)})["global"]
                results.append({"subject": subject, "family": family, "count": n,
                                "unique_rendered_views": n, "usable_fields": sorted(fused), "surface": result,
                                "rebind_scale": scale, "true_dimensions": exact[:4].tolist()})
    return {"scope": "deterministic measurements of distinct synthetic rasterized silhouettes, separate from GPT visual replay",
            "projection": "orthogonal front/back and left/right, distinct scales and translations",
            "degradation": "known lower-section segmentation bleed in two thirds of mixed-axis views",
            "aggregation": "median separately per axis and section, fixed weight",
            "results": results, "views": views}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.runtime)
    args.output.write_text(json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n")
    print(f"X_VLM_REFERENCE_SWEEP {len(report['views'])} renders, {len(report['results'])} fitted results")
