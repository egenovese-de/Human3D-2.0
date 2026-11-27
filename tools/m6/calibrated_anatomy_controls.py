"""Check authored joint frames and projection with an analytic reference and Blender."""
import argparse
from hashlib import sha256
import json
from math import radians
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
import numpy as np

from audit_bind_frames import SOURCE_TO_CANONICAL, angular_distance, revision


def anatomical_frame(longitudinal, transverse):
    """Return an anatomical basis only when the transverse direction is identifiable."""
    along = np.asarray(longitudinal, dtype=float)
    hint = np.asarray(transverse, dtype=float)
    length = np.linalg.norm(along)
    if length <= 1e-10:
        return None
    along /= length
    across = hint - along * (hint @ along)
    width = np.linalg.norm(across)
    if width <= 1e-6 * max(np.linalg.norm(hint), 1e-10):
        return None
    across /= width
    return np.column_stack((across, along, np.cross(across, along)))


def rotations():
    # Authored reference directions exercise non-axis-aligned, reflected and axial poses.
    controls = (
        ("shoulder", (2, 1, 1), (0, 1, 0)),
        ("hip", (1, 3, -2), (1, 0, 0)),
        ("elbow", (2, -1, 1), (0, 0, 1)),
        ("knee", (1, -3, 1), (1, 0, 0)),
        ("wrist", (2, 1, -1), (0, 1, 1)),
        ("ankle", (-1, -2, 1), (1, 0, 0)),
        ("foot", (1, 0, 2), (0, 1, 0)),
        ("pelvis", (1, 2, 1), (1, 0, 0)),
        ("spine", (0, 2, 1), (1, 0, 0)),
        ("neck", (0, 2, -1), (1, 0, 1)),
        ("head", (-1, 2, 0), (1, 0, 0)),
    )
    rows = []
    transform = Matrix(SOURCE_TO_CANONICAL.tolist())
    for name, longitudinal, transverse in controls:
        source = anatomical_frame(longitudinal, transverse)
        target = anatomical_frame(SOURCE_TO_CANONICAL @ longitudinal, SOURCE_TO_CANONICAL @ transverse)
        for axis, label in enumerate("XYZ"):
            for angle in (-35, 35):
                local = Matrix.Rotation(radians(angle), 3, label)
                actual = target @ np.asarray(local) @ target.T
                source_frame = Matrix(source.tolist())
                expected = transform @ source_frame @ local @ source_frame.transposed() @ transform.transposed()
                pivot = np.array([.07, .63, .25])
                test = np.array([.04, .15, .09])
                observed = pivot + actual @ test
                truth = pivot + np.asarray(expected @ Vector(test))
                rows.append(dict(joint=name, axis=axis, signed_degrees=angle,
                                 global_geodesic_error_deg=angular_distance(actual, np.asarray(expected)),
                                 local_geodesic_error_deg=angular_distance(target.T @ actual @ target, np.asarray(local)),
                                 point_error_mm=float(np.linalg.norm(observed - truth) * 1000),
                                 length_error_mm=float(abs(np.linalg.norm(observed - pivot) - np.linalg.norm(test)) * 1000)))
    assert anatomical_frame((0, 1, 0), (0, 3, 0)) is None
    return rows


def projections():
    from bpy_extras.object_utils import world_to_camera_view

    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 640, 480
    camera = bpy.data.objects.new("calibrated_orthographic", bpy.data.cameras.new("oracle"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0, 0, 4)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.4
    bpy.context.view_layer.update()
    width, height = scene.render.resolution_x, scene.render.resolution_y
    rows = []
    # The 33 points are indexing/coordinate probes, with no anatomical labels.
    for index in range(33):
        source = np.array([((index % 7) - 3) * .11, ((index // 7) - 2) * .13, (index % 4) * .1])
        canonical = SOURCE_TO_CANONICAL @ source
        recovered = SOURCE_TO_CANONICAL.T @ canonical
        observed = world_to_camera_view(scene, camera, Vector(source))
        expected = np.array([width / 2 + source[0] * width / 2.4,
                             height / 2 - source[1] * width / 2.4])
        pixels = np.array([observed.x * width, (1 - observed.y) * height])
        rows.append(dict(index=index, source_m=source.tolist(), pixel=expected.tolist(),
                         error_px=float(np.linalg.norm(pixels - expected)),
                         canonical_roundtrip_mm=float(np.linalg.norm(recovered - source) * 1000)))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = dict(candidate_sha=revision(args.candidate), lab_sha=revision(Path(__file__).parents[2]),
                  blender=bpy.app.version_string, controls_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope="analytic controls; independent computations, not independent human anatomical annotations",
                  rotations=rotations(), projections=projections(), collinear_twist_underdetermined=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
