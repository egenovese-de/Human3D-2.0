# SPDX-License-Identifier: GPL-3.0-or-later
"""Render held-out clothed controls from Khronos Cesium Man (CC-BY-4.0)."""
from hashlib import sha256
import json
from math import radians, sin, cos
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from PIL import Image

asset, output = map(Path, sys.argv[sys.argv.index("--") + 1:])
output.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(asset.resolve()))
scene = bpy.context.scene
source = next(obj for obj in scene.objects if obj.type == "MESH")
rig = next(obj for obj in scene.objects if obj.type == "ARMATURE")
source.hide_render = True
camera = bpy.data.objects.new("Calibrated", bpy.data.cameras.new("Calibrated"))
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = 2.16
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 384
scene.render.resolution_y = 384
scene.render.resolution_percentage = 100
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = True
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_shadows = False


def acquire(frame, state):
    rig.data.pose_position = state
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = source.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    faces = [list(face.vertices) for face in mesh.polygons]
    evaluated.to_mesh_clear()
    return points, faces


base, _ = acquire(1, "REST")
source_height = max(point.z for point in base) - min(point.z for point in base)
scale = 1.8 / source_height
for label, frame, state in (("rest", 1, "REST"), ("animated", 18, "POSE")):
    points, faces = acquire(frame, state)
    floor = min(point.z for point in points)
    center_x = (min(point.x for point in points) + max(point.x for point in points)) / 2
    center_y = (min(point.y for point in points) + max(point.y for point in points)) / 2
    translate = Vector((center_x, center_y, floor))
    points = [(point - translate) * scale for point in points]
    height = max(point.z for point in points)
    mesh = bpy.data.meshes.new(label)
    mesh.from_pydata(points, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(label, mesh)
    scene.collection.objects.link(obj)
    # Uniform material avoids redistributing the original trademark texture.
    obj.color = (.28, .46, .67, 1.)
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    destination = output / ("CesiumMan_" + label)
    destination.mkdir(exist_ok=True)
    mesh_file = destination / "mesh.json"
    mesh_file.write_text(json.dumps({"vertices": [list(point) for point in points], "faces": faces}))
    center = Vector((0., 0., height / 2.))
    rows = []
    for yaw in (0, 90, 180, 270, 22.5, 112.5):
        angle = radians(yaw)
        camera.location = center + Vector((4 * sin(angle), -4 * cos(angle), 0))
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        file = destination / f"yaw-{yaw:g}.png"
        scene.render.filepath = str(file.resolve())
        bpy.ops.render.render(write_still=True)
        source_raster = Image.open(file).convert("RGBA")
        rgb = Image.new("RGBA", source_raster.size, (122, 137, 150, 255))
        rgb.alpha_composite(source_raster)
        photo = destination / f"rgb-yaw-{yaw:g}.png"
        rgb.convert("RGB").save(photo)
        rows.append(dict(file=file.name, rgb_file=photo.name, sha256=sha256(file.read_bytes()).hexdigest(),
                         rgb_sha256=sha256(photo.read_bytes()).hexdigest(), yaw=yaw,
                         held_out=yaw in (22.5, 112.5), camera_to_world=[list(row) for row in camera.matrix_world]))
    joints = {bone.name: list((rig.matrix_world @ bone.head - translate) * scale) for bone in rig.pose.bones}
    manifest = dict(identity="CesiumMan", source_family="Khronos CesiumMan",
                    attribution="Cesium (2017), CC-BY-4.0, uniform material, floor normalization",
                    source_sha256=sha256(asset.read_bytes()).hexdigest(),
                    asset_license_url="https://github.com/KhronosGroup/glTF-Sample-Assets/blob/main/Models/CesiumMan/LICENSE.md",
                    frame=frame, pose_state=state, scene_scale=scale, camera="orthographic", ortho_scale_m=2.16,
                    rendered_height_m=height, skeleton_joint_centers_m=joints,
                    mesh_sha256=sha256(mesh_file.read_bytes()).hexdigest(), images=rows)
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    photo_rows = [dict(file=row["rgb_file"], sha256=row["rgb_sha256"], yaw=row["yaw"]) for row in rows if not row["held_out"]]
    for count in (1, 4):
        (destination / f"native-{count}.json").write_text(json.dumps(dict(images=photo_rows[:count]), indent=2) + "\n")
    bpy.data.objects.remove(obj, do_unlink=True)
