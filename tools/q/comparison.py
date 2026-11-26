"""Render native and calibrated neutral comparison panels using identical Blender framing."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def mesh_object(scene, name, geometry):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(geometry["vertices"], [], geometry["faces"])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj.color = (.48, .27, .18, 1)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def main(pack, output):
    output.mkdir(parents=True, exist_ok=True)
    data = json.loads(pack.read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = "RGB"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
    shading.background_type = "WORLD"
    shading.show_shadows = False
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.16
    center = Vector((0, 0, data["height"] / 2))
    for name, geometry in data["meshes"].items():
        body = mesh_object(scene, name, geometry)
        for yaw in (0, 45, 90, 180):
            angle = math.radians(yaw)
            camera.location = center + Vector((4 * math.sin(angle), -4 * math.cos(angle), 0))
            camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str((output / f"{name}-{yaw}.png").resolve())
            bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(body, do_unlink=True)


if __name__ == "__main__":
    main(*map(Path, sys.argv[sys.argv.index("--") + 1:]))
