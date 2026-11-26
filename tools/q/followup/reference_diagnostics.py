"""Exercise reference ranking with one fixed target and eight controlled reference types."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageDraw

from benchmark_geometry import compare
from evaluate import load_mask
from human3d.vision import PoseLandmarker, estimate_world_yaw


def run(previous, clothes, work, output):
    work.mkdir(parents=True,exist_ok=True)
    detector = PoseLandmarker(previous/"assets/pose.task",segmentation=True)
    rows = []
    pairs = (("f_af01","f_ca01","m_la01"),("m_la01","m_as01","f_af01"))
    try:
        for identity, similar, other in pairs:
            fixture = lambda ident, bend=0: next((previous/"holdout").glob(f"*_{ident}_bend{bend}"))
            original = fixture(identity)
            alternate = {
                "complementary": original/"rgb-yaw-90.png",
                "redundant": original/"rgb-yaw-0.png",
                "same_identity_new_pose": fixture(identity,32)/"rgb-yaw-90.png",
                "same_identity_new_clothing": clothes/identity/"top"/"composite-90.png",
                "similar_other_identity": fixture(similar)/"rgb-yaw-90.png",
                "strongly_inconsistent": fixture(other)/"rgb-yaw-90.png",
                "same_identity_occluded": original/"rgb-yaw-90.png",
            }
            for label, source in alternate.items():
                started = perf_counter()
                raw = Image.open(source).convert("RGBA")
                photo = Image.new("RGBA",raw.size,(230,230,230,255))
                photo.alpha_composite(raw)
                photo = photo.convert("RGB")
                if label.endswith("occluded"):
                    ImageDraw.Draw(photo).rectangle((173,170,224,245),fill=(90,130,180))
                path = work/f"{identity}-{label}.png"
                photo.save(path)
                digest = sha256(path.read_bytes()).hexdigest()
                item = detector.detect(path,digest)
                n = len(item.candidates)
                yaw, count, mask_iou = None, 0, None
                if n == 1:
                    world = item.world_landmarks[0] if item.world_landmarks else ()
                    yaw = estimate_world_yaw(item.candidates[0],world)
                    count = sum(p.observed for p in item.visible_pose(0))
                if len(item.masks)==1 and item.masks[0] is not None:
                    angle = 0 if label=="redundant" else 90
                    mask_iou = compare(load_mask(original/f"yaw-{angle}.png"),
                                       Image.open(BytesIO(item.masks[0])).convert("1"))["iou"]
                # Candidate utility only. No identity claim is inferred from photo yaw.
                novelty = yaw is not None and abs(yaw) >= 30
                acceptable_geometry = n==1 and count>=17 and novelty
                acceptable_appearance = n==1 and count>=12 and novelty
                rows.append(dict(identity=identity,treatment=label,candidates=n,native_yaw_deg=yaw,
                    visible_landmarks=count,masked_reference_iou_to_neutral_for_evaluation=mask_iou,
                    reject_identity_ground_truth=label in {"similar_other_identity","strongly_inconsistent"},
                    geometry_policy_accept=acceptable_geometry,appearance_policy_accept=acceptable_appearance,
                    review_reason=item.review_reason,detector_and_policy_seconds=perf_counter()-started))
                output.write_text(json.dumps(rows,indent=2,allow_nan=False)+"\n")
    finally:
        detector.close()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("previous","clothes","work","output"):
        parser.add_argument(name,type=Path)
    run(**vars(parser.parse_args()))
