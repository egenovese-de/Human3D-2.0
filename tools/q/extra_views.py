# SPDX-License-Identifier: GPL-3.0-or-later
"""Render interleaved calibrated Blender cameras for a focused sixteen-view repeat."""
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

from comparison import mesh_object


def main(pilot, output, names):
    for name in names:
        meta = json.loads((pilot / name / "manifest.json").read_text())
        geometry = json.loads((pilot / name / "mesh.json").read_text())
        height = max(p[2] for p in geometry["vertices"])
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = scene.render.resolution_y = 384
        scene.render.resolution_percentage = 100
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.film_transparent = True
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "OBJECT"
        scene.display.shading.show_shadows = False
        obj = mesh_object(scene, "reference", geometry)
        cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
        scene.collection.objects.link(cam)
        scene.camera = cam
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = meta["ortho_scale_m"]
        center = Vector((0, 0, height / 2))
        folder = output / name
        folder.mkdir(parents=True, exist_ok=True)
        rows = []
        for yaw in [11.25 + step * 45 for step in range(8)]:
            a = math.radians(yaw)
            cam.location = center + Vector((4 * math.sin(a), -4 * math.cos(a), 0))
            cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
            bpy.context.view_layer.update()
            path = folder / f"yaw-{yaw:g}.png"
            scene.render.filepath = str(path.resolve())
            bpy.ops.render.render(write_still=True)
            rows.append({"yaw": yaw, "file": path.name, "camera_to_world": [list(row) for row in cam.matrix_world],
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        (folder / "manifest.json").write_text(json.dumps(rows, indent=2) + "\n")
        bpy.data.objects.remove(obj, do_unlink=True)


if __name__ == "__main__":
    source, output, *names = sys.argv[sys.argv.index("--") + 1:]
    main(Path(source), Path(output), names)
