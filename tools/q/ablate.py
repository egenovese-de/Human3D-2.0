"""Matched Lab-only mask and orthographic camera interventions against native evidence."""
import argparse
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import numpy as np

from evaluate import camera_for, load_mask
from human3d import fitting
from human3d.alignment import Camera
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.mask_review import SubjectMask
from human3d.session import Session
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from benchmark_geometry import compare, silhouette


def main(pilot, native, output):
    output.mkdir(parents=True, exist_ok=True)
    original_refine = fitting.refine_views
    for folder in sorted(pilot.iterdir()):
        path = native / (folder.name + "-4")
        if not (path / "benchmark.json").exists():
            continue
        report = output / (folder.name + ".json")
        if report.exists():
            continue
        run = json.loads((path / "benchmark.json").read_text())
        if "fit" not in run:
            report.write_text(json.dumps({"native_error": run.get("error")}) + "\n")
            continue
        session = Session(path / "project")
        body = load_project_body(session.store)
        evidence = session.shared_evidence()
        metadata = json.loads((folder / "manifest.json").read_text())
        mesh = json.loads((folder / "mesh.json").read_text())
        height = np.ptp(np.asarray(mesh["vertices"])[:, 2])
        native_rows = {row["sha256"]: row for row in json.loads((folder / "native-4.json").read_text())["images"]}
        rest = np.asarray(deform_vertices(body, {}))
        faces = [tuple(i for i, _ in f["corners"]) for f in body["mesh"]["faces"] if f["group"] == "body"]
        body_y = rest[np.unique(np.concatenate(faces)), 1]
        floor = body_y.min()
        scale = 10 * height / np.ptp(body_y)
        truth_cameras, truth_masks, oracle_views = {}, {}, []
        for view in evidence.views:
            key = view.ref.photo_id
            if key not in run["fit"]["per_view_iou"]:
                continue
            row = native_rows[view.ref.photo_digest]
            mask = load_mask(folder / row["truth_mask"])
            truth_masks[key] = mask
            png = BytesIO()
            mask.save(png, format="PNG")
            oracle_views.append(replace(view, mask=SubjectMask(view.ref.photo_digest, view.candidate, png.getvalue())))
            cam = camera_for(row["yaw"], height)
            truth_cameras[key] = Camera(cam.yaw_degrees, cam.similarity * scale,
                                         cam.origin + cam.similarity * complex(0, floor * scale), 1)
        matched = replace(evidence, views=tuple(view for view in evidence.views
                                               if view.ref.photo_id in truth_masks))
        results = {}
        for name, use_mask, use_camera in (
            ("matched_native", False, False), ("mask_only", True, False),
            ("camera_only", False, True), ("mask_and_camera", True, True),
        ):
            def refine(model, evidence):
                views, missing = original_refine(model, evidence)
                if use_camera:
                    views = {key: replace(value, camera=truth_cameras[key]) for key, value in views.items()}
                return views, missing

            def no_refinement(body, vertices, masks, alignments):
                return alignments

            start = perf_counter()
            selected = replace(matched, views=tuple(oracle_views)) if use_mask else matched
            camera_final = no_refinement if use_camera else fitting._refine_silhouette_cameras
            with patch.object(fitting, "refine_views", refine), patch.object(
                fitting, "_refine_silhouette_cameras", camera_final
            ):
                fit = fitting.fit_shared(body, selected)
            vertices = deform_vertices(body, fit.fit.controls)
            joints = rebind_joints(body["rig"], vertices)
            scores = {}
            camera_errors = {}
            for key, estimate in fit.alignments.items():
                if key not in truth_masks:
                    continue
                mask = truth_masks[key]
                posed = skin_vertices(vertices, body["rig"]["skin"], pose_transforms(body["rig"], joints, estimate))
                scores[key] = compare(mask, silhouette(posed, faces, estimate.camera, mask.size))["iou"]
                truth = truth_cameras[key]
                camera_errors[key] = {
                    "yaw_abs_deg": abs((estimate.camera.yaw_degrees - truth.yaw_degrees + 180) % 360 - 180),
                    "height_aligned_scale_ratio": abs(estimate.camera.similarity / truth.similarity),
                    "height_aligned_origin_error_px": abs(estimate.camera.origin - truth.origin),
                }
            results[name] = {"independent_silhouette_iou": scores, "camera_errors": camera_errors,
                             "controls": fit.fit.controls, "seconds": perf_counter() - start}
        report.write_text(json.dumps({"fixture": metadata["subject"], "results": results}, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("pilot", "native", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(**vars(parser.parse_args()))
