"""Compose actual Blender comparison renders and evaluated silhouette disagreements."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from benchmark_geometry import silhouette
from evaluate import camera_for, load_mask


LABELS = {"ground-truth": "Independent ground truth", "native": "Native four-view neutral mesh",
          "calibrated-four": "Calibrated four-view neutral fit", "direct-3d": "Direct bounded surface fit"}


def main(fixture, comparison, pack, output):
    size = 192
    montage = Image.new("RGB", (size * 4, (size + 24) * 5), "#161e2a")
    draw = ImageDraw.Draw(montage)
    for y, (key, label) in enumerate(LABELS.items()):
        for x, angle in enumerate((0, 45, 90, 180)):
            im = Image.open(comparison / f"{key}-{angle}.png").convert("RGB")
            montage.paste(im.resize((size, size)), (x * size, y * (size + 24)))
            draw.text((x * size + 6, (y + 1) * (size + 24) - 18), f"{angle}° {label}", fill="#f2f4f7")
    data = json.loads(pack.read_text())
    geometry = data["meshes"]["native"]
    x, y, z = np.asarray(geometry["vertices"]).T
    vertices = np.column_stack((x, z, -y)) * 10
    for index, angle in enumerate((0, 45, 90, 180)):
        expected = np.asarray(load_mask(fixture / f"yaw-{angle}.png"))
        actual = np.asarray(silhouette(vertices, geometry["faces"], camera_for(angle, data["height"]), (384, 384)))
        rgb = np.full((*actual.shape, 3), (22, 30, 42), dtype=np.uint8)
        rgb[expected & actual] = (183, 198, 209)
        rgb[expected & ~actual] = (65, 199, 219)
        rgb[actual & ~expected] = (251, 140, 83)
        montage.paste(Image.fromarray(rgb).resize((size, size)), (index * size, 4 * (size + 24)))
        draw.text((index * size + 6, 5 * (size + 24) - 18),
                  f"{angle}° cyan missed, orange excess", fill="#f2f4f7")
    montage.save(output, optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("fixture", "comparison", "pack", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
