# SPDX-License-Identifier: GPL-3.0-or-later
"""Render camera-only perturbations and a compound case with exact masks."""
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np

from comparison import mesh_object


def main(pilot):
    for manifest in sorted(pilot.glob("*/manifest.json")):
        folder = manifest.parent
        truth = json.loads((folder / "mesh.json").read_text())
        height = np.ptp(np.asarray(truth["vertices"])[:, 2])
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.render.resolution_x = scene.render.resolution_y = 384
        scene.render.resolution_percentage = 100
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.film_transparent = True
        scene.display.shading.color_type = "OBJECT"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.show_shadows = False
        mesh_object(scene, "body", truth)
        cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
        scene.collection.objects.link(cam)
        scene.camera = cam
        center = Vector((0, 0, height / 2))
        rows = []
        for name, lens, distance, elevation in (
            ("wide-perspective", 25, 1.60, 0), ("long-perspective", 85, 5.1, 0),
            ("elevated", 50, 3.0, 30), ("low", 50, 3.0, -25),
        ):
            angle = math.radians(elevation)
            cam.data.lens = lens
            cam.location = center + Vector((0, -distance * math.cos(angle), distance * math.sin(angle)))
            cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
            bpy.context.view_layer.update()
            image = folder / f"{name}-alpha.png"
            scene.render.filepath = str(image.resolve())
            bpy.ops.render.render(write_still=True)
            rows.append({"file": image.name, "variant": name, "lens_mm": lens, "elevation_deg": elevation,
                         "distance_m": distance, "sensor_width_mm": cam.data.sensor_width,
                         "camera_to_world": [list(row) for row in cam.matrix_world],
                         "sha256": hashlib.sha256(image.read_bytes()).hexdigest()})
        (folder / "perspective.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main(Path(sys.argv[sys.argv.index("--") + 1]))
