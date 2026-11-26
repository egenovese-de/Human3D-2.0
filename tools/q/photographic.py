"""Build hash-verified opaque photographs and controlled single-factor variants."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root):
    for manifest in sorted(root.glob("*/manifest.json")):
        source = json.loads(manifest.read_text())
        fixture = manifest.parent
        assert digest(fixture / "mesh.json") == source["mesh_sha256"]
        rows = []
        for row in source["images"]:
            assert digest(fixture / row["file"]) == row["sha256"]
            rgba = Image.open(fixture / row["file"]).convert("RGBA")
            mask = rgba.getchannel("A")
            assert mask.getextrema() == (0, 255)
            border = Image.new("RGBA", rgba.size, (82, 103, 126, 255))
            image = Image.alpha_composite(border, rgba).convert("RGB")
            target = fixture / f"rgb-{row['file']}"
            image.save(target)
            rows.append(dict(row, file=target.name, sha256=digest(target), truth_mask=row["file"]))
        for count in (1, 2, 3, 4, 8):
            order = [0, 90, 180, 270, 45, 135, 225, 315][:count]
            ordered = [next(row for row in rows if row["yaw"] == yaw) for yaw in order]
            (fixture / f"native-{count}.json").write_text(json.dumps({"images": ordered}, indent=2))
        front = Image.open(fixture / rows[0]["file"])
        pixels = np.asarray(front, dtype=float)
        rng = np.random.default_rng(2471)
        variants = {
            "resolution": (front.resize((96, 96), Image.Resampling.LANCZOS), {}),
            "jpeg": (front, {"quality": 12}),
            "blur": (front.filter(ImageFilter.GaussianBlur(5)), {}),
            "noise": (Image.fromarray(np.clip(pixels + rng.normal(0, 22, pixels.shape), 0, 255)
                                      .astype("uint8")), {}),
            "dark": (Image.fromarray((pixels * .35).astype("uint8")), {}),
            "crop": (front.crop((0, 42, 384, 330)), {}),
        }
        altered = front.copy()
        altered.paste((82, 103, 126), (150, 145, 235, 235))
        variants["occlusion"] = (altered, {})
        rows = []
        for name, (image, options) in variants.items():
            path = fixture / (f"{name}.jpg" if name == "jpeg" else f"{name}.png")
            image.save(path, **options)
            rows.append({"file": path.name, "sha256": digest(path), "variant": name,
                         "truth_mask": source["images"][0]["file"]})
        (fixture / "robustness.json").write_text(json.dumps({"images": rows}, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
