# SPDX-License-Identifier: GPL-3.0-or-later
"""Rasterize first-visible geometry with Blender BVH in the recorded metric cameras."""
import hashlib
import json
from pathlib import Path
import sys

from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np


def main(pilot, output):
    output.mkdir(exist_ok=True)
    for manifest in sorted(pilot.glob("*/manifest.json")):
        meta = json.loads(manifest.read_text())
        mesh = json.loads((manifest.parent / "mesh.json").read_text())
        bvh = BVHTree.FromPolygons(mesh["vertices"], mesh["faces"])
        width, height = meta["size"]
        scale = meta["ortho_scale_m"]
        atlas = output / manifest.parent.name
        atlas.mkdir(exist_ok=True)
        records = []
        for row in meta["images"]:
            matrix = np.asarray(row["camera_to_world"])
            direction = Vector(-matrix[:3, 2])
            origin = Vector(matrix[:3, 3])
            axis_x = Vector(matrix[:3, 0])
            axis_y = Vector(matrix[:3, 1])
            depth = np.full((height, width), np.nan, dtype=np.float32)
            face = np.full((height, width), -1, dtype=np.int32)
            x_offsets = [(float((x + .5) / width - .5) * scale) * axis_x for x in range(width)]
            for y in range(height):
                scanline = origin + ((.5 - (y + .5) / height) * scale) * axis_y
                for x, offset in enumerate(x_offsets):
                    _, _, index, distance = bvh.ray_cast(scanline + offset, direction, 10)
                    if index is not None:
                        depth[y, x], face[y, x] = distance, index
            path = atlas / f"{row['yaw']:g}.npz"
            np.savez_compressed(path, depth_meter=depth, visible_polygon=face)
            records.append({"yaw": row["yaw"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "hits": int(np.isfinite(depth).sum()),
                            "depth_min_m": float(np.nanmin(depth)), "depth_max_m": float(np.nanmax(depth))})
        (atlas / "manifest.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main(*map(Path, sys.argv[sys.argv.index("--") + 1:]))
