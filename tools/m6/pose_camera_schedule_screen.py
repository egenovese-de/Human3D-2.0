"""Compare block order over the same bounded pose and camera search budget."""
import argparse
from dataclasses import replace
import json
from math import radians
from pathlib import Path
from statistics import mean
from time import perf_counter

import numpy as np

from audit_bind_frames import revision
from benchmark_geometry import compare, silhouette
from evaluate import camera_for, load_mask
from human3d.fitting import _scorer
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, posed_segments, rebind_joints, skin_vertices
from human3d.session import Session

BONE = "lowerarm01.L"
SCHEDULES = {"pose_first": "PPCC", "camera_first": "CCPP", "alternating": "PCPC"}


def screen(folder, project):
    meta = json.loads((folder / "manifest.json").read_text())
    truth = np.asarray(json.loads((folder / "mesh.json").read_text())["vertices"])
    height = np.ptp(truth[:, 2])
    session = Session(project)
    view = session.shared_evidence().views[0]
    native = session.current_shared_fit().alignments[view.ref.photo_id]
    body = load_project_body(session.store)
    rig = body["rig"]
    geometry = np.asarray(deform_vertices(body, {}))
    joints = rebind_joints(rig, geometry)
    faces = [tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"] if face["group"] == "body"]
    y = geometry[np.unique(np.concatenate(faces)), 1]
    world_scale = height / np.ptp(y)
    anchor = np.diff(meta["joint_anchors"]["lowerarm_L"], axis=0)[0]
    masks = {frame["yaw"]: load_mask(folder / frame["file"]) for frame in meta["images"] if frame["held_out"]}
    center = complex(*[size / 2 for size in view.detection.image_size])

    def model_to_world(points):
        x, vertical, z = np.asarray(points).T
        return np.column_stack((x, -z, vertical - y.min())) * world_scale

    def metrics(alignment):
        segment = model_to_world(posed_segments(rig, joints, alignment)[BONE])
        direction = np.diff(segment, axis=0)[0]
        cosine = (direction @ anchor) / (np.linalg.norm(direction) * np.linalg.norm(anchor))
        posed = skin_vertices(geometry, rig["skin"], pose_transforms(rig, joints, alignment))
        x, vertical, z = model_to_world(posed).T
        canonical = np.column_stack((x, z, -vertical)) * 10
        iou = {yaw: compare(mask, silhouette(canonical, faces, camera_for(yaw, height), mask.size))["iou"]
               for yaw, mask in masks.items()}
        return dict(direction_error_deg=float(np.degrees(np.arccos(np.clip(cosine, -1, 1)))),
                    held_out_iou=iou, held_out_mean_iou=mean(iou.values()))

    def alignment_for(state):
        angle, dx, dy, scale_steps = state
        scale = 1 + .025 * scale_steps
        camera = replace(native.camera, similarity=native.camera.similarity * scale,
                         origin=center + (native.camera.origin - center) * scale + complex(dx, dy))
        angles = native.limb_angles | {BONE: native.limb_angles[BONE] + radians(angle)}
        return replace(native, camera=camera, limb_angles=angles)

    def training(state):
        alignment = alignment_for(state)
        return _scorer(body, {0: view.mask}, {0: alignment}, geometry, edge=128)(geometry)[0]

    seed = (0, 0, 0, 0)
    initial = training(seed)
    results = {"native": dict(training_iou=initial, **metrics(native))}
    for label, schedule in SCHEDULES.items():
        state, best, calls = seed, initial, 1
        visits = {"P": 0, "C": 0}
        start = perf_counter()
        for block in schedule:
            coarse = visits[block] == 0
            visits[block] += 1
            parameters = [(0, 10 if coarse else 5)] if block == "P" else [
                (1, 4 if coarse else 2), (2, 4 if coarse else 2), (3, 2 if coarse else 1),
            ]
            for index, step in parameters:
                options = []
                for delta in (-step, step):
                    candidate = state[:index] + (state[index] + delta,) + state[index + 1:]
                    options.append((training(candidate), candidate))
                    calls += 1
                score, proposal = max(options, key=lambda result: result[0])
                if score > best + 1e-8:
                    best, state = score, proposal
        results[label] = dict(state=state, training_iou=best, evaluations=calls,
                              seconds=perf_counter() - start, **metrics(alignment_for(state)))
    return dict(identity=meta["identity"], fixture_sha256=meta["mesh_sha256"], compared=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "original_q_workspace", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    root = args.original_q_workspace
    cases = [screen(folder, root / "holdout-native" / (folder.name + "-1") / "project")
             for folder in sorted((root / "holdout").glob("*_bend32"))]
    report = dict(candidate_sha=revision(args.candidate), lab_sha=revision(Path(__file__).parents[2]), cases=cases)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
