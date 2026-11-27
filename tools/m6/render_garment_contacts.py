# SPDX-License-Identifier: GPL-3.0-or-later
"""Render two views of the same posed Q body and garment, showing Blender triangle contacts."""
import json
from pathlib import Path
import sys
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree

pack_path, output, label = sys.argv[sys.argv.index("--") + 1:]
pack, out = Path(pack_path), Path(output)
fixture = json.loads(pack.read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 780
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "BOTH"
scene.display.shading.background_type = "WORLD"
scene.world = bpy.data.worlds.new("Background")
scene.world.color = (.14, .165, .2)

def mesh(name, vertices, faces, color):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.)
    data.materials.append(material)
    for polygon in data.polygons:
        polygon.use_smooth = True
    return obj

body = mesh("Canonical posed body", fixture["body"], fixture["body_triangles"], (.52, .59, .66))
garment = mesh("Native posed garment", fixture["garment"], fixture["garment_triangles"], (.13, .40, .58))
trees = [BVHTree.FromPolygons(fixture[item], fixture[item + "_triangles"], all_triangles=True)
         for item in ("body", "garment")]
pairs = trees[0].overlap(trees[1])
expected = fixture.get("expected_blender_pairs", 34)
if expected is not None:
    assert len(pairs) == expected, pairs
if not pairs:
    raise ValueError("No contacts to visualize")

highlight = bpy.data.materials.new("Triangles participating in intersection")
highlight.diffuse_color = (.95, .20, .065, 1)
garment.data.materials.append(highlight)
body.data.materials.append(highlight)

points = [Vector(p) for p in fixture["garment"]]
center = Vector(tuple((min(p[i] for p in points) + max(p[i] for p in points)) / 2 for i in range(3)))
camera = bpy.data.objects.new("Fixed comparison camera", bpy.data.cameras.new("Camera"))
scene.collection.objects.link(camera)
camera.data.type = "ORTHO"
camera.data.ortho_scale = 17.5
contact_centers = [sum((points[i] for i in fixture["garment_triangles"][b]), Vector()) / 3
                   for _, b in pairs]
contact_center = sum(contact_centers, Vector()) / len(contact_centers)
direction = 1 if contact_center.y > center.y else -1
camera.location = center + Vector((4.8, direction * 28., 11.))
camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = camera
if label == "triangles":
    body.hide_render = True
    for _, index in pairs:
        garment.data.polygons[index].material_index = 1
    garment.data.update()
    bpy.context.view_layer.update()
    projected = [world_to_camera_view(scene, camera, point) for point in contact_centers]
    (out / "projected-contacts.json").write_text(json.dumps([[point.x, point.y] for point in projected]))
scene.render.filepath = str((out / (label + ".png")).resolve())
bpy.ops.render.render(write_still=True)
