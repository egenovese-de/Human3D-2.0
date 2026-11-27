# SPDX-License-Identifier: GPL-3.0-or-later
"""Render independent metric fixtures with Blender 4.3.2."""
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


def material(name, color):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1)
    return result


def main():
    library, destination, *holdout = map(Path, sys.argv[sys.argv.index("--") + 1:])
    destination.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = False
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.16
    with bpy.data.libraries.load(str(library)) as (_, destination_data):
        destination_data.objects = ["MBLab_human_female", "MBLab_human_male"]
    skin = material("Pilot skin", (.48, .27, .18))
    for body in destination_data.objects:
        family = body.name.removeprefix("MBLab_")
        if holdout:
            upstream = holdout[0]
            identities = ("f_ca01", "f_af01") if family == "human_female" else ("m_as01", "m_la01")
            variants = [(identity, angle) for identity in identities for angle in (0, 32)]
        else:
            variants = [(name, 0) for name in ("base", "wide", "asymmetric")]
        for variant, bend in variants:
            subject = body.copy()
            subject.data = body.data.copy()
            subject.animation_data_clear()
            subject.parent = None
            subject.modifiers.clear()
            subject.data.materials.clear()
            subject.data.materials.append(skin)
            scene.collection.objects.link(subject)
            for polygon in subject.data.polygons:
                polygon.material_index = 0
                polygon.use_smooth = True
            base = [subject.matrix_world @ vertex.co for vertex in subject.data.vertices]
            metadata = {}
            if holdout:
                vpath = upstream / "data" / "vertices" / f"{variant}_verts.json"
                base = [Vector(p) for p in json.loads(vpath.read_text())]
                assert len(base) == len(subject.data.vertices)
                joint_dir = upstream / "data" / "joints"
                keys = json.loads((joint_dir / f"{family}_joints.json").read_text())
                offsets = json.loads((joint_dir / f"{family}_joints_offset.json").read_text())

                def anchor(key):
                    return sum((base[i] for i in keys[key]), Vector()) / len(keys[key]) + Vector(offsets.get(key, [0, 0, 0]))

                selected = {name: [anchor(f"{name}_head"), anchor(f"{name}_tail")]
                            for part in ("upperarm", "lowerarm", "thigh", "calf", "hand", "foot")
                            for side in ("L", "R") for name in [f"{part}_{side}"]}
                pivot = selected["lowerarm_L"][0].copy()
                from mathutils import Matrix
                sign = 1 if pivot.x > 0 else -1
                rotation = Matrix.Rotation(math.radians(-sign * bend), 3, "Y")

                def articulated(point):
                    ramp = max(0.0, min(1.0, (sign * (point.x - pivot.x) + .02) / .075))
                    return point.lerp(pivot + rotation @ (point - pivot), ramp * ramp * (3 - 2 * ramp))

                if bend:
                    base = [articulated(point) for point in base]
                    selected = {name: [articulated(p) for p in points] for name, points in selected.items()}
                floor = min(point.z for point in base)
                metadata = {"identity": variant, "left_forearm_bend_deg": bend,
                            "source_vertices_sha256": hashlib.sha256(vpath.read_bytes()).hexdigest(),
                            "joint_anchors": {name: [[p.x, p.y, p.z - floor] for p in points]
                                              for name, points in selected.items()}}
            low = min(v.z for v in base)
            high = max(v.z for v in base)
            for vertex, p in zip(subject.data.vertices, base):
                h = (p.z - low) / (high - low)
                torso = math.exp(-((h - .58) / .13) ** 2)
                central = math.exp(-(p.x / .25) ** 4)
                if variant == "wide":
                    p.x *= 1 + .28 * torso * central
                    p.y *= 1 + .58 * torso * central
                if variant == "asymmetric":
                    p.x += .065 * math.exp(-((h - .67) / .16) ** 2)
                    p.y += .08 * math.exp(-((h - .65) / .12) ** 2)
                vertex.co = (p.x, p.y, p.z - low)
            subject.matrix_world.identity()
            center = Vector((0, 0, (high - low) / 2))
            output = destination / (f"{body.name}_{variant}" + (f"_bend{bend}" if holdout else ""))
            output.mkdir(exist_ok=True)
            mesh = {"vertices": [list(v.co) for v in subject.data.vertices],
                    "faces": [list(p.vertices) for p in subject.data.polygons]}
            mesh_path = output / "mesh.json"
            mesh_path.write_text(json.dumps(mesh))
            rows = []
            for yaw in (*range(0, 360, 45), 22.5, 112.5):
                angle = math.radians(yaw)
                camera.location = center + Vector((4 * math.sin(angle), -4 * math.cos(angle), 0))
                camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
                bpy.context.view_layer.update()
                path = output / f"yaw-{yaw:g}.png"
                scene.render.filepath = str(path.resolve())
                bpy.ops.render.render(write_still=True)
                projected = [world_to_camera_view(scene, camera, v.co) for v in subject.data.vertices]
                assert all(0 < p.x < 1 and 0 < p.y < 1 and p.z > 0 for p in projected)
                rows.append({"file": path.name,
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                             "yaw": yaw, "held_out": yaw % 45 != 0,
                             "camera_to_world": [list(row) for row in camera.matrix_world]})
            (output / "manifest.json").write_text(json.dumps({
                "subject": output.name, "source_family": body.name,
                "units": "meters", "coordinates": "Blender Z up, -Y frontal, floor Z=0",
                "mask": "PNG alpha > 127", "camera": "orthographic", "ortho_scale_m": 2.16,
                "size": [384, 384], "mesh_sha256": hashlib.sha256(mesh_path.read_bytes()).hexdigest(),
                "material_rgb": [.48, .27, .18], **metadata, "images": rows,
            }, indent=2) + "\n")
            bpy.data.objects.remove(subject, do_unlink=True)


main()
