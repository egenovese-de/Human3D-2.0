"""Paired clothing effects on release vision and a fixed-camera neutral silhouette fit."""
import argparse
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from benchmark_geometry import compare
from evaluate import camera_for, load_mask, metric_distance, sample_surface
from human3d.alignment import Alignment
from human3d.fitting import _optimize, _scorer
from human3d.frozen_body import deform_vertices, load_project_body, morph_controls
from human3d.mask_review import SubjectMask
from human3d.proportions import length_controls
from human3d.regional_morphs import regional_controls
from human3d.session import Session
from human3d.vision import PoseLandmarker, estimate_world_yaw


def main(previous, dataset, clothes, work, output):
    work.mkdir(parents=True, exist_ok=True)
    detector = PoseLandmarker(previous / "assets/pose.task", segmentation=True)
    rows = json.loads(output.read_text()) if output.exists() else []
    completed = {(row["identity"], row["condition"]) for row in rows}
    try:
        for identity in ("f_af01", "m_la01"):
            filepath = dataset / f"{identity}_neutral" / "mesh.json"
            mesh = json.loads(filepath.read_text())
            truth = np.asarray(mesh["vertices"])
            height = np.ptp(truth[:, 2])
            body = load_project_body(Session(next((previous / "holdout-native").glob(f"*_{identity}_bend0-1")) / "project").store)
            base = np.asarray(deform_vertices(body, {}))
            faces = [tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"] if face["group"] == "body"]
            elevations = base[np.unique(np.concatenate(faces)), 1]
            factor = height / np.ptp(elevations)
            samples = sample_surface(truth, mesh["faces"], 12000, 2473)
            tree = cKDTree(samples)
            bands = {"head": (.86*height, height+1e-8), "torso_and_arms": (.54*height, .86*height),
                     "lower_body": (-1e-8, .54*height)}
            supported = (*morph_controls(body), *length_controls(body), *regional_controls(body))
            for folder in sorted((clothes / identity).iterdir()):
                if (identity, folder.name) in completed:
                    continue
                views, masks, cameras = [], {}, {}
                for yaw in (0, 90):
                    source = folder / f"composite-{yaw}.png"
                    visible = load_mask(source)
                    body_only = load_mask(folder / f"body_only-{yaw}.png")
                    reference = Image.open(source).convert("RGBA")
                    photo = Image.new("RGBA", reference.size, (230, 230, 230, 255))
                    photo.alpha_composite(reference)
                    path = work / f"{identity}-{folder.name}-{yaw}.png"
                    photo.convert("RGB").save(path)
                    digest = sha256(path.read_bytes()).hexdigest()
                    det = detector.detect(path, digest)
                    record = dict(yaw=yaw, candidates=len(det.candidates), review_reason=det.review_reason,
                                  composite_to_body_iou=compare(body_only, visible)["iou"])
                    if len(det.candidates) == 1:
                        pose = det.candidates[0]
                        record["observed_count"] = sum(p.observed for p in pose)
                        record["yaw_deg"] = estimate_world_yaw(pose, det.world_landmarks[0] if det.world_landmarks else ())
                        if len(det.masks) == 1 and det.masks[0] is not None:
                            actual = Image.open(BytesIO(det.masks[0])).convert("1")
                            record |= dict(mask_to_clothed_iou=compare(visible, actual)["iou"],
                                           mask_to_body_iou=compare(body_only, actual)["iou"])
                            masks[yaw] = SubjectMask(digest, 0, det.masks[0])
                            camera = camera_for(yaw, height)
                            camera = replace(camera, similarity=camera.similarity*10*factor,
                                             origin=camera.origin + camera.similarity*complex(0, elevations.min()*10*factor))
                            cameras[yaw] = Alignment(camera, 0, {})
                    views.append(record)
                result = dict(identity=identity, condition=folder.name, views=views, used_fit_views=list(masks))
                if len(masks) == 2:
                    score = _scorer(body, masks, cameras, base)
                    controls, scores = _optimize(body, score, {}, supported, (.25,))
                    x, y, z = np.asarray(deform_vertices(body, controls)).T
                    prediction = np.column_stack((x, -z, y-elevations.min()))*factor
                    result.update(controls=controls, training_iou=scores,
                                  body_surface=metric_distance(samples, tree,
                                      sample_surface(prediction, faces, 12000, 2473), bands))
                rows.append(result)
                output.write_text(json.dumps(rows, indent=2, allow_nan=False)+"\n")
    finally:
        detector.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("previous", "dataset", "clothes", "work", "output"):
        parser.add_argument(name, type=Path)
    main(**vars(parser.parse_args()))
