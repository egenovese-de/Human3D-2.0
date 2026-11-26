"""Export the calibrated benchmark's fitted mesh with a diagnostic UV checker."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from human3d.alignment import Alignment, Camera
from human3d.fitting import Fit
from human3d.frozen_body import load_frozen_body
from human3d.usd_export import export_body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    directory = args.run
    report = json.loads((directory / "geometry.json").read_text())
    body = load_frozen_body(directory / "frozen" / (report["frozen_sha256"] + ".json"))
    front = report["views"]["front"]
    alignment = Alignment(Camera(front["yaw"], front["scale"], complex(*front["origin"]), 1), 0, {})
    texture = Image.new("RGB", (256, 256), "#b3bfd1")
    draw = ImageDraw.Draw(texture)
    for x in range(8):
        for y in range(8):
            if (x + y) % 2:
                draw.rectangle((32 * x, 32 * y, 32 * x + 31, 32 * y + 31), fill="#435a72")
    fit = Fit(report["fitted_controls"], 0, 0)
    export_body(directory / "diagnostic_uv.usdz", body, fit, alignment, texture=texture)


if __name__ == "__main__":
    main()
