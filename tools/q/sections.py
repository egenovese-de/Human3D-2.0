"""Measure metric-height-aligned cross-section perimeter proxies for the pilot."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

from human3d.frozen_body import deform_vertices, load_frozen_body


def edge_indices(faces):
    return np.asarray(sorted({tuple(sorted((face[i - 1], index)))
                              for face in faces for i, index in enumerate(face)}))


def sections(vertices, edges, height):
    starts, ends = vertices[edges].transpose((1, 0, 2))
    measures = {}
    for name, fraction in {"hip_band": .52, "waist_band": .61, "chest_band": .71}.items():
        z = fraction * height
        select = ((starts[:, 2] <= z) & (ends[:, 2] > z)) | ((ends[:, 2] <= z) & (starts[:, 2] > z))
        a, b = starts[select], ends[select]
        cross = a + ((z - a[:, 2]) / (b[:, 2] - a[:, 2]))[:, None] * (b - a)
        points = cross[np.abs(cross[:, 0]) < .18 * height, :2]
        hull = ConvexHull(points)
        measures[name] = {"convex_perimeter_mm": float(hull.area * 1000), "area_cm2": float(hull.volume * 10000)}
    return measures


def main(pilot, native, evaluation, frozen, output):
    body = load_frozen_body(frozen)
    edges = edge_indices([tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"])
    model_y = np.asarray(deform_vertices(body, {}))[np.unique(edges), 1]
    out = []
    for fixture in sorted(pilot.iterdir()):
        gt = json.loads((fixture / "mesh.json").read_text())
        vertices = np.asarray(gt["vertices"])
        height = np.ptp(vertices[:, 2])
        results = {}
        cases = {"bootstrap": {}}
        for count in (1, 4):
            path = native / (fixture.name + f"-{count}") / "benchmark.json"
            if path.exists() and "fit" in (data := json.loads(path.read_text())):
                cases[f"native-{count}"] = data["fit"]["controls"]
        path = evaluation / (fixture.name + ".json")
        if path.exists():
            results_3d = json.loads(path.read_text())["results"]
            for key in ("direct_refined", "four"):
                cases[key] = results_3d[key]["controls"]
        expected = sections(vertices, edge_indices(gt["faces"]), height)
        for label, controls in cases.items():
            x, y, z = np.asarray(deform_vertices(body, controls)).T
            world = np.column_stack((x, -z, y - model_y.min())) * height / np.ptp(model_y)
            predicted = sections(world, edges, height)
            results[label] = {key: value | {"perimeter_error_mm":
                              value["convex_perimeter_mm"] - expected[key]["convex_perimeter_mm"]}
                              for key, value in predicted.items()}
        out.append({"fixture": fixture.name, "truth": expected, "results": results})
    output.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("pilot", "native", "evaluation", "frozen", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
