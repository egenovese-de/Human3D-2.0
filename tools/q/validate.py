"""Validate Blender camera matrices, split membership, source masks and file hashes."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw


def main(pilot, output):
    results = []
    for manifest in sorted(pilot.glob("*/manifest.json")):
        metadata = json.loads(manifest.read_text())
        root = manifest.parent
        mesh_data = (root / "mesh.json").read_bytes()
        assert hashlib.sha256(mesh_data).hexdigest() == metadata["mesh_sha256"]
        mesh = json.loads(mesh_data)
        vertices = np.asarray(mesh["vertices"])
        world = np.column_stack((vertices, np.ones(len(vertices))))
        assert np.isfinite(world).all() and abs(vertices[:, 2].min()) < 1e-6
        width, height = metadata["size"]
        validation = []
        train = set()
        test = set()
        for row in metadata["images"]:
            (test if row["held_out"] else train).add(row["sha256"])
            source = root / row["file"]
            assert hashlib.sha256(source.read_bytes()).hexdigest() == row["sha256"]
            camera = np.asarray(row["camera_to_world"])
            local = world @ np.linalg.inv(camera).T
            pixels = (local[:, :2] / metadata["ortho_scale_m"] * [1, -1] + .5) * [width, height]
            assert (pixels > 0).all() and (pixels < [width, height]).all() and (local[:, 2] < 0).all()
            points = [tuple(point) for point in pixels]
            prediction = Image.new("1", (width, height))
            draw = ImageDraw.Draw(prediction)
            for face in mesh["faces"]:
                draw.polygon([points[index] for index in face], fill=1)
            truth = np.asarray(Image.open(source).getchannel("A")) >= 128
            predicted = np.asarray(prediction)
            iou = np.count_nonzero(truth & predicted) / np.count_nonzero(truth | predicted)
            assert iou > .94, (root, row["yaw"], iou)
            validation.append({"yaw": row["yaw"], "projection_iou": iou,
                               "visible_mask_px": int(truth.sum())})
        assert train.isdisjoint(test)
        results.append({"subject": metadata["subject"], "dimensions_xyz_m": np.ptp(vertices, axis=0).tolist(),
                        "training_views": len(train), "held_out_views": len(test), "validation": validation})
    output.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main(*map(Path, sys.argv[1:]))
