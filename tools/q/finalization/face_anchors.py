# SPDX-License-Identifier: GPL-3.0-or-later
"""Ray-cast manually chosen image points onto independent facial surfaces."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import bpy  # Registers Blender mathutils.
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np

from human3d.vision import PoseLandmarker

# Picks from the 384px fixture renders, using a coordinate grid over the head crop.
# This is one annotation pass per view from one reviewer.
PICKS = {
    "f_af01": {
        0: {"nose_tip": (192, 68.5), "eye_R_center": (187, 62), "eye_L_center": (197.5, 62),
            "mouth_R": (188, 72), "mouth_L": (196.5, 72), "chin": (192, 78),
            "jaw_R": (184, 74), "jaw_L": (200, 74), "cheek_R": (182.5, 67), "cheek_L": (202, 67)},
        90: {"nose_tip": (164.5, 68), "chin": (169.5, 78.5), "ear_L": (185.5, 63)},
    },
    "m_la01": {
        0: {"nose_tip": (192, 55), "eye_R_center": (185.5, 49.5), "eye_L_center": (197, 49.5),
            "mouth_R": (188, 60), "mouth_L": (195.5, 60), "chin": (192, 68),
            "jaw_R": (183, 63.5), "jaw_L": (200, 63.5), "cheek_R": (181, 55), "cheek_L": (202, 55)},
        90: {"nose_tip": (161, 55), "chin": (165, 68), "ear_L": (184, 54)},
    },
}
DETECTOR = {"nose_tip": 0, "eye_L_center": 2, "eye_R_center": 5,
            "mouth_L": 9, "mouth_R": 10, "ear_L": 7}


def run(dataset, model, photos, output):
    detector = PoseLandmarker(model, segmentation=True)
    results = []
    try:
        for identity, picks in PICKS.items():
            folder = dataset / f"{identity}_neutral"
            meta = json.loads((folder / "manifest.json").read_text())
            raw = (folder / "mesh.json").read_bytes()
            assert sha256(raw).hexdigest() == meta["mesh_sha256"]
            mesh = json.loads(raw)
            tree = BVHTree.FromPolygons(mesh["vertices"], mesh["faces"])
            for yaw, labels in picks.items():
                view = next(view for view in meta["images"] if view["yaw"] == yaw)
                camera = np.asarray(view["camera_to_world"])
                photo = photos / f"{folder.name}-{view['file']}"
                detection = detector.detect(photo, sha256(photo.read_bytes()).hexdigest())
                pose = detection.candidates[0] if len(detection.candidates) == 1 else ()
                size = meta["resolution_px"]
                scale = meta["camera_scale_m"]

                def cast(x, y):
                    origin = camera @ [(x / size - .5) * scale, (.5 - y / size) * scale, 0, 1]
                    hit, _, polygon, _ = tree.ray_cast(Vector(origin[:3]), Vector(-camera[:3, 2]), 10)
                    return (list(hit), polygon) if hit is not None else (None, None)

                for name, (x, y) in labels.items():
                    point, polygon = cast(x, y)
                    neighbors = [cast(x + dx, y + dy)[0] for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))]
                    distances = [float(np.linalg.norm(np.asarray(p) - point) * 1000)
                                 for p in neighbors if p is not None and point is not None]
                    index = DETECTOR.get(name)
                    detector_error = None
                    if point is not None and index is not None and pose and pose[index].observed:
                        detector_error = float(np.hypot(x - size * pose[index].x, y - size * pose[index].y))
                    results.append({"identity": identity, "yaw_deg": yaw, "feature": name,
                                    "source_image_sha256": view["sha256"], "mesh_sha256": meta["mesh_sha256"],
                                    "xy_px": [x, y], "xyz_m": point, "polygon": polygon,
                                    "detector_index_candidate": index, "detector_to_pick_px": detector_error,
                                    "valid_neighbor_rays": len(distances),
                                    "one_pixel_surface_sensitivity_max_mm": max(distances) if distances else None})
    finally:
        detector.close()
    output.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for argument in ("dataset", "model", "photos", "output"):
        parser.add_argument(argument, type=Path)
    run(**vars(parser.parse_args()))
