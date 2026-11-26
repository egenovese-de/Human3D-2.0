"""Build controlled reference substitutions and score neutral on untouched cameras."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

import numpy as np

from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.session import Session


PAIRS = [("f_af01", "f_ca01"), ("m_la01", "m_as01")]
TREATMENTS = ["different-pose", "contradictory"]


def create(root, inputs):
    for identity, substitute in PAIRS:
        neutral = next(root.glob(f"*_{identity}_bend0"))
        posed = next(root.glob(f"*_{identity}_bend32"))
        other = next(root.glob(f"*_{substitute}_bend0"))
        destination = inputs / identity
        destination.mkdir(parents=True, exist_ok=True)
        baseline = json.loads((neutral / "native-4.json").read_text())["images"]
        for row in baseline:
            shutil.copy2(neutral / row["file"], destination / row["file"])
        for label, alternate in zip(TREATMENTS, (posed, other), strict=True):
            filename = label + "-yaw-90.png"
            data = (alternate / "rgb-yaw-90.png").read_bytes()
            (destination / filename).write_bytes(data)
            changed = [dict(row, file=filename, sha256=sha256(data).hexdigest(),
                            reference_source=alternate.name) if row["yaw"] == 90 else row for row in baseline]
            (destination / (label + ".json")).write_text(json.dumps({"images": changed}, indent=2) + "\n")


def score(holdout, ordinary, mixed, output):
    measurements = {}
    for identity, _ in PAIRS:
        fixture = next(holdout.glob(f"*_{identity}_bend0"))
        meta = json.loads((fixture / "manifest.json").read_text())
        gt = json.loads((fixture / "mesh.json").read_text())
        height = np.ptp(np.asarray(gt["vertices"])[:, 2])
        groups = {"matched": ordinary / (fixture.name + "-4")} | {
            label: mixed / f"{identity}-{label}" for label in TREATMENTS}
        rows = {}
        for label, run in groups.items():
            record = json.loads((run / "benchmark.json").read_text())
            if "fit" not in record:
                rows[label] = {"failure": record.get("error", "fit_missing")}
                continue
            session = Session(run / "project")
            evidence = session.shared_evidence()
            body = load_project_body(session.store)
            faces = [tuple(i for i,_ in face["corners"]) for face in body["mesh"]["faces"] if face["group"] == "body"]
            base = np.asarray(deform_vertices(body, {}))
            floor = base[np.unique(np.concatenate(faces)), 1]
            vertices = np.asarray(deform_vertices(body, record["fit"]["controls"]))
            vertices[:, 1] -= floor.min()
            vertices *= 10 * height / np.ptp(floor)
            holdout_ious = {}
            for item in meta["images"]:
                if item["held_out"]:
                    mask = load_mask(fixture / item["file"])
                    predicted = silhouette(vertices, faces, camera_for(item["yaw"], height), mask.size)
                    holdout_ious[str(item["yaw"])] = compare(mask, predicted)["iou"]
            rows[label] = {"neutral_iou": holdout_ious, "used_views": len(record["fit"]["per_view_iou"]),
                           "unresolved": [reason for _, reason in evidence.unresolved],
                           "target_fit_iou": record["fit"]["per_view_iou"].get(record["photo_ids"]["rgb-yaw-0.png"]),
                           "controls": record["fit"]["controls"], "input_detections": record["detections"],
                           "fit_seconds": record["fit_seconds"]}
        measurements[identity] = rows
    output.write_text(json.dumps(measurements, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    builder = sub.add_parser("create")
    for name in ("root", "inputs"):
        builder.add_argument(name, type=Path)
    evaluator = sub.add_parser("score")
    for name in ("holdout", "ordinary", "mixed", "output"):
        evaluator.add_argument(name, type=Path)
    args = vars(parser.parse_args())
    {"create": create, "score": score}[args.pop("command")](**args)
