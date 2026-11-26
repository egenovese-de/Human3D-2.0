"""Test supported external evidence with ray-derived region visibility."""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image

from benchmark_geometry import compare, silhouette
from evaluate import load_mask
from human3d.alignment import initialize_alignment
from human3d.anatomical_evidence import AnatomicalEvidence, RegionVisibility, yaw_conflicts
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session
from human3d.vision import PoseLandmarker, estimate_world_yaw


def run(dataset, previous, visibility, work, output):
    work.mkdir(parents=True, exist_ok=True)
    detector = PoseLandmarker(previous / "assets/pose.task", segmentation=True)
    rows = []
    try:
        for fixture in json.loads(visibility.read_text()):
            name = fixture["fixture"]
            if not (name.endswith("_neutral") and "_morph_" not in name or name.endswith("_seated")):
                continue
            identity = name.split("_", 2)[0] + "_" + name.split("_", 2)[1]
            session = Session(next((previous / "holdout-native").glob(f"*_{identity}_bend0-1")) / "project")
            body = load_project_body(session.store)
            points = deform_vertices(body, {})
            joints = rebind_joints(body["rig"], points)
            faces = [tuple(i for i, _ in item["corners"]) for item in body["mesh"]["faces"] if item["group"] == "body"]
            for view in fixture["views"]:
                yaw = view["yaw"]
                source = dataset / name / f"yaw-{yaw:g}.png"
                front = Image.open(source).convert("RGBA")
                photo = Image.new("RGBA", front.size, (230, 230, 230, 255))
                photo.alpha_composite(front)
                path = work / f"{name}-{yaw:g}.png"
                photo.convert("RGB").save(path)
                digest = sha256(path.read_bytes()).hexdigest()
                record = dict(fixture=name, yaw_deg=yaw, ray_mask_iou=view["sampled_mask_iou"], conditions={})
                native = detector.detect(path, digest)
                record.update(candidates=len(native.candidates), review_reason=native.review_reason)
                if view["sampled_mask_iou"] < .95 or len(native.candidates) != 1:
                    rows.append(record | {"exclusion": "visibility_calibration_or_candidate_gate"})
                    continue
                # Treat an entire region as hidden only if its visible projected area is below
                # 5% of its front-facing projected area. Confidence is deterministic within
                # the geometric model, rather than a detector probability.
                regions = tuple(RegionVisibility(region, fraction >= .05, 1)
                                for region, metric in view["regions"].items()
                                if (fraction := metric["visible_fraction_of_front_projected"]) is not None)
                camera_yaw = (-yaw+180) % 360-180
                provider = AnatomicalEvidence(digest, "calibrated_bvh", "regional_area_v1", 0, regions, camera_yaw, 1)
                native_yaw = estimate_world_yaw(native.candidates[0], native.world_landmarks[0] if native.world_landmarks else ())
                record.update(native_yaw_deg=native_yaw, provider_yaw_veto=yaw_conflicts(provider, native_yaw),
                              hidden_regions=[item.region for item in regions if not item.visible])
                expected = load_mask(source)
                for label, evidence in (("native", None), ("visibility", replace(provider, yaw=None, yaw_confidence=0)),
                                        ("yaw", replace(provider, regions=())), ("yaw_and_visibility", provider)):
                    detection = replace(native, anatomical=evidence)
                    result = dict(observed_landmarks=sum(p.observed for p in detection.visible_pose(0)))
                    try:
                        alignment = initialize_alignment(body, detection, 0, refine=True)
                        posed = skin_vertices(points, body["rig"]["skin"], pose_transforms(body["rig"], joints, alignment))
                        result |= dict(estimate_yaw_deg=alignment.camera.yaw_degrees,
                                       estimated_camera_poses_bootstrap_iou=compare(
                                           expected, silhouette(posed, faces, alignment.camera, expected.size))["iou"])
                    except ValueError as error:
                        result["error"] = str(error)
                    record["conditions"][label] = result
                rows.append(record)
                output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    finally:
        detector.close()
    output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("dataset", "previous", "visibility", "work", "output"):
        parser.add_argument(name, type=Path)
    run(**vars(parser.parse_args()))
