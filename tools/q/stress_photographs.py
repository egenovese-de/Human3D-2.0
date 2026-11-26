"""Composite stress fixtures while retaining visible pixel masks."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter


def main(pilot):
    for folder in sorted(pilot.iterdir()):
        manifest = folder / "robustness.json"
        rows = [row for row in json.loads(manifest.read_text())["images"] if "extended" not in row]
        front = Image.open(folder / "yaw-0.png")
        mask = front.getchannel("A")
        rng = np.random.default_rng(2471)
        tile = Image.fromarray(rng.integers(22, 215, (20, 20, 3), dtype=np.uint8)).resize(front.size)
        clutter = Image.composite(front.convert("RGB"), tile, mask)
        gradient = np.linspace(.33, 1.5, front.width)[None, :, None]
        bright = Image.fromarray(np.clip(np.asarray(front.convert("RGB")) * gradient, 0, 255).astype("uint8"))
        lit = Image.composite(bright, Image.new("RGB", front.size, (82, 103, 126)), mask)
        compound = clutter.crop((16, 29, 368, 330)).resize((176, 151)).filter(ImageFilter.GaussianBlur(2))
        compound.paste((22, 34, 39), (61, 47, 119, 82))
        transformed = mask.crop((16, 29, 368, 330)).resize(compound.size, Image.Resampling.NEAREST)
        transformed.paste(0, (61, 47, 119, 82))
        alpha = Image.new("RGBA", compound.size)
        alpha.putalpha(transformed)
        alpha.save(folder / "compound-alpha.png")
        perspective = json.loads((folder / "perspective.json").read_text())

        def composite(row):
            path = folder / row["file"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
            rgba = Image.open(path).convert("RGBA")
            return Image.alpha_composite(Image.new("RGBA", rgba.size, (82, 103, 126, 255)), rgba).convert("RGB")

        records = [(name, image, truth) for name, image, truth in (
            ("clutter", clutter, "yaw-0.png"), ("illumination-gradient", lit, "yaw-0.png"),
            ("compound", compound, "compound-alpha.png"))]
        records.extend((row["variant"], composite(row), row["file"]) for row in perspective)
        for name, image, mask_path in records:
            out = folder / f"{name}.png"
            image.save(out)
            rows.append({"file": out.name, "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                         "variant": name, "truth_mask": mask_path, "extended": True})
        manifest.write_text(json.dumps({"images": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
