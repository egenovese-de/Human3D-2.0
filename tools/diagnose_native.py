"""Measure result-to-mask overlap, pose invariants and export clearance."""
import argparse
from io import BytesIO
import json
from pathlib import Path

import numpy as np
from PIL import Image
from pxr import Usd

from benchmark_geometry import compare, silhouette
from human3d.alignment import Camera
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.native_rig import pose_transforms, posed_segments, skin_vertices, validate_pose, validate_rebind
from human3d.session import Session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run
    metrics = json.loads((run / "benchmark.json").read_text())
    session = Session(run / "project")
    shared = session.current_shared_fit()
    body = load_project_body(session.store)
    vertices = deform_vertices(body, shared.fit.controls)
    rig = body["rig"]
    joints = validate_rebind(body, vertices)
    faces = [tuple(i for i, _ in face["corners"]) for face in body["mesh"]["faces"] if face["group"] == "body"]
    body_vertices = sorted({i for face in faces for i in face})
    names = {photo: name for name, photo in metrics["photo_ids"].items()}
    report = {"views": {}}
    output = run / "diagnostics"
    output.mkdir(exist_ok=True)
    for view in session.shared_evidence().views:
        key = view.ref.photo_id
        if key not in shared.scores or view.mask is None:
            continue
        name = names[key]
        alignment = shared.alignments[key]
        transforms = pose_transforms(rig, joints, alignment)
        posed = skin_vertices(vertices, rig["skin"], transforms)
        validate_pose(body, vertices, posed)
        segments = posed_segments(rig, joints, alignment)
        bone_error = max(abs(np.linalg.norm(tail - head) - np.linalg.norm(
            joints[rig["bones"][bone]["tail"]] - joints[rig["bones"][bone]["head"]]))
            for bone, (head, tail) in segments.items())
        with Image.open(BytesIO(view.mask.png)) as img:
            size = tuple(max(1, round(v * 512 / max(img.size))) for v in img.size)
            scale = 512 / max(img.size)
            observed = img.resize(size, Image.Resampling.NEAREST).convert("1")
        camera = alignment.camera
        projected_camera = Camera(camera.yaw_degrees, camera.similarity * scale,
                                  camera.origin * scale, camera.horizontal_sign)
        predicted = silhouette(posed, faces, projected_camera, size)
        overlap = compare(observed, predicted)
        a, b = np.asarray(observed), np.asarray(predicted)
        Image.fromarray(np.stack((a, b, np.zeros_like(a)), axis=2).astype(np.uint8) * 255).save(
            output / (Path(name).stem + "_overlay.png"))
        report["views"][name] = overlap | {"bone_length_max_error": float(bone_error),
            "wrist_cross_axes": getattr(alignment, "wrist_cross_axes", {}),
            "lowest_body_vertex_model_y": float(posed[body_vertices, 1].min())}
    for artifact in ("native.usdz", "garment.usdz"):
        if not (run / artifact).exists():
            continue
        stage = Usd.Stage.Open(str(run / artifact))
        support = stage.GetDefaultPrim().GetCustomDataByKey("supportPlaneY")
        report[artifact] = {"support_plane_model_y": support,
                            "metadata": stage.GetRootLayer().customLayerData}
    (output / "diagnostics.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
