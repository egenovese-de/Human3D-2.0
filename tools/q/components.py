"""Measure pose and garment structural diagnostics on recovered photographic poses."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
from pxr import Usd, UsdGeom, UsdSkel

from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import CATEGORIES, correct_clearance, posed_garment, prototype
from human3d.native_rig import pose_transforms, posed_segments, skin_vertices, validate_rebind
from human3d.session import Session


def main(native, output):
    output.mkdir(parents=True, exist_ok=True)
    for source in sorted(native.glob("*-1/benchmark.json")):
        report = json.loads(source.read_text())
        if "fit" not in report:
            continue
        session = Session(source.parent / "project")
        body = load_project_body(session.store)
        shared = session.current_shared_fit()
        vertices = deform_vertices(body, shared.fit.controls)
        rig = body["rig"]
        joints = validate_rebind(body, vertices)
        alignment = shared.alignments[report["photo_ids"]["rgb-yaw-0.png"]]
        transforms = pose_transforms(rig, joints, alignment)
        posed = skin_vertices(vertices, rig["skin"], transforms)
        segments = posed_segments(rig, joints, alignment)
        lengths = [
            abs(np.linalg.norm(np.asarray(joints[rig["bones"][name]["head"]]) -
                               joints[rig["bones"][name]["tail"]]) -
                np.linalg.norm(np.asarray(a) - b)) * 100
            for name, (a, b) in segments.items()
        ]
        garments = {}
        for category in CATEGORIES:
            shell = prototype(body, vertices, category, ease_mm=3)
            corrected, clearance = correct_clearance(shell, body, posed, transforms)
            garments[category] = asdict(clearance) | {
                "minimum_signed_sample_mm": 100 * clearance.minimum,
                "topology_uv_preserved": shell.faces == corrected.faces and shell.uv == corrected.uv,
                "max_pose_vertex_motion_mm": float(np.linalg.norm(
                    posed_garment(corrected, transforms) - corrected.points, axis=1).max() * 100),
            }
        stage = Usd.Stage.Open(str(source.parent / "native.usdz"))
        result = {"max_bone_length_change_mm": max(lengths), "bones": len(lengths),
                  "garment_clearance": garments, "observed_uv_fraction": report.get("observed_uv_fraction"),
                  "usdz_meshes": sum(prim.IsA(UsdGeom.Mesh) for prim in stage.Traverse()),
                  "usdz_skeletons": sum(prim.IsA(UsdSkel.Skeleton) for prim in stage.Traverse())}
        (output / (source.parent.name + ".json")).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("native", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
