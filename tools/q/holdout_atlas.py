"""Compose the rendered held-out poses without redistributing the local meshes."""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def main(holdout, visual, output):
    size = 208
    pitch = size + 23
    montage = Image.new("RGB", (size * 4, 5 * pitch), "#171e28")
    draw = ImageDraw.Draw(montage)
    for column, (identity, yaw) in enumerate(
        (("f_af01", 0), ("f_af01", 45), ("m_la01", 0), ("m_la01", 45))
    ):
        neutral = next(holdout.glob(f"*_{identity}_bend0"))
        bent = next(holdout.glob(f"*_{identity}_bend32"))
        views = [
            (neutral / f"rgb-yaw-{yaw}.png", "Neutral input"),
            (bent / f"rgb-yaw-{yaw}.png", "Articulated input"),
            (visual / identity / f"ground-truth-{yaw}.png", "Ground truth"),
            (visual / identity / f"native-posed-{yaw}.png", "Native posed"),
        ]
        draw.text((column * size + 7, 9), f"{identity} / {yaw}°", fill="white")
        for row, (path, label) in enumerate(views):
            im = Image.open(path).convert("RGB").resize((size, size))
            y = 30 + row * pitch
            montage.paste(im, (column * size, y))
            draw.text((column * size + 7, y + size + 3), label, fill="white")
    montage = montage.crop((0, 0, montage.width, 30 + 4 * pitch))
    montage.save(output, optimize=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("holdout", "visual", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
