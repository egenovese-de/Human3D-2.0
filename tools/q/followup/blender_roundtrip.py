"""Inspect, deform, save, reopen, edit and remove garment objects with Blender USD."""
import argparse
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Vector


def mesh_digest(obj):
    h = hashlib.sha256()
    for vertex in obj.data.vertices:
        h.update(repr(tuple(vertex.co)).encode())
    for polygon in obj.data.polygons:
        h.update(repr(tuple(polygon.vertices)).encode())
    return h.hexdigest()


def positions(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]


def armature_info(obj, rig):
    skin = {group.index for group in obj.vertex_groups if group.name in rig.data.bones}
    totals = [sum(entry.weight for entry in vertex.groups if entry.group in skin)
              for vertex in obj.data.vertices]
    return dict(vertices=len(totals), faces=len(obj.data.polygons), uv_layers=len(obj.data.uv_layers),
                mapped_groups=len(skin), weighted_vertices=sum(value > 0 for value in totals),
                max_weight_sum_error=max(abs(value - 1) for value in totals),
                armature_bound=any(m.type == "ARMATURE" and m.object == rig for m in obj.modifiers))


def inspect(source, directory):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    op = bpy.ops.wm.usd_import.get_rna_type().identifier
    if not bpy.app.build_options.usd or bpy.ops.wm.usd_import(filepath=str(source.resolve())) != {"FINISHED"}:
        raise RuntimeError("Direct USDZ import failed")
    rig, = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    body = bpy.context.scene.objects["Body"]
    garments = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.name != body.name]
    if not garments:
        raise RuntimeError("Imported scene contains no separate garment meshes")
    meshes = {obj.name: armature_info(obj, rig) for obj in [body, *garments]}
    before = mesh_digest(body)
    originals = {obj.name: positions(obj) for obj in garments}
    pose = {bone.name: [tuple(row) for row in bone.matrix_basis] for bone in rig.pose.bones}
    exaggerated = rig.pose.bones["upperarm01_L"]
    original_rotation = exaggerated.rotation_quaternion.copy()
    exaggerated.rotation_quaternion.rotate(Vector((0, 1, 0)).rotation_difference(Vector((0, .9, .4))))
    bpy.context.view_layer.update()
    movement = {obj.name: max((p - q).length for p, q in zip(originals[obj.name], positions(obj)))
                for obj in garments}
    exaggerated.rotation_quaternion = original_rotation
    bpy.context.view_layer.update()
    garment_names = [obj.name for obj in garments]
    rig_name = rig.name
    scene_file = directory / f"{source.parent.name}-{source.stem}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_file.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(scene_file.resolve()))
    rig = bpy.data.objects[rig_name]
    restored_pose = max(abs(a - b) for bone in rig.pose.bones
                        for left, right in zip(pose[bone.name], bone.matrix_basis) for a, b in zip(left, right))
    body = bpy.data.objects["Body"]
    edit_deltas = {}
    for name in garment_names:
        garment = bpy.data.objects[name]
        first = garment.data.vertices[0].co.copy()
        garment.data.vertices[0].co.x += .01
        garment.data.update()
        edit_deltas[name] = (garment.data.vertices[0].co - first).length
    edited = {name: mesh_digest(bpy.data.objects[name]) for name in garment_names}
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_file.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(scene_file.resolve()))
    persisted = {name: mesh_digest(bpy.data.objects[name]) for name in garment_names}
    edits_preserved = persisted == edited
    for name in garment_names:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    body_preserved = mesh_digest(bpy.data.objects["Body"]) == before
    return dict(blender=bpy.app.version_string, usd_operator=op, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                mesh_info=meshes, bones=len(pose), garment_pose_motion_scene_units=movement,
                pose_roundtrip_max_matrix_difference=restored_pose,
                imported_nonidentity_pose_matrix_elements=sum(abs(float(row[i]) - (i == j)) > 1e-5
                                                   for matrix in pose.values() for j, row in enumerate(matrix)
                                                   for i in range(4)),
                garment_edit_delta_scene_units=edit_deltas, persisted_edited_mesh_digest=persisted,
                vertex_edits_persisted=edits_preserved, body_preserved_after_garment_removal=body_preserved)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("source", nargs="+", type=Path)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    rows = []
    for source in args.source:
        try:
            rows.append({"fixture": source.parent.name, **inspect(source, args.work)})
        except (ValueError, RuntimeError, KeyError) as error:
            rows.append({"fixture": source.parent.name, "error": str(error)})
    args.output.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
