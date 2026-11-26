"""Replay the Q detector stress matrix and record independent suitability decisions."""
import argparse
from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image

from detector_sweep import treatments
from evaluate import load_mask
from human3d.vision import _NativePoseLandmarker


def rev(root):
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def cases(root, detector, work):
    for folder in sorted((root / "holdout").glob("*_bend0")):
        for yaw in (0, 90, 270):
            path = folder / f"rgb-yaw-{yaw}.png"
            image = Image.open(path).convert("RGB")
            truth = load_mask(folder / f"yaw-{yaw}.png")
            for treatment, level, variant, label in treatments(image, truth):
                if yaw and treatment != "clean":
                    continue
                path = work / "case.png"
                variant.save(path)
                image_hash = sha256(path.read_bytes()).hexdigest()
                result = detector.detect(path, image_hash)
                row = dict(fixture=folder.name, yaw=yaw, treatment=treatment, level=level,
                           sha256=image_hash, candidates=len(result.candidates),
                           review_reason=result.review_reason)
                if len(result.candidates) == 1:
                    row.update(asdict(result.suitability(0)))
                    if result.masks and result.masks[0] is not None:
                        mask = np.asarray(Image.open(BytesIO(result.masks[0])).convert("1"))
                        target = np.asarray(label.convert("1"))
                        row["mask_iou"] = float((mask & target).sum() / (mask | target).sum())
                yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("product", "original_q_workspace", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    detector = _NativePoseLandmarker(args.original_q_workspace / "assets" / "pose.task", segmentation=True)
    try:
        with TemporaryDirectory() as directory:
            rows = list(cases(args.original_q_workspace, detector, Path(directory)))
    finally:
        detector.close()
    args.output.write_text(json.dumps({"product_sha": rev(args.product),
                                      "lab_sha": rev(Path(__file__).parents[2]), "cases": rows},
                                     indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
