"""Create a local renderer input for an existing observed garment configuration."""
import argparse
import json
from pathlib import Path

import numpy as np

from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import _body_faces, _triangulate, correct_clearance, posed_garment, prototype
from human3d.native_rig import pose_transforms, skin_vertices, validate_rebind
from human3d.session import Session


def run(project, output, ease):
    session = Session(project)
    fit = session.current_shared_fit()
    body = load_project_body(session.store)
    rig = body["rig"]
    neutral = deform_vertices(body, fit.fit.controls)
    target = session.store.load().photos.target
    transforms = pose_transforms(rig, validate_rebind(body, neutral), fit.alignments[target])
    posed = skin_vertices(neutral, rig["skin"], transforms)
    garment, _ = correct_clearance(prototype(body, neutral, "top", ease_mm=ease), body, posed, transforms)

    def blender_axes(points):
        x, y, z = np.asarray(points).T
        return np.column_stack((x, -z, y)).tolist()

    result = dict(body=blender_axes(posed), body_triangles=_triangulate(_body_faces(body)).tolist(),
                  garment=blender_axes(posed_garment(garment, transforms)),
                  garment_triangles=_triangulate(garment.faces).tolist(), expected_blender_pairs=None)
    output.write_text(json.dumps(result, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ease", type=float, default=6)
    run(**vars(parser.parse_args()))
