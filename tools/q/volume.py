# SPDX-License-Identifier: GPL-3.0-or-later
"""Approximate common-frame body occupancy with axis-wise Blender BVH parity."""
from collections import Counter
import json
from pathlib import Path
import sys

from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np


def occupied(mesh, axes):
    bvh = BVHTree.FromPolygons(mesh["vertices"], mesh["faces"])
    labels = []
    for axis in range(3):
        permutation = np.roll([0, 1, 2], -axis)
        x, y, z = axes[permutation]
        seen = np.zeros((len(x), len(y), len(z)), dtype=np.bool_)
        direction = Vector([float(i == axis) for i in range(3)])
        for j, y_val in enumerate(y):
            for k, z_val in enumerate(z):
                start = [0., 0., 0.]
                start[axis], start[permutation[1]], start[permutation[2]] = x[0] - .10, y_val, z_val
                origin = Vector(start)
                depth = []
                for _ in range(128):
                    point, _, index, _ = bvh.ray_cast(origin, direction, 4)
                    if index is None:
                        break
                    depth.append(point[axis])
                    origin = point + direction * .00003
                seen[:, j, k] = np.searchsorted(depth, x) % 2
        labels.append(np.transpose(seen, np.argsort(permutation)))
    votes = np.sum(labels, axis=0)
    counts = Counter(tuple(sorted((f[i - 1], v))) for f in mesh["faces"] for i, v in enumerate(f))
    majority = votes >= 2
    return majority, {"majority_occupied_voxels": int(majority.sum()),
                      "ambiguous_axis_voxels": int(np.count_nonzero((votes > 0) & (votes < 3))),
                      "boundary_edges": sum(n == 1 for n in counts.values()),
                      "nonmanifold_edges": sum(n > 2 for n in counts.values())}


def main(geometry, output):
    pack = json.loads(geometry.read_text())
    h = pack["height"]
    step = h / 55
    axes = [np.arange(low, high, step) for low, high in ((-.60*h, .60*h), (-.28*h, .28*h), (-.03*h, 1.04*h))]
    axes = np.array(axes, dtype=object)
    truth, calibration = occupied(pack["meshes"]["ground-truth"], axes)
    metrics = {"ground-truth": calibration}
    for name, mesh in pack["meshes"].items():
        if name == "ground-truth":
            continue
        prediction, metrics[name] = occupied(mesh, axes)
        metrics[name]["approximate_volume_iou"] = (
            int(np.count_nonzero(prediction & truth)) / int(np.count_nonzero(prediction | truth)))
    output.write_text(json.dumps({"voxel_size_m": step, "metrics": metrics}, indent=2) + "\n")


if __name__ == "__main__":
    main(*map(Path, sys.argv[sys.argv.index("--") + 1:]))
