# SPDX-License-Identifier: GPL-3.0-or-later
"""Render native topology, sampled error color and released UV texture in Blender."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

from comparison import mesh_object


def main(pack, frozen, texture, output):
    output.mkdir(parents=True, exist_ok=True)
    data = json.loads(pack.read_text())
    source = json.loads(frozen.read_text())["mesh"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = "RGB"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_shadows = False
    obj = mesh_object(scene, "native reconstruction", data["meshes"]["native"])
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.16
    center = Vector((0, 0, data["height"] / 2))
    truth = data["meshes"]["ground-truth"]["vertices"]
    tree = KDTree(len(truth))
    for idx, vec in enumerate(truth):
        tree.insert(vec, idx)
    tree.balance()
    colors = obj.data.color_attributes.new(name="Nearest reference vertex", type="FLOAT_COLOR", domain="POINT")
    for vertex, attr in zip(obj.data.vertices, colors.data):
        distance = tree.find(vertex.co)[2]
        t = min(1, distance / .12)
        attr.color = (t, .25 * (1 - t), .8 * (1 - t), 1)
    obj.data.color_attributes.active_color = colors
    uv = obj.data.uv_layers.new(name="Release UV")
    source_faces = [f for f in source["faces"] if f["group"] == "body"]
    for face, original in zip(obj.data.polygons, source_faces, strict=True):
        for loop_index, (vertex_index, uv_index) in zip(face.loop_indices, original["corners"], strict=True):
            assert obj.data.loops[loop_index].vertex_index == vertex_index
            uv.data[loop_index].uv = source["texcoords"][uv_index]
    material = bpy.data.materials.new("Native albedo")
    obj.data.materials.append(material)
    material.use_nodes = True
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(str(texture.resolve()))
    material.node_tree.nodes.active = node
    wire = obj.modifiers.new("Diagnostic wire", "WIREFRAME")
    wire.thickness = .0012
    wire.show_render = False
    for style, color_mode in (("wire", "OBJECT"), ("distance", "VERTEX"), ("texture", "TEXTURE")):
        wire.show_render = style == "wire"
        scene.display.shading.color_type = color_mode
        for yaw in (0, 45, 90):
            a = math.radians(yaw)
            camera.location = center + Vector((4 * math.sin(a), -4 * math.cos(a), 0))
            camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = str((output / f"{style}-{yaw}.png").resolve())
            bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main(*map(Path, sys.argv[sys.argv.index("--") + 1:]))
