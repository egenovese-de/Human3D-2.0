# SPDX-License-Identifier: GPL-3.0-or-later
"""Compute regional surface visibility using independent rays against calibrated fixtures."""
import argparse
import json
from pathlib import Path

import bpy  # Initializes Blender mathutils in the module distribution.
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np
from PIL import Image


REGIONS = {
    "face": ("head",), "torso": ("pelvis", "spine01", "spine02", "spine03"),
    "left_arm": ("upperarm_L", "lowerarm_L", "hand_L"),
    "right_arm": ("upperarm_R", "lowerarm_R", "hand_R"),
    "left_leg": ("thigh_L", "calf_L", "foot_L"), "right_leg": ("thigh_R", "calf_R", "foot_R"),
}


def classify(points, meta):
    distances = []
    labels = []
    for region, names in REGIONS.items():
        for name in names:
            start, end = (np.array(meta["bones"][name][key]) for key in ("head", "tail"))
            direction = end - start
            position = np.clip((points - start) @ direction / (direction @ direction), 0, 1)
            distances.append(np.linalg.norm(points - start - position[:, None] * direction, axis=1))
            labels.append(region)
    return np.array(labels)[np.argmin(distances, axis=0)]


def process(folder):
    meta = json.loads((folder / "manifest.json").read_text())
    mesh = json.loads((folder / "mesh.json").read_text())
    points = np.asarray(mesh["vertices"])
    indices = np.asarray([(face[0], face[k], face[k+1]) for face in mesh["faces"] for k in range(1, len(face)-1)])
    triangles = points[indices]
    centers = triangles.mean(axis=1)
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]) / 2
    areas = np.linalg.norm(normals, axis=1)
    labels = classify(centers, meta)
    bvh = BVHTree.FromPolygons(points.tolist(), indices.tolist(), all_triangles=True)
    rows = []
    for row in meta["images"]:
        camera = np.array(row["camera_to_world"])
        origin = camera[:3, 3]
        right, up, backward = camera[:3, :3].T
        direction = Vector(-backward)
        toward = (origin - centers) @ backward
        visible = np.zeros(len(centers), dtype=bool)
        for i, (point, offset) in enumerate(zip(centers, toward)):
            hit, _, _, _ = bvh.ray_cast(Vector(point + backward * offset), direction)
            visible[i] = hit is not None and (hit - Vector(point)).length < .00035
        alpha = np.asarray(Image.open(folder / row["file"]).getchannel("A")) >= 128
        size = meta["resolution_px"]
        step = 4
        coords = np.arange(0, size, step)
        sample = np.zeros((len(coords), len(coords)), dtype=bool)
        for r, y in enumerate(coords):
            for c, x in enumerate(coords):
                location = origin + right * ((x+.5)/size-.5)*2.16 + up * (.5-(y+.5)/size)*2.16
                sample[r, c] = bvh.ray_cast(Vector(location), direction)[0] is not None
        truth = alpha[::step, ::step]
        projected = np.abs(normals @ backward)
        regional = {}
        for name in REGIONS:
            selected = labels == name
            front = selected & ((normals @ backward) > 0)
            reference_area = projected[front].sum()
            area = projected[front & visible].sum()
            regional[name] = {"visible_projected_area_m2": float(area),
                              "front_projected_area_m2": float(reference_area),
                              "visible_fraction_of_front_projected": float(area / reference_area) if reference_area else None,
                              "triangle_area_m2": float(areas[selected].sum())}
        rows.append({"yaw": row["yaw"], "sampled_mask_iou": float((sample & truth).sum()/(sample | truth).sum()),
                     "regions": regional})
    return {"fixture": folder.name, "mesh_sha256": meta["mesh_sha256"], "views": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    folders = sorted(p for p in args.dataset.iterdir() if p.name.startswith(("f_af01_", "m_la01_")))
    rows = []
    for folder in folders:
        rows.append(process(folder))
        args.output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
