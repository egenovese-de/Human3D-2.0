"""Prepare height-aligned geometry locally for Blender comparison; do not redistribute the pack."""
import argparse
import json
from pathlib import Path

import numpy as np

from human3d.frozen_body import deform_vertices, load_frozen_body


def main(fixture, measurements, frozen, native, output):
    truth = json.loads((fixture / "mesh.json").read_text())
    results = json.loads(measurements.read_text())
    body = load_frozen_body(frozen)
    faces = [tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"]
    y = np.asarray(deform_vertices(body, {}))[np.unique(np.concatenate(faces)), 1]
    scale = results["height_alignment_scale"] / 10
    meshes = {"ground-truth": truth}
    controls = {"native": json.loads(native.read_text())["fit"]["controls"],
                "calibrated-four": results["results"]["four"]["controls"],
                "direct-3d": results["results"]["direct_refined"]["controls"]}
    for name, values in controls.items():
        x, vertical, z = np.asarray(deform_vertices(body, values)).T
        meshes[name] = {"vertices": (np.column_stack((x, -z, vertical - y.min())) * scale).tolist(),
                        "faces": faces}
    output.write_text(json.dumps({"height": results["truth_height_m"], "meshes": meshes}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("fixture", "measurements", "frozen", "native", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
