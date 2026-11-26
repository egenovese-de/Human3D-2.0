"""Progressive degradation and downstream preflight on frozen calibrated identities."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageFilter

from benchmark_geometry import compare, silhouette
from evaluate import load_mask
from human3d.alignment import initialize_alignment
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session
from human3d.vision import FULL_BODY_ANCHORS, PoseLandmarker, estimate_world_yaw


def treatments(image, mask):
    noise = np.random.default_rng(2471).standard_normal(np.asarray(image).shape)
    yield "clean", 0, image, mask
    for radius in (1, 2, 4, 6, 8, 12):
        yield "blur", radius, image.filter(ImageFilter.GaussianBlur(radius)), mask
    for quality in (80, 50, 30, 15, 8, 3):
        buffer = BytesIO()
        image.save(buffer, "JPEG", quality=quality)
        yield "jpeg_quality", quality, Image.open(buffer).convert("RGB"), mask
    for sigma in (4, 8, 16, 24, 40, 64):
        rgb = np.uint8(np.clip(np.asarray(image) + noise * sigma, 0, 255))
        yield "noise_sigma", sigma, Image.fromarray(rgb), mask
    for pixels in (8, 16, 24, 32, 48, 64):
        box = (0, pixels, image.width, image.height - pixels)
        yield "symmetric_vertical_crop_px", pixels, image.crop(box), mask.crop(box)
    for radius in (1, 2, 4, 6, 8, 12):
        blurred = image.filter(ImageFilter.GaussianBlur(radius))
        rgb = np.uint8(np.clip(np.asarray(blurred) + noise * (radius * 3), 0, 255))
        buffer = BytesIO()
        Image.fromarray(rgb).save(buffer, "JPEG", quality=max(5, 80 - radius * 6))
        yield "compound_blur_px", radius, Image.open(buffer).convert("RGB"), mask


def run(previous, work, output):
    work.mkdir(parents=True, exist_ok=True)
    detector = PoseLandmarker(previous / "assets/pose.task", segmentation=True)
    rows = []
    try:
        for folder in sorted((previous / "holdout").glob("*_bend0")):
            session = Session(previous / "holdout-native" / (folder.name + "-1") / "project")
            body = load_project_body(session.store)
            vertices = deform_vertices(body, {})
            rig = body["rig"]
            joints = rebind_joints(rig, vertices)
            faces = [tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"]
                     if face["group"] == "body"]
            for yaw in (0, 90, 270):
                image = Image.open(folder / f"rgb-yaw-{yaw}.png").convert("RGB")
                mask = load_mask(folder / f"yaw-{yaw}.png")
                cases = treatments(image, mask)
                for kind, level, variant, truth in cases:
                    if yaw and kind != "clean":
                        continue
                    path = work / f"{folder.name}-{yaw}-{kind}-{level}.png"
                    variant.save(path)
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    row = dict(fixture=folder.name, yaw=yaw, treatment=kind, level=level, sha256=digest)
                    started = perf_counter()
                    try:
                        item = detector.detect(path, digest)
                        row.update(candidates=len(item.candidates), review_reason=item.review_reason)
                        if len(item.masks) == 1 and item.masks[0] is not None:
                            row["mask_iou"] = compare(truth, Image.open(BytesIO(item.masks[0])).convert("1"))["iou"]
                        if len(item.candidates) == 1:
                            pose, = item.candidates
                            world = item.world_landmarks[0] if item.world_landmarks else ()
                            row["native_yaw_deg"] = estimate_world_yaw(pose, world)
                            row["missing_full_body_anchors"] = [i for i in FULL_BODY_ANCHORS if not pose[i].observed]
                            row["landmarks_observed"] = sum(point.observed for point in pose)
                            alignment = initialize_alignment(body, item, 0, refine=True)
                            posed = skin_vertices(vertices, rig["skin"], pose_transforms(rig, joints, alignment))
                            projected = silhouette(posed, faces, alignment.camera, truth.size)
                            row["posed_bootstrap_iou"] = compare(truth, projected)["iou"]
                    except (ValueError, RuntimeError) as error:
                        row["preflight_error"] = str(error)
                    row["elapsed_seconds"] = perf_counter() - started
                    rows.append(row)
                    output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    finally:
        detector.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("previous", "work", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
