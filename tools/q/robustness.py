"""Run the native detector on base views and controlled photographic variants."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image

from human3d.vision import PoseLandmarker


def run(pilot, model, output):
    output.mkdir(parents=True, exist_ok=True)
    detector = PoseLandmarker(model, segmentation=True)
    try:
        for folder in sorted(pilot.iterdir()):
            report = output / (folder.name + ".json")
            if report.exists():
                continue
            rows = []
            for filename in ("native-8.json", "robustness.json"):
                rows.extend(json.loads((folder / filename).read_text())["images"])
            measurements = []
            for row in rows:
                path = folder / row["file"]
                start = perf_counter()
                result = {key: value for key, value in row.items() if key != "camera_to_world"}
                try:
                    assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
                    observation = detector.detect(path, row["sha256"])
                    result |= {"candidate_count": len(observation.candidates),
                               "review_reason": observation.review_reason}
                    if len(observation.masks) == 1 and observation.masks[0] is not None:
                        expected = Image.open(folder / row["truth_mask"]).getchannel("A")
                        if row.get("variant") == "crop":
                            expected = expected.crop((0, 42, 384, 330))
                        actual = np.asarray(Image.open(BytesIO(observation.masks[0]))) > 0
                        expected = np.asarray(expected.resize(observation.image_size, Image.Resampling.NEAREST)) >= 128
                        intersection = np.count_nonzero(actual & expected)
                        result |= {"mask_iou": intersection / np.count_nonzero(actual | expected),
                                   "mask_false_positive_px": int(np.count_nonzero(actual & ~expected)),
                                   "mask_false_negative_px": int(np.count_nonzero(~actual & expected))}
                except (RuntimeError, ValueError) as exc:
                    result["error"] = str(exc)
                result["seconds"] = perf_counter() - start
                measurements.append(result)
            report.write_text(json.dumps(measurements, indent=2) + "\n")
    finally:
        detector.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("pilot", "model", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    run(**vars(parser.parse_args()))
