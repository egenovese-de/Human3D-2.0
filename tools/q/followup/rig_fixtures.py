# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate independent MB-Lab skinning fixtures and calibrated views (local only)."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


POSES = {
    "neutral": {},
    "pelvis_spine_flex": {"pelvis": (8, -9, 12), "spine01": (-13, 0, 0), "spine02": (-10, 0, 7),
                          "spine03": (-8, 0, 8), "clavicle_L": (0, 12, 0), "head": (7, 0, 12)},
    "pelvis_spine_extend": {"pelvis": (-7, 9, -12), "spine01": (11, 0, 0), "spine02": (8, 0, -7),
                            "spine03": (5, 0, -8), "clavicle_R": (0, -14, 0), "head": (-6, 0, -10)},
    "wrist_torsion": {"upperarm_L": (10, 20, -23), "lowerarm_L": (26, 30, 8), "hand_L": (0, 45, 0),
                      "lowerarm_R": (22, -30, -10), "hand_R": (0, -50, 0)},
    "raised_foot": {"thigh_L": (-30, 7, 3), "calf_L": (55, 0, 0), "foot_L": (-20, 0, 0),
                    "upperarm_R": (13, 0, 10), "head": (6, 10, 0)},
    "seated": {"thigh_L": (-80, 0, 7), "thigh_R": (-80, 0, -7), "calf_L": (90, 0, 0),
               "calf_R": (90, 0, 0), "spine01": (-10, 0, 0)},
}


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_subject(bodies, skeleton, data, source, morphology=False):
    family = "human_female" if source.name.startswith("f_") else "human_male"
    if source.stem[2:6] in {"an01", "an02"}:
        family = family.replace("human", "anime")
    original = bodies[family]
    body = original.copy()
    body.data = original.data.copy()
    body.parent = None
    body.modifiers.clear()
    body.animation_data_clear()
    bpy.context.collection.objects.link(body)
    rig = skeleton.copy()
    rig.data = skeleton.data.copy()
    rig.animation_data_clear()
    bpy.context.collection.objects.link(rig)
    positions = [Vector(x) for x in read(source)]
    floor = min(x.z for x in positions)
    height = max(x.z for x in positions) - floor
    for vertex, point in zip(body.data.vertices, positions, strict=True):
        point.z -= floor
        if morphology:
            h = point.z / height
            side = max(0, min(1, point.x / .15))
            point.y -= .025 * side * math.exp(-((h - .72) / .09) ** 2)
            point.x += .018 * side * math.exp(-((h - .75) / .07) ** 2)
            point.z += .012 * side * math.exp(-((h - .81) / .06) ** 2)
            calf = max(0, min(1, -point.x / .12)) * math.exp(-((h - .22) / .065) ** 2)
            point.x -= .013 * calf
            point.y -= .010 * calf
        vertex.co = point
    for group in tuple(body.vertex_groups):
        body.vertex_groups.remove(group)
    for name, entries in read(data / "vgroups" / f"{family}_vgroups_base.json").items():
        group = body.vertex_groups.new(name=name)
        for index, value in entries:
            group.add([index], value, "REPLACE")
    tags = read(data / "joints" / f"{family}_joints.json")
    offset_path = data / "joints" / f"{family}_joints_offset.json"
    offsets = read(offset_path) if offset_path.exists() else {}
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for bone in rig.data.edit_bones:
        bone.use_connect = False
    for bone in rig.data.edit_bones:
        for endpoint in ("head", "tail"):
            key = f"{bone.name}_{endpoint}"
            if key in tags:
                anchor = sum((positions[i] for i in tags[key]), Vector()) / len(tags[key])
                setattr(bone, endpoint, anchor + Vector(offsets.get(key, [0, 0, 0])))
    bpy.ops.object.mode_set(mode="OBJECT")
    for bone in rig.pose.bones:
        for constraint in tuple(bone.constraints):
            bone.constraints.remove(constraint)
        bone.rotation_mode = "XYZ"
        bone.matrix_basis = Matrix.Identity(4)
    armature = body.modifiers.new("Independent MB-Lab weights", "ARMATURE")
    armature.object = rig
    return body, rig, family, height


def matrix_list(m):
    return [list(row) for row in m]


def run(upstream, output):
    data = upstream / "data"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (.48, .27, .18)
    scene.display.shading.show_shadows = False
    camera = bpy.data.objects.new("Calibrated", bpy.data.cameras.new("Calibrated"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.16
    with bpy.data.libraries.load(str(data / "humanoid_library.blend")) as (_, dst):
        dst.objects = ["MBLab_human_female", "MBLab_human_male", "MBLab_anime_female", "MBLab_anime_male", "MBLab_skeleton_base_fk"]
    female, male, anime_female, anime_male, skeleton = dst.objects
    bodies = {"human_female": female, "human_male": male,
              "anime_female": anime_female, "anime_male": anime_male}

    for source in sorted((data / "vertices").glob("*_verts.json")):
        identity = source.name.removesuffix("_verts.json")
        extended = identity in {"f_af01", "m_la01"}
        for morphology in ((False, True) if extended else (False,)):
            body, rig, family, height = set_subject(bodies, skeleton, data, source, morphology)
            faces = [list(poly.vertices) for poly in body.data.polygons]
            center = Vector((0, 0, height / 2))
            conditions = POSES.items() if extended and not morphology else [("neutral", {})]
            for label, angles in conditions:
                target = output / (identity + ("_morph" if morphology else "") + "_" + label)
                target.mkdir(parents=True, exist_ok=True)
                if (target / "manifest.json").exists():
                    continue
                for bone in rig.pose.bones:
                    bone.rotation_euler = tuple(map(math.radians, angles.get(bone.name, (0, 0, 0))))
                bpy.context.view_layer.update()
                evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
                mesh_hash = write(target / "mesh.json", {"vertices": [list(v.co) for v in evaluated.data.vertices],
                                                         "faces": faces})
                bones = {b.name: {"parent": b.parent.name if b.parent else None,
                                   "rest_global": matrix_list(b.bone.matrix_local),
                                   "posed_global": matrix_list(b.matrix),
                                   "pose_basis": matrix_list(b.matrix_basis),
                                   "head": list(b.head), "tail": list(b.tail)}
                         for b in rig.pose.bones}
                views = []
                for yaw in ((0, 22.5, 90, 112.5) if extended else (0, 90)):
                    rad = math.radians(yaw)
                    camera.location = center + Vector((4 * math.sin(rad), -4 * math.cos(rad), 0))
                    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
                    bpy.context.view_layer.update()
                    path = target / f"yaw-{yaw:g}.png"
                    scene.render.filepath = str(path.resolve())
                    bpy.ops.render.render(write_still=True)
                    views.append({"file": path.name, "yaw": yaw, "held_out": yaw % 90 != 0,
                                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                  "camera_to_world": matrix_list(camera.matrix_world)})
                write(target / "manifest.json", {"identity": identity, "source_family": family,
                      "pose": label, "morphology_asymmetry": morphology, "height_m": height,
                      "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "mesh_sha256": mesh_hash,
                      "joint_local_euler_xyz_deg": angles, "bones": bones, "images": views,
                      "camera_scale_m": 2.16, "resolution_px": 384, "camera_center_m": list(center),
                      "coordinates": "Blender XYZ metres, Z up and -Y frontal"})
            bpy.data.objects.remove(body, do_unlink=True)
            bpy.data.objects.remove(rig, do_unlink=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    parser.add_argument("output", type=Path)
    run(**vars(parser.parse_args()))
