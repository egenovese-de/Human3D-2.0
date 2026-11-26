import json
import sys
from pathlib import Path
import numpy as np
from human3d.frozen_body import deform_vertices, load_project_body
from human3d.garments import posed_garment, prototype
from human3d.native_rig import pose_transforms, rebind_joints, skin_vertices
from human3d.session import Session

root, output = map(Path, sys.argv[1:])
rest = Session(next(root.glob("*_f_af01_bend0-1")) / "project")
target = Session(next(root.glob("*_f_af01_bend32-1")) / "project")
body = load_project_body(rest.store)
neutral = deform_vertices(body, {})
rig = body["rig"]
view = target.shared_evidence().views[0]
alignment = target.current_shared_fit().alignments[view.ref.photo_id]
transforms = pose_transforms(rig, rebind_joints(rig, neutral), alignment)
shell = prototype(body, neutral, "shorts")

def blender_axes(points):
    x, y, z = np.asarray(points).T
    return np.column_stack((x, -z, y)).tolist()

def triangles(faces):
    return [(face[0][0], face[i][0], face[i + 1][0]) for face in faces for i in range(1,len(face)-1)]

pack = {"body": blender_axes(skin_vertices(neutral, rig["skin"], transforms)),
        "body_triangles": triangles([face["corners"] for face in body["mesh"]["faces"] if face["group"] == "body"]),
        "garment": blender_axes(posed_garment(shell, transforms)),
        "garment_triangles": triangles(shell.faces)}
output.write_text(json.dumps(pack))
