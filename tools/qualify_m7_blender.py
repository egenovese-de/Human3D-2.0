"""Import the actual M7 USD assets, edit and deform them, then reopen a Blender scene."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector


def evaluated_positions(mesh):
    updated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [vertex.co.copy() for vertex in updated.data.vertices]


def bindings(mesh):
    return sorted(slot.material.name for slot in mesh.material_slots if slot.material)


def snapshot(directory):
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                region = area.spaces.active.region_3d
                region.view_distance = 3.5
                region.view_rotation = Quaternion((1, 0, 0), 1.5707963268)
                region.view_location = (0, 0, .9)
    body = bpy.data.objects["Body"]
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("Evidence camera")
    camera = bpy.data.objects.new("Evidence camera", camera_data)
    scene.collection.objects.link(camera)
    bbox = [body.matrix_world @ Vector(point) for point in body.bound_box]
    center = sum(bbox, Vector()) / len(bbox)
    span = max(max(v[i] for v in bbox) - min(v[i] for v in bbox) for i in range(3))
    camera.location = center + Vector((1.7, -3, .7)) * span
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span * 1.33
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(directory)
    bpy.ops.render.render(write_still=True)


def verify(source, output):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    assert bpy.app.build_options.usd
    assert bpy.ops.wm.usd_import(filepath=str(source)) == {"FINISHED"}, source
    mesh = bpy.data.objects["Body"]
    rig, = [ob for ob in bpy.context.scene.objects if ob.type == "ARMATURE"]
    materials = bindings(mesh)
    counts = {"vertices": len(mesh.data.vertices), "faces": len(mesh.data.polygons),
              "uv_layers": len(mesh.data.uv_layers), "bones": len(rig.data.bones)}
    assert all(counts.values()), counts
    assert any(mod.type == "ARMATURE" and mod.object == rig for mod in mesh.modifiers)
    groups = {group.index for group in mesh.vertex_groups if group.name in rig.data.bones}
    weight_error = max(abs(1 - sum(g.weight for g in vertex.groups if g.group in groups))
                       for vertex in mesh.data.vertices)
    assert weight_error <= 1e-4, weight_error
    assert source.suffix != ".usdz" or materials, materials
    textures = sum(1 for material in bpy.data.materials if material.node_tree for node in material.node_tree.nodes
                   if node.type == "TEX_IMAGE" and node.image and len(node.image.pixels))
    assert source.suffix != ".usdz" or textures, "Textured package lost its image on import."
    animated = bool(rig.animation_data and rig.animation_data.action)
    identity_error = max(abs(value - (i == j)) for bone in rig.pose.bones
                         for i, row in enumerate(bone.matrix_basis) for j, value in enumerate(row))
    if "target" in source.stem:
        assert animated and identity_error > 1e-5, "Target articulation missing."
    before = evaluated_positions(mesh)
    bone = next(bone for bone in rig.pose.bones if "upperarm01" in bone.name)
    rotation = bone.rotation_quaternion.copy()
    bone.rotation_mode = "QUATERNION"
    bone.rotation_quaternion = rotation @ Quaternion((1, 0, 0), .34)
    bpy.context.view_layer.update()
    deformation = max((a - b).length for a, b in zip(before, evaluated_positions(mesh)))
    assert deformation > 1e-5, deformation
    bone.rotation_quaternion = rotation
    bpy.context.view_layer.update()
    mesh.data.vertices[0].co.x += .005
    mesh.data.update()
    expected = mesh.data.vertices[0].co.copy()
    name = mesh.name
    rig_name = rig.name
    for image in bpy.data.images:
        if image.source == "FILE" and image.has_data and not image.packed_file:
            image.pack()
    destination = output / (source.stem + ".blend")
    if "target" in source.stem:
        snapshot(output / (source.stem + "-blender.png"))
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    bpy.ops.wm.open_mainfile(filepath=str(destination))
    mesh = bpy.data.objects[name]
    assert (mesh.data.vertices[0].co - expected).length < 1e-7
    assert bindings(mesh) == materials and len(mesh.data.uv_layers) == counts["uv_layers"]
    restored = bpy.data.objects[rig_name]
    assert len(restored.data.bones) == counts["bones"]
    assert bool(restored.animation_data and restored.animation_data.action) == animated
    return {"source": source.name, "source_sha256": sha256(source.read_bytes()).hexdigest(),
            "blender": bpy.app.version_string, **counts, "max_weight_sum_error": weight_error,
            "materials": materials, "loaded_textures": textures, "imported_action": animated,
            "pose_nonidentity": identity_error, "max_skin_deformation": deformation,
            "editable_geometry_save_reopen": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("sources", type=Path, nargs="+")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = [verify(source.resolve(), output) for source in args.sources]
    (output / "blender-roundtrip.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
